import io
import time
import itertools
import collections
import traceback
import functools
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

        key_it = iter(keys)
        results = []

        def push_next_key():
            """
            :return: True if succeed, otherwise False
            """
            try:
                id = next(key_it)
                results.append(queue.enqueue(func, id, job_timeout=600))
                return True
            except StopIteration:
                return False

        counter = collections.Counter()

        def wait_one_round(tq):
            filter_results = (
                lambda *whats, complement=False:
                [r for r in results if (r.status in whats) ^ complement]
            )
            jobs_done = filter_results(JobStatus.FINISHED, JobStatus.FAILED)
            counter.update([r.status for r in jobs_done])

            jobs_undone = filter_results(JobStatus.FINISHED, JobStatus.FAILED, complement=True)
            cur_counter = counter.copy()
            cur_counter.update([r.status for r in jobs_undone])

            tq.desc = ' '.join(
                '{}={}'.format(k, v)
                for k, v in sorted(cur_counter.items())
            )

            tq.update(len(jobs_done))
            results.clear()
            results.extend(jobs_undone)

            while len(results) < buf_size:
                if not push_next_key():
                    return False
            return True

        tq = tqdm(total=len(keys))
        while wait_one_round(tq):
            time.sleep(1)


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
            j.format = "jpg"
            j.transform(resize="x{}".format(config.PDF_THUMBNAIL_SIZE))

            bio = io.BytesIO()
            j.save(bio)
            img_data = bio.getvalue()

            rst[idx] = img_data
        pdf_imgs.close()
    finally:
        shutil.rmtree(tmpdir)

    return rst


def pdf_data_to_thumbnails_by_preview_generator(
        pdf_data, page=None,
        width_max=256,
        height_max=256):
    """A more robust preview generator than imagemagick (wand).
    
    :param page: an int for one page or a list of ints for multiple pages

    :return: dict map from page number to encoded image of that page.
    """
    # Installation:
    #    - pip install preview-generator
    #    - pakges to install: perl-image-exiftool, inskcape, scribus
    # Testcase:
    #    - http://arxiv.org/abs/1612.01033v2
    #    - where preview_generator succeed but wand failed.


    if not isinstance(page, (tuple, list)):
        page_list = [page]
    else:
        page_list = page

    if page_list is None:
        page_list = list(range(num_pages))

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
        for page in page_list: 
            if not (0 <= page < num_pages):
                continue
            preview_path = manager.get_jpeg_preview(
                pdf_path,
                width=width_max,
                height=height_max,
                page=page)
            with open(preview_path, 'rb') as f:
                rst[page] = f.read()
    finally:
        shutil.rmtree(cache_dir)

    return rst


def pdf_data_to_thumbnails_by_qpdf(pdf_data):
    # `qpdf` seems quite robust at reading PDF files than other libraries.  It is
    # the last-resort we have: splitting pdf into a set of
    # one-page pdfs, and then creating thumbnails one-by-one.
    # `qpdf` can be install via system package manager
    from plumbum.cmd import qpdf

    tempdir = tempfile.mkdtemp(prefix='qpdf-temp')

    def make_tempfile():
        fd, path = tempfile.mkstemp(dir=tempdir)
        os.close(fd)
        return path

    try:
        pdf_path = make_tempfile()
        with open(pdf_path, 'wb') as f:
            f.write(pdf_data)

        # retcode=3: suppress error of
        #     qpdf: operation succeeded with warnings; resulting file may have some problems
        retcode = (0, 3)
        num_pages = int(qpdf('--show-npages', pdf_path, retcode=retcode).strip())

        pdf_pages = {}
        for page in range(min(num_pages, config.NUM_THUMBNAIL_PAGE)):
            page_out = make_tempfile()
            qpdf('--pages', pdf_path, '{page}-{page}'.format(page=page+1),
                 '--', pdf_path, page_out, retcode=retcode)

            pdf_pages[page] = page_out

        rst = {}
        for page, path in sorted(pdf_pages.items()):
            with open(path, 'rb') as f:
                out = pdf_data_to_thumbnails(f.read(), use_last_resort=False)

            assert len(out) == 1, (len(out), page, path)
            rst[page] = list(out.values())[0]

        return rst
    finally:
        shutil.rmtree(tempdir)


def pdf_data_to_thumbnails(pdf_data, use_last_resort=True):
    pdf_thumbnailing_funcs = [
        functools.partial(
            pdf_data_to_thumbnails_by_preview_generator,
            width_max=config.PDF_THUMBNAIL_SIZE,
            height_max=config.PDF_THUMBNAIL_SIZE,
            page=list(range(config.NUM_THUMBNAIL_PAGE)),
        ),
        pdf_data_to_thumbnails_by_imagemagick,
    ]

    if use_last_resort:
        pdf_thumbnailing_funcs.append(pdf_data_to_thumbnails_by_qpdf)

    exceptions = []
    for func in pdf_thumbnailing_funcs:
        try:
            return func(pdf_data)
        except Exception as e:
            traceback.print_exc()
            exceptions.append(e)
    else:
        raise ValueError('Error generating thumbnails: ', exceptions)


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
