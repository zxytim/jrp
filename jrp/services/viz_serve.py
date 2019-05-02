from sqlitedict import SqliteDict
import argparse
from flask import Flask, send_file
import io
from tabulate import tabulate
import re
from jrp import db
import random
import magic


def get_db_stats():
    # arxiv db
    num_paper_entries = len(db.arxiv_db)

    # pdf_db
    num_papers_with_pdf = len(db.pdf_db)

    # pdf_text_db
    num_pdf_text = len(db.pdf_text_db)

    # pdf_thumbnail_db
    thumbnail_keys = list(db.pdf_thumbnail_db.keys())
    num_thumbnails = len(thumbnail_keys)
    num_thumbnail_paper = len(set("-".join(k.split("-")[:-1]) for k in thumbnail_keys))

    return {
        'num_paper_entries': num_paper_entries,
        'num_papers_with_pdf': num_papers_with_pdf,
        'num_pdf_text': num_pdf_text,
        'num_thumbnails': num_thumbnails,
        'num_paper_with_thumbnail': num_thumbnail_paper,
    }


def main():
    # define flask app
    app = Flask(__name__)

    @app.route("/")
    def home():
        from .pdf import get_num_thumbnails, get_thumbnail_key

        stats_str = tabulate(sorted(get_db_stats().items()),
                             tablefmt='html')

        keys = list(db.pdf_db.keys())
        random.shuffle(keys)
        keys = keys[:100]

        data = [
            [
                k,  # key
                db.arxiv_db[k].title,  # title
                ", ".join(db.arxiv_db[k].authors),  # authors
                '<a target="_blank" href="/pdf/{}">PDF</a>'.format(k),  # pdf
                # thumbnail
                "".join(
                    [
                        '<img src="/thumbnail/{}">'.format(get_thumbnail_key(k, i))
                        for i in range(get_num_thumbnails(k))
                    ]
                ),
            ]
            for k in keys
        ]

        viz_str = tabulate(data, tablefmt="html")

        return stats_str + '<hr />' + viz_str

    @app.route("/pdf/<path:path>")
    def pdf_download(path):
        return send_file(io.BytesIO(db.pdf_db[path]), mimetype="application/pdf")

    @app.route("/thumbnail/<path:path>")
    def thumbnail(path):
        data = db.pdf_thumbnail_db[path]
        return send_file(io.BytesIO(data), mimetype=magic.from_buffer(data, mime=True))

    app.run()


if __name__ == "__main__":
    main()
