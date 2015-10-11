import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, UnicodeText, ForeignKey

# Initialize
ROOT_DIR = os.environ['ROOT_DIR']

DB_ENGINE = create_engine('sqlite:///%s/pandora.db' % ROOT_DIR,
                          convert_unicode=True)
DB_SESSION = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=DB_ENGINE))
BASE = declarative_base()
BASE.query = DB_SESSION.query_property()
print 'Initialized database session'

class Song(BASE):
    __tablename__ = 'songs'

    id = Column(Integer, primary_key=True)
    song_id = Column(String(18), unique=True, index=True)
    title = Column(UnicodeText(200), index=True)
    artist = Column(UnicodeText(100))

    def __init__(self, song_id=None, title=None, artist=None):
        self.song_id = song_id
        self.title = title
        self.artist = artist

    def __repr__(self):
        return '<Song %r>' % (self.title)

class User(BASE):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(50), index=True)
    token = Column(String(100))
    secret = Column(String(100))

class Playlist(BASE):
    __tablename__ = 'playlists'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
