from pony.orm import Database, Required, Optional, Set, PrimaryKey, Json
from datetime import datetime
from . import config


db = Database()


class ArxivPaper(db.Entity):
    id = PrimaryKey(str)
    guidislink = Optional(bool)
    updated = Optional(datetime)
    data = Optional(Json)


def init_db(db_file):
    db.bind(provider='sqlite', filename=db_file, create_db=True)
    db.generate_mapping(create_tables=True)


init_db(config.DB_FILE)
