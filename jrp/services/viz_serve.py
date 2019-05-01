from sqlitedict import SqliteDict
import argparse
from flask import Flask, send_file
import io
from tabulate import tabulate
import re


def main():
    from jrp import db
    # define flask app
    app = Flask(__name__)

    @app.route('/')
    def home():
        from .pdf import get_num_thumbnails, get_thumbnail_key

        keys = list(db.pdf_db.keys())
        keys = keys[-100:]

        data = [
            [
                k,  # key
                db.arxiv_db[k].title,  # title
                ', '.join(db.arxiv_db[k].authors),  # authors
                '<a href="/pdf/{}">PDF</a>'.format(k),  # pdf
                # thumbnail
                ''.join([
                    '<img src="/thumbnail/{}">'.format(get_thumbnail_key(k, i))
                    for i in range(get_num_thumbnails(k))
                ])
            ]
            for k in keys]
        return tabulate(data, tablefmt='html')

    @app.route('/pdf/<path:path>')
    def pdf_download(path):
        return send_file(io.BytesIO(db.pdf_db[path]), mimetype='application/pdf')

    @app.route('/thumbnail/<path:path>')
    def thumbnail(path):
        return send_file(io.BytesIO(db.pdf_thumbnail_db[path]), mimetype='image/png')

    app.run()


if __name__ == '__main__':
    main()
