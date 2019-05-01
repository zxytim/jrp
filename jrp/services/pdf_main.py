from jrp import db
from .pdf import (
    update_pdf_data, update_pdf_thumbnail, update_pdf_text,
    sweep_db)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(dest='task', 
                        choices=[
                            'update_pdf_db', 
                            'update_pdf_thumbnail_db',
                            'update_pdf_text_db',
                        ])
    parser.add_argument('--rq', action='store_true')
    args = parser.parse_args() 

    setting = {
        'update_pdf_db': {
            'keys_db': db.arxiv_db,
            'func': update_pdf_data, 
        },
        'update_pdf_thumbnail_db': {
            'keys_db': db.pdf_db,
            'func': update_pdf_thumbnail,
        },
        'update_pdf_text_db': {
            'keys_db': db.pdf_db,
            'func': update_pdf_text,
        }
    }[args.task]

    func, keys_db = setting['func'], setting['keys_db']

    queue = None
    if args.rq:
        import rq
        queue = rq.Queue(connection=db.redis)
    sweep_db(func, keys_db, queue=queue)
