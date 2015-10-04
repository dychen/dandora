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
```
$ ssh -i [PEMFILE].pem ubuntu@[public DNS hostname].amazonaws.com
> $ sudo mkdir /data
> $ sudo mount /dev/xvdf /data
```
4. `scp -i [private key pemfile] ubuntu@[public DNS hostname].amazonaws.com:[/path/to/track_metadata.db] .`

###Recommendation Script
To run the MapReduce job that calculates pairwise intersections:
```
Convert the input to a usable format
$ python scripts/recommend.py --format-input --input data/train/kaggle_visible_evaluation_triplets.txt --output mr_training
# User model
$ hadoop jar /usr/local/Cellar/hadoop/2.7.1/libexec/share/hadoop/tools/lib/hadoop-streaming-2.7.1.jar \
  -file scripts/mapper.py -mapper scripts/mapper.py \
  -file scripts/reducer.py -reducer scripts/reducer.py \
  -input mr_training_song_users.txt -output data/models/usersim
# Song model
$ hadoop jar /usr/local/Cellar/hadoop/2.7.1/libexec/share/hadoop/tools/lib/hadoop-streaming-2.7.1.jar \
  -file scripts/mapper.py -mapper scripts/mapper.py \
  -file scripts/reducer.py -reducer scripts/reducer.py \
  -input mr_training_user_songs.txt -output data/models/songsim
```
To compute the locality-weighted cosine similarities (note: this expects the trained MR files to be in the folders `data/models/usersim` and `data/models/songsim` and outputs the resulting similarity adjacency list to those directories):
```
$ python scripts/recommend.py --train --alpha 0.3 --q 5 --threshold 0 --foruser true
$ python scripts/recommend.py --train --alpha 0.15 --q 3 --threshold 0 --foruser false
```
To run the same thing without MapReduce:
```
$ python scripts/recommend.py --train --no-mr --alpha 0.15 --q 3 --threshold 0 --input data/train/kaggle_visible_evaluation_triplets.txt
```
To generate score based on similarities:
```
$ python scripts/recommend.py --score \
  --usersim-file data/models/usersim/similarities_0.3_5_0.txt \
  --songsim-file data/models/songsim/similarities_0.15_3_0.txt
```
To generate recommendations:
```
$ python scripts/recommend.py --score \
  --usersong-file data/models/usersim/similarities_0.3_5_0.txt.score \
  --songsong-file data/models/songsim/similarities_0.15_3_0.txt.score
```
To evaluate the recommendations (note: this expects the validation set file `year1_valid_triplets_hidden` in the folder `data/test`)
```
$ python scripts/evaluate --file data/submissions/submission.txt
```
Results:
```
p=1.0 0.118594
p=0.9 0.116871
p=0.8 0.114447
p=0.5
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
