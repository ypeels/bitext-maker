import os
import random


### 1. read data from databases - giant, read-only globals ###
print('Reading data from files...')
import data
# a bit more typing in the short run, but should be very helpful and sanity-preserving in the long run
#from data import CLAUSE_TEMPLATE_BANK, NAME_BANK, VERBSET_BANK
#from data import LANGUAGES, TAXONOMY
#from data import RAW_NOUNS, RAW_NOUNSETS

UNIMPLEMENTED_EXCEPTION = Exception('Needs to be implemented in derived class')


# TODO: inherit from object?
# TODO: rename this to "Node"? but will all modifiers, etc. have templates?? or should I use multiple inheritance?? sigh

# duh, just have Templated inherit from Node
class Node: 
    def __init__(self, **options): # contains data, so probably don't want to use as a mixin (would have to call constructor in derived classes)
        self.__dependencies = []
        
        # just store them for now and figure out what to do with them later... can always use dict.pop()
        #if options: 
        self.__options = options # need to instantiate even if empty - that way can query if empty
        
    def add_dependency(self, node, **kwargs):
        self.__dependencies.append((node, kwargs))
        
        
    def add_options(self, options):
        assert(type(options) is dict)
        
        # TODO: allow multiple sources for monolingual tags...
        assert(all(type(v) is list for v in options.values()))
        for key, value in options.items():
            old_value = self.__options.get(key) or []
            # TODO: change self.__options to defaultdict(list) and just use +=? meh, doesn't even save any lines
            self.__options[key] = old_value + value
        
        
        
    def lexicalize_tree(self):
        '''TODO: multiple synsets per node, to allow for outer product'''
        for _, sn in self._subnodes():
            sn.lexicalize_tree()
        self._lexicalize()
        
    # override this iff a node has any lexical ("population") choices to be made
    def _lexicalize(self):
        pass
        
    def _subnodes(self):
        return []
        
    # convenience function for derived classes... breaks encapsulation... but only if you have a valid key?
    def _get_option(self, key):
        return self.__options.get(key)
        
        

class TemplatedNode(Node):
    '''
    A templated node is like "S V O" - and so it generally branches into other nodes and is non-terminal.
    Currently subclasses to NP and Clause
    '''
    def __init__(self, bank, **kwargs):
        Node.__init__(self, **kwargs)
        
        self.__nodes = {}
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
    def _ready_to_create_nodes(self):
        raise UNIMPLEMENTED_EXCEPTION
        
    ### "protected" functions - default implementations, MAY be overridden in derived classes ###
    def _create_subnodes(self):
        if self._ready_to_create_nodes():
            assert(not self.__nodes) # this function should only be called once, for initialization 
        
             # requires symbols to be unique... but they SHOULD be, since they're in a dict
            self.__nodes = { s: create_node(self._type_for_symbol(s), tags=self._tags_for_symbol(s)) 
                for s in self._symbols() }
            
            # hook up dependencies between NODES and their data - all nodes must have been instantiated first
            # add_dependency() should allow pronouns to work all the way across the tree...right?
            for s in self._symbols():                
                for lang, deps in self._deps_for_symbol(s).items():
                    for d in deps:
                        self.__nodes[s].add_dependency(self.__nodes[d], lang=lang)
                        
    def _tags_for_symbol(self, symbol):
        tags = self._syntax_tags_for_symbol(symbol)
        if tags:
            return [tags]
        else:
            return []
            
    ### "protected" - these override the base class ###
    def _subnodes(self):
        return self.__nodes.items()


    ### "protected" functions - available to derived classes ###

    
    def _deps_for_symbol(self, symbol):
        return self.__template.deps_for_symbol(symbol)
        
    def _get_subnode(self, symbol):
        return self.__nodes.get(symbol)
    
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



class Clause(TemplatedNode):
    '''A node that is headed by a verb'''
    def __init__(self, **kwargs): 
        TemplatedNode.__init__(self, data.CLAUSE_TEMPLATE_BANK, **kwargs)
        
        self.__verb_category_id = ''
        self.__verb_category = {}
        
        
    # clauses really need to have semantics figured out before populating the next level down (except blank symbols in participles, etc.)
    def has_verb_category(self):
        return bool(self.__verb_category_id) and bool(self.__verb_category)
        
    def set_verb_category(self, id):    
        assert(id in data.VERBSET_BANK.categories())
        
        # TODO: hmm, what if you want to specify semantic category first, or neither? (like with a participle)
        category = data.VERBSET_BANK.get_category(id)            
        if self._template_id() == category.template_id():
            self.__verb_category_id = id
            self.__verb_category = category
        else:
            raise Exception('incompatible template', id, self._template_id())
    
    # overrides
    def _ready_to_create_nodes(self):
        return self.has_template() and self.has_verb_category()
    
    # hey, notice that you don't really have to order the symbols until generation time anyway, even if specified by templates
    def _create_subnodes(self):
        TemplatedNode._create_subnodes(self)
        
        # head node gets special treatment
        # alternative: _create_nodes_subclass() call in base class and override here. 
        V = self._get_subnode('V')
        assert(V)
        if V:           
            V.set_category(self.__verb_category)
    

                

        

    def _tags_for_symbol(self, symbol): 
        semantic_tags = self.__verb_category.tags_for_symbol(symbol) or []
        assert(type(semantic_tags) is list)
        
        return TemplatedNode._tags_for_symbol(self, symbol) + semantic_tags
        

        



        
        
    # notice that populating the nodes is a separate step from just constructing them
    #def populate_nodes(self):
        
        

    ### DELETE ME: debugging interfaces ###

        
        

    
        
        
class NounPhrase(TemplatedNode):
    def __init__(self, **options):
        TemplatedNode.__init__(self, data.NP_TEMPLATE_BANK, **options)
        self.__options = options
        
    # overrides
    def _ready_to_create_nodes(self):
        return self.has_template()
        
    def _create_subnodes(self):
        TemplatedNode._create_subnodes(self)
    
        # propagate tags from parent node into head word
        # TODO: handle "multiple headwords" (Alice and Bob and...)
        self._get_subnode('N').add_options(self.__options)
        
    # TODO: handle semantic tags (pre-nounset constraints)
        
    # pick a template from np_templates
        # NN
        # NR
        # VP-NP - who knows!
        
# leaf nodes - hmm, are all non-leaf nodes Templated, then?
class Name(Node):
    def __init__(self, **kwargs):
        Node.__init__(self, **kwargs)
        self.__namesets = []
        
    def _lexicalize(self):
        semantic_tags = [tag for tag in self._get_option('tags') if type(tag) is str]
        assert(len(semantic_tags) <= 1)
        
        if semantic_tags:
            candidates = data.NAME_BANK.find_tagged(semantic_tags[0])   

            # TODO: move random.sample() into NameBank? abstraction level is different for VerbCategory, which sample()s there...
            self.__namesets = random.sample(candidates, 1)
        
    
class Verb(Node):
    def __init__(self, **kwargs):
        Node.__init__(self, **kwargs)
        self.__category = {} # data.VerbCategory
        self.__verbsets = [] # data.VerbSet
        
    def set_category(self, category):
        self.__category = category
        
    # DELETE ME: debugging interfaces
    def _category(self):
        return self.__category
        
    def _lexicalize(self):
        # TODO: filter further by, say, semantic tags 
        self.__verbsets = self.__category.all_verbsets()
        
        
def create_node(type, **kwargs):
    '''Object factory that will instantiate the appropriate class, with an optional dict of tags, etc.'''
    
    #print('create_node', type, kwargs)
    # Templated (and thus non-leaf?) nodes
    if type == 'Clause':
        return Clause(**kwargs)
    elif type == 'NP':
        return NounPhrase(**kwargs)
        
    # leaf nodes
    elif type == 'name':
        return Name(**kwargs)
    elif type == 'verb':
        return Verb(**kwargs)
        
    else:
        raise Exception('Unknown node type ' + type)
        
    
    
#make_node('NP', tags=['man', 'plural'])
        








### 2. Generate sentences ###

# some quickie testing
names = data.NAME_BANK
women = names.find_tagged('woman')
#men = names.find_tagged('man')
people = names.find_tagged('person')


#def hello():
#template = RAW_CLAUSE_TEMPLATES[1]

# where will this logic live??
# actually, i think it should commute - user CAN specify certain constraints, then object specifies the rest
    # I suppose this is important for transformed Clauses, for which you specify "empty subject" or something
    # BUT, don't you have to create a public API with which you reach down into the tree?
clause = create_node('Clause')
clause.set_template('transitive')
clause.set_verb_category('action.possession') 
clause._create_subnodes()


S, V, O = [clause._get_subnode(sym) for sym in 'SVO']
for n in [S, O]:
    n.set_template('name')
    n._create_subnodes()
    
A, B = [np._get_subnode('N') for np in [S, O]]
A.add_options({'tags': ['woman']})
B.add_options({'tags': ['man']}) # hmm... 



clause.lexicalize_tree()


# ok, so I have 3 terminal nodes now - V, A, B
    # "populate" - pick a multilingual synset at each node
    # "generate" - monolingual generators process each node (with dependencies) and then bubble it up
    
# TODO (ugh basically EVERYTHING is left to do...)
    # transformations (tense, participle, etc.)
    # modifiers
    # additional modifications or constraints like plural or tag

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