from contextvars import ContextVar

import peewee
from peewee import Model, MySQLDatabase
from playhouse.migrate import *

from stilio.config import (
    DATABASE_HOST,
    DATABASE_NAME,
    DATABASE_PASSWORD,
    DATABASE_PORT,
    DATABASE_USER,
)

db_state_default = {"closed": None, "conn": None, "ctx": None, "transactions": None}
db_state = ContextVar("db_state", default=db_state_default.copy())


class PeeweeConnectionState(peewee._ConnectionState):
    def __init__(self, **kwargs):
        super().__setattr__("_state", db_state)
        super().__init__(**kwargs)

    def __setattr__(self, name, value):
        self._state.get()[name] = value

    def __getattr__(self, name):
        return self._state.get()[name]


db = MySQLDatabase(
    DATABASE_NAME,
    host=DATABASE_HOST,
    port=int(DATABASE_PORT),
    user=DATABASE_USER,
    password=DATABASE_PASSWORD,
    autorollback=True,
)
db._state = PeeweeConnectionState()


class BaseModel(Model):
    class Meta:
        database = db


@db.connection_context()
def init() -> None:
    from stilio.persistence.constants import MODELS

    db.connect(reuse_if_open=True)
    db.create_tables(MODELS)
    # db.execute_sql("ALTER DATABASE `stilio` CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_520_ci;")
    db.execute_sql("ALTER TABLE `torrent` ENGINE=Mroonga;")
    try:
        db.execute_sql("ALTER TABLE `torrent` ADD FULLTEXT INDEX `files` (`files`);")
    except peewee.OperationalError:
        pass
    if not db.is_closed():
        db.close()
