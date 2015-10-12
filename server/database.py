import argparse
import os

from sqlalchemy import create_engine, Column, Integer, String, Unicode, \
    ForeignKey, UniqueConstraint
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Initialize
DB_ENGINE = create_engine(os.environ['DATABASE_URL'], convert_unicode=True)
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
    title = Column(Unicode(500), index=True)
    artist = Column(Unicode(500))

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
    name = Column(Unicode(200))
    __table_args__ = (UniqueConstraint('user_id', 'name'),)

def init_db():
    print 'Creating database'
    BASE.metadata.create_all(bind=DB_ENGINE)

def seed_db(path):
    print 'Seeding database'
    songs = {}
    print '    Reading song file'
    with open(path) as f:
        for line in f:
            track_id, song_id, artist, song_name = line.strip().split('<SEP>')
            # There may be duplicate entries for songs (multiple tracks per
            # song)
            if song_id not in songs:
                songs[song_id] = (song_id,
                                  unicode(song_name, encoding='utf8'),
                                  unicode(artist, encoding='utf8'))
    print '    Adding to DB transaction'
    for key in songs:
        DB_SESSION.add(Song(*songs[key]))
    print '    Committing to DB'
    DB_SESSION.commit()

def drop_db():
    print 'Dropping database'
    BASE.metadata.drop_all(bind=DB_ENGINE)

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', action='store_const', const=True,
                        help='Initialize database with existing DDL')
    parser.add_argument('--seed', type=str,
                        help='Seed database with data at the target file path')
    parser.add_argument('--drop', action='store_const', const=True,
                        help='Drop all tables in existing database')
    args = parser.parse_args()
    if args.drop:
        drop_db()
    if args.init:
        init_db()
    if args.seed:
        seed_db(args.seed)
