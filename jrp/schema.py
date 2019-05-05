from datetime import datetime
from pony.orm import (
    Database, PrimaryKey, Required,
    Optional, Json, Set, buffer,
    StrArray,
)
from pony import orm


from .db import aio_db as db
from . import config


class Paper(db.Entity):
    id = PrimaryKey(int, auto=True)
    paper_id = Required(str, unique=True, index=True)
    affiliation = Optional(str, nullable=True)
    arxiv_comment = Optional(str, nullable=True)
    arxiv_primary_category_scheme = Optional(str)
    arxiv_primary_category_term = Optional(str)
    author = Optional(str)
    author_detail_name = Optional(str)
    authors = Optional(StrArray)
    doi = Optional(str, nullable=True)
    guidislink = Optional(bool)
    journal_reference = Optional(str, nullable=True)
    links = Optional(Json)
    pdf_text = Optional(str, nullable=True)
    pdf_url = Optional(str)
    published = Optional(datetime)
    summary = Optional(str)
    summary_detail_base = Optional(str)
    summary_detail_language = Optional(str, nullable=True)
    summary_detail_type = Optional(str)
    summary_detail_value = Optional(str)
    tags = Optional(StrArray)
    title = Optional(str)
    title_detail_base = Optional(str)
    title_detail_language = Optional(str, nullable=True)
    title_detail_type = Optional(str)
    title_detail_value = Optional(str)
    updated = Optional(datetime)
    pdf = Optional('PDF')
    pdf_text = Optional('PDFText')
    version = Optional(int)
    genesis_id = Optional(str)
    user_paper_status = Set('UserPaperStatus')


class PDF(db.Entity):
    id = PrimaryKey(int, auto=True)
    paper_id = Required(str, unique=True, index=True)
    data = Optional(buffer, nullable=True)
    paper = Optional(Paper)
    thumbnails = Set('Thumbnail')


class PDFText(db.Entity):
    id = PrimaryKey(int, auto=True)
    paper_id = Required(str, unique=True, index=True)
    text = Optional(str, nullable=True)
    paper = Optional(Paper)


class Thumbnail(db.Entity):
    id = PrimaryKey(int, auto=True)
    paper_id = Required(str, index=True)
    pdf = Required(PDF)
    page = Optional(int)
    data = Optional(buffer)


class User(db.Entity):
    id = PrimaryKey(int, auto=True)
    username = Optional(str)
    user_paper_status = Set('UserPaperStatus')


class UserPaperStatus(db.Entity):
    id = PrimaryKey(int, auto=True)
    user = Required(User)
    paper = Required(Paper)
    score = Optional(float)
    is_read = Optional(bool)


@db.on_connect(provider='sqlite')
def db_on_connect(db, connection):
    cursor = connection.cursor()
    cursor.execute('PRAGMA journal_mode=WAL')
    # cursor.execute('PRAGMA case_sensitive_like = OFF')


db.bind(provider='sqlite',
        filename=config.AIO_DB_PATH,
        create_db=True)

db.generate_mapping(create_tables=True)
