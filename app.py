import os
import random
import requests
from flask import Flask, jsonify, flash, render_template, session, redirect, url_for, request
from flask.ext.sqlalchemy import SQLAlchemy
from server.database import DB_SESSION, Song, User, Playlist
from server.oauth import twitter_oauth

ROOT_DIR = os.environ['ROOT_DIR']

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']

def is_logged_in():
    return True if session.get('twitter_token') else False

def get_current_user():
    if is_logged_in():
        return User.query.filter_by(username=session['username']).first()
    return None

@app.teardown_appcontext
def shutdown_session(exception=None):
    DB_SESSION.remove()

@app.route('/')
@app.route('/index')
def index():
    return render_template('main.html')

# Authentication

@twitter_oauth.tokengetter
def get_twitter_token(token=None):
    return session.get('twitter_token')

@app.route('/login')
def login():
    if is_logged_in():
        return redirect('/')
    else:
        return twitter_oauth.authorize(
            callback=url_for('oauth_authorized', next=request.args.get('next')
                                                      or request.referrer
                                                      or None)
        )

@app.route('/logout')
def logout():
    session.clear()
    print session
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
        new_account = User(
            username=response['screen_name'],
            token=response['oauth_token'],
            secret=response['oauth_token_secret']
        )
        DB_SESSION.add(new_account)
        DB_SESSION.commit()

    session['twitter_token'] = (
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

@app.route('/api/playlists', methods=['GET', 'POST'])
def playlist():
    def build_playlist(seed):
        LIMIT = 100

        songs = list(set([s.artist for s in Song.query.limit(LIMIT).all()]))
        random.shuffle(songs)
        return songs

    def save_playlist(playlist_name, user_id):
        new_playlist = Playlist(user_id=user_id, name=playlist_name)
        DB_SESSION.add(new_playlist)
        DB_SESSION.commit()

    if request.method == 'POST':
        user = get_current_user()
        seed = request.form.get('query')

        songs = build_playlist(seed)
        save_playlist(seed, user.id)

        return jsonify({
            'length': len(songs),
            'data': songs
        })
    else:
        user = get_current_user()
        playlists = [
            {
                'name': playlist.name,
                'songs': build_playlist(playlist.name),
                'index': 0,
                'maxIdx': 0
            }
            for playlist in (DB_SESSION.query(Playlist)
                                       .filter(Playlist.user_id == user.id)
                                       .all())
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
    # TODO: Remove debug before deployment
    app.run(debug=True)
