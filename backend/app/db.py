"""Mongo handle. Only modules in app/repo/ should call get_db()."""
from datetime import datetime, timezone
from uuid import uuid4

from pymongo import MongoClient

from app import config

_db = None


def get_db():
    global _db
    if _db is None:
        if not config.MONGODB_URI:
            raise RuntimeError("MONGODB_URI is not set - copy .env.example to .env and fill it in")
        _db = MongoClient(config.MONGODB_URI, appname="promptforge", tz_aware=True)[config.MONGODB_DB]
    return _db


def set_db(db) -> None:
    """Tests inject a mongomock database here."""
    global _db
    _db = db


def new_id() -> str:
    return uuid4().hex


def now() -> datetime:
    return datetime.now(timezone.utc)
