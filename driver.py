#!/usr/bin/env python3

import os
from jrp.db import ArxivPaper
import datetime
import dateutil.parser

import arxiv
from pony.orm import select, db_session


def main():
    query = 'cat:cs.CV+OR+cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.NE+OR+cat:stat.ML'.replace('+', ' ')
    rst = arxiv.query(query, sort_by='lastUpdatedDate', start=0, max_results=100)
    with db_session:
        for r in rst:
            if not ArxivPaper.exists(id=r['id']):
                ArxivPaper(id=r['id'], guidislink=r['guidislink'],
                           updated=dateutil.parser.parse(r['updated']), data=r)
    
    
if __name__ == '__main__':
    main()

