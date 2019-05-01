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
            area = '|'.join([t['term'] for t in r['tags']])
            print(r['id'], area, r['title'].replace('\n ', ''), r['authors'])
            if not ArxivPaper.exists(id=r['id']):
                ArxivPaper(id=r['id'], guidislink=r['guidislink'],
                           updated=dateutil.parser.parse(r['updated']), 
                           published=dateutil.parser.parse(r['published']),
                           title=r['title'].replace('\n ', ''),
                           title_detail=r['title_detail'],
                           summary=r['summary'].replace('\n', ' ').replace('   ', '\n'),
                           summary_detail=r['summary_detail'],
                           authors=r['authors'],
                           author=r['author'],
                           author_detail=r['author_detail'],
                           arxiv_comment=str(r['arxiv_comment']),
                           links=r['links'],
                           arxiv_primary_category=r['arxiv_primary_category'],
                           tags=r['tags'],
                           pdf_url=r['pdf_url'],
                           affiliation=r['affiliation'],
                           journal_reference=str(r['journal_reference']),
                           doi=str(r['doi']),
                           data=r)
    
    
if __name__ == '__main__':
    main()

