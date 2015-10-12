import os
import flask_s3
from app import app
flask_s3.create_all(app,
                    user=os.environ['AWS_ACCESS_KEY_ID'],
                    password=os.environ['AWS_SECRET_ACCESS_KEY'],
                    bucket_name=os.environ['S3_BUCKET'])
