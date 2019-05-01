import io
import time
import collections

import requests
import arxiv
import magic  # python-magic

import pdftotext
from wand.image import Image
from tqdm import tqdm

from jrp import db, config


def sweep_db(func, keys, *, queue=None, num_retry_max=3):
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

        results = [queue.enqueue(func, id, job_timeout=600) for id in keys]

        total = len(results)

        tq = tqdm(total=total)
        prev = total
        fq = FailedQueue(queue.connection)

        while True:
            new_results = [r for r in results if r.status != JobStatus.FINISHED]
            now = len(new_results)
            print(len(new_results), len(failed_jobs))
            if len(new_results) - len(failed_jobs) == 0:
                break
            tq.update(n=prev - now)

            results = new_results
            prev = now

            fjobs = fq.get_jobs()
            fjobs = [j for j in fjobs if j.args[0] not in failed_jobs]
            if len(fjobs):
                print("Found {} failed jobs. Try requeueing.".format(len(fjobs)))
                for j in fjobs:
                    cnt = fjob_retry_count[j.args[0]]
                    if cnt == num_retry_max:
                        print(
                            "Job `{}`:`{}` failed {} times. Abort trying".format(
                                j.id, j.args[0], cnt
                            )
                        )
                        failed_jobs.add(j.args[0])
                        continue
                    fq.requeue(j.id)
                    fjob_retry_count[j.args[0]] = cnt + 1

            time.sleep(1)


def requests_get(url):
    return config.requests_get(url)


# download pdf
def update_pdf_data(id):
    if id in db.pdf_db:
        print("{}: exists".format(id))
        return False

    obj = db.arxiv_db[id]
    if "pdf_url" not in obj:
        db.pdf_db[id] = None
        print("{}: no pdf_url".format(id))
        return False

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
        print("{}: downloaded".format(id))
        return True

    if mime.startswith("text"):
        if r.text.find("PDF unavailable") >= 0:
            db.pdf_db[id] = None
            print("{}: PDF unavailable".format(id))
            return True

    s = "{}: not pdf, but `{}`".format(id, mime)
    print(s)
    raise Exception(s)


# thumbnail
def get_thumbnail_key(id, idx):
    return id + "-{:03d}".format(idx)


def get_num_thumbnails(id):
    for i in range(config.NUM_THUMBNAIL_PAGE):
        if get_thumbnail_key(id, i) not in db.pdf_thumbnail_db:
            return i
    return config.NUM_THUMBNAIL_PAGE


def pdf_data_to_thumbnails(pdf_data):
    """
    :return: dict: index -> png_data
    """
    rst = {}
    with Image(blob=pdf_data) as pdf_imgs:
        for idx, i in enumerate(pdf_imgs.sequence[: config.NUM_THUMBNAIL_PAGE]):
            j = Image(image=i)
            j.format = "png"
            j.transform(resize="x180")

            bio = io.BytesIO()
            j.save(bio)
            img_data = bio.getvalue()

            rst[idx] = img_data

    return rst


def update_pdf_thumbnail_given_pdf_data(id, pdf_data):
    for k, v in pdf_data_to_thumbnails(db.pdf_db[id]).items():
        db.pdf_thumbnail_db[get_thumbnail_key(id, k)] = v


def update_pdf_thumbnail(id):
    if id in db.pdf_thumbnail_db:
        return False
    assert id in db.pdf_db, id
    return update_pdf_thumbnail_given_pdf_data(id, db.pdf_db[id])


# generate pdf text for search
def pdf_data2text(pdf_data):
    with io.BytesIO(pdf_data) as f:
        return "".join(pdftotext.PDF(f)).strip()


def update_pdf_text(id):
    if id in db.pdf_text_db:
        return False
    assert id in db.pdf_db, id
    text = pdf_data2text(db.pdf_db[id])
    db.pdf_text_db[id] = text

    doc = db.es.get(index="arxiv", id=id)
    body = doc["_source"]
    body["pdf_text"] = text
    db.es.index(index="arxiv", body=body, id=id)

    return True
