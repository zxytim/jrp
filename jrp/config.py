import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')

# arxiv crawler setting
ARXIV_QUERY = "cat:cs.CV+OR+cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.NE+OR+cat:stat.ML".replace(
    "+", " "
)
ARIXV_DB_PATH = os.path.join(DATA_DIR, "arixv.sqlite")
ARXIV_UPDATE_INTERVAL = 4 * 60 * 60  # 4 hours

# pdf db
PDF_DB_PATH = os.path.join(DATA_DIR, "pdf.sqlite")
PDF_THUMBNAIL_DB_PATH = os.path.join(DATA_DIR, 'pdf_thumbnail.sqlite')
NUM_THUMBNAIL_PAGE = 8

# Elasticsearch settings
ES_HOSTS = ['localhost']

# redis settings
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
