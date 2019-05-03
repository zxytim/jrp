#!/usr/bin/env python
import argparse
import os

from jrp.services.pdf import (
    pdf_data2text, update_pdf_data,  update_pdf_text, update_pdf_thumbnail,
    pdf_data_to_thumbnails,
)

from jrp import db

def dump_pdf(id, path):
    with open(path, 'wb') as f:
        f.write(db.pdf_db[id])


def pdf2thumbnail(pdf_path, out_prefix):
    with open(pdf_path, 'rb') as f:
        thumbnails = pdf_data_to_thumbnails(f.read())
    from IPython import embed; embed() 

    for k, v in sorted(thumbnails.items()):
        out_path = out_prefix + str(k) + '.jpg'
        with open(out_path, 'wb') as f:
            f.write(v)


def main():
    task_func_list = [
        update_pdf_data,
        update_pdf_text,
        update_pdf_thumbnail,
        dump_pdf,
        pdf2thumbnail,
    ]
    task_name2func = {
        f.__name__: f for f in task_func_list
    }
    parser = argparse.ArgumentParser()
    parser.add_argument(dest='task', choices=task_name2func)
    parser.add_argument(dest='args', nargs='+')
    args = parser.parse_args() 

    print(task_name2func[args.task](*args.args))


if __name__ == '__main__':
    main()

    

