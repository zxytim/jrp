from sqlitedict import SqliteDict
from elasticsearch import Elasticsearch

from . import config

pdf_db = SqliteDict(config.PDF_DB_PATH, autocommit=True)
arxiv_db = SqliteDict(config.ARIXV_DB_PATH, autocommit=True)

es = Elasticsearch()  # XXX: connect to local host by default (for now)
