import argparse
import os
import time
from recommend import Timer

ROOT_DIR = os.environ['ROOT_DIR']

def evaluate(filename, TAU=500):

    def calculate_mAP(predictions, actuals):
        """
        Calculates the truncated mean average precision between a training and
        a test dataset as defined here:
        http://eceweb.ucsd.edu/~gert/papers/msdc.pdf

        @param predictions [list]: List of lists top k user recommendations
            [[[song id 1], ..., [song id 500]], ...]
        @param actuals [list]: List of lists of (song, user, playcount)
                               triples
            [[[user id], [song id], [playcount]], ...]
        """

        def construct_listened_map(actuals):
            user_listened = {}
            for line in actuals:
                user, song, _ = line
                if user in user_listened:
                    user_listened[user].add(song)
                else:
                    user_listened[user] = set([song])
            return user_listened

        """
        OLD IMPLEMENTATION; UNUSED (Asymptotically slower)

        def calculate_precision_at_k(user, user_songs_k, listened_map, k):
            # Calculate precision-at-k, the proportion of correct
            # recommendations within the top-k of the predicted ranking
            return len([1 for song in user_songs_k
                        if song in listened_map[user]]) / float(k)

        def calculate_average_precision(user, user_songs, listened_map):
            # Calculate average precision, the proportion of correct
            # recommendations from k=1 to @TAU
            precision_at_ks = []
            n_u = min(TAU, len(listened_map[user]))
            for k in range(1, TAU+1):
                if user_songs[k-1] in listened_map[user]:
                    p_k = calculate_precision_at_k(user, user_songs[:k],
                                                   listened_map, k)
                    precision_at_ks.append(p_k)
            return sum(precision_at_ks) / n_u
        """

        def calculate_average_precision(user, user_songs, listened_map):
            # Calculate average precision, the proportion of correct
            # recommendations from k=1 to @TAU
            n_u = min(TAU, len(listened_map[user]))
            num_matches = 0.0
            average_precision = 0.0
            for k in range(1, TAU+1):
                if user_songs[k-1] in listened_map[user]:
                    num_matches += 1.0
                    average_precision += num_matches / k # Precision at k
            return average_precision / n_u

        print '    Loading listened map'
        listened_map = construct_listened_map(actuals) # Matrix M in the paper
        print len(listened_map)

        user_average_precisions = []
        for i, user_predictions in enumerate(predictions):
            if i % 1000 == 0 and i > 0:
                print ('    mAP over %d (out of %d) predictions: %f'
                       % (i, len(predictions),
                          sum(user_average_precisions)
                          / len(user_average_precisions)))
            user = user_predictions[0]
            user_songs = user_predictions[1:]
            if user in listened_map:
                uAP = calculate_average_precision(user, user_songs,
                                                  listened_map)
                user_average_precisions.append(uAP)
        return sum(user_average_precisions) / len(user_average_precisions)

    t0 = time.time()
    with open(filename) as f:
        submission_data = [line.strip().split(',') for line in f.readlines()]
    t1 = Timer.log_elapsed_time('Loaded submission data', t0)
    with open('%s/data/test/year1_valid_triplets_hidden.txt' % ROOT_DIR) as f:
        test_data = [line.strip().split('\t') for line in f.readlines()]
    t2 = Timer.log_elapsed_time('Loaded test data', t1)
    mAP = calculate_mAP(submission_data, test_data)
    t3 = Timer.log_elapsed_time('Evaluated test data', t2)
    return mAP

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', type=str, help='Input file path')
    parser.add_argument('--tau', type=int, help='Number of recommendations')
    args = parser.parse_args()

    tau = args.tau if args.tau else 500
    filename = args.file if args.file else 'submission.txt'

    mAP = evaluate(filename, TAU=tau)
    print 'Mean average precision: %f' % mAP
