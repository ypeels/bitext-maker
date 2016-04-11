import os


### 1. read data from databases - giant, read-only globals ###
print('Reading data from files...')
import data
# a bit more typing in the short run, but should be very helpful and sanity-preserving in the long run
#from data import CLAUSE_TEMPLATE_BANK, NAME_BANK, VERBSET_BANK
#from data import LANGUAGES, TAXONOMY
#from data import RAW_NOUNS, RAW_NOUNSETS



# TODO: inherit from object?
class Templated:
    '''Currently covers NP and Clause'''
    def __init__(self, bank):
        self.__template_bank = bank
        
        # syntactic template
        self.__template = None # data.Template
        self.__template_id = ''
        
    def __str__(self): # for interactive probing
        return "{type}({template})".format(type=self.__class__, template=self.__template)
        
    ### "public" API - for use outside this class ###
    def has_template(self):
        return bool(self.__template_id) and bool(self.__template)
    
    def set_template(self, id):
        self.__template = self.__template_bank.get_template_by_id(id)
        assert(type(self.__template) == data.Template)
        self.__template_id = id
        
        
    
        
    ### "pure virtual" functions - to be implemented in derived classes ###


    ### "protected" functions - available to derived classes ###
    def _symbols(self):
        return self.__template.symbols()
        
    # TODO: wrap all accesses to data chunks into dedicated Data objects
        # - their ONE AND ONLY PURPOSE should be to mediate between data and logic
        # - it's tempting to keep things as they are, but that interleaves data calls and logic calls, right?
    # oh hey, this lets me break the rather restrictive inheritance for Clause and NounPhrase
    def _syntax_tags_for_symbol(self, symbol):
        return self.__template.syntax_tags_for_symbol(symbol)


    def _template_id(self):
        return self.__template_id

    def _type_for_symbol(self, symbol):
        return self.__template.type_for_symbol(symbol)


        
    #### "private" functions - not intended to be called outside this class ###


        
        
    ### TODO: delete these debugging aliases ###
    def _template(self):
        return self.__template
    def _template_id(self):
        return self.__template_id



class Clause(Templated):
    def __init__(self): 
        Templated.__init__(self, data.CLAUSE_TEMPLATE_BANK)
        
        self.__verb_category_id = ''
        self.__verb_category = {}
        self.__nodes = {}
        
    # clauses really need to have semantics figured out before populating the next level down (except blank symbols in participles, etc.)
    def has_verb_category(self):
        return bool(self.__verb_category_id) and bool(self.__verb_category)
        
    def set_verb_category(self, category):    
        assert(category in data.VERBSET_BANK.categories())
        self.__verb_category_id = category
        self.__verb_category = data.VERBSET_BANK.get_category(category)
    
    
    # hey, notice that you don't really have to order the symbols until generation time anyway, even if specified by templates
    def _create_nodes(self):
        if self.has_template() and self.has_verb_category():            
            assert(not self.__nodes) # this function should only be called once, for initialization 
        
            for s in self._symbols():
                self.__nodes[s] = create_node(self._type_for_symbol(s), tags=self._tags_for_symbol(s)) # requires symbols to be unique... but they SHOULD be, since they're in a dict
        

    def _tags_for_symbol(self, symbol):
        semantic_tags = self.__verb_category.tags_for_symbol(symbol) or []
        syntax_tags = [self._syntax_tags_for_symbol(symbol)]            
        return semantic_tags + syntax_tags
        



        
        
    # notice that populating the nodes is a separate step from just constructing them
    #def populate_nodes(self):
        
        

        


        
    #def symbols_needed(self):
    #    return [v['type'] for v in self.__symbols.values()]
        
        
class NounPhrase(Templated):
    def __init__(self, tags=[]):
        pass
        
        
def create_node(type, **kwargs):
    '''Object factory that will instantiate the appropriate class, with an optional dict of tags, etc.'''
    print(type, kwargs)
#make_node('NP', tags=['man', 'plural'])
        








### 2. Generate sentences ###

# some quickie testing
names = data.NAME_BANK
women = names.find_tagged('woman')
#men = names.find_tagged('man')
people = names.find_tagged('person')


#def hello():
#template = RAW_CLAUSE_TEMPLATES[1]
clause = Clause()
clause.set_template('transitive')
clause.set_verb_category('action.possession')
print(clause._symbols())
print(clause._syntax_tags_for_symbol('O'))
clause._create_nodes()
#
## TODO: have the Clause grab its own data from a TemplateBank
## well, it should really do this
#clause.set_template(template['syntax'], template['semantics'][0])

# putting logic outside the class seems like a BAD idea - it kind of defeats the whole point of encapsulation
#print(clause.symbols_needed())

#hello()






# dependents/specifics - just pick SOMETHING to start with 



# pick a verb, any verb

# pick subject and object, based on constraints?

# render sentence


# TODO: class NounPhrase 
    # TODO: allow verb (gerund/infinitive) as head word
    # TODO: class Word

# TODO: class Verb? no, I think each Verb naturally lives inside a Clause, even if it's a finite-verb clause