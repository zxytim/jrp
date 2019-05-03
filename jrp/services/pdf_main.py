from jrp import db
from .pdf import update_pdf_data, update_pdf_thumbnail, update_pdf_text, sweep_db
from tqdm import tqdm


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        dest="task",
        choices=["update_pdf_db", "update_pdf_thumbnail_db", "update_pdf_text_db"],
    )
    parser.add_argument("--rq", action="store_true")
    parser.add_argument("--top-keys", default=10000, type=int)
    args = parser.parse_args()

    def get_arxiv_db_keys_by_updated_descending():
        kvs = sorted([(k, v['updated'])
                      for k, v in db.arxiv_db.items()],
                     key=lambda x: x[1],
                     reverse=True)
        return [x[0] for x in kvs]


    setting = {
        "update_pdf_db": {
            "source_keys_getter": get_arxiv_db_keys_by_updated_descending,
            "target_db": db.pdf_db,
            'workload_type': 'io',
            "func": update_pdf_data,
        },
        "update_pdf_thumbnail_db": {
            "source_keys_getter": db.pdf_db.keys,
            "target_db": db.pdf_thumbnail_db,
            'workload_type': 'computation',
            "func": update_pdf_thumbnail,
        },
        "update_pdf_text_db": {
            "source_keys_getter": db.pdf_db.keys,
            "target_db": db.pdf_text_db,
            'workload_type': 'computation',
            "func": update_pdf_text,
        },
    }[args.task]

    func, source_keys_getter, target_db, workload_type = (
        setting["func"],
        setting["source_keys_getter"],
        setting["target_db"],
        setting['workload_type'],
    )

    queue = None
    if args.rq:
        import rq

        queue = rq.Queue(name=workload_type, connection=db.redis)

    ks0 = list(tqdm(source_keys_getter(), desc='get_source_keys'))
    ks1 = list(tqdm(target_db.keys(), desc='get_target_db_keys'))
    if "update_pdf_thumbnail_db" in args.task:
        ks1 = set("-".join(k.split("-")[:-1]) for k in ks1)

    ks1_set = set(ks1)
    keys = [k for k in ks0 if k not in ks1_set][:args.top_keys]
    sweep_db(func, keys, queue=queue)
