import io
import time

import requests
import arxiv

import pdftotext
from wand.image import Image
from tqdm import tqdm

from jrp import db


def sweep_db(func, db, *, queue=None):
    """
    :param queue: rq.Queue object or None
    """
    keys = list(db.keys())
    if queue is None:
        for id in tqdm(keys):
            func(id)
    else:
        from rq.job import JobStatus

        results = [
            queue.enqueue(func, id, job_timeout=600)
            for id in keys
        ]
        status_set = [JobStatus.FINISHED, JobStatus.FAILED, JobStatus.DEFERRED]
        for r in tqdm(results):
            while r.status not in status_set:
                time.sleep(0.01)
            

# download pdf
def update_pdf_data(id):
    if id in db.pdf_db:
        return False
    obj = db.arxiv_db[id]
    if 'pdf_url' not in obj:
        db.pdf_db[id] = None
        return False

    db.pdf_db[id] = requests.get(obj['pdf_url']).content
    return True


def get_thumbnail_key(id, idx):
    return id + '-{:03d}'.format(idx)


def get_num_thumbnails(id):
    for i in range(config.NUM_THUMBNAIL_PAGE):
        if get_thumbnail_key(id, i) not in db.pdf_thumbnail_db:
            return i
    return config.NUM_THUMBNAIL_PAGE


# generate thumbnail
def update_pdf_thumbnail(id):
    if id in db.pdf_thumbnail_db:
        return False
    pdf_data = db.pdf_db[id]
    for idx, i in enumerate(
            Image(blob=pdf_data).sequence[:config.NUM_THUMBNAIL_PAGE]):
        j = Image(image=i)
        j.format = 'png'
        j.transform(resize='x180')

        bio = io.BytesIO()
        j.save(bio)
        img_data = bio.getvalue()

        key = get_thumbnail_key(id, idx)
        db.pdf_thumbnail_db[key] = img_data


# generate pdf text for search
def pdf2text(pdf_path):
    return '\n\n'.join(pdftotext.PDF(pdf_path))


def update_pdf_text(id):
    pass

