import os
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from server.database import DB_SESSION

ROOT_DIR = os.environ['ROOT_DIR']

app = Flask(__name__)

@app.teardown_appcontext
def shutdown_session(exception=None):
    DB_SESSION.remove()

@app.route('/')
def hello_world():
    return 'Hello World!'

if __name__ == '__main__':
    # TODO: Remove debug before deployment
    app.run(debug=True)
