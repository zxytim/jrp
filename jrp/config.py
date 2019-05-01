import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# arxiv crawler setting
ARXIV_QUERY = "cat:cs.CV+OR+cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL+OR+cat:cs.NE+OR+cat:stat.ML".replace(
    "+", " "
)
ARIXV_DB_PATH = os.path.join(BASE_DIR, "arixv.sqlite")
ARXIV_UPDATE_INTERVAL = 4 * 60 * 60  # 4 hours

# pdf
PDF_DB_PATH = os.path.join(BASE_DIR, "pdf.sqlite")
