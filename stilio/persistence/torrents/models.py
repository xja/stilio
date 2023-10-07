from __future__ import annotations

import datetime as dt
from typing import List, Tuple
from playhouse.mysql_ext import Match

from peewee import (
    BigIntegerField,
    CharField,
    DateTimeField,
    IntegerField,
    TextField,
)

from stilio.persistence.database import BaseModel


class Torrent(BaseModel):
    info_hash = CharField(max_length=40, primary_key=True)
    name = CharField(max_length=512)
    seeders = IntegerField(default=0)
    leechers = IntegerField(default=0)
    files = TextField()
    size = BigIntegerField()
    added_at = DateTimeField(default=dt.datetime.now)

    def __str__(self):
        return self.name

    @classmethod
    def exists(cls, info_hash: bytes):
        return cls.select().where(cls.info_hash == info_hash.hex()).exists()

    @classmethod
    def total_torrent_count(cls) -> int:
        count = cls.select().count()
        return count

    @classmethod
    def search_by_name(
        cls, name: str, limit=None, offset=None
    ) -> Tuple[List["Torrent"], int]:
        # Remove characters that are not considered a "letter"
        cleaned_name = "".join([letter for letter in name if letter.isalpha() or " "])
        keywords = cleaned_name.split()
        queryset = cls.select().where(
            Match(cls.files, ' '.join(f'+"{keyword}"' for keyword in keywords), 'IN BOOLEAN MODE')
        ).order_by(cls.added_at.desc())

        torrent_count = queryset.select().count()
        torrents = (
            queryset.select()
            .order_by(Torrent.added_at.desc())
            .limit(limit)
            .offset(offset)
            .execute()
        )

        return torrents, torrent_count
