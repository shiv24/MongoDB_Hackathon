"""Mongo client. Import `db` from here; only repo/ should touch db.lessons."""
from pymongo import MongoClient
from app import config

client = MongoClient(config.MONGODB_URI) if config.MONGODB_URI else None
db = client[config.MONGODB_DB] if client else None
