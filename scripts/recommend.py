import argparse
import os
import random
import time

class Timer:
    @classmethod
    def log_elapsed_time(cls, s, prev_time):
        curr_time = time.time()
        print '[Elapsed time] %s: %f' % (s, curr_time - prev_time)
        return curr_time

class BaseRecommender:
    _ROOT_DIR = os.environ['ROOT_DIR']
    _DATA_FOLDER = 'data/train'
    _DATA_FILE = 'kaggle_visible_evaluation_triplets.txt'

    def _load_dataset(self, filepath=
                      ('%s/%s/%s' % (_ROOT_DIR, _DATA_FOLDER, _DATA_FILE))):
        with open(filepath) as f:
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

    def get_popular_songs(self, limit=500):
        data = self._load_dataset()
        return self.__compute_song_popularity(data)[:limit]

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

    def __init__(self, filepath=None):
        t0 = time.time()
        data = (self._load_dataset(filepath) if filepath
                else self._load_dataset())
        t1 = Timer.log_elapsed_time('Loading training dataset', t0)
        self._users = self._get_ordered_users()
        t2 = Timer.log_elapsed_time('Getting user list', t1)
        self._songs = self._get_ordered_songs()
        t3 = Timer.log_elapsed_time('Getting song list', t2)
        self._user_song_dict = self._get_user_song_dict(data)
        t4 = Timer.log_elapsed_time('Getting user-song mapping', t3)
        self._song_user_dict = self._get_song_user_dict(data)
        Timer.log_elapsed_time('Getting song-user mapping', t4)

    def __cosine_similarity(self, curr_dict, u, v, alpha, q, foruser=True):
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

        if u in curr_dict and v in curr_dict:
            u_set = curr_dict[u]
            v_set = curr_dict[v]
            return (len(u_set & v_set)
                    / (len(u_set) ** alpha * len(v_set) ** (1 - alpha))) ** q
        return 0.0 # There are some songs that haven't been listened to. Set
                   # their similarity vectors to 0

    def __iterate_model(self, alpha, q, foruser=True, threshold=0):
        """
        UNUSED - too slow
        @return [dict]: |user|x|user| map of user-user similarities or a
                        |song|x|song| map of song-song similarities
            { [u/s id]: { [u/s id]: [w_01], [u/s id]: [w_02], ... },
              [u/s id]: { [u/s id]: [w_10], [u/s id]: [w_12], ... },
              ... }
        """
        similarities = {}
        curr_dict = self._user_song_dict if foruser else self._song_user_dict
        curr_set = self._users if foruser else self._songs
        other_set = self._songs if foruser else self._users
        for i in xrange(len(curr_set)):
            similarities[curr_set[i]] = {}
            print '    Iteration: %d/%d %s' % (i, len(curr_set), curr_set[i])

            for j in xrange(len(curr_set)):
                u, v = curr_set[i], curr_set[j]
                if (i != j and u in curr_dict and v in curr_dict
                    and len(curr_dict[u] & curr_dict[v]) > threshold):

                    u_set = curr_dict[u]
                    v_set = curr_dict[v]
                    similarity = (
                        len(u_set & v_set) /
                        (len(u_set) ** alpha * len(v_set) ** (1 - alpha))
                    ) ** q
                    similarities[curr_set[i]][curr_set[j]] = similarity
        return similarities

    def __iterate_model_fast(self, alpha, q, foruser=True, threshold=0):
        """
        Basically, a serial version of the MR algorithm.
        @return [dict]: |user|x|user| map of user-user similarities or a
                        |song|x|song| map of song-song similarities
            { [u/s id]: { [u/s id]: [w_01], [u/s id]: [w_02], ... },
              [u/s id]: { [u/s id]: [w_10], [u/s id]: [w_12], ... },
              ... }
        """
        curr_dict = self._user_song_dict if foruser else self._song_user_dict
        other_dict = self._song_user_dict if foruser else self._user_song_dict
        intersections = {}
        similarities = {}
        count, dictlen = 0, len(other_dict)
        for entityid, related in other_dict.iteritems():
            if count % 10000 == 0:
                print count, dictlen
            relatedlist = list(related)
            for i in xrange(len(relatedlist)):
                for j in xrange(len(relatedlist)):
                    if i != j:
                        if (relatedlist[i], relatedlist[j]) in intersections:
                            intersections[(relatedlist[i], relatedlist[j])] += 1
                        else:
                            intersections[(relatedlist[i], relatedlist[j])] = 1
            count += 1
        count, dictlen = 0, len(other_dict)
        for itempair, count in intersections.iteritems():
            if count % 10000 == 0:
                print count, dictlen
            if count > threshold:
                item1, item2 = itempair
                item1len = len(curr_dict[item1])
                item2len = len(curr_dict[item2])
                similarity = (count
                              / (item1len ** alpha * item2len ** (1 - alpha))
                              ** q)
                if item1 in similarities:
                    similarities[item1][item2] = similarity
                else:
                    similarities[item1] = { item2: similarity }
            count += 1
        return similarities

    def __write_similarities(self, similarities, outfile='similarities.txt'):
        with open(outfile, 'w') as f:
            for x1, x1similarities in similarities.iteritems():
                for x2, x1x2sim in x1similarities.iteritems():
                    if x1x2sim != 0:
                        f.write('%s\t%s\t%f\n' % (x1, x2, x1x2sim))

    def __debug_similarities(self, similarities):
        for x1, x1similarities in similarities.iteritems():
            for x2, x1x2sim in x1similarities.iteritems():
                if x1x2sim != 0:
                    print x1, x2, x1x2sim

    def train(self, alpha=0.5, q=1, foruser=False, threshold=0):
        print (('Training for %s with parameters:\n'
                '  alpha=%g\n'
                '  q=%d\n'
                '  threshold=%d')
                % ('users' if foruser else 'songs', alpha, q, threshold))
        t0 = time.time()

        outfile = ('user-similarities_%g_%d_%d.txt' % (alpha, q, threshold)
                   if foruser else
                   'song-similarities_%g_%d_%d.txt' % (alpha, q, threshold))
        #similarities = self.__iterate_model(alpha, q, foruser=foruser,
        #                                    threshold=threshold)
        similarities = self.__iterate_model_fast(alpha, q, foruser=foruser,
                                                 threshold=threshold)
        t1 = Timer.log_elapsed_time('Computing similarities', t0)
        self.__write_similarities(similarities, outfile=outfile)

class CosineSimilarityMapReduce(CosineSimilarityRecommender):

    __USER_MODEL_FOLDER = 'data/models/usersim'
    __SONG_MODEL_FOLDER = 'data/models/songsim'
    __INFILE = 'part-00000'
    __OUTFILE = 'similarities'

    @classmethod
    def format_input(cls, infile, outfile, foruser=True):
        """
        Helper function that rewrites the input format from:
        For users:
            "[user id] [song id] [listened count]\n"
        To:
            "[song id] [user id] [user id] [user id] ...\n"
        Each song followed by all the users who listened to that song. This
        file is used in the MapReduce job to construct the sparse adjacency
        list.

        For songs:
            "[user id] [song id] [listened count]\n"
        To:
            "[user id] [song id] [song id] [song id] ...\n"
        Each user followed by all the songs that user listened to. This file is
        used in the MapReduce job to construct the sparse adjacency list.

        @param foruser [bool]: True to construct output for the user-user
                               matrix, False to construct output for the
                               song-song matrix.
                               The naming is a bit counter-intuitive. The
                               reasoning is if the output file is
                               "[song] [user] [user] [user], ...", we use that
                               in MapReduce to construct a count over all
                               user-user pairs for that song, which gets us a
                               user-user matrix.
        """

        print 'Formatting input'

        with open(infile) as f:
            data = f.readlines()

        entity_map = {} # Either { user: [songs] } or { song: [users] }
        for line in data:
            user, song, _ = line.strip().split('\t')
            if foruser:
                if song in entity_map:
                    entity_map[song].add(user)
                else:
                    entity_map[song] = set([user])
            else:
                if user in entity_map:
                    entity_map[user].add(song)
                else:
                    entity_map[user] = set([song])

        outfilename = ('%s_song_users.txt' % outfile if foruser
                       else '%s_user_songs.txt' % outfile)

        print 'Writing formatted input to %s' % outfilename

        with open(outfilename, 'w') as fout:
            for k, v in entity_map.iteritems():
                fout.write('%s %s\n' % (k, ' '.join(v)))

    def mapper(self, line):
        """
        Suppose we are calculating user-user similarity.
        For each "song user user user ..." line:
            emit ((user, user), song) for each pair of users
        See mapper.py for implementation.
        """
        return

    def reducer(self, key, values):
        """
        For each ((user, user), [songs]) tuple:
            emit len(songs)
        See reducer.py for implementation.
        """
        return

    def __calculate_similarities(self, alpha=0.5, q=1, foruser=True,
                                 threshold=0, infilename=__INFILE,
                                 outfilename=__OUTFILE):
        """
        Calculates the cosine similarities for an intersection file with the
        format:
            "[user/song u id] [user/song v id] [|u & v|]"
        As it reads similarities in the input file @infilename, it writes the
        following to an output file @outfilename:
            "[user/song u id] [user/song v id] [f(w_uv)]"
        """

        def cosine_similarity(curr_dict, u, v, intersection):
            sim = (intersection /
                   (len(curr_dict[u]) ** alpha *
                    len(curr_dict[v]) ** (1 - alpha)))
            return sim ** q

        curr_dict = self._user_song_dict if foruser else self._song_user_dict
        folder = (self.__USER_MODEL_FOLDER if foruser
                  else self.__SONG_MODEL_FOLDER)
        outfilename = '%s_%g_%d_%d.txt' % (outfilename, alpha, q, threshold)
        infile = '%s/%s/%s' % (self._ROOT_DIR, folder, infilename)
        outfile = '%s/%s/%s' % (self._ROOT_DIR, folder, outfilename)
        with open(infile, 'r') as fin, open(outfile, 'w') as fout:
            for line in fin:
                linelist = line.split('\t')
                id1, id2 = linelist[0].split(':')
                count = int(linelist[1])
                if count > threshold:
                    sim = cosine_similarity(curr_dict, id1, id2, count)
                    fout.write('%s\t%s\t%f\n' % (id1, id2, sim))

    def train(self, alpha=0.5, q=1, foruser=True, threshold=0):
        print (('Training for %s with parameters:\n'
                '  alpha=%g\n'
                '  q=%d\n'
                '  threshold=%d')
                % ('users' if foruser else 'songs', alpha, q, threshold))
        t0 = time.time()

        self.__calculate_similarities(
            alpha=alpha, q=q, foruser=foruser, threshold=threshold
        )
        if foruser:
            Timer.log_elapsed_time('Computing user similarity', t0)
        else:
            Timer.log_elapsed_time('Computing song similarity', t0)

    def __generate_recommendations(self, user_model_scores, song_model_scores,
                                   user_song_dict_idx, p=0.5, tau=500):
        """
        Strategy: Given an ordered set of user model song recommendations and
        song model song recommendations, to make @tau recommendations, for each
        recommendation, take the next song model recommendation with
        probability @p and the next user model recommendation with probability
        1-@p, and then fill the remaining songs (if any) with the most popular
        songs. All songs the user has already listened to should be removed
        before this process starts.

        @param user_model_scores [dict]: Nonzero scores for each song per user
            { [useridx]: { [songidx]: score } }
        @param song_model_scores [dict]: Same as above, but for song models
        @param user_song_dict_idx [dict]: Mapping of all songidx a useridx has
                                    listened to
            { [useridx]: set([songidx, songidx, ...]) }
        @param p [float]: Probability of using the song model recommendation
                    (otherwise, use the user model recommendations)
        @param tau [int]: Number of recommendations to make
        @return [list]: List of lists of recommendations for each useridx
            [[song1, song2, ...], ...]
        """
        song_index_map = {s: i for i, s in enumerate(self._songs)}
        popular_songs = [song_index_map[song] for song in
                         PopularityRecommender().get_popular_songs()]
        recommendations = []
        tloop = time.time()
        for useridx in xrange(len(self._users)):
            print '%d/%d' % (useridx, len(self._users))
            user_listened = user_song_dict_idx[useridx]
            user_recommendations = []

            if useridx in user_model_scores:
                user_model_user_scores = user_model_scores[useridx]
                user_model_user_scores_list = [song for song in sorted(
                    user_model_user_scores.keys(),
                    key=lambda x: user_model_user_scores[x],
                    reverse=True
                ) if song not in user_listened]
            else:
                user_model_user_scores_list = []
            if useridx in song_model_scores:
                song_model_user_scores = song_model_scores[useridx]
                song_model_user_scores_list = [song for song in sorted(
                    song_model_user_scores.keys(),
                    key=lambda x: song_model_user_scores[x],
                    reverse=True
                ) if song not in user_listened]
            else:
                song_model_user_scores_list = []

            for _ in xrange(tau):
                if song_model_user_scores_list and user_model_user_scores_list:
                    if random.random() < p:
                        songidx = song_model_user_scores_list.pop(0)
                        if songidx in user_model_user_scores_list:
                            user_model_user_scores_list.remove(songidx)
                    else:
                        songidx = user_model_user_scores_list.pop(0)
                        if songidx in song_model_user_scores_list:
                            song_model_user_scores_list.remove(songidx)
                    user_recommendations.append(songidx)
                elif song_model_user_scores_list:
                    user_recommendations.append(
                        song_model_user_scores_list.pop(0)
                    )
                elif user_model_user_scores_list:
                    user_recommendations.append(
                        user_model_user_scores_list.pop(0)
                    )
                else:
                    break
            # Fill the remaining with popular song recommendations
            popular_songs_copy = popular_songs[:]
            user_recommendations_current_set = set(user_recommendations)
            while len(user_recommendations) < tau:
                nextsongidx = popular_songs_copy.pop(0)
                if nextsongidx not in user_recommendations_current_set:
                    user_recommendations.append(nextsongidx)
            recommendations.append(user_recommendations)
            tloop = Timer.log_elapsed_time('recommendations', tloop)
        return recommendations

    def __format_submission(self, recommendations, filename):
        """
        See corresponding method for each parameter
        Output:
            '[user id], [song id], [song id], ..., [song id]'
            ...
        """
        with open(filename, 'w') as f:
            for useridx, recommendation_idxs in enumerate(recommendations):
                song_recommendations = [self._songs[songidx] for songidx in
                                        recommendation_idxs]
                f.write('%s\n' % ','.join([self._users[useridx]]
                                          + song_recommendations))

    def recommend(self, userfile, songfile, p=0.5, tau=500,
                  output='./submissions.txt'):
        """
        Scores all nonzero user-song pairs for both the user and song models.
        To compute the score of song s for user u:
        From the user-user weight matrix M (let U be the set of all users):
            s_su = sum(for v in U != u: M_uv * I_vs)
        For the song-song weight matrix N (let S be the set of all songs):
            s_su = sum(for t in S != s: N_st * I_ut)
        Where I_ij is 1 if user i has listened to song j and 0 otherwise.
        At a high level: the user-based score sums over user-based similarity
        to all other users who have listened to that song; the song-based score
        sums over song-based similarity to all other songs that user has
        listened to.
        For performance reasons, for each user in the user-user similarity
        matrix, we precompute the set intersection of users who have listened
        to the song and users similar to that user, and sum over the weights of
        that set (and likewise for the song-song simlarity matrix).

        To recommend, we take the scores and choose between recommendations
        given by the user model and the song model with the probability
        parameter @p (see __generate_recommendations() for more details).

        @param userfile [str]: File with pre-computed user model weights.
        @param songfile [str]: File with pre-computed song model weights.
        @param p [float]: Probability of selecting the user model
                          recommendation.
        @param tau [int]: Total number of recommendations per user.
        @param output [str]: Output file.
        """


        t0 = time.time()

        song_index_map = {s: i for i, s in enumerate(self._songs)}
        user_index_map = {u: i for i, u in enumerate(self._users)}

        with open('%s/data/train/%s' % (self._ROOT_DIR, self._DATA_FILE)) as f:
            data = f.readlines()

        user_song_dict_idx = {}
        song_user_dict_idx = {}
        for line in data:
            user, song, _ = line.strip().split('\t')
            useridx, songidx = user_index_map[user], song_index_map[song]
            if useridx in user_song_dict_idx:
                user_song_dict_idx[useridx].add(songidx)
            else:
                user_song_dict_idx[useridx] = set([songidx])
            if songidx in song_user_dict_idx:
                song_user_dict_idx[songidx].add(useridx)
            else:
                song_user_dict_idx[songidx] = set([useridx])

        # Load user similarities
        user_similarities = {}
        with open(userfile) as fusers:
            for line in fusers:
                u1, u2, similarity = line.strip().split('\t')
                u1idx, u2idx = user_index_map[u1], user_index_map[u2]
                if u1 in user_similarities:
                    user_similarities[u1idx][u2idx] = float(similarity)
                else:
                    user_similarities[u1idx] = {}
                    user_similarities[u1idx][u2idx] = float(similarity)

        t1 = Timer.log_elapsed_time('Loaded sparse user similarity matrix', t0)

        # Compute user scores
        otheruseridxs = user_similarities.keys()
        user_similarity_set = dict(zip(user_similarities,
                                   map(set, user_similarities.values())))
        user_model_scores = {}
        tloop = time.time()
        for songidx in xrange(len(self._songs)):
            if songidx in song_user_dict_idx:
                print '%d/%d' % (songidx, len(self._songs))
                # Users that have listened to the song
                song_user_set = song_user_dict_idx[songidx]
                for useridx in otheruseridxs:
                    similar_users = song_user_set & user_similarity_set[useridx]
                    score = 0.0
                    for otheruseridx in similar_users:
                        score += user_similarities[useridx][otheruseridx]
                    if score > 0:
                        if useridx in user_model_scores:
                            user_model_scores[useridx][songidx] = score
                        else:
                            user_model_scores[useridx] = { songidx: score }

                print len(user_model_scores)
                tloop = Timer.log_elapsed_time('user scores', tloop)

        t2 = Timer.log_elapsed_time('Computed user model scores', t1)

        # Load song similarities
        song_similarities = {}
        with open(songfile) as fsongs:
            for line in fsongs:
                s1, s2, similarity = line.strip().split('\t')
                s1idx, s2idx = song_index_map[s1], song_index_map[s2]
                if s1 in song_similarities:
                    song_similarities[s1idx][s2idx] = float(similarity)
                else:
                    song_similarities[s1idx] = {}
                    song_similarities[s1idx][s2idx] = float(similarity)

        t3 = Timer.log_elapsed_time('Loaded sparse song similarity matrix', t2)

        # Compute song scores
        othersongidxs = song_similarities.keys()
        song_similarity_set = dict(zip(song_similarities,
                                   map(set, song_similarities.values())))
        song_model_scores = {}
        tloop = time.time()
        for useridx in xrange(len(self._users)):
            print '%d/%d' % (useridx, len(self._users))
            # Songs the user has listened to
            user_song_set = user_song_dict_idx[useridx]
            for songidx in othersongidxs:
                similar_songs = user_song_set & song_similarity_set[songidx]
                score = 0.0
                for othersongidx in similar_songs:
                    score += song_similarities[songidx][othersongidx]
                if score > 0:
                    if useridx in song_model_scores:
                        song_model_scores[useridx][songidx] = score
                    else:
                        song_model_scores[useridx] = { songidx: score }

            print len(song_model_scores)
            tloop = Timer.log_elapsed_time('song scores', tloop)

        t4 = Timer.log_elapsed_time('Computed song model scores', t3)

        recommendations = self.__generate_recommendations(user_model_scores,
                                                          song_model_scores,
                                                          user_song_dict_idx,
                                                          p, tau)
        Timer.log_elapsed_time('Generated recommendations', t4)

        self.__format_submission(recommendations, output)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--format-input', action='store_const', const=True,
                        help='Format data for MR processing')
    parser.add_argument('--train', action='store_const', const=True,
                        help='Train the model')
    parser.add_argument('--recommend', action='store_const', const=True,
                        help='Generate recommendations')
    parser.add_argument('--no-mr', action='store_const', const=True,
                        help='Use the non-MR model')
    parser.add_argument('--alpha', type=float,
                        help='alpha tuning parameter in cosine computation')
    parser.add_argument('--q', type=int,
                        help='q tuning parameter in locality weighting')
    parser.add_argument('--foruser', type=str,
                        help=('[true/false] to only run for users or only for'
                              ' songs (runs both if this is not supplied)'))
    parser.add_argument('--threshold', type=int,
                        help='Set intersection magnitude cutoff')
    parser.add_argument('--p', type=float,
                        help='p tuning parameter in stochastic recommendation'
                             ' - % chance to use the song model recommendation'
                             ' instead of the user model recommendation')
    parser.add_argument('--tau', type=int,
                        help='Number recommendations to make')
    parser.add_argument('--input', type=str, help='Input file path')
    parser.add_argument('--output', type=str, help='Output file path')
    parser.add_argument('--usersim-file', type=str,
                        help='User similarities file path')
    parser.add_argument('--songsim-file', type=str,
                        help='Song similarities file path')
    args = parser.parse_args()

    if args.format_input:
        CosineSimilarityMapReduce.format_input(args.input, args.output,
                                               foruser=True)
        CosineSimilarityMapReduce.format_input(args.input, args.output,
                                               foruser=False)

    if args.train:
        alpha = args.alpha if args.alpha else 0.5
        q = args.q if args.q else 1
        threshold = args.threshold if args.threshold else 0
        if args.no_mr:
            recommender = (CosineSimilarityRecommender(args.input)
                           if args.input else CosineSimilarityRecommender())
        else:
            recommender = CosineSimilarityMapReduce()
        if args.foruser:
            if args.foruser.lower() == 'true':
                recommender.train(
                    alpha=alpha, q=q, foruser=True, threshold=threshold
                )
            elif args.foruser.lower() == 'false':
                recommender.train(
                    alpha=alpha, q=q, foruser=False, threshold=threshold
                )
        else:
            recommender.train(
                alpha=alpha, q=q, foruser=True, threshold=threshold
            )
            recommender.train(
                alpha=alpha, q=q, foruser=False, threshold=threshold
            )

    if args.recommend and args.usersim_file and args.songsim_file:
        p = args.p if args.p else 0.5
        tau = args.tau if args.tau else 500
        if args.output:
            CosineSimilarityMapReduce().recommend(args.usersim_file,
                                                  args.songsim_file,
                                                  p=0.5, tau=tau,
                                                  output=args.output)
        else:
            CosineSimilarityMapReduce().recommend(args.usersim_file,
                                                  args.songsim_file,
                                                  p=0.5, tau=tau)
