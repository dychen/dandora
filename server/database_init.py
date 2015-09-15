# Need to import all models before calling init_db()
from database import BASE, DB_ENGINE, DB_SESSION, ROOT_DIR, Song

def seed_db():
    print 'Seeding database'
    songs = {}
    print '    Reading song file'
    with open('%s/data/train/unique_tracks.txt' % ROOT_DIR) as f:
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

def init_db():
    print 'Creating new SQLite database'
    BASE.metadata.create_all(bind=DB_ENGINE)

if __name__=='__main__':
    init_db()
    seed_db()
