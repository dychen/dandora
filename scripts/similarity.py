import os
import time

ROOT_DIR = os.environ['ROOT_DIR']

def log_elapsed_time(s, prev_time):
    curr_time = time.time()
    print '[Elapsed time] %s: %f' % (s, curr_time - prev_time)
    return curr_time

def compute_song_popularity(data):
    song_counts = {}
    for line in data:
        _, song, _ = line.strip().split('\t')
        if song in song_counts:
            song_counts[song] += 1
        else:
            song_counts[song] = 1
    return sorted(song_counts.keys(),
                  key=lambda x: song_counts[x],
                  reverse=True)

if __name__=='__main__':
    t0 = time.time()
    with open('%s/data/kaggle_visible_evaluation_triplets.txt' % ROOT_DIR) as f:
        data = f.readlines()
    t1 = log_elapsed_time('Reading files', t0)
    popular_songs = compute_song_popularity(data)
    print popular_songs[:100]
    t2 = log_elapsed_time('Computing song popularity', t1)
