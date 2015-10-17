import os
import random
import requests
from flask import Flask, jsonify, flash, render_template, session, redirect, url_for, request
from flask.ext.sqlalchemy import SQLAlchemy
from flask_s3 import FlaskS3
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from server.database import DB_SESSION, Song, User, Playlist
from server.oauth import twitter_oauth

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']
if os.environ['ENVIRONMENT'] == 'production':
    app.config['S3_BUCKET_NAME'] = os.environ['S3_BUCKET_NAME']
    FlaskS3(app)

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

def create_playlist(playlist_name, user_id):
    new_playlist = Playlist(user_id=user_id, name=playlist_name)
    DB_SESSION.add(new_playlist)
    DB_SESSION.commit()
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
        return 'Guest-%d' % random.randint(0, 1000000)
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
    # Result set is a list of tuples [('[Artist]',), ...]
    artists = [s[0] for s in DB_SESSION.query(Song.artist.distinct())]
    return jsonify({
        'length': len(artists),
        'data': artists
    })

@app.route('/api/songs')
def songs():
    # Try quering a Redis cache for better performance
    LIMIT = 50000
    import time
    start = time.time()
    songs = ['%s - %s' % (s.artist, s.title)
             for s in Song.query.limit(LIMIT).all()]
    print 'Queried songs in %.10fs' % (time.time() - start)
    return jsonify({
        'length': len(songs),
        'data': songs
    })

@app.route('/api/playlists', methods=['GET', 'POST', 'DELETE'])
def playlist():
    def build_playlist(seed):
        LIMIT = 20
        MIN_SONG_COUNT = 5
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
        params = { 'artist': seed, 'count': MIN_SONG_COUNT, 'limit': LIMIT }
        # Result tuple: ('artist1', 'artist2', sim_ct, song_ct, norm_sim_ct)
        results = [row[1] for row in DB_SESSION.execute(QUERYSTR, params)]
        print 'Query: %s, Results: %s' % (seed, results)
        return results

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

        songs = build_playlist(seed)
        try:
            create_playlist(seed, user.id)
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
                'songs': build_playlist(playlist.name),
                'index': 0,
                'maxIndex': 0
            }
            for playlist in Playlist.query.filter_by(user_id=user.id).all()
        ]
        return jsonify({
            'length': len(playlists),
            'data': playlists
        })

@app.route('/api/song')
def song():
    """
    For response format, check:
    https://developers.soundcloud.com/docs/api/reference#tracks
    The response will be a list of the example response dicts.
    """

    SOUNDCLOUD_URL = 'http://api.soundcloud.com/tracks/'
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
