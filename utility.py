import sys
if sys.version_info < (3, 0):
    raise Exception('This project requires Python 3 - mainly for better Unicode support')
    
# "global" read-only variables
DATA_DIR = 'datasets/'
LANGUAGES = ['en', 'zh']
USE_RANDOM = True

import operator # itemgetter
import random

def nested_sort(items):
    '''
    Sort (string, number) tuples deterministically
    - descending in number
    - within each number, ascending in string
    '''
    return (
        sorted(
            sorted(items, key=operator.itemgetter(0)),      # inner ascending sort by secondary key (string)
            reverse=True, 
            key=operator.itemgetter(1)))                    # outer descending sort by primary key (number)

# TODO: call this once at startup
# BUT there might still be nondeterminism in terms of dict key ordering...
def seed_rng(seed=2016):
    random.seed(seed)


# run with "python -O" to disable assertions globally