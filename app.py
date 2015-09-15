import os
from flask import Flask, jsonify
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
    LIMIT = 10000
    import time
    start = time.time()
    songs = [s.title for s in Song.query.limit(LIMIT).all()]
    print 'Queried songs in %.10fs' % (time.time() - start)
    return jsonify({
        'data': songs
    })

if __name__ == '__main__':
    # TODO: Remove debug before deployment
    app.run(debug=True)
