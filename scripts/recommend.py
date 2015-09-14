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

    def __get_user_listened_dict(self, data):
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

    def __get_ordered_users(self):
        """
        @return [list]: List of users in the canonical order for submission
            [[user id], [user id], ...]
        """
        with open('%s/data/train/kaggle_users.txt' % self._ROOT_DIR) as f:
            ordered_users = [line.strip() for line in f.readlines()]
        return ordered_users

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

        with open('%s/data/train/kaggle_visible_evaluation_triplets.txt'
                  % self._ROOT_DIR) as f:
            data = f.readlines()
        t1 = Timer.log_elapsed_time('Reading files', t0)

        popular_songs = self.__compute_song_popularity(data)
        #print popular_songs[:100]
        t2 = Timer.log_elapsed_time('Computing song popularity', t1)

        user_listened = self.__get_user_listened_dict(data)
        #print user_listened['d7083f5e1d50c264277d624340edaaf3dc16095b']
        t3 = Timer.log_elapsed_time('Getting songs users already heard', t2)

        ordered_users = self.__get_ordered_users()
        #print ordered_users[:2]
        t4 = Timer.log_elapsed_time('Getting the canonical ordering of users',
                                    t3)

        # This is unnecessary for my custom evaluation script
        """
        song_idx_map = self.__get_song_idx_map()
        #print song_idx_map['SOSOUKN12A8C13AB79']
        t5 = Timer.log_elapsed_time('Getting song index mapping', t4)
        """

        self.__format_submission(popular_songs, user_listened, ordered_users)
        t4 = Timer.log_elapsed_time('Writing submission', t3)

if __name__=='__main__':
    PopularityRecommender().run()

