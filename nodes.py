'''
Nodes make up the primary "parse tree" data structure
'''

import collections
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
        
        self.__generated_text = None # { 'en': 'Alice' ... }
        
        # just store them for now and figure out what to do with them later... can always use dict.pop()
        self.__type = options.pop('type') # n.b. this modifies the original data structure!! 
        self.__options = collections.defaultdict(list, options) # need to instantiate even if empty - that way can query if empty
        
    def add_dependency(self, node, **kwargs):
        self.__dependencies.append((node, kwargs))
        
        
    def add_options(self, options):
        assert(type(options) is dict or type(options) is collections.defaultdict)
        
        # TODO: allow multiple sources for monolingual tags...
        #assert(all(type(v) is list for v in options.values()))
        for key, value in options.items():
            # TODO: handle duplicate options? or does that not matter??
            if type(value) is list:
                new_values = value
            else:
                new_values = [value]
                
            for nv in new_values:
                if not nv in self.__options[key]:
                    self.__options[key] += [nv]
            
    def generated_text(self, lang):
        return self.__generated_text[lang] # throw an exception to reveal premature accesses #.get(lang, '')
    def has_generated_text(self, lang):
        return bool(self.__generated_text.get(lang))
    def set_generated_text(self, lang, text):
        self.__generated_text[lang] = text
    def reset_generated_text(self):
        self.__generated_text = {}

    def get_dependencies(self, **input_options): # input_options is here to mirror add_dependency() - deps can vary with language
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
    
    def analyze_all(self, analyzer):
        for _, sn in self._subnodes():
            sn.analyze_all(analyzer)
        analyzer.analyze(self)
        #for lang in generators.keys():
        #    generators[lang].analyze(self)
    
    def generate_all(self, generators):
        for _, sn in self._subnodes():
            sn.generate_all(generators)        
        for lang in generators.keys():
            self._generate(generators)
            
    # not very pretty, but should get the job done...
    def get_all_lexical_nodes(self):
        '''used by external loop to call set_num_samples, instead of having to reach deep down into the tree manually'''
        if issubclass(type(self), LexicalNode):
            lexical_nodes = [self]
        else:
            lexical_nodes = []        
            
        for _, sn in self._subnodes():
            lexical_nodes += sn.get_all_lexical_nodes()
        return lexical_nodes
            
        
    def lexicalize_all(self):
        '''TODO: multiple synsets per node, to allow for outer product'''
        
        # ugh, previously assumed only templated nodes would have subnodes... 
        # but now that non-templated lexical nodes have modifiers as subnodes, 
        # need to make sure that _subnodes() has the right return type...
        assert(all(type(i) is tuple for i in self._subnodes()))
        
        for _, sn in self._subnodes():
            sn.lexicalize_all()
        self._lexicalize()
        
    def ungenerate_all(self): # tempting to call this "reset_all", but there are other operations like lexicalize()...
        for _, sn in self._subnodes():
            sn.ungenerate_all()
        self.reset_generated_text()  
        
    ### "pure virtual" functions - to be implemented in derived classes ###
    # override this iff a node has any lexical choices to be made
    def _lexicalize(self):
        raise UNIMPLEMENTED_EXCEPTION
        
    def _subnodes(self):
        '''Needs to return an iterable over the subnodes'''
        raise UNIMPLEMENTED_EXCEPTION
        
    ### "protected" functions - for use in derived classes ###
        
    # convenience function for derived classes... breaks encapsulation... but only if you have a valid key?
    def _get_option(self, key):
        return self.__options[key] #.get(key, []) # it's a defaultdict(list) now
        
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
    def add_modifier(self, modifier_node):
        assert(len(self._get_headnodes()) <= 1) # TODO: handle applying modifier to multiple head nodes (red cats and dogs)
        assert(len(self._get_headnodes()) > 0) # TODO: ignore add_modifier() on headless node? or raise Exception?
        for head in self._get_headnodes():  
            head.add_modifier(modifier_node) # convention for now: modifiers belong to (lexical) head nodes
    
    def add_options(self, options):
        Node.add_options(self, options)    
        for symbol, subnode in self.__subnodes.items():
            subnode.add_options(self._options())
    
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
        
        if self._ready_to_create_subnodes():
            self._create_subnodes()
        
    def template_id(self):
        return self._template_id()

        
        
    ### "pure virtual" functions - to be implemented in derived classes ###
    # not needed per se (duck typing will get it), but still valuable to document what this function is
    def _ready_to_create_subnodes(self):
        raise UNIMPLEMENTED_EXCEPTION
        
    ### "protected" functions - default implementations, MAY be overridden in derived classes ###
    def _create_subnodes(self):
        if not self.__subnodes and self._ready_to_create_subnodes():
            # new implementation ignores multiple calls to this function - to simplify enclosing logic
            #assert(not self.__subnodes) # this function should only be called once, for initialization 
        
            # requires symbols to be unique... but they SHOULD be, since they're in a dict
            self.__subnodes = { s: node_factory(self._type_for_symbol(s))
                for s in self._symbols() }
                
            for symbol, subnode in self.__subnodes.items():
                # language-specific syntax tags 
                subnode.add_options({'tags': self._tags_for_symbol(symbol)})
                
                if issubclass(type(subnode), LexicalNode):
                    subnode.set_parent(self) # for modifiers to query parent node for target
           
            # hook up dependencies between NODES and their data - all nodes must have been instantiated first
            # add_dependency() should allow pronouns to work all the way across the tree...right?
            for s in self._symbols():                
                for lang, deps in self._deps_for_symbol(s).items():
                    for d in deps:
                        self.__subnodes[s].add_dependency(self.__subnodes[d], lang=lang)
            
            
            self.__headnodes = [self._get_subnode(s) for s in self.__template.head_symbols()]
            assert(len(self.__headnodes) <= 1)            
            # TODO: alter head upon transformation

            
                        
    def _tags_for_symbol(self, symbol):
        tags = self._syntax_tags_for_symbol(symbol)
        if tags:
            if type(tags) is list:
                return tags
            else:
                return [tags]
        else:
            return []
            
    ### "protected" - these override the base class ###
    def _generate(self, generators):
        assert(self._ready_to_create_subnodes()) #self._subnodes())
        for lang in generators.keys():
            if all(sn.has_generated_text(lang) for _, sn in self._subnodes()) and not self.has_generated_text(lang):  
                generators[lang].generate(self)
                
    def _lexicalize(self):
        '''Currently assuming TemplatedNodes are not lexicalized (do not need to choose any words from database)'''
        pass
                
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

    def _template(self):
        return self.__template

    def _template_id(self):
        return self.__template_id

    def _type_for_symbol(self, symbol):
        return self.__template.type_for_symbol(symbol)
        
    #### "private" functions - not intended to be called outside this class ###        
        

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
            
            self.__bequeath_verb_category()
            
        else:
            raise Exception('incompatible template', id, self._template_id())
    
    # overrides
    def _ready_to_create_subnodes(self):
        return self.has_template() #and self.has_verb_category()  set_verb_category() now also triggers propagation to subnodes
    
    # hey, notice that you don't really have to order the symbols until generation time anyway, even if specified by templates
    def _create_subnodes(self):
        TemplatedNode._create_subnodes(self)
        
        # head node gets special treatment
        # alternative: _create_nodes_subclass() call in base class and override here. 
        self.__bequeath_verb_category()
    
    def _tags_for_symbol(self, symbol): 
        if self.__verb_category:
            semantic_tags = self.__verb_category.tags_for_symbol(symbol) or []
            assert(type(semantic_tags) is list)
            
            return TemplatedNode._tags_for_symbol(self, symbol) + semantic_tags
        else:
            return []
        
    def __bequeath_verb_category(self):
        V = self._get_subnode('V')
        if self.__verb_category and V:
            V.set_category(self.__verb_category)
    
        
        
class CustomTemplate(TemplatedNode):
    def __init__(self, **kwargs): 
        TemplatedNode.__init__(self, data.CUSTOM_TEMPLATE_BANK, **kwargs)

    def _ready_to_create_subnodes(self):
        return self.has_template()
    
    def _create_subnodes(self):
        TemplatedNode._create_subnodes(self)
        for sym in self._symbols():
            self.add_options(self._template().options_for_symbol(sym))
        # pass other language-independent options from template
        # TODO: refactor this into TemplatedNode and the awkward _tags/_deps system?
    
        
        
class NounPhrase(TemplatedNode):
    def __init__(self, **options):
        TemplatedNode.__init__(self, data.NP_TEMPLATE_BANK, **options)
        
    def number(self):
        '''singular or plural?'''
        heads = self._get_headnodes()
        assert(len(heads) > 0)

        # wow, i got WAY ahead of myself, huh?
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
        
        
        
class ModifierNode(TemplatedNode):
    def __init__(self, bank, **kwargs):
        TemplatedNode.__init__(self, bank, **kwargs)
        self.__targets = [] 
        
    def add_target(self, target_node):
        assert(issubclass(type(target_node), LexicalNode))
        
        self.__targets.append(target_node)
        
        ## ugh, but i should propagate this down to its head, right?
        #raise Exception('''
        #    no, actually, to symmetrize with S-V dependencies, I think DT should query its parent (ADJP) for its target.
        #    that way, target/modifier "bonds" are set all in one go, without any propagation. 
        #    (well, the through-query is KIND of a propagation...
        #    ''')
        #for head in self._get_headnodes():
        #    head.add_target(target_node)
        
    def targets(self):
        return tuple(self.__targets) # makes the LIST read-only, but individual nodes still aren't...
        
        
class AdjectivePhrase(ModifierNode):
    def __init__(self, **kwargs): 
        ModifierNode.__init__(self, data.ADJP_TEMPLATE_BANK, **kwargs)
        
    def _ready_to_create_subnodes(self):
        return self.has_template()
        
        
        
        
        
class LexicalNode(Node):
    '''
    Collects operations over multiple VerbSets, etc.
    These operations don't really belong in Node or TemplatedNode
    
    Order of operations...
    set_num_samples() - # samples to pick (default = 1)
    _pick_samples() - pick a minibatch
    select_sample() - selects one concrete sample from the picked minibatch
    '''
    def __init__(self, **options):
        Node.__init__(self, **options)
        self.__datasets = []
        self.__modifiers = []
        self.__parent = None # Node
        #self.__targets = [] # allows for multiple targets, like "little boys and girls" - but this kind of breaks the assumption that modifiers target WORDS
        #raise Exception('I am here - adding modifier infrastructure')
        
        # default values: single-sample words (multi-sample: [cat, dog, ...])
        self.__num_samples = 1 #options.pop('num_samples', 1) # not quite - would have to propagate down from parent
        self.__selected_sample_index = 0
        
    # public
    def modifiers(self): # used directly by generator... but I'm not totally sure I should be exposing something this powerful
        return self.__get_modifiers() 
    def has_modifiers(self):
        return bool(self.__modifiers) #self._subnodes())        
    def add_modifier(self, modifier_node):
        # perform error-checking as to whether the modifier is compatible
        if modifier_node.type() in self._compatible_modifier_types():
            #raise Exception('I am in the middle of adding determiners')
            
            # add to subnode list - with None to hack into the previously templated-only subnode format of (symbol, node)
            self.__modifiers.append((None, modifier_node))
            
            # because the tree is generated from bottom up, the modifier needs to store a link to its target, in case it depends on it
                # example: this cat/these cats
                # TODO: merge with existing "dependency" framework?
            modifier_node.add_target(self)            
            
        else:
            raise Exception('Tried to modify {} with {} - incompatible'.format(self.type(), modifier_node.type()))
        
    def num_samples(self):
        if self.__datasets:
            assert(self.__num_samples == len(self.__datasets))
            pass
        return self.__num_samples
    def set_num_samples(self, num):
        '''Number of samples desired from the candidate datasets'''
        self.__num_samples = num
        
    # originally just intended for modifiers to query parent (say, ADJP) for target node... use with caution
    def parent(self):
        return self.__parent
    def set_parent(self, parent):
        self.__parent = parent
        assert(issubclass(type(parent), TemplatedNode))
        
    def select_sample(self, index):
        assert(self.__datasets) # remember to call _pick_samples() at the end of _lexicalize()...
        if 0 <= index < len(self.__datasets):
            self.__selected_sample_index = index
        else:
            #import pdb; pdb.set_trace()
            raise Exception('out of range: {}/{}'.format(index, len(self.__datasets))) 
            # can't just let the system raise IndexError, because it might not for a WHILE before it actually uses index to access

    ## some words can be both modifiers and targets (adv > adj > noun)
    #def add_target(self, target_node):
    #    # TODO: check whether target is SEMANTICALLY compatible with modifier...
    #    self.__targets.append(target_node)
        
    def targets(self):
        return self.parent().targets()
        #return self.__targets

            
    def total_num_datasets(self, lang): # TODO: rename this atrocity
        # each dataset object could contain more than one "dataset" (nameset, etc.), e.g., en: [Bob, Robert]
        return sum(ds.num_words(lang) for ds in self.__datasets) 
     
    # pure virtual - must be implemented by derived classes
    def _get_lexical_candidates(self):
        raise UNIMPLEMENTED_EXCEPTION
     
    # empty default to be overridden by derived classes as needed
    def _compatible_modifier_types(self):
        '''Check whether modifier is SYNTACTICALLY compatible with this target'''
        return set()
        
    # override base class
    def _generate(self, generators):
        #assert(not self._subnodes()) # LexicalNode now may have modifiers as subnodes
        for lang in generators.keys():
            if not self.has_generated_text(lang):
                generators[lang].generate(self)

    def _lexicalize(self):
        self._pick_samples(self._get_lexical_candidates())
                
    def _subnodes(self):
        return self.__modifiers
                
        
    # protected - used by derived classes
    def _pick_samples(self, candidates):
        num_candidates = len(candidates)
        assert(num_candidates > 0)
        if self.num_samples() > num_candidates:
            self.set_num_samples(num_candidates)

        # TODO: random sampling (using deterministic candidate bank for test/debugging)
        # TODO: make the choice a user option
        #self.__datasets = random.sample(candidates, self.num_samples())
        self.__datasets = candidates[:self.num_samples()]

    def _sample_dataset(self):
        '''Return the currently selected dataset'''
        return self.__get_dataset_by_index(self.__selected_sample_index)
        
    def __get_dataset_by_index(self, index):
        return self.__datasets[index]
        
    def __get_modifiers(self):
        # probably don't want to return the ACTUAL data structure
        return [node for _, node in self.__modifiers]

        
class Determiner(LexicalNode):
    def add_modifier(self, _):
        raise Exception('do not modify Determiner nodes - are you trying PDT? how about hooking on a second DT?')
        
    def determiner(self, lang):
        detset = self._sample_dataset()
        assert(detset.num_words(lang) is 1)
        return detset.determiner(lang, 0)
        
    def _get_lexical_candidates(self):
        tags = [t for t in (self._get_option('tags') or []) if type(t) is str]
        assert(len(tags) <= 1)
        if tags:            
            candidates = data.DETSET_BANK.find_tagged(tags[0])
        else:
            candidates = data.DETSET_BANK.all_detsets()
        return candidates
        
        
        
class GenericNoun(LexicalNode): 
    '''Abstract base class to share code with Name, Noun, Pronoun, ...'''
    def number(self):
        #if 'plural' in self._get_option('tags'): # should this really be lumped with semantic tags? well, it is language-independent...
        number_options = self._get_option('number')        
        assert(not number_options or not('plural' in number_options and 'singular' in number_options))
        if number_options and 'plural' in number_options:
            return 'plural'
        else:
            # TODO: some nouns might override and be always plural...
            return 'singular'
            
    def person(self):
        raise UNIMPLEMENTED_EXCEPTION
        
        
# leaf nodes - hmm, are all non-leaf nodes Templated, then?
class Name(GenericNoun):
    #def __init__(self, **kwargs):
    #    LexicalNode.__init__(self, **kwargs)
    #    #self.__namesets = []
        
    #def get_nameset_by_index(self, index):
    #    return self.get_dataset_by_index(index) #self.__namesets[index]
    
    def person(self): # a name is always third person
        return 3
        
    def name(self, lang):
        nameset = self._sample_dataset() #get_dataset_by_index(0) #node.get_nameset_by_index(0)
        
        assert(nameset.num_words(lang) == 1)
        name = nameset.name(lang, 0)
        return name
        
    def _get_lexical_candidates(self):
        assert(self._get_option('tags') is not None)
        semantic_tags = [tag for tag in self._get_option('tags') if type(tag) is str]
        assert(len(semantic_tags) <= 1)
        
        if semantic_tags:
            candidates = data.NAME_BANK.find_tagged(semantic_tags[0])   
        else:
            candidates = data.NAME_BANK.all_namesets()
            
        return candidates
            

        
            
            
    # expose to BASE class ("pure virtual")
    #def _datasets(self):
    #    return self.__namesets
    #    
    #def _set_datasets(self, datasets):
    #    self.__namesets = datasets
    
class Noun(GenericNoun):
    def person(self):
        return 3
        
    def noun(self, lang):
        nounset = self._sample_dataset()
        assert(nounset.num_words(lang) == 1)
        return nounset.noun(lang, 0)
        
    def set_plural(self): # just not available in Name, although could call add_options directly, or on parent node...
        self.add_options({'number': ['plural']})
        
    def _compatible_modifier_types(self):
        return { 'ADJP' }
        
    def _get_lexical_candidates(self):
        semantic_tags = [tag for tag in self._get_option('tags') if type(tag) is str] 
        assert(len(semantic_tags) <= 1)
        if semantic_tags:
            candidates = data.NOUNSET_BANK.find_tagged(semantic_tags[0])   
        else:
            candidates = data.NOUNSET_BANK.all_nounsets()
        return candidates
        

        
    
class Verb(LexicalNode):
    def __init__(self, **kwargs):
        LexicalNode.__init__(self, **kwargs)
        self.__category = {} # data.VerbCategory
        #self.__verbsets = [] # data.VerbSet
        
        # TODO: does this really belong here, in a multilingual data structure?
        self.__tense = 'present' # default tense
        
    #def get_verbset_by_index(self, index):
    #    return self.get_dataset_by_index(index) #self.__verbsets[index]
        
    def set_category(self, category):
        self.__category = category
        
    def get_tense(self):
        return self.__tense
        
    def verb(self, lang):    
        verbset = self._sample_dataset()
        return verbset.verb(lang)
        
    # DELETE ME: debugging interfaces
    def _category(self):
        return self.__category
        
    def _get_lexical_candidates(self):
        # TODO: filter further by, say, semantic tags 
        return self.__category.all_verbsets()
        
    ## expose to base class
    #def _datasets(self):
    #    return self.__verbsets
    #    
    #def _set_datasets(self, datasets):
    #    self.__verbsets = datasets




       
def node_factory(type, **kwargs):
    '''Object factory that will instantiate the appropriate class, with an optional dict of tags, etc.'''
    
    #print('create_node', type, kwargs)
    # Templated nodes
    if type == 'ADJP':
        factory = AdjectivePhrase
    elif type == 'Clause':
        factory = Clause    
    elif type == 'CustomTemplate':
        factory = CustomTemplate
    elif type == 'NP':
        factory = NounPhrase
        
    # lexical nodes (not necessarily leaf nodes - may have modifiers)
    elif type == 'determiner':
        factory = Determiner
    elif type == 'name':
        factory = Name
    elif type == 'noun':
        factory = Noun
    elif type == 'verb':
        factory = Verb
        
    else:
        raise Exception('Unknown node type ' + type)
        
    return factory(type=type, **kwargs)
        
        
        
        
    
    




