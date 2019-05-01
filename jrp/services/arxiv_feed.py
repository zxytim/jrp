#!/usr/bin/env python3

import os
from tqdm import tqdm
import time
import datetime
import dateutil.parser
import sqlitedict

from jrp import db, config

import arxiv


class StopCrawling(Exception):
    pass


def save_arxiv_object(r):
    id = r["id"]

    area = "|".join([t["term"] for t in r["tags"]])
    print(r["id"], area, r["title"].replace("\n ", ""), r["authors"])

    tags = [t["term"] for t in r["tags"]]
    body = dict(
        id=id,
        guidislink=r["guidislink"],
        updated=dateutil.parser.parse(r["updated"]),
        published=dateutil.parser.parse(r["published"]),
        title=r["title"].replace("\n ", ""),
        title_detail=r["title_detail"],
        summary=r["summary"].replace("\n", " ").replace("   ", "\n"),
        summary_detail=r["summary_detail"],
        authors=r["authors"],
        author=r["author"],
        author_detail=r["author_detail"],
        arxiv_comment=str(r["arxiv_comment"]),
        links=r["links"],
        arxiv_primary_category=r["arxiv_primary_category"],
        tags=tags,
        pdf_url=r["pdf_url"],
        affiliation=r["affiliation"],
        journal_reference=str(r["journal_reference"]),
        doi=str(r["doi"]),
    )
    db.es.index(index="arxiv", body=body, id=id)
    db.arxiv_db[id] = r


def iter_arixv_objects(query, total=1000, stride=1000, sort_order="descending"):
    """
    :param sort_order: 'descending' or 'ascending'
    """
    for i in range(0, total, stride):
        start = i
        rst = arxiv.query(
            query,
            sort_by="lastUpdatedDate",
            sort_order=sort_order,
            start=start,
            max_results=min(total, stride),
        )

        if len(rst) == 0:
            break

        yield from rst


def populate_db():
    # iter all existing papers, from old to new (to prevent from affecting by
    # new updates while populating)
    for r in tqdm(
        iter_arixv_objects(config.ARXIV_QUERY, total=100000000, sort_order="ascending")
    ):
        save_arxiv_object(r)


def update_db():
    total = 10000
    while True:
        try:
            for r in tqdm(iter_arixv_objects(config.ARXIV_QUERY, total), total=total):
                if r.id in db.arxiv_db:
                    raise StopCrawling(r.id)
                save_arxiv_object(r)
        except StopCrawling as e:
            print("Stop crawling: {} has been crawled already".format(e.args[0]))

        print("sleep for {} seconds".format(config.ARXIV_UPDATE_INTERVAL))
        time.sleep(config.ARXIV_UPDATE_INTERVAL)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(dest="task", choices={"update", "populate"})
    args = parser.parse_args()

    dict(update=update_db, populate=populate_db)[args.task]()