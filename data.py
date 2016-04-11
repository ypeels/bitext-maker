'''
Data module - only gets run once; an effective singleton

Note that this file CANNOT be called as a top-level script - circular imports with Taxonomy
'''
import collections
import os

from taxonomy import Taxonomy
from utility import DATA_DIR, LANGUAGES # kept in separate file for fast unit testing
from yaml_reader import read_file

# TODO: put Bank classes into their own file(s) once the interface is stable enough
class Bank:
    '''Base class that reads a single YAML file'''
    def __init__(self, filename):
        self._data = read_file(filename) # TODO: self.__data, and access in derived classes via self._Bank__data? (discourage interactive access)


class NameSetBank(Bank):    
    def _makeN(self, item):
        raise Exception('Unimplemented in abstract base class' + __class__)
        
    def find_tagged(self, target_tag):
        # TODO: handle single-tag case where it's not even a list?
        # TODO: share code with NounSetBank? is it worth sacrificing clarity just to DRY out 2 lines?
        return [NameSet(item['nameset']) for item in self._data 
            for tag in item['tags'] if TAXONOMY.isa(tag, target_tag)]

            
            
class TemplateBank(Bank):
    def get_template_by_id(self, id):
        return Template(self._data[id])

# not currently inheriting Bank, since this is multi-file...
class VerbSetBank:
    def __init__(self, path):
        self.__data = {}
        for basename in os.listdir(path):
            if basename.endswith('.yml'):
                self.__add_file(path + basename)  

    def categories(self):
        return self.__data.keys()
        
    def get_category(self, category):
        return VerbCategory(self.__data[category])
    
    def __add_file(self, filename):
        new_data = read_file(filename)
        
        # error-checking (TODO: dedicated error-checking test file)
        assert(type(new_data) is dict)
        assert(not any(key in self.__data.keys() for key in new_data.keys()))        
        self.__data.update(new_data)
            
            

            
# chunks of data files that nevertheless should be isolated into objects
# this way, if/when the data format changes, ONLY these classes would need to be changed.
# this is a LITTLE different from typical object-oriented programming, since the data files impose external constraints

# as thin as possible to begin with - just the raw data + whatever accessors you need
# then add processing, etc... wait a second, isn't that just standard object-oriented programming??
    # well, this is still important, since it separates Data-level logic from Linguistics-level logic
class Template:
    '''Verb and NP syntax'''
    def __init__(self, data):
        # "declarations"
        self.__data = {}
        self.__symbols = {}
        self.__syntax_tags_per_symbol = collections.defaultdict(dict)
        self.__deps_per_symbol = collections.defaultdict(dict)
        
        #self.__symbol_metadata = collections.defaultdict(collections.defaultdict(dict))
        # e.g., symbol_metadata[symbol]['tags']
        
        self.__data = data        
        self.__parse()
        
    def __str__(self):
        return 'Template({})'.format(self.__data)
        
    def deps_for_symbol(self, symbol):
        return self.__deps_per_symbol[symbol]
        
    def symbols(self):
        return self.__symbols.keys()
        
    def syntax_tags_for_symbol(self, symbol):
        '''
        Returns { 'en': [<en tags>], ... }
        This is a reconstituted data structure (the innermost lists might be shallow copies)
        '''
        return self.__syntax_tags_per_symbol[symbol]
        #return self.__symbol_metadata[symbol]['tags']
        
    def type_for_symbol(self, symbol):
        return self.__data['symbols'][symbol]['type']

        
    def __wrap_as_list(self, item):
        if type(item) is list:
            return item
        else:
            return [item]
        
        
    def __parse(self):
        # parse symbols
        assert(type(self.__data['symbols']) == dict)
        self.__symbols = self.__data['symbols']
        
        # parse tags for each symbol - a bit of non-trivial inversion, so do it here at load time, once-only
        # imperative style is just a bit more DRY and flexible for something like this...
        for lang, metadata in self.__data['templates'].items():
            if lang in LANGUAGES:                
                for symbol, tags in metadata.get('tags', {}).items():
                    self.__syntax_tags_per_symbol[symbol][lang] = self.__wrap_as_list(tags)
                    
                for symbol, deps in metadata.get('dependencies', {}).items():
                    deps_list = self.__wrap_as_list(deps)
                    assert(all(d in self.symbols() for d in deps_list))
                    self.__deps_per_symbol[symbol][lang] = deps_list
                    

        


   
   
# polylingual lexical "Sets" - e.g., { 'en': 'Alice', 'zh': ... }
class VerbCategory:
    '''Verb semantics'''
    def __init__(self, data):
        self.__data = data
        
    def tags_for_symbol(self, symbol):
        return self.__data['tags'].get(symbol)
        
        
class NameSet:
    def __init__(self, data):
        self.__data = data
    def __repr__(self): # TODO: get lists of NameSets to print info using __str__ instead of __repr__?
        return self.__data.__repr__()
            
            
### module-level variables (intended to be read-only after initialization) ###




RAW_NOUNS = { lang: read_file(DATA_DIR + 'nouns_{}.yml'.format(lang)) for lang in LANGUAGES }
RAW_NOUNSETS = read_file(DATA_DIR + 'nounsets.yml')

RAW_VERBS = {}
for lang in LANGUAGES:
    verb_file = DATA_DIR + 'verbs_{}.yml'.format(lang)
    try:
        RAW_VERBS[lang] = read_file(verb_file)
    except FileNotFoundError as e:
        print('Skipping verb file for {} - tenseless like zh, right?'.format(lang))
        # TODO: some sort of dummy dict so that verbs['zh'][<anything>] == <anything>, or something similar?



#raise Exception('''TODO: load verbsets, pass to Clause initializer 
#actually, I think it should just be able to initialize given "transitive" and "action.possessive"''')
        
NAME_BANK = NameSetBank(DATA_DIR + 'namesets.yml')
# TODO: load language-specific name files, for any languages that might have noun declensions

TAXONOMY = Taxonomy(DATA_DIR + 'taxonomy.yml')
VERBSET_BANK = VerbSetBank(DATA_DIR + 'verbsets/')


TEMPLATE_DIR = DATA_DIR + 'templates/'
CLAUSE_TEMPLATE_BANK = TemplateBank(TEMPLATE_DIR + 'clause_templates.yml')
NP_TEMPLATE_BANK = TemplateBank(TEMPLATE_DIR + 'np_templates.yml')




    