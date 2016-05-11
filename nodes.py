'''
Nodes make up the primary "parse tree" data structure
'''

import collections
import random

import data # read data from databases - giant, read-only globals
import generator
import utility

UNIMPLEMENTED_EXCEPTION = Exception('Needs to be implemented in derived class')


# TODO: inherit from object?
# TODO: rename this to "Node"? but will all modifiers, etc. have templates?? or should I use multiple inheritance?? sigh

# duh, just have Templated inherit from Node
class Node: 
    def __init__(self, **options): # contains data, so probably don't want to use as a mixin (would have to call constructor in derived classes)
        self.__dependencies = []
        
        self.__generated_text = None # { 'en': 'Alice' ... }
        
        # just store them for now and figure out what to do with them later... can always use dict.pop()
        self.__type = options.pop('type') # n.b. this modifies the input original data structure!! (assumed disposable)
        self.__options = collections.defaultdict(list, options) # need to instantiate even if empty - that way can query if empty
        
    # currently only used for subject/verb agreement? (ADJP uses a bidirectional modifier/target system...)
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

    def semantic_tags(self):
        '''Returns all language-independent tags'''
        return [t for t in self._get_option('tags') if type(t) is str]
        
    def type(self):
        return self.__type
        
    # default implementation - override for nodes that could potentially have modifiers
    def has_modifiers(self):
        return False
        
    ### tree-walking operations ###
    
    # TODO: use generic tree traversal operation to DRY out code... meh, confusing and not really worth it for now
    #def for_all(self, operation, **kwargs):
    #    '''Bottom-up tree traversal'''
    #    for sn in self._subnodes():
    #        sn.for_all(operation, **kwargs)
    #    operation(self, **kwargs)
    
    def analyze_all(self, analyzer):
        for sn in self._subnodes():
            sn.analyze_all(analyzer)
        analyzer.analyze(self)
    
    def generate_all(self, generators):
        for sn in self._subnodes():
            sn.generate_all(generators)        
        #for lang in generators.keys():
        self._generate(generators)
            
    # not very pretty, but should get the job done...
    def get_all_lexical_nodes(self):
        '''used by external loop to call set_num_samples, instead of having to reach deep down into the tree manually'''
        if issubclass(type(self), LexicalNode):
            lexical_nodes = [self]
        else:
            lexical_nodes = []        
            
        for sn in self._subnodes():
            lexical_nodes += sn.get_all_lexical_nodes()
        return lexical_nodes
            
        
    def lexicalize_all(self):
        '''TODO: multiple synsets per node, to allow for outer product'''
        
        # ugh, previously assumed only templated nodes would have subnodes... 
        # but now that non-templated lexical nodes have modifiers as subnodes, 
        # need to make sure that _subnodes() has the right return type...
        assert(all(issubclass(type(i), Node) for i in self._subnodes()))
        
        for sn in self._subnodes():
            sn.lexicalize_all()
        self._lexicalize()
        
    def ungenerate_all(self): # tempting to call this "reset_all", but there are other operations like lexicalize()...
        for sn in self._subnodes():
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
        
    def _set_type(self, type):
        '''Intended for use in TransformableNode'''
        self.__type = type
        
        
        

class TemplatedNode(Node):
    '''
    A templated node is like "S V O" - and so it generally branches into other nodes and is non-terminal.
    Currently subclasses to NP and Clause
    '''
    def __init__(self, bank, **kwargs):
        Node.__init__(self, **kwargs)
        
        self.__headnodes = [] # Node
        self.__symbol_subnodes = {}
        self.__modifier_subnodes = []
        
        assert(bank) # catch uninitialization errors
        self.__template_bank = bank
        
        
        # syntactic template
        self._template_readonly = None # bool - expected to be write-once
        self.__template = None # data.Template
        self.__template_id = ''
        
    def __str__(self): # for interactive probing
        return "{type}({template})".format(type=self.__class__, template=self.__template)
        
    ### "public" API - for use outside this class ###
    def add_modifier(self, modifier_node):
        # TODO: check whether target is SEMANTICALLY compatible with modifier...
        assert(len(self._get_headnodes()) <= 1) # TODO: handle applying modifier to multiple head nodes (red cats and dogs)
        assert(len(self._get_headnodes()) > 0) # TODO: ignore add_modifier() on headless node? or raise Exception?
        headnodes = self._get_headnodes()
        if all(modifier_node.can_modify(head) for head in headnodes): 
            assert(modifier_node not in self.__modifier_subnodes)
            self.__modifier_subnodes.append(modifier_node)
        
            for head in headnodes:              
                modifier_node.add_lexical_target(head) # TODO: merge with existing "dependency" framework?
        else:
            # TODO: more graceful error handling - to let nodes cycle through modifiers autonomously
            #raise Exception('Syntactic incompatibility: cannot modify {} with {}'.format(headnodes[0].type(), modifier_node.type()))
            raise Exception('TemplatedNode.add_modifier() failed') # can_modify() now does some semantic checking too...
                
    def has_modifiers(self):
        return bool(self.__modifier_subnodes)
    def modifiers(self):
        return self.__modifier_subnodes[:] # probably don't want to return the actual data structure...
    
    def add_options(self, options):
        '''Propagate any externally-specified options down to head node'''
        Node.add_options(self, options)    
        for subnode in self._get_headnodes(): #subnode in self._subnodes(): # no, that's WAY too powerful
            subnode.add_options(self._options())
    
    # used by Generator
    def generated_symbols(self, lang):    
        return { symbol: subnode.generated_text(lang) 
            for symbol, subnode in self.__symbol_subnodes.items() if subnode.has_generated_text(lang) }
            
    def get_template_text(self, lang):
        return self.__template.template_text(lang)
            
    def num_symbols(self):
        return len(self._symbols()) # TODO: cache this on calling set_template()?
    
    def has_template(self):
        return bool(self.__template_id) and bool(self.__template)    
    def set_template(self, id, readonly=True):
        assert(self._template_readonly is None)
        self._template_readonly = readonly
    
        self.__template = self.__template_bank.get_template_by_id(id, readonly)
        assert(type(self.__template) == data.Template)
        self.__template_id = id
        
        if self._can_create_symbol_subnodes():
            self._create_symbol_subnodes()
        
    def template_id(self):
        return self._template_id()

        
        
    ### "pure virtual" functions - to be implemented in derived classes ###
    # not needed per se (duck typing will get it), but still valuable to document what this function is
    def _can_create_symbol_subnodes(self):
        raise UNIMPLEMENTED_EXCEPTION
        
    ### "protected" functions - default implementations, MAY be overridden in derived classes ###
    def _create_symbol_subnodes(self):
        '''Creates only the subnodes specified by the template - no modifiers'''
        if not self.__symbol_subnodes and self._can_create_symbol_subnodes():
            # new implementation ignores multiple calls to this function - to simplify enclosing logic
            #assert(not self.__subnodes) # this function should only be called once, for initialization 
        
            # requires symbols to be unique... but they SHOULD be, since they're in a dict
            self.__symbol_subnodes = { s: node_factory(self._type_for_symbol(s))
                for s in self._symbols() }
                
            for symbol, subnode in self.__symbol_subnodes.items():
                # language-specific syntax tags 
                subnode.add_options({'tags': self._tags_for_symbol(symbol)})
                
                if issubclass(type(subnode), LexicalNode):
                    subnode.set_parent(self) # for modifiers to query parent node for target
           
            # hook up dependencies between NODES and their data - all nodes must have been instantiated first
            # add_dependency() should allow pronouns to work all the way across the tree...right?
            for s in self._symbols():                
                for lang, deps in self._deps_for_symbol(s).items():
                    for d in deps:
                        self.__symbol_subnodes[s].add_dependency(self.__symbol_subnodes[d], lang=lang)
            
            self.__headnodes = [self._get_symbol_subnode(s) for s in self.__template.head_symbols()]
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
        assert(self._subnodes()) #self._ready_to_create_subnodes()) #self._subnodes())
        for lang in generators.keys():
            if all(sn.has_generated_text(lang) for sn in self._subnodes()) and not self.has_generated_text(lang):  
                generators[lang].generate(self)
                
    def _lexicalize(self):
        '''Currently assuming TemplatedNodes are not lexicalized (do not need to choose any words from database)'''
        pass
                
    def _subnodes(self):
        return self.__modifier_subnodes + list(self.__symbol_subnodes.values())


    ### "protected" functions - available to derived classes ###

    
    def _deps_for_symbol(self, symbol):
        return self.__template.deps_for_symbol(symbol)
        
    def _get_symbol_subnode(self, symbol):
        return self.__symbol_subnodes.get(symbol)
        
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
        
        
class ModifierNode(TemplatedNode):
    def __init__(self, bank, **kwargs):
        TemplatedNode.__init__(self, bank, **kwargs)
        self.__lexical_targets = [] 
        
    def add_lexical_target(self, target_node):
        '''Used by Generator to pull word-level information'''
        assert(issubclass(type(target_node), LexicalNode))
        assert(target_node not in self.__lexical_targets)
        assert(self.type() in ['ADJP', 'ADVP'])
        self.__lexical_targets.append(target_node)        
    def lexical_targets(self):
        return tuple(self.__lexical_targets) # pointless? makes the LIST read-only, but individual nodes still aren't...
        
    def can_modify(self, target):
        return self.type() in target.compatible_modifier_types()
        
        
        
class TransformableNode(ModifierNode):        
    # transformation-related functions, not kept in TemplatedNode
        # - avoid making TemplatedNode's code more complicated
        # - also, most subclasses don't need this functionality for now
    # not kept in ModifierNode, since that covers other classes like ADJP that might never need transforming
    
    def __init__(self, bank, **kwargs):
        ModifierNode.__init__(self, bank, **kwargs)
        
        # possible ghost nodes
        # - participle target (used to be a Clause subject)
        # - uh....?
        self.__ghostnodes = {} # basically just parallels subnodes
        self.__ghosttargets = [] # admits the possibility that not all ghost nodes are targets
        
        self.__transformations = []
        
    def can_modify(self, target_head):
        assert(issubclass(type(target_head), LexicalNode)) # the alternative was to expose TemplatedNode.headnodes()... maybe that ain't so bad?
        
        # get base class out of the way
        if not ModifierNode.can_modify(self, target_head):
            return False
        
        # the tests below work for multiple targets, but do they make any sense??
        assert(len(self.__ghosttargets) <= 1) 
        
        # syntactic compatibility
        if not all(gt.type() == target_head.type()  or  gt.type() == target_head.parent().type()  for gt in self.__ghosttargets):
            return False
        
        # check tags on ghosted target nodes
        # TODO: can't FULLY check semantics here, since we haven't lexicalized yet...
            # here, we assume that all tags have been set on the target, and then reject if match is not guaranteed...
        target_tags = target_head.semantic_tags()
        for ghost_target in self.__ghosttargets:
            ghost_tags = ghost_target.semantic_tags()
            for gtag in ghost_tags:            
                # the following passes: ghost target needs ['animal'], real target supplies ['person']
                if type(target_head) is Noun and not any(data.TAXONOMY.isa(ttag, gtag) for ttag in target_tags):
                    return False # other types may not go through the taxonomy...
                    
        return True
    
    def template_id(self):
        '''Overrides base class'''
        if self.__transformations:
            assert(len(self.__transformations) is 1)
            return self.__transformations[0]
        else:
            return TemplatedNode.template_id()
    
    def transformations(self):
        return self.__transformations    
    def set_transformation(self, transformation_str):    
        assert(self._template())
        assert(not self._template_readonly)
        assert(type(transformation_str) is str)
        
        # keep a running list that can be queried
        self.__transformations.append(transformation_str)
        
        # transformation will directly modify the template data structure
        template = self._template()
        
        transform = data.TRANSFORMATION_BANK.get_transformation_by_id(transformation_str)
        if transform.input_type() != self.type():
            raise Exception('Tried to transform {} - expected {}'.format(self.type(), transform.input_type()))

        self._set_type(transform.output_type())
        
        for symbol in transform.targets():
            template.add_target(template.pop_symbol(symbol)) # pop_symbol() also remove its traces from templates as a side effect
            
        if transform.remove_trailing_punctuation():
            template.remove_trailing_punctuation()
        
    def _create_symbol_subnodes(self):   
        TemplatedNode._create_symbol_subnodes(self)
        
        # create phantom node that just stores attributes for matching purposes?
        template = self._template()
        
        for k in template.target_keys():
            assert(not self.__ghostnodes.get(k))
            self.__ghostnodes[k] = Node(**dict(template.target_options_for_key(k))) # TODO: plug memory leak? (alternative is to trash template's data...)
            self.__ghosttargets.append(self.__ghostnodes[k])
            
        
    def _ghost_symbols(self):
        return self.__ghostnodes.keys()
        
    def _get_symbol_ghostnode(self, symbol):
        return self.__ghostnodes.get(symbol)
        

# now subclassing TransformableNode, to allow participles
class Clause(TransformableNode):
    '''A node that is headed by a verb'''
    def __init__(self, **kwargs): 
        TransformableNode.__init__(self, data.CLAUSE_TEMPLATE_BANK, **kwargs)
        
        self.__verb_category_id = ''
        self.__verb_category = {}
        
        
    # clauses really need to have semantics figured out before populating the next level down (except blank symbols in participles, etc.)
    def has_verb_category(self):
        return bool(self.__verb_category_id) and bool(self.__verb_category)
    def set_verb_category(self, id):    
        assert(id in data.VERBSET_BANK.categories())
        assert(not self.__verb_category)
        
        # TODO: hmm, what if you want to specify semantic category first, or neither? (like with a participle)
        category = data.VERBSET_BANK.get_category(id)            
        if self._template_id() == category.template_id():
            self.__verb_category_id = id
            self.__verb_category = category

            assert(self._can_create_symbol_subnodes())
            self._create_symbol_subnodes()
           
            self.__bequeath_to_subnodes()
            
        else:
            raise Exception('incompatible template', id, self._template_id())
            
            
    
    # overrides
    def _can_create_symbol_subnodes(self):
        # although set_verb_category() now also triggers propagation to subnodes,
        # it's still useful to wait for has_verb_category(), since then you get a chance to perform template transformations:
        # e.g., set_template(); transform(); set_verb_category()
        return self.has_template() and self.has_verb_category()
    
    # hey, notice that you don't really have to order the symbols until generation time anyway, even if specified by templates
    def _create_symbol_subnodes(self):
        TransformableNode._create_symbol_subnodes(self)
        
        # head node gets special treatment
        # this is different from other TemplatedNodes because verbs have semantic sub-categories instead of just tags...
        # alternative: _create_nodes_subclass() call in base class and override here. 
        # TODO: use add_option instead somehow?
        self.__bequeath_to_subnodes()
    
    def _tags_for_symbol(self, symbol): 
        if self.__verb_category:
            semantic_tags = self.__verb_category.tags_for_symbol(symbol) or []
            assert(type(semantic_tags) is list)
            
            return TemplatedNode._tags_for_symbol(self, symbol) + semantic_tags
        else:
            return []
    
    def __bequeath_to_subnodes(self):
        # propagate category down to head verb
        assert(self._subnodes())
        V = self._get_symbol_subnode('V')
        if self.__verb_category and V:
            V.set_category(self.__verb_category)
            
            # propagate any other semantic tags from verb category down to other symbols
            for s in self.__verb_category.tagged_symbols():
                tags = self.__verb_category.tags_for_symbol(s)
                
                # TODO: doesn't this really belong in a superclass?
                if s in self._symbols():
                    node = self._get_symbol_subnode(s)
                elif s in self._ghost_symbols(): # also propagate down to any ghost nodes, for semantic matching with real nodes
                    node = self._get_symbol_ghostnode(s)
                    
                assert(node)
                node.add_options({'tags': tags})
                
            
        
        
class CustomTemplate(TemplatedNode):
    def __init__(self, **kwargs): 
        TemplatedNode.__init__(self, data.CUSTOM_TEMPLATE_BANK, **kwargs)

    def _can_create_symbol_subnodes(self):
        return self.has_template()
    
    def _create_symbol_subnodes(self):
        TemplatedNode._create_symbol_subnodes(self)
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
    def _can_create_symbol_subnodes(self):
        return self.has_template()
        
    def _create_symbol_subnodes(self):
        TemplatedNode._create_symbol_subnodes(self)
    
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
        
        
        
class AdjectivePhrase(ModifierNode):
    def __init__(self, **kwargs): 
        ModifierNode.__init__(self, data.ADJP_TEMPLATE_BANK, **kwargs)
        
    def _can_create_symbol_subnodes(self):
        return self.has_template()
        
        
        
class AdverbPhrase(ModifierNode):
    def __init__(self, **kwargs): 
        ModifierNode.__init__(self, data.ADVP_TEMPLATE_BANK, **kwargs)
        
    def _can_create_symbol_subnodes(self):
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
        self.__parent = None # Node
        
        # default values: single-sample words (multi-sample: [cat, dog, ...])
        self.__num_samples = 1 #options.pop('num_samples', 1) # not quite - would have to propagate down from parent
        self.__selected_sample_index = 0
        
    # public
    def lexical_targets(self):
        return self.parent().lexical_targets()
    
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
            raise Exception('out of range: {}/{}'.format(index, len(self.__datasets))) 
            # can't just let the system raise IndexError, because it might not for a WHILE before it actually uses index to access
            
    def total_num_datasets(self, lang): # TODO: rename this atrocity
        # each dataset object could contain more than one "dataset" (nameset, etc.), e.g., en: [Bob, Robert]
        return sum(ds.num_words(lang) for ds in self.__datasets) 
     
    # pure virtual - must be implemented by derived classes
    def _get_lexical_candidates(self):
        raise UNIMPLEMENTED_EXCEPTION
     
    # empty default to be overridden by derived classes as needed
    def compatible_modifier_types(self):
        '''Check whether modifier is SYNTACTICALLY compatible with this target'''
        return set()
        
    # override base class
    def _generate(self, generators):
        assert(not self._subnodes()) # LexicalNode now may have modifiers as subnodes
        for lang in generators.keys():
            if not self.has_generated_text(lang):
                generators[lang].generate(self)

    def _lexicalize(self):
        self._pick_samples(self._get_lexical_candidates())
                
    def _subnodes(self):
        return [] #return self.__modifiers
                
        
    # protected - used by derived classes
    def _pick_samples(self, candidates):
        num_candidates = len(candidates)
        assert(num_candidates > 0)
        if self.num_samples() > num_candidates:
            self.set_num_samples(num_candidates)
        
        if utility.USE_RANDOM:
            self.__datasets = random.sample(candidates, self.num_samples())
        else:
            self.__datasets = candidates[:self.num_samples()]

    def _sample_dataset(self):
        '''Return the currently selected dataset'''
        return self.__get_dataset_by_index(self.__selected_sample_index)
        
    def __get_dataset_by_index(self, index):
        return self.__datasets[index]

     


class Adverb(LexicalNode):
    def adverb(self, lang):
        advset = self._sample_dataset()
        assert(advset.num_words(lang) is 1)
        return advset.adverb(lang, 0)
        
    def _get_lexical_candidates(self):
        tags = [t for t in (self._get_option('tags') or []) if type(t) is str]
        assert(len(tags) <= 1)
        if tags:            
            candidates = data.ADVSET_BANK.find_tagged(tags[0])
        else:
            candidates = data.ADVSET_BANK.all_advsets()
            
        # also need to filter by target type (not all adverbs can target all parts of speech)
        # should I really be reaching through the parent ADJP? no, i think the parent should set metadata when setting target
        advp = self.parent()
        lexical_target_types = [t.type() for t in advp.lexical_targets()]
        
        candidates = [c  for c in candidates   for lex_type in lexical_target_types   if lex_type in c.compatible_lexical_targets()]
            
        return candidates
        
        
        
# TODO: consolidate shared code with Determiner?
# TODO: semantic filtering
class Adjective(LexicalNode):
    def adjective(self, lang):
        adjset = self._sample_dataset()
        assert(adjset.num_words(lang) is 1)
        return adjset.adjective(lang, 0)
        
    def compatible_modifier_types(self):
        return { 'ADVP' }
        
    def _get_lexical_candidates(self):
        tags = [t for t in (self._get_option('tags') or []) if type(t) is str]
        assert(len(tags) <= 1)
        if tags:            
            candidates = data.ADJSET_BANK.find_tagged(tags[0])
        else:
            candidates = data.ADJSET_BANK.all_adjsets()
        return candidates
        
class Determiner(LexicalNode):
    #def add_modifier(self, _):
    #    raise Exception('do not modify Determiner nodes - are you trying PDT? how about hooking on a second DT?')
        
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
            

        
            
            

    
class Noun(GenericNoun):
    def compatible_modifier_types(self):
        return { 'ADJP' }
        
    def person(self):
        return 3
        
    def noun(self, lang):
        nounset = self._sample_dataset()
        assert(nounset.num_words(lang) == 1)
        return nounset.noun(lang, 0)
        
    def set_plural(self): # just not available in Name, although could call add_options directly, or on parent node...
        self.add_options({'number': ['plural']})
        
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

    def compatible_modifier_types(self):
        return { 'ADVP' }
        
    def get_tense(self):
        return self.__tense
        
    def verb(self, lang):    
        verbset = self._sample_dataset()
        return verbset.verb(lang)

        
    def _get_lexical_candidates(self):
        # TODO: filter further by, say, semantic tags 
        return self.__category.all_verbsets()
        
    # DELETE ME: debugging interfaces
    #def _category(self):
    #    return self.__category
        

        




    
FACTORY_MAP = {
    # Templated nodes
    'ADJP': AdjectivePhrase,
    'ADVP': AdverbPhrase,
    'Clause': Clause,
    'CustomTemplate': CustomTemplate,
    'NP': NounPhrase,
    
    # lexical nodes
    'adjective': Adjective,
    'adverb': Adverb,
    'determiner': Determiner,
    'name': Name, 
    'noun': Noun,
    'verb': Verb
}

       
def node_factory(type, **kwargs):
    '''Object factory that will instantiate the appropriate class, with an optional dict of tags, etc.'''
    factory = FACTORY_MAP[type] # will raise KeyError if not found
    return factory(type=type, **kwargs)
        
        
        
        
    
    




