from sqlitedict import SqliteDict
from elasticsearch import Elasticsearch
from redis import StrictRedis
import functools
from pony.orm import Database

import oss2
from . import config

journal_mode = 'WAL'  # Write-Ahead Logging
sdict = functools.partial(SqliteDict, autocommit=True, journal_mode=journal_mode)

arxiv_db = sdict(config.ARIXV_DB_PATH)

es = Elasticsearch(hosts=config.ES_HOSTS)

pdf_db = sdict(config.PDF_DB_PATH)
pdf_thumbnail_db = sdict(config.PDF_THUMBNAIL_DB_PATH)
pdf_text_db = sdict(config.PDF_TEXT_DB_PATH)

aio_db = Database()

oss_arixv_auth = oss2.Auth(config.OSS2_ACCESS_KEY_ID, config.OSS2_ACCESS_KEY_SECRET)   
oss_arxiv_bucket = oss2.Bucket(oss_arixv_auth, config.OSS2_ARXIV_ENDPOINT,
                               config.OSS2_ARXIV_BUCKET_NAME)

redis = StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT)
