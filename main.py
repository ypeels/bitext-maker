from yaml_reader import read_file
import os

DATA_DIR = 'dict/'
languages = ['en', 'zh']

# interface classes between raw YAML and program logic - because so much is subject to change...

# TODO: put Bank classes into their own file(s) once the interface is stable enough
class NameBank:
    def __init__(self, filename):
        self.__data = read_file(filename)
    
    def find_tagged(self, tag):
        # hey, this is nice and concise
        return [item['nameset'] for item in self.__data if tag in item['tags']]
        
        
        
        

### 1. read data from databases ###
nouns = { lang: read_file(DATA_DIR + 'nouns_{}.yml'.format(lang)) for lang in languages }
nounsets = read_file(DATA_DIR + 'nounsets.yml')

verbs = {}
for lang in languages:
    verb_file = DATA_DIR + 'verbs_{}.yml'.format(lang)
    try:
        verbs[lang] = read_file(verb_file)
    except FileNotFoundError as e:
        print('Skipping verb file for {} - tenseless like zh, right?'.format(lang))
        # TODO: some sort of dummy dict so that verbs['zh'][<anything>] == <anything>, or something similar?

        
names = NameBank(DATA_DIR + 'namesets.yml') #read_file(DATA_DIR + 'namesets.yml')
# TODO: load language-specific name files, for any languages that might have noun declensions




### 2. Generate sentences ###


# dependents/specifics
women = names.find_tagged('woman')
men = names.find_tagged('man')





