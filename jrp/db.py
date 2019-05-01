from pony.orm import Database, Required, Optional, Set, PrimaryKey, Json, IntArray, StrArray
from datetime import datetime
from . import config


db = Database()


class ArxivPaper(db.Entity):
    id = PrimaryKey(str)
    guidislink = Optional(bool)
    updated = Optional(datetime)
    published = Optional(datetime)

    title = Optional(str)
    title_detail = Optional(Json)

    summary = Optional(str)
    summary_detail = Optional(Json)

    authors = Optional(StrArray)
    author = Optional(str)
    author_detail = Optional(Json)

    arxiv_comment = Optional(str)
    links = Optional(Json)
    arxiv_primary_category = Optional(Json)

    tags = Optional(Json)

    pdf_url = Optional(str)
    affiliation = Optional(str)
    journal_reference = Optional(str)
    doi = Optional(str)

    data = Optional(Json)


def init_db(db_file):
    db.bind(provider='sqlite', filename=db_file, create_db=True)
    db.generate_mapping(create_tables=True)


init_db(config.DB_FILE)
