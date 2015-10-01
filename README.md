#Pandora

###Install React
```
$ npm install -g react-tools # Install React CLI
$ jsx --watch static/js/src/ static/js/dist/ # Start JSX compiler
```

###Setup
```
$ python # Initialize the local database
>>> from server.database_init import init_db
>>> init_db()
```

###Million Song Dataset (MSD)
This is a publicly available dataset of song metadata. Instructions for downloading the dataset are [here](http://labrosa.ee.columbia.edu/millionsong/pages/getting-dataset). Since I'm just using this for a (song id: song name) mapping, I just need to access the metadata database, which comes as part of the full snapshot. To do this, I needed to:
1. Provision a separate AWS instance (US East), set up a public/private key pair, and set up a public DNS hostname
2. Create a new volume from the [existing snapshot](https://aws.amazon.com/datasets/million-song-dataset/)
3. SSH into the instance and mount the volume
4. `scp -i [private key pemfile] ubuntu@[public DNS hostname]:[/path/to/track_metadata.db]``

###Hadoop
To run the MapReduce job that calculates pairwise intersections:
```
$ hadoop jar /usr/local/Cellar/hadoop/2.7.1/libexec/share/hadoop/tools/lib/hadoop-streaming-2.7.1.jar \
  -file scripts/mapper.py -mapper scripts/mapper.py \
  -file scripts/reducer.py -reducer scripts/reducer.py \
  -input song_users_visible_evaluation.txt -output data/models/usersim
```
To compute the locality-weighted cosine similarities:
```
$ python scripts/recommend.py # You can supply various command-line args
```

###Dependencies
```
Flask
+ itsdangerous
+ Jinja2
+ MarkupSafe
+ Werkzeug
+ wheel

flask-sqlalchemy
+ SQLAlchemy

requests
```

###Old/Unused
Install HDF5 (for the Million Song Dataset):
```
$ brew install homebrew/science/hdf5
```
Dependencies:
```
h5py # For reading MSD HDF5 files (currently unused)
+ Cython
+ numpy
+ six

tables # Dependency for the hdf5_getters.py script
+ numexpr
```
