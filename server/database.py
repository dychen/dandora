import argparse
import os

from sqlalchemy import create_engine, Column, Integer, String, Unicode, Float,\
    Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import scoped_session, sessionmaker, relationship, backref
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
    similarities_to = relationship('Similarity',
                                   foreign_keys='Similarity.song1_id',
                                   backref='song1', lazy='dynamic')
    similarities_from = relationship('Similarity',
                                     foreign_keys='Similarity.song2_id',
                                     backref='song2', lazy='dynamic')

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

class PlaylistSong(BASE):
    __tablename__ = 'playlist_songs'

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer, ForeignKey('playlists.id'), nullable=False)
    soundcloud_song_id = Column(Integer, ForeignKey('soundcloud_songs.id'),
                                nullable=False)
    liked = Column(Boolean) # True if liked, False if disliked, None otherwise
    __table_args__ = (UniqueConstraint('playlist_id', 'soundcloud_song_id'),)

class SoundcloudSong(BASE):
    __tablename__ = 'soundcloud_songs'

    id = Column(Integer, primary_key=True)
    query = Column(Unicode(500), nullable=False)
    url = Column(String(250), nullable=False)
    title = Column(Unicode(500))
    user = Column(Unicode(500))
    artwork_url = Column(String(250))
    playback_count = Column(Integer)
    likes_count = Column(Integer)
    __table_args__ = (UniqueConstraint('query', 'url'),)

class Similarity(BASE):
    __tablename__ = 'similarities'

    id = Column(Integer, primary_key=True)
    song1_id = Column(String(18), ForeignKey('songs.song_id'), nullable=False)
    song2_id = Column(String(18), ForeignKey('songs.song_id'), nullable=False)
    similarity = Column(Float, nullable=False)
    __table_args__ = (UniqueConstraint('song1_id', 'song2_id'),)

def init_db():
    print 'Creating database'
    BASE.metadata.create_all(bind=DB_ENGINE)

def seed_db_songs(path):
    print 'Seeding database songs'
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

def seed_db_similarities(path):
    print 'Seeding database song similarities'
    songs = {}
    print '    Reading similarity file'
    with open(path) as f:
        for line in f:
            song1_id, song2_id, sim = line.strip().split('\t')
            if sim > 0:
                DB_SESSION.add(Similarity(
                    song1_id=song1_id, song2_id=song2_id, similarity=float(sim)
                ))
    print '    Committing to DB'
    DB_SESSION.commit()

def drop_db():
    print 'Dropping database'
    BASE.metadata.drop_all(bind=DB_ENGINE)

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', action='store_const', const=True,
                        help='Initialize database with existing DDL')
    parser.add_argument('--seed', action='store_const', const=True,
                        help='Seed database with existing data')
    parser.add_argument('--song-file', type=str,
                        help='Song filepath for seeding the database')
    parser.add_argument('--similarity-file', type=str,
                        help='Similarity filepath for seeding the database')
    parser.add_argument('--drop', action='store_const', const=True,
                        help='Drop all tables in existing database')
    args = parser.parse_args()
    if args.drop:
        drop_db()
    if args.init:
        init_db()
    if args.seed:
        if args.song_file:
            seed_db_songs(args.song_file)
        if args.similarity_file:
            seed_db_similarities(args.similarity_file)

