#!/usr/bin/python

import sys

def main(separator='\t'):
    def read_input(f):
        for line in f:
            yield line.split()

    for line in read_input(sys.stdin):
        song, users = line[0], line[1:]
        for i in xrange(len(users)):
            for j in xrange(len(users)):
                if i != j:
                    # '[user i]:[user j]\t[song k]'
                    print ('%s:%s%s%s'
                           % (users[i], users[j], separator, song))

if __name__=='__main__':
    main()
