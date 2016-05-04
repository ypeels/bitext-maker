import sys
if sys.version_info < (3, 0):
    raise Exception('This project requires Python 3 - mainly for better Unicode support')
    
# "global" read-only variables
DATA_DIR = 'datasets/'
LANGUAGES = ['en', 'zh']
USE_RANDOM = False

# TODO: call this once at startup
# BUT there might still be nondeterminism in terms of dict key ordering...
def seed_rng():
    import random
    random.seed(2016)


# run with "python -O" to disable assertions globally