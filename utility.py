import sys
if sys.version_info < (3, 0):
    raise Exception('This project requires Python 3 - mainly for better Unicode support')
    
# "global" read-only variables
DATA_DIR = 'datasets/'
LANGUAGES = ['en', 'zh']

# TODO: call this once at startup
def seed_rng():
    import random
    random.seed(2016)


# run with "python -O" to disable assertions globally