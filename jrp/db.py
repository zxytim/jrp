from sqlitedict import SqliteDict
from elasticsearch import Elasticsearch
from redis import StrictRedis

from . import config

arxiv_db = SqliteDict(config.ARIXV_DB_PATH, autocommit=True)

es = Elasticsearch(hosts=config.ES_HOSTS)

pdf_db = SqliteDict(config.PDF_DB_PATH, autocommit=True)
pdf_thumbnail_db = SqliteDict(config.PDF_THUMBNAIL_DB_PATH, autocommit=True)
pdf_text_db = SqliteDict(config.PDF_TEXT_DB_PATH, autocommit=True)

redis = StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT)
