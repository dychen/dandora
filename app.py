import math
import os
import random
import requests
from flask import Flask, jsonify, flash, render_template, session, redirect, url_for, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask_s3 import FlaskS3
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from server.database import DB_SESSION, Song, User, Playlist, SoundcloudSong
from server.oauth import twitter_oauth

SOUNDCLOUD_URL = 'http://api.soundcloud.com/tracks/'

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
if os.environ['ENVIRONMENT'] == 'production':
    app.config['S3_BUCKET_NAME'] = os.environ['S3_BUCKET_NAME']
    FlaskS3(app)

def update_or_create(model, defaults={}, commit=True, **kwargs):
    """
    Equivalent of Django's update_or_create, with an additional option to
    commit the transaction (commits by default).
    @param model: Model to update, e.g. Song
    @param defaults: Parameters to update, e.g. {
        'playback_count': 1000, 'likes_count': 10
    }
    @param commit: Commit the transaction?
    @param **kwargs: Parameters to check uniqueness on, e.g. {
        'title': 'How We Do', 'artist': '50 Cent'
    }
    """
    model_instance = DB_SESSION.query(model).filter_by(**kwargs).first()
    if model_instance:
        for arg, value in defaults.iteritems():
            setattr(model_instance, arg, value)
        if commit:
            DB_SESSION.commit()
        return model_instance, True
    else:
        params = { k: v for k, v in kwargs.iteritems() }
        params.update(defaults)
        model_instance = model(**params)
        DB_SESSION.add(model_instance)
        if commit:
            DB_SESSION.commit()
        return model_instance, False

def is_logged_in():
    return True if session.get('token') else False

def get_current_user():
    if is_logged_in():
        return User.query.filter_by(username=session['username']).first()
    return None

def create_user(username, token, secret):
    new_account = User(username=username, token=token, secret=secret)
    DB_SESSION.add(new_account)
    DB_SESSION.commit()
    return new_account

def get_similar_artists(artist, limit=10, min_song_ct=5, artist_first=True):
    """Returns a list of similar artist names to @artist."""
    # Skip the ORM and directly execute the SQL for performance reasons
    QUERYSTR = text('''
SELECT song1.artist, song2.artist, COUNT(sim.similarity) AS sim_count,
    scounts.count AS song_count,
    COUNT(sim.similarity) / CAST(scounts.count AS FLOAT) AS sim_count_norm
    FROM songs AS song1 JOIN similarities AS sim ON song1.song_id=sim.song1_id
    JOIN songs AS song2 ON sim.song2_id=song2.song_id
    JOIN (SELECT s.artist AS artist, COUNT(s.id) AS count
        FROM songs AS s
        GROUP BY s.artist) AS scounts ON song2.artist=scounts.artist
    WHERE song1.artist=:artist AND scounts.count > :count
    GROUP BY song1.artist, song2.artist, scounts.artist, scounts.count
    ORDER BY sim_count_norm DESC
    LIMIT :limit;
    ''')
    # This *should* be secure since it uses bound parameters which are
    # passed to the underlying DPAPI:
    # http://docs.sqlalchemy.org/en/rel_0_9/orm/session_api.html
    #     #sqlalchemy.orm.session.Session.execute
    # http://docs.sqlalchemy.org/en/rel_0_9/core/sqlelement.html
    #     #sqlalchemy.sql.expression.text
    # http://docs.sqlalchemy.org/en/rel_0_9/core/sqlelement.html
    #     #sqlalchemy.sql.expression.bindparam
    params = { 'artist': artist, 'count': min_song_ct, 'limit': limit }
    # Result tuple: ('artist1', 'artist2', sim_ct, song_ct, norm_sim_ct)
    artists = [row[1] for row in DB_SESSION.execute(QUERYSTR, params)]
    if artist_first:
        if artist in artists:
            artists.remove(artist)
        return [artist] + artists
    else:
        return artists

def get_similar_songs(artist, limit=10):
    """Returns a list of similar (song, artist) tuples to @artist."""
    QUERYSTR = text('''
SELECT song1.artist, song2.title, song2.artist, SUM(sim.similarity) AS total_sim
    FROM songs AS song1 JOIN similarities AS sim ON song1.song_id=sim.song1_id
    JOIN songs AS song2 ON sim.song2_id=song2.song_id
    WHERE song1.artist=:artist
    GROUP BY song1.artist, song2.title, song2.artist
    ORDER BY total_sim DESC
    LIMIT :limit;
    ''')
    params = { 'artist': artist, 'limit': limit }
    # Result tuple: ('artist1', 'song2', 'artist2', sim)
    return ['%s %s' % (row[1], row[2])
            for row in DB_SESSION.execute(QUERYSTR, params)]

def populate_soundcloud_songs(query):
    """
    For response format, check:
    https://developers.soundcloud.com/docs/api/reference#tracks
    The response will be a list of the example response dicts.
    """

    PLAYBACK_FLOOR = 200000
    LIKES_FLOOR = 500

    def soundcloud_song_filter(song_metadata):
        return (song_metadata['streamable']
                and song_metadata['playback_count'] > PLAYBACK_FLOOR
                and song_metadata['likes_count'] > LIKES_FLOOR)

    response = requests.get(SOUNDCLOUD_URL, params={
        'q': query,
        'client_id': os.environ['SOUNDCLOUD_CLIENT_ID'],
        'limit': 100
    })
    data = response.json()
    filtered = [d for d in data if d['streamable']]
    for d in filtered:
        update_or_create(SoundcloudSong, search=query, sc_id=d['id'],
                         defaults={
                             'url': d['stream_url'],
                             'title': d['title'],
                             'user': d['user']['username'],
                             'artwork_url': d['artwork_url'],
                             'playback_count': d['playback_count'],
                             'likes_count': d['likes_count']
                        })
    print 'Updated songs for query %s' % query

def create_playlist(playlist_name, user_id):
    print 'Creating new playlist %s for user %s' % (playlist_name, user_id)
    new_playlist = Playlist(user_id=user_id, name=playlist_name)
    DB_SESSION.add(new_playlist)
    DB_SESSION.commit()
    # Seed soundcloud_songs database table
    map(populate_soundcloud_songs, get_similar_artists(playlist_name))
    return new_playlist

@app.teardown_appcontext
def shutdown_session(exception=None):
    DB_SESSION.remove()

@app.route('/')
def index():
    try:
        if is_logged_in():
            return render_template('main.html')
        else:
            return redirect('/login')
    except Exception, e:
        print 'Error'
        print url_for('static', filename='js/dist/main.js')
        print e
        import sys, traceback
        traceback.print_exc(file=sys.stdout)

# Authentication

@twitter_oauth.tokengetter
def get_twitter_token(token=None):
    return session.get('token')

@app.route('/login/')
def login():
    if is_logged_in():
        return redirect('/')
    else:
        return render_template('login.html')

@app.route('/login/auth')
def auth():
    if is_logged_in():
        return redirect('/')
    else:
        return twitter_oauth.authorize(
            callback=url_for(
                'oauth_authorized',
                next=request.args.get('next') or request.referrer or None
            )
        )

@app.route('/login/auth/null')
def fake_auth():
    def generate_username():
        return 'Guest-%d' % random.randint(0, 1000000000000)
    def generate_fake_token():
        token = os.urandom(20).encode('hex')[:39]
        return '0000000000-%s' % token
    def generate_fake_secret():
        return os.urandom(23).encode('hex')[:45]

    if is_logged_in():
        return redirect('/')
    else:
        playlist = request.args.get('query')
        username = generate_username()
        token = generate_fake_token()
        secret = generate_fake_secret()
        user = create_user(username, token, secret)
        session['username'] = username
        session['token'] = (token, secret)
        create_playlist(playlist, user.id)
        return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/oauth-authorized')
@twitter_oauth.authorized_handler
def oauth_authorized(response):
    next_url = request.args.get('next') or url_for('/')
    if response is None:
        return redirect(next_url)

    user = User.query.filter_by(username=response['screen_name']).first()

    if user:
        pass
    else:
        create_user(response['screen_name'],
                    response['oauth_token'],
                    response['oauth_token_secret'])

    session['token'] = (
        response['oauth_token'],
        response['oauth_token_secret']
    )
    session['username'] = response['screen_name']

    return redirect(next_url)

# Internal API

@app.route('/api/user')
def user():
    if is_logged_in():
        return jsonify({ 'username': session['username']})
    return jsonify({ 'username': None })

@app.route('/api/artists')
def artists():
    def artist_filter(artist_str):
        stop_words = ['ft.', 'feat', 'featuring', '_', '+', '/', '|']
        artist_str = artist_str.lower()
        for stop_word in stop_words:
            if stop_word in artist_str:
                return False
        return True

    # Result set is a list of tuples [('[Artist]',), ...]
    artists = [s[0] for s in DB_SESSION.query(Song.artist.distinct())
               if artist_filter(s[0])]
    return jsonify({
        'length': len(artists),
        'data': artists
    })

@app.route('/api/playlists', methods=['GET', 'POST', 'DELETE'])
def playlist():
    def build_playlist(seed, length=100):
        similar_artists = get_similar_artists(seed)
        soundcloud_songs = []
        for i, artist in enumerate(similar_artists):
            soundcloud_songs += (SoundcloudSong.query
                                               .filter_by(search=seed)
                                               .limit((10-i) * 10)
                                               .all())
        # Weighted shuffle
        soundcloud_songs.sort(key=lambda song:
                              math.log(song.playback_count) * random.random())
        playlist_songs = [{ k: getattr(song, k)
            for k in ('sc_id', 'url', 'title', 'user', 'artwork_url') }
            for song in soundcloud_songs
        ][:length]
        random.shuffle(playlist_songs)
        return playlist_songs

    def delete_playlist(playlist_name, user_id):
            playlist = (Playlist.query
                                .filter_by(user_id=user.id, name=playlist_name)
                                .one())
            DB_SESSION.delete(playlist)
            DB_SESSION.commit()

    if not is_logged_in():
        response = jsonify({ 'error': 'Not logged in' })
        response.status_code = 401
        return response
    user = get_current_user()

    if request.method == 'POST':
        seed = request.form.get('query')

        try:
            create_playlist(seed, user.id)
            songs = build_playlist(seed)
            response = jsonify({ 'length': len(songs), 'data': songs })
            response.status_code = 201
            return response
        except IntegrityError:
            response = jsonify({ 'error': 'Playlist already exists' })
            response.status_code = 409
            return response

    elif request.method == 'DELETE':
        name = request.form.get('name')
        delete_playlist(name, user.id)
        return jsonify({ 'playlist': name })

    else:
        playlists = [
            {
                'name': playlist.name,
                'songs': build_playlist(playlist.name)
            }
            for playlist in Playlist.query.filter_by(user_id=user.id).all()
        ]
        return jsonify({
            'length': len(playlists),
            'data': playlists
        })

@app.route('/api/song')
def song():

    print 'Querying songs'
    query = request.args.get('query')
    response = requests.get(SOUNDCLOUD_URL, params={
        'q': query,
        'client_id': os.environ['SOUNDCLOUD_CLIENT_ID']
    })
    data = response.json()
    filtered = [d for d in data if d['streamable']]
    song = filtered[0]
    # TODO: Handle 0 results returned
    print song
    user = (song['user']['full_name'] if 'full_name' in song['user']
            else song['user']['username'])
    return jsonify({
        'id': song['id'],
        'user': user,
        'title': song['title'],
        'artwork_url': song['artwork_url'],
        'permalink_url': song['permalink_url'],
        'stream_url': song['stream_url']
    })

if __name__ == '__main__':
    if os.environ['ENVIRONMENT'] == 'development':
        app.run(debug=True)
    else:
        app.run(debug=False)
