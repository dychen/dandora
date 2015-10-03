#!/usr/bin/python

from itertools import groupby
from operator import itemgetter
import sys

def main(threshold=0, separator='\t'):
    def read_input(f, separator):
        for line in f:
            yield line.split(separator)

    data = read_input(sys.stdin, separator=separator)
    for usertup, songs in groupby(data, itemgetter(0)):
        count = sum(1 for song in songs)
        if count > threshold: # To decrease I/O and output filesize
            print '%s%s%d' % (usertup, separator, count)

if __name__=='__main__':
    main()
