#Pandora

###Install React
```
$ npm install -g react-tools # Install React CLI
$ jsx --watch static/js/src/ static/js/dist/ # Start JSX compiler
```

###Setup
```
(venv)$ python server/database.py --init --seed data/train/unique_tracks.txt
```

###Deployment
```
$ python deploy_assets.py # Deploy assets. WARNING: Also uploads the js/src directory
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
$ python scripts/recommend.py --recommend \
  --userscore-file data/models/usersim/similarities_0.3_5_0.txt.score \
  --songscore-file data/models/songsim/similarities_0.15_3_0.txt.score
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
p=0.5 0.104069
p=0.0 0.104282
```

###Dataset Queries
```
# Artists with the most non-zero similarity scores
SELECT s.artist, COUNT(s.artist) AS count
    FROM similarities AS sim JOIN songs AS s ON song1_id=s.song_id
    GROUP BY s.artist
    ORDER BY count DESC
    LIMIT 1000;

Coldplay               | 22981
Florence + The Machine | 15324
Kings Of Leon          | 14943
The Black Keys         | 11806
Jack Johnson           | 11434
The Killers            | 10619
Train                  | 10390
Justin Bieber          | 10258
Eminem                 |  9604
Linkin Park            |  9480
OneRepublic            |  9370
...

# Artists with the highest total similarity scores
SELECT s.artist, SUM(similarity) AS sim_total
    FROM similarities AS sim JOIN songs AS s
    ON song1_id=s.song_id
    GROUP BY s.artist
    ORDER BY sim_total DESC
    LIMIT 1000;

Big D and The Kids Table | 54.028778
Jesse Cook               | 49.065007
Stephy Tang              | 49.008365
The Sundays              | 47.775178
Mitch Hedberg            | 45.910202
Paul Cardall             | 40.820242
Bosse                    | 40.150111
Dora The Explorer        |  37.80326
Ruckus Roboticus         | 37.368392
Cloud Cult               | 36.716575
...

# Songs with the most non-zero similarity scores by artist <ARTIST>
SELECT s.artist, s.title, COUNT(sim.id) AS sim_count
    FROM songs AS s JOIN similarities AS sim ON s.song_id=sim.song1_id
    WHERE s.artist='<ARTIST>'
    GROUP BY s.artist, s.title
    ORDER BY sim_count DESC;

# The number of non-zero similarity scores for song <SONG> (by artist <ARTIST>)
SELECT s.title, s.artist, COUNT(sim.id) AS sim_count
    FROM songs AS s JOIN similarities AS sim ON s.song_id=sim.song1_id
    WHERE s.title='<SONG>' AND s.artist='<ARTIST>'
    GROUP BY s.title, s.artist
    ORDER BY sim_count DESC;

# Songs most similar to song <SONG> (by artist <ARTIST>)
SELECT song1.title, song1.artist, song2.title, song2.artist, sim.similarity
    FROM songs AS song1 JOIN similarities AS sim ON song1.song_id=sim.song1_id
    JOIN songs AS song2 ON sim.song2_id=song2.song_id
    WHERE song1.title='<SONG>' AND song1.artist='<ARTIST>'
    ORDER BY sim.similarity DESC;

# Songs most similar to songs by the artist <ARTIST>
SELECT song1.title, song1.artist, song2.title, song2.artist, sim.similarity
    FROM songs AS song1 JOIN similarities AS sim ON song1.song_id=sim.song1_id
    JOIN songs AS song2 ON sim.song2_id=song2.song_id
    WHERE song1.artist='<ARTIST>'
    ORDER BY sim.similarity DESC;

# Artists with songs the most number of songs similar to songs by the artist
# <ARTIST> (where number of songs is greater than <X>)
SELECT song1.artist, song2.artist, COUNT(sim.similarity) AS sim_count
    FROM songs AS song1 JOIN similarities AS sim ON song1.song_id=sim.song1_id
    JOIN songs AS song2 ON sim.song2_id=song2.song_id
    WHERE song1.artist='<ARTIST>'
    GROUP BY song1.artist, song2.artist
    ORDER BY sim_count DESC;

# Artists with songs the most number of songs similar to songs by the artist
# <ARTIST> (normalized by number of songs, where number of songs > <X>)
SELECT song1.artist, song2.artist, COUNT(sim.similarity) AS sim_count,
    scounts.count AS song_count,
    COUNT(sim.similarity) / CAST(scounts.count AS FLOAT) AS sim_count_norm
    FROM songs AS song1 JOIN similarities AS sim ON song1.song_id=sim.song1_id
    JOIN songs AS song2 ON sim.song2_id=song2.song_id
    JOIN (SELECT s.artist AS artist, COUNT(s.id) AS count
        FROM songs AS s
        GROUP BY s.artist) AS scounts ON song2.artist=scounts.artist
    WHERE song1.artist='<ARTIST>' AND scounts.count > <X>
    GROUP BY song1.artist, song2.artist, scounts.artist, scounts.count
    ORDER BY sim_count_norm DESC;

# Artists with songs most similar (total similarity) to songs by the artist
# <ARTIST>
SELECT song1.artist, song2.artist, SUM(sim.similarity) AS total_sim
    FROM songs AS song1 JOIN similarities AS sim ON song1.song_id=sim.song1_id
    JOIN songs AS song2 ON sim.song2_id=song2.song_id
    WHERE song1.artist='<ARTIST>'
    GROUP BY song1.artist, song2.artist
    ORDER BY total_sim DESC;

# Artists with songs most similar (total similarity) to songs by the artist
# <ARTIST> (normalized by number of songs, where number of songs > <X>)
SELECT song1.artist, song2.artist, SUM(sim.similarity) AS total_sim,
    scounts.count AS song_count,
    SUM(sim.similarity) / CAST(scounts.count AS FLOAT) AS total_sim_norm
    FROM songs AS song1 JOIN similarities AS sim ON song1.song_id=sim.song1_id
    JOIN songs AS song2 ON sim.song2_id=song2.song_id
    JOIN (SELECT s.artist AS artist, COUNT(s.id) AS count
        FROM songs AS s
        GROUP BY s.artist) AS scounts ON song2.artist=scounts.artist
    WHERE song1.artist='<ARTIST>' AND scounts.count > <X>
    GROUP BY song1.artist, song2.artist, scounts.artist, scounts.count
    ORDER BY total_sim_norm DESC;
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

Flask-OAuth
+ httplib2
+ oauth2

# For Heroku deployment
gunicorn
psycopg2
flask-s3
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
