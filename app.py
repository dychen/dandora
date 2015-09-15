import os
import requests
from flask import Flask, jsonify
from flask import request as flask_request
from flask.ext.sqlalchemy import SQLAlchemy
from server.database import DB_SESSION, Song

ROOT_DIR = os.environ['ROOT_DIR']

app = Flask(__name__)

@app.teardown_appcontext
def shutdown_session(exception=None):
    DB_SESSION.remove()

@app.route('/')
def hello_world():
    return 'Hello World!'

@app.route('/api/songs.json')
def songs():
    # Try quering a Redis cache for better performance
    LIMIT = 50000
    import time
    start = time.time()
    songs = ['%s - %s' % (s.artist, s.title)
             for s in Song.query.limit(LIMIT).all()]
    print 'Queried songs in %.10fs' % (time.time() - start)
    return jsonify({
        'data': songs
    })

@app.route('/api/songs')
def song():
    """
    For response format, check:
    https://developers.soundcloud.com/docs/api/reference#tracks
    The response will be a list of the example response dicts.
    """

    SOUNDCLOUD_URL = 'http://api.soundcloud.com/tracks/'
    print 'Querying songs'
    query = flask_request.args['query']
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
