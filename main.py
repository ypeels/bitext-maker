import os

from taxonomy import Taxonomy
from utility import DATA_DIR
from yaml_reader import read_file




# interface classes between raw YAML and program logic - because so much is subject to change...

# TODO: put Bank classes into their own file(s) once the interface is stable enough
class NameBank:
    def __init__(self, filename):
        self.__data = read_file(filename)
    
    def find_tagged(self, target_tag):
        # TODO: handle single-tag case where it's not even a list?
        return [item['nameset'] for item in self.__data 
            for tag in item['tags'] if TAXONOMY.isa(tag, target_tag)]
        
        
        #if tag in item['tags']]
  

# TODO: inherit from object
class Clause:
    def __init__(self):
        self.__symbols = {}
        self.__nodes = {}
        
        self.__syntax = {}
        self.__semantics = {}
        
        

    # TODO: have Clause reach into TemplateBank 
    def set_template(self, syntax, semantics):
        
        
        # should I really be storing all this raw data? can I just store the bits I need and discard the rest?
        # but I suppose it's all shallow-copying anyway...
        self.__set_syntax(syntax)
        self.__set_semantics(semantics)               

        
        
    def __set_syntax(self, syntax):
        self.__parse_symbols(syntax)
        self.__syntax = syntax
        self.__make_nodes()
        
    def __set_semantics(self, semantics):
        self.__semantics = semantics
        self.__make_nodes()
            
        
    def __parse_symbols(self, syntax):
        self.__symbols = syntax['symbols']
        assert(type(self.__symbols) == dict)
        
    # hey, notice that you don't really have to order the symbols until generation time anyway, even if specified by templates
    def __make_nodes(self):
        if self.__semantics and self.__syntax:            
            assert(not self.__nodes) # this function should only be called once, for initialization 
        
            for s in self._symbols():
                self.__nodes[s] = make_node(self._type_for_symbol(s), tags=self._tags_for_symbol(s)) # requires symbols to be unique... but they SHOULD be, since they're in a dict
        
    # notice that populating the nodes is a separate step from just constructing them
    #def populate_nodes(self):
        
        
    ### internal functions that I might still want to noodle with at the interactive prompt ###
    def _symbols(self):
        return self.__symbols.keys()
        
    def _type_for_symbol(self, symbol):
        return self.__symbols[symbol]['type']
        
    def _tags_for_symbol(self, symbol):
        assert(self.__syntax and self.__semantics) # must be initialized
        
        lang_tags = {}
        for lang in LANGUAGES:
            try:
                tags = self.__syntax['templates'][lang]['tags'][symbol]
                if type(tags) is not list:
                    tags = [tags]
                lang_tags[lang] = tags 
            except KeyError as e:
                pass # not every language is going to have syntactic tags for every symbol...
        
        try:        
            main_tags = self.__semantics['tags'].get(symbol) or []
        except KeyError as e:
            raise(e) # TODO: handle gracefully
            
        return main_tags.append(lang_tags)
        
    ### TODO: delete these debugging aliases ###
    def _syntax(self):
        return self.__syntax
    def _semantics(self):
        return self.__semantics

        
    #def symbols_needed(self):
    #    return [v['type'] for v in self.__symbols.values()]
        
        
class NounPhrase:
    def __init__(self, tags=[]):
        pass
        
        
def make_node(type, **kwargs):
    '''Object factory that will instantiate the appropriate class, with an optional dict of tags, etc.'''
    print(type, kwargs)
make_node('NP', tags=['man', 'plural'])
        

### 1. read data from databases - giant, read-only globals ###
LANGUAGES = ['en', 'zh']
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

RAW_VERB_TEMPLATES = read_file(DATA_DIR + 'verb_templates.yml')
        
        
NAME_BANK = NameBank(DATA_DIR + 'namesets.yml') #read_file(DATA_DIR + 'namesets.yml')
# TODO: load language-specific name files, for any languages that might have noun declensions

TAXONOMY = Taxonomy(DATA_DIR + 'taxonomy.yml')





### 2. Generate sentences ###

#def hello():
template = RAW_VERB_TEMPLATES[1]
clause = Clause()

# TODO: have the Clause grab its own data from a TemplateBank
# well, it should really do this
clause.set_template(template['syntax'], template['semantics'][0])

# putting logic outside the class seems like a BAD idea - it kind of defeats the whole point of encapsulation
#print(clause.symbols_needed())

#hello()






# dependents/specifics - just pick SOMETHING to start with 
names = NAME_BANK
women = names.find_tagged('woman')
#men = names.find_tagged('man')
people = names.find_tagged('person')

# pick a verb, any verb

# pick subject and object, based on constraints?

# render sentence


# TODO: class NounPhrase 
    # TODO: allow verb (gerund/infinitive) as head word
    # TODO: class Word

# TODO: class Verb? no, I think each Verb naturally lives inside a Clause, even if it's a finite-verb clause