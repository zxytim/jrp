import io
import time
import itertools
import collections
import shutil
import subprocess
import os
import tempfile

import requests
import arxiv
import magic  # python-magic

import pdftotext
from wand.image import Image
from tqdm import tqdm

from jrp import db, config


def sweep_db(func, keys, *, queue=None, num_retry_max=3, buf_size=100):
    """
    :param queue: rq.Queue object or None
    """
    if queue is None:
        for id in tqdm(keys):
            func(id)
    else:
        from rq.job import JobStatus
        from rq.queue import FailedQueue

        fjob_retry_count = collections.defaultdict(int)
        failed_jobs = set()

        key_it = iter(keys)
        results = []

        def push_next_key():
            try:
                id = next(key_it)
                results.append(queue.enqueue(func, id, job_timeout=600))
                return True
            except StopIteration:
                return False

        def push_batch_job():
            """
            :return: where finish on this batch
            """
            for i in range(buf_size):
                if not push_next_key():
                    return True
            return False

        def wait_results_finish():
            filter_results = lambda what: [r for r in results if r.status == what]

            total = len(results)
            tq = tqdm(total=total)
            while True:
                finished_jobs = filter_results(JobStatus.FINISHED)

                # Failed jobs are failed jobs. Recovery of these jobs
                # is not the responsibility here. Recover should be
                # done in higher logic level.
                failed_jobs = filter_results(JobStatus.FAILED)

                jobs_done = len(finished_jobs) + len(failed_jobs)
                if jobs_done == len(results):
                    results.clear()
                    break
                tq.update(jobs_done - tq.n)

                tq.desc = ' '.join('{}={}'.format(k, v)
                for k, v in sorted(
                        collections.Counter([r.status for r in results]).items()
                ))

                time.sleep(1)

        while True:
            no_more_jobs = push_batch_job()
            wait_results_finish()

            if no_more_jobs:
                break


def requests_get(url):
    return config.requests_get(url)


# download pdf
def update_pdf_data(id):
    if id in db.pdf_db:
        s = "{}: exists".format(id)
        print(s)
        return False, s

    obj = db.arxiv_db[id]
    if "pdf_url" not in obj:
        db.pdf_db[id] = None
        db.pdf_db.commit()
        s = "{}: no pdf_url".format(id)
        print(s)
        return False, s

    r = requests_get(obj["pdf_url"])
    data = r.content

    mime = magic.from_buffer(data, mime=True)

    if mime == "application/pdf":
        pdf_text = pdf_data2text(data)

        # Downloading pdf through scraperapi would result in
        # wrong pdf file, which seems contain no text inside.
        if len(pdf_text) == 0:
            # db.pdf_db[id] = 'WRONG_FILE'  # XXX
            raise Exception("{}: WRONG_FILE; try again".format(id))

        db.pdf_db[id] = data
        db.pdf_db.commit()
        s = "{}: downloaded".format(id)
        print(s)
        return True, s

    if mime.startswith("text"):
        if r.text.find("PDF unavailable") >= 0:
            db.pdf_db[id] = None
            db.pdf_db.commit()
            s = "{}: PDF unavailable".format(id)
            print(s)
            return True, s

    s = "{}: not pdf, but `{}`".format(id, mime, data)
    raise Exception(s)


# thumbnail
def get_thumbnail_key(id, idx):
    return id + "-{:03d}".format(idx)


def get_num_thumbnails(id):
    for i in range(config.NUM_THUMBNAIL_PAGE):
        if get_thumbnail_key(id, i) not in db.pdf_thumbnail_db:
            return i
    return config.NUM_THUMBNAIL_PAGE


def pdf_data_to_thumbnails_by_imagemagick(pdf_data):
    """This is quite buggy.
    :return: dict: index -> png_data
    """
    if pdf_data is None:
        return {0: None}

    rst = {}
    tmpdir = tempfile.mkdtemp(prefix='mymagick')
    try:
        os.environ['MAGICK_TMPDIR'] = tmpdir

        pdf_imgs = Image()
        pdf_imgs.read(blob=pdf_data)

        # XXX: There's a known bug that some pdf cannot be read using
        #       constructor, but to use `read` method after construction of
        #       Image. The following code will result in
        #       wand.exceptions.CorruptImageError:
        #               with Image(blob=pdf_data) as pdf_imgs:

        for idx, i in enumerate(pdf_imgs.sequence[: config.NUM_THUMBNAIL_PAGE]):
            j = Image()
            j.read(image=i)
            j.format = "png"
            j.transform(resize="x180")

            bio = io.BytesIO()
            j.save(bio)
            img_data = bio.getvalue()

            rst[idx] = img_data
        pdf_imgs.close()
    finally:
        shutil.rmtree(tmpdir)

    return rst


def pdf_data_to_thumbnails_by_preview_generator(pdf_data):
    """A more robust preview generator than imagemagick (wand).
    """
    # Installation:
    #    - pip install preview-generator
    #    - pakges to install: perl-image-exiftool, inskcape, scribus
    # Testcase:
    #    - http://arxiv.org/abs/1612.01033v2
    #    - where preview_generator succeed but wand failed.

    from preview_generator.manager import PreviewManager

    cache_dir = tempfile.mkdtemp(prefix='preview-cache-')
    try:
        # save pdf
        fd, pdf_path = tempfile.mkstemp(dir=cache_dir)
        os.close(fd)
        with open(pdf_path, 'wb') as f:
            f.write(pdf_data)

        manager = PreviewManager(cache_dir, create_folder=True)
        num_pages = manager.get_page_nb(pdf_path)

        rst = {}
        for page in range(min(num_pages, config.NUM_THUMBNAIL_PAGE)):
            preview_path = manager.get_jpeg_preview(
                pdf_path, width=256, height=256, page=page)
            with open(preview_path, 'rb') as f:
                rst[page] = f.read()
    finally:
        shutil.rmtree(cache_dir)

    return rst


pdf_data_to_thumbnails = pdf_data_to_thumbnails_by_preview_generator


def update_pdf_thumbnail_given_pdf_data(id, pdf_data):
    for k, v in pdf_data_to_thumbnails(db.pdf_db[id]).items():
        db.pdf_thumbnail_db[get_thumbnail_key(id, k)] = v
    db.pdf_thumbnail_db.commit()
    return True, id


def update_pdf_thumbnail(id):
    if id in db.pdf_thumbnail_db:
        return False, id
    assert id in db.pdf_db, id
    return update_pdf_thumbnail_given_pdf_data(id, db.pdf_db[id])


# generate pdf text for search
def pdf_data2text(pdf_data):
    # The commandline tool `pdftotext` generates text that is more search
    # friendly, while the python package `pdftotext` generates text that
    # preserves the layout in original pdf, which is better for text-only-view,
    # but hard to search.
    from plumbum.cmd import pdftotext as pdftotext_exe

    if pdf_data is None:
        return None

    return (pdftotext_exe['-', '-'] << pdf_data)()


def update_pdf_text(id):
    if id in db.pdf_text_db:
        return False, id
    assert id in db.pdf_db, id
    text = pdf_data2text(db.pdf_db[id])
    db.pdf_text_db[id] = text
    db.pdf_text_db.commit()

    doc = db.es.get(index='arxiv', id=id)
    body = doc['_source']
    body['pdf_text'] = text
    db.es.index(index="arxiv", body=body, id=id)

    return True, id
