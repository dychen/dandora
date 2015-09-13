#Pandora

###Install React
```
$ npm install -g react-tools # Install React CLI
$ jsx --watch static/js/src/ static/js/dist/ # Start JSX compiler
```

###Million Song Dataset (MSD)
This is a publicly available dataset of song metadata. Instructions for downloading the dataset are [here](http://labrosa.ee.columbia.edu/millionsong/pages/getting-dataset). Since I'm just using this for a (song id: song name) mapping, I just need to access the metadata database, which comes as part of the full snapshot. To do this, I needed to:
1. Provision a separate AWS instance (US East), set up a public/private key pair, and set up a public DNS hostname
2. Create a new volume from the [existing snapshot](https://aws.amazon.com/datasets/million-song-dataset/)
3. SSH into the instance and mount the volume
4. `scp -i [private key pemfile] ubuntu@[public DNS hostname]:[/path/to/track_metadata.db]``

###Dependencies
```
Flask
+ itsdangerous
+ Jinja2
+ MarkupSafe
+ Werkzeug
+ wheel
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
