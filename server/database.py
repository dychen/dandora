import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

# Initialize
ROOT_DIR = os.environ['ROOT_DIR']

DB_ENGINE = create_engine('sqlite:///%s/tmp.db' % ROOT_DIR,
                          convert_unicode=True)
DB_SESSION = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=DB_ENGINE))
BASE = declarative_base()
BASE.query = DB_SESSION.query_property()
print BASE

class Song(BASE):
    __tablename__ = 'songs'

    id = Column(Integer, primary_key=True)
    track_id = Column(String(18), unique=True)
    title = Column(String(120))

    def __init__(self, track_id=None, title=None):
        self.track_id = track_id
        self.title = title

    def __repr__(self):
        return '<Song %r>' % (self.title)

def init_db():
    # import all modules here that might define models so that
    # they will be registered properly on the metadata.  Otherwise
    # you will have to import them first before calling init_db()
    BASE.metadata.create_all(bind=DB_ENGINE)

