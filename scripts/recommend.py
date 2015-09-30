import os
import time

class Timer:
    @classmethod
    def log_elapsed_time(cls, s, prev_time):
        curr_time = time.time()
        print '[Elapsed time] %s: %f' % (s, curr_time - prev_time)
        return curr_time

class BaseRecommender:
    _ROOT_DIR = os.environ['ROOT_DIR']

    def _load_dataset(self, filename='kaggle_visible_evaluation_triplets.txt'):
        with open('%s/data/train/%s' % (self._ROOT_DIR, filename)) as f:
            return f.readlines()

    def _get_user_song_dict(self, data):
        """
        @param data [list]: Raw file data
            ['fd50c4007b68a3737fe052d5a4f78ce8aa117f3d\tSOBONKR12A58A7A7E0\t1',
             ...]
        @return [dict]: Dict of songs each user has listened to
            { [user id]: set([listened to set]) }
        """
        user_listened = {}
        for line in data:
            user, song, _ = line.strip().split('\t')
            if user in user_listened:
                user_listened[user].add(song)
            else:
                user_listened[user] = set([song])
        return user_listened

    def _get_song_user_dict(self, data):
        """
        @param data [list]: Raw file data
            ['fd50c4007b68a3737fe052d5a4f78ce8aa117f3d\tSOBONKR12A58A7A7E0\t1',
             ...]
        @return [dict]: Dict of users each song has listeners of
            { [song id]: set([listener set]) }
        """
        song_listened = {}
        for line in data:
            user, song, _ = line.strip().split('\t')
            if song in song_listened:
                song_listened[song].add(user)
            else:
                song_listened[song] = set([user])
        return song_listened

    def _get_ordered_users(self):
        """
        @return [list]: List of users in the canonical order
            [[user id], [user id], ...]
        """
        with open('%s/data/train/kaggle_users.txt' % self._ROOT_DIR) as f:
            ordered_users = [line.strip() for line in f.readlines()]
        return ordered_users

    def _get_ordered_songs(self):
        """
        @return [list]: List of songs in the canonical order
            [[song id], [song id], ...]
        """
        with open('%s/data/train/kaggle_songs.txt' % self._ROOT_DIR) as f:
            ordered_songs = [line.strip().split()[0] for line in f.readlines()]
        return ordered_songs

class PopularityRecommender(BaseRecommender):
    """
    Strategy: Sort songs by popularity and recommend the same top-k songs to
    each user in descending order, filtered by what they've already heard.
    This is the baseline recommender used described in the original paper.
    """

    def __compute_song_popularity(self, data):
        """
        @param data [list]: Raw file data
            ['fd50c4007b68a3737fe052d5a4f78ce8aa117f3d\tSOBONKR12A58A7A7E0\t1',
             ...]
        @return [list]: List of songs in order of decreasing popularity
            [[song id], [song id], ...]
        """
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

    def __get_song_idx_map(self):
        """
        UNUSED
        @return [dict]: Dict of song ids mapped to song indexes for submission
            { [song id]: [song idx] }, e.g. { 'SOAAADD12AB018A9DD': '1', ...}
        """
        with open('%s/data/train/kaggle_songs.txt' % self._ROOT_DIR) as f:
            song_idx_map = {line.strip().split(' ')[0]:
                            line.strip().split(' ')[1]
                            for line in f.readlines()}
        return song_idx_map

    def __format_submission(self, recommendations_list, user_listened,
                            ordered_users, filename='submission.txt'):
        """
        See corresponding method for each parameter
        Output:
            '[user id], [song id], [song id], ..., [song id]'
            ...
        """
        with open('%s/data/submissions/%s' % (self._ROOT_DIR, filename),
                  'w') as f:
            for user in ordered_users:
                user_recommendations = []
                for song in recommendations_list:
                    if len(user_recommendations) == 500:
                        break
                    if song not in user_listened[user]:
                        user_recommendations.append(song)
                f.write('%s\n' % ','.join([user] + user_recommendations))

    def run(self):
        t0 = time.time()

        data = self._load_dataset()
        t1 = Timer.log_elapsed_time('Loading training dataset', t0)

        popular_songs = self.__compute_song_popularity(data)
        #print popular_songs[:100]
        t2 = Timer.log_elapsed_time('Computing song popularity', t1)

        user_listened = self._get_user_song_dict(data)
        #print user_listened['d7083f5e1d50c264277d624340edaaf3dc16095b']
        t3 = Timer.log_elapsed_time('Getting songs users already heard', t2)

        ordered_users = self._get_ordered_users()
        #print ordered_users[:2]
        t4 = Timer.log_elapsed_time('Getting the canonical ordering of users',
                                    t3)

        self.__format_submission(popular_songs, user_listened, ordered_users)
        t5 = Timer.log_elapsed_time('Writing submission', t4)

class CosineSimilarityRecommender(BaseRecommender):
    """
    Strategy: Calculate the user-user and song-song locally weighted cosine
    similarities as follows (for users or songs u, v):
    w_uv = |u.v| / (||u||| |v||) where u.v is the dot product of the two
                                 vectors and ||u|| and ||v|| are the L2 norms
         = u & v / (len(u) len(v)) since elements in u, v are either 0 or 1,
                                   where u & v is the set intersection
    We want to parameterize the relative contributions of the vectors:
         = u & v / (len(u)^alpha len(v)^(1-alpha))
    And parameterize the contribution of each individual weight:
    f(w_uv) = w_uv^q
    Each w_uv is an element of the corresponding user-user or song-song weight
    matrix M or N (respectively).

    Then, to compute the score of song s for user u:
    From the user-user weight matrix M (let U be the set of all users):
    s_su = sum(for v in U != u: M_uv * I_vs)
    For the song-song weight matrix N (let S be the set of all songs):
    s_su = sum(for t in S != s: N_st * I_ut)
    Where I_ij is 1 if user i has listened to song j and 0 otherwise.
    At a high level: the user-based score sums over user-based similarity to
    all other users who have listened to that song; the song-based score sums
    over song-based similarity to all other songs that user has listened to.

    Finally, the recommendation is given by the top 500 songs from mixing the
    song-based and user-based models by taking the recommendations made by each
    model with probability p for the song-based model and probability 1-p for
    the user-based model.

    The entire system is parameterized by alpha, q, p
    The optimal parameters in the paper were:
    Song model: alpha=0.15, q=3
    User model: alpha=0.3, q=5
    p=0.8

    Paper: http://www.ke.tu-darmstadt.de/events/PL-12/papers/08-aiolli.pdf
    """

    def __init__(self):
        t0 = time.time()
        data = self._load_dataset()
        t1 = Timer.log_elapsed_time('Loading training dataset', t0)
        self.__users = self._get_ordered_users()
        t2 = Timer.log_elapsed_time('Getting user list', t1)
        self.__songs = self._get_ordered_songs()
        t3 = Timer.log_elapsed_time('Getting song list', t2)
        self.__user_song_dict = self._get_user_song_dict(data)
        t4 = Timer.log_elapsed_time('Getting user-song mapping', t3)
        self.__song_user_dict = self._get_song_user_dict(data)
        Timer.log_elapsed_time('Getting song-user mapping', t4)

    def __cosine_similarity(self, u, v, alpha, q, foruser=False):
        """
        @u, v [str]: Song or user ids
        @alpha [float]: Weighting parameter from 0.0 to 1.0, inclusive
        @q [int]: Weighting parameter, a nonnegative integer
        @foruser [bool]: True if u and v are users (use the user set)
                         False if u and v are songs (use the song set)
                          |set(u) INTERSECT set(v)|
        similarity w_uv = ---------------------------
                          |set(u)|^alpha * |set(v)|^(1-alpha)
        @return [float] w_uv^q
        """

        curr_dict = self.__user_song_dict if foruser else self.__song_user_dict
        if u in curr_dict and v in curr_dict:
            u_set = curr_dict[u]
            v_set = curr_dict[v]
            return (len(u_set & v_set)
                    / (len(u_set) ** alpha * len(v_set) ** (1 - alpha))) ** q
        return 0.0 # There are some songs that haven't been listened to. Set
                   # their similarity vectors to 0

    def __iterate_model(self, alpha, q, foruser=False):
        """
        @return [dict]: |user|x|user| map of user-user similarities or a
                        |song|x|song| map of song-song similarities
            { [u/s id]: { [u/s id]: [w_01], [u/s id]: [w_02], ... },
              [u/s id]: { [u/s id]: [w_10], [u/s id]: [w_12], ... },
              ... }
        """
        similarities = {}
        curr_set = self.__users if foruser else self.__songs
        for i in xrange(len(curr_set)):
            similarities[curr_set[i]] = {}
            #print '  Iteration: %d/%d %s' % (i, len(curr_set), curr_set[i])
            for j in xrange(len(curr_set)):
                if i != j:
                    similarities[curr_set[i]][curr_set[j]] = \
                        self.__cosine_similarity(curr_set[i], curr_set[j],
                                                 alpha, q, foruser=foruser)
        return similarities

    def __write_similarities(self):
        return

    def __debug_similarities(self, similarities):
        for x1, x1similarities in similarities.iteritems():
            for x2, x1x2sim in x1similarities.iteritems():
                if x1x2sim != 0:
                    print x1, x2, x1x2sim

    def run(self):
        t0 = time.time()

        user_similarities = self.__iterate_model(0.5, 1, foruser=True)
        t1 = Timer.log_elapsed_time('Computing user-user similarity', t0)
        song_similarities = self.__iterate_model(0.5, 1, foruser=False)
        t2 = Timer.log_elapsed_time('Computing song-song similarity', t1)
        self.__debug_similarities(user_similarities)
        self.__debug_similarities(song_similarities)

class CosineSimilarityMapReduce(BaseRecommender):

    def format_input(self, infile='kaggle_visible_evaluation_triplets.txt',
                     outfile='song_users_visible_evaluation.txt'):
        """
        Helper function that rewrites the input format from:
            "[user id] [song id] [listened count]\n"
        To:
            "[song id] [user id] [user id] [user id] ...\n"
        Each song followed by all the users who listened to that song
        """

        data = self._load_dataset()

        song_users = {}
        for line in data:
            user, song, _ = line.strip().split('\t')
            if song in song_users:
                song_users[song].add(user)
            else:
                song_users[song] = set([user])

        with open(outfile, 'w') as fout:
            for song, users in song_users.iteritems():
                fout.write('%s %s\n' % (song, ' '.join(users)))

    def map(self, separator='\t'):
        """
        Suppose we are calculating user-user similarity.
        For each "song user user user ..." line:
            emit ((user, user), song) for each pair of users
        See mapper.py for implementation.
        """
        return

    def reduce(self):
        """
        For each ((user, user), [songs]) tuple:
            emit len(songs)
        See reducer.py for implementation.
        """
        return

if __name__=='__main__':
    #PopularityRecommender().run()
    #CosineSimilarityRecommender().run()
    CosineSimilarityMapReduce().format_input()
