import os
import random
import requests
from flask import Flask, jsonify, flash, render_template, session, redirect, url_for, request
from flask.ext.sqlalchemy import SQLAlchemy
from server.database import DB_SESSION, Song
from server.oauth import twitter_oauth

ROOT_DIR = os.environ['ROOT_DIR']

app = Flask(__name__)
app.secret_key = os.environ['SECRET_KEY']

def is_logged_in():
    return True if session.get('twitter_token') else False

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

@app.route('/oauth-authorized')
@twitter_oauth.authorized_handler
def oauth_authorized(response):
    next_url = request.args.get('next') or url_for('/')
    if response is None:
        flash('Unable to log in')
        return redirect(next_url)

    session['twitter_token'] = (
        response['oauth_token'],
        response['oauth_token_secret']
    )
    session['twitter_user'] = response['screen_name']

    return redirect(next_url)

# Internal API

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

@app.route('/api/playlist')
def playlist():
    LIMIT = 100
    def get_playlist(seed):
        songs = list(set([s.artist for s in Song.query.limit(LIMIT).all()]))
        random.shuffle(songs)
        return songs

    seed = request.args.get('query')
    songs = get_playlist(seed)

    return jsonify({
        'length': len(songs),
        'data': songs
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
