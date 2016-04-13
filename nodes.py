'''
Nodes make up the primary "parse tree" data structure
'''

import random

import data # read data from databases - giant, read-only globals
import generator

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
        
        self.__generated_text = {} # { 'en': 'Alice' ... }
        
        # just store them for now and figure out what to do with them later... can always use dict.pop()
        self.__type = options.pop('type')
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
      
    def generated_text(self, lang):
        return self.__generated_text.get(lang, '')
    def has_generated_text(self, lang):
        return bool(self.__generated_text.get(lang))
    def set_generated_text(self, lang, text):
        self.__generated_text[lang] = text

    def get_dependencies(self, **input_options):
        return [dep for (dep, options) in self.__dependencies if all(options[ik] == iv for ik, iv in input_options.items())]

    def type(self):
        return self.__type
        
    ### tree-walking operations ###
    
    # TODO: use generic tree traversal operation to DRY out code... meh, confusing and not really worth it for now
    #def for_all(self, operation, **kwargs):
    #    '''Bottom-up tree traversal'''
    #    for _, sn in self._subnodes():
    #        sn.for_all(operation, **kwargs)
    #    operation(self, **kwargs)
    
    def analyze_all(self, generators):
        for _, sn in self._subnodes():
            sn.analyze_all(generators)
        for lang in generators.keys():
            generators[lang].analyze(self)
    
    def generate_all(self, generators):
        for _, sn in self._subnodes():
            sn.generate_all(generators)        
        for lang in generators.keys():
            self._generate(generators)

        
    def lexicalize_all(self):
        '''TODO: multiple synsets per node, to allow for outer product'''
        for _, sn in self._subnodes():
            sn.lexicalize_all()
        self._lexicalize()
        
    ### "protected" functions - silent defaults to be overridden in derived classes as needed ###
    # override this iff a node has any lexical choices to be made
    def _lexicalize(self):
        pass
        
    def _subnodes(self):
        return []
        
    # convenience function for derived classes... breaks encapsulation... but only if you have a valid key?
    def _get_option(self, key):
        return self.__options.get(key)
        
    # ugh, breaking encapsulation to give access to NounPhrase ... but it's only "vertical" encapsulation, right?
    def _options(self):
        return self.__options
        
        

class TemplatedNode(Node):
    '''
    A templated node is like "S V O" - and so it generally branches into other nodes and is non-terminal.
    Currently subclasses to NP and Clause
    '''
    def __init__(self, bank, **kwargs):
        Node.__init__(self, **kwargs)
        
        self.__headnodes = [] # Node
        self.__subnodes = {}
        
        assert(bank) # catch uninitialization errors
        self.__template_bank = bank
        
        
        # syntactic template
        self.__template = None # data.Template
        self.__template_id = ''
        
    def __str__(self): # for interactive probing
        return "{type}({template})".format(type=self.__class__, template=self.__template)
        
    ### "public" API - for use outside this class ###
    def generated_symbols(self, lang):
        return { symbol: subnode.generated_text(lang) for symbol, subnode in self.__subnodes.items() if subnode.has_generated_text(lang) }
            
    def get_template_text(self, lang):
        return self.__template.template_text(lang)
            
    def num_symbols(self):
        return len(self._symbols()) # TODO: cache this on calling set_template()?
    
    def has_template(self):
        return bool(self.__template_id) and bool(self.__template)    
    def set_template(self, id):
        self.__template = self.__template_bank.get_template_by_id(id)
        assert(type(self.__template) == data.Template)
        self.__template_id = id
        

        
        
    ### "pure virtual" functions - to be implemented in derived classes ###
    # not needed per se (duck typing will get it), but still valuable to document what this function is
    def _ready_to_create_subnodes(self):
        raise UNIMPLEMENTED_EXCEPTION
        
    ### "protected" functions - default implementations, MAY be overridden in derived classes ###
    def _create_subnodes(self):
        if self._ready_to_create_subnodes():
            assert(not self.__subnodes) # this function should only be called once, for initialization 
        
             # requires symbols to be unique... but they SHOULD be, since they're in a dict
            self.__subnodes = { s: node_factory(self._type_for_symbol(s), tags=self._tags_for_symbol(s)) 
                for s in self._symbols() }
            
            # hook up dependencies between NODES and their data - all nodes must have been instantiated first
            # add_dependency() should allow pronouns to work all the way across the tree...right?
            for s in self._symbols():                
                for lang, deps in self._deps_for_symbol(s).items():
                    for d in deps:
                        self.__subnodes[s].add_dependency(self.__subnodes[d], lang=lang)
            
            
            self.__headnodes = [self._get_subnode(s) for s in self.__template.head_symbols()]
            assert(len(self.__headnodes) == 1)            
            #import pdb; pdb.set_trace()
            # TODO: alter head upon transformation

            
                        
    def _tags_for_symbol(self, symbol):
        tags = self._syntax_tags_for_symbol(symbol)
        if tags:
            return [tags]
        else:
            return []
            
    ### "protected" - these override the base class ###
    def _generate(self, generators):
        assert(self._subnodes())
        for lang in generators.keys():
            if all(sn.has_generated_text(lang) for _, sn in self._subnodes()) and not self.has_generated_text(lang):  
                generators[lang].generate(self)
                
    def _subnodes(self):
        return self.__subnodes.items()


    ### "protected" functions - available to derived classes ###

    
    def _deps_for_symbol(self, symbol):
        return self.__template.deps_for_symbol(symbol)
        
    def _get_subnode(self, symbol):
        return self.__subnodes.get(symbol)
        
    def _get_headnodes(self):
        return self.__headnodes
    
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
    def _ready_to_create_subnodes(self):
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
        
    def number(self):
        '''singular or plural?'''
        heads = self._get_headnodes()
        assert(len(heads) > 0)
        
        if len(self._get_headnodes()) > 1:
            return 'plural' # in a disjunction like "candy or dogs", only one should be marked as a headword, right?
        else:
            return heads[0].number()
        
    
    def person(self):
        '''1: I/we, 2: You/y'all, 3: all others'''
        heads = self._get_headnodes()
        assert(len(heads) is 1)
        
        # hey, person only matters for SINGULAR? can I just return something like "0" if there are multiple headwords?
        return heads[0].person()
        
        
        
        
    # overrides
    def _ready_to_create_subnodes(self):
        return self.has_template()
        
    def _create_subnodes(self):
        TemplatedNode._create_subnodes(self)
    
        # propagate tags from parent node into head word
        # TODO: handle "multiple headwords" correctly (Alice and Bob and...)
            # n.b. tags don't necessarily propagate into all head words... (Alice and tacos and killing)
        head_subnodes = self._get_headnodes()
        assert(len(head_subnodes) == 1)
        for head in head_subnodes:
            head.add_options(self._options())
        
    # TODO: handle semantic tags (pre-nounset constraints)
        
    # pick a template from np_templates
        # NN
        # NR
        # VP-NP - who knows!
        
        
class LexicalNode(Node):
    '''
    Collects operations over multiple VerbSets, etc.
    These operations don't really belong in Node or TemplatedNode
    '''
    def __init__(self, **options):
        Node.__init__(self, **options)
        self.__num_samples = 1
        
    # public
    def num_datasets(self, lang):
        return sum(ds.num_words(lang) for ds in self._datasets())
        
    def num_samples(self):
        #import pdb; pdb.set_trace()
        return self.__num_samples
    def set_num_samples(self, num):
        self.__num_samples = num
        
    # pure virtual
    def _lexicalize(self):
        raise UNIMPLEMENTED_EXCEPTION
        
    # override base class
    def _generate(self, generators):
        assert(not self._subnodes())
        for lang in generators.keys():
            if not self.has_generated_text(lang):
                generators[lang].generate(self)
                
        
    # protected - used by derived classes
    def _pick_samples(self, candidates):
        num_candidates = len(candidates)
        if self.num_samples() > num_candidates:
            self.set_num_samples(num_candidates)
        self._set_datasets(random.sample(candidates, self.num_samples()))

        
        
# leaf nodes - hmm, are all non-leaf nodes Templated, then?
class Name(LexicalNode):
    def __init__(self, **kwargs):
        LexicalNode.__init__(self, **kwargs)
        self.__namesets = []
        
    def get_nameset_by_index(self, index):
        return self.__namesets[index]
        
    def number(self):
        if 'plural' in self._get_option('tags'):
            return 'plural'
        else:
            return 'singular'
            
    def person(self): # a name is always third person
        return 3
        
    def _lexicalize(self):
        semantic_tags = [tag for tag in self._get_option('tags') if type(tag) is str]
        assert(len(semantic_tags) <= 1)
        
        if semantic_tags:
            candidates = data.NAME_BANK.find_tagged(semantic_tags[0])   
        else:
            candidates = data.NAME_BANK.all_namesets()
            
        self._pick_samples(candidates)
            

        
        #self.__namesets = self._sample(candidates)
            
            
    # expose to BASE class ("pure virtual")
    def _datasets(self):
        return self.__namesets
        
    def _set_datasets(self, datasets):
        self.__namesets = datasets
        
    
class Verb(LexicalNode):
    def __init__(self, **kwargs):
        LexicalNode.__init__(self, **kwargs)
        self.__category = {} # data.VerbCategory
        self.__verbsets = [] # data.VerbSet
        
        # TODO: does this really belong here, in a multilingual data structure?
        self.__tense = 'present' # default tense
        
    def get_verbset_by_index(self, index):
        return self.__verbsets[index]
        
    def set_category(self, category):
        self.__category = category
        
    def get_tense(self):
        return self.__tense
        
    # DELETE ME: debugging interfaces
    def _category(self):
        return self.__category
        
    def _lexicalize(self):
        # TODO: filter further by, say, semantic tags 
        self._pick_samples(self.__category.all_verbsets())
        
    # expose to base class
    def _datasets(self):
        return self.__verbsets
        
    def _set_datasets(self, datasets):
        self.__verbsets = datasets




       
def node_factory(type, **kwargs):
    '''Object factory that will instantiate the appropriate class, with an optional dict of tags, etc.'''
    
    #print('create_node', type, kwargs)
    # Templated (and thus non-leaf?) nodes
    if type == 'Clause':
        factory = Clause        
    elif type == 'NP':
        factory = NounPhrase
        
    # leaf nodes
    elif type == 'name':
        factory = Name
    elif type == 'verb':
        factory = Verb
        
    else:
        raise Exception('Unknown node type ' + type)
        
    return factory(type=type, **kwargs)
        
        
        
        
    
    




