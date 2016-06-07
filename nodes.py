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
    def __init__(self, **input_options): # contains data, so probably don't want to use as a mixin (would have to call constructor in derived classes)
        self.__dependencies = []
        
        self.__generated_text = None # { 'en': 'Alice' ... }
        self.__is_all_lexicalized = False
        
        # just store them for now and figure out what to do with them later... can always use dict.pop()
        options = dict(input_options) # make copy for trashing - would it be clearer to call self.__options.pop()?
        self.__type = options.pop('type', None) # might be a ghost node, which doesn't need a type
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
                
            # duplicates are not added
            for nv in new_values:
                if nv not in self.__options[key]:
                    self.__options[key] += [nv]
            
    def generated_text(self, lang):
        return self.__generated_text[lang] # throw an exception to reveal premature accesses #.get(lang, '')
    def has_generated_text(self, lang):
        return self.__generated_text.get(lang) is not None
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
        if not self.__is_all_lexicalized:
            self.lexicalize_all()
            
        for sn in self._subnodes():
            sn.analyze_all(analyzer)
        analyzer.analyze(self)
    
    def generate_all(self, generators):
        if not self.__is_all_lexicalized:
            self.lexicalize_all()
    
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
        self.__is_all_lexicalized = True
        
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
    def __init__(self, bank, manually_create_subnodes=False, **kwargs):
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
        
        self.__waiting_for_manual_subnodes = manually_create_subnodes 
        
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
    
    # still keeping _symbols() "protected" (non-external) as a precaution - should only be called by external tree-builder, which SHOULD know symbols
    def add_symbol_subnode(self, symbol, subnode):
        '''Allows trees to be built 'bottom-up' by creating subnodes externally, then tacking them on'''
        assert(self.has_template())
        assert(not self.__symbol_subnodes.get(symbol)) # incoming symbol should be new
        
        old_symbols = self.__symbol_subnodes.keys()
        assert(symbol not in old_symbols)
        
        # alternative: if this is the final symbol subnode, call the "post-processing" portion of _create_symbol_subnode
        if len(old_symbols) >= len(self._symbols())-1:
            raise Exception('Cannot add ALL symbols manually - not yet, anyway')
            
        self.__symbol_subnodes[symbol] = subnode
        
    # used by tree-making harness        
    def create_symbol_subnodes_manually(self):
        '''Delayed manual subnode creation when instantiated with manually_create_subnodes=True'''
        assert(self.__waiting_for_manual_subnodes is True)
        self.__waiting_for_manual_subnodes = False # ready to proceed
        self._create_symbol_subnodes()
        
    
    # used by Generator
    def analyze_all(self, analyzer): # an override
        if not self.has_template():
            raise Exception('Untemplated node', self.type())
        Node.analyze_all(self, analyzer)        
    
    def generated_symbols(self, lang):   
        # TODO: patch template-specified literal words properly through the data and tree system
        return { symbol: subnode.generated_text(lang) 
            for symbol, subnode in self.__symbol_subnodes.items() if subnode.has_generated_text(lang) }
            
    def get_template_text(self, lang):
        return self._template().template_text(lang)
            
    def head_symbols(self):
        return [symbol for symbol, subnode in self.__symbol_subnodes.items() if subnode in self._get_headnodes()]
            
    def num_symbols(self):
        return len(self._symbols()) # TODO: cache this on calling set_template()?
    
    def has_template(self):
        return bool(self._template_id()) and bool(self._template())    
    def set_template(self, id, readonly=True):
        assert(self._template_readonly is None) # set_template should only be called once, for initialization
        self._template_readonly = readonly
    
        self.__template = self.__template_bank.get_template_by_id(id, readonly)
        assert(type(self.__template) is data.Template)
        self.__template_id = id
        
        if self._can_create_symbol_subnodes():
            self._create_symbol_subnodes()
        
    def syntax_tags_for_symbol(self, symbol, lang): 
        # TODO: delegate to Template? kind of assuming knowledge of this data structure here...
        syntax_tags = [t for t in self._tags_for_symbol(symbol) if type(t) is dict]
        if syntax_tags:
            assert(len(syntax_tags) is 1)
            return syntax_tags[0].get(lang, [])
        else:
            return []   
        
        
    def template_id(self):     # ugh, exposed for external use
        return self._template_id()

    def template_prewords(self, lang):
        return self._template().prewords(lang)
    def template_postwords(self, lang):
        return self._template().postwords(lang)        
        
        
    ### "pure virtual" functions - to be implemented in derived classes ###
    # not needed per se (duck typing will get it), but still valuable to document what this function is
    # currently empty
        
    ### "protected" functions - default implementations, MAY be overridden in derived classes ###
    def _bequeath_to_subnodes(self):
        if self._subnodes():
            for symbol, subnode in self.__symbol_subnodes.items():
                # language-specific syntax tags 
                subnode.add_options({'tags': self._tags_for_symbol(symbol)})
                   
                # literal lexical forms (VBG, VBP, etc.) hard-coded into template - propagate to lexical node
                # rebuild data structure using data API, instead of assuming particular form of raw data. probably no slower than deepcopy...?
                forms = { lang: self._template().form_for_symbol(symbol, lang)
                    for lang in utility.LANGUAGES
                    if self._template().form_for_symbol(symbol, lang) }                
                    
                # TODO: migrate away from add_options, which it won't overwrite literal forms... currently just read "newest" form in LexicalNode
                if forms:
                    subnode.add_options({'forms': forms}) 
                
                # this was previously only done in CustomTemplatedNode. is it okay to double-add? will this break anything? 
                subnode.add_options(self._template().options_for_symbol(symbol))
                
        else:
            raise Exception('cannot bequeath to non-existent subnodes')

    def _can_create_symbol_subnodes(self):
        return self.has_template() and not self.__waiting_for_manual_subnodes
            
    def _create_symbol_subnodes(self):
        '''Creates only the subnodes specified by the template - no modifiers'''
        # currently assumes not ALL subnodes are created from bottom up - also asserted in add_subnode()
        if self._can_create_symbol_subnodes() and not all(s in self.__symbol_subnodes.keys() for s in self._symbols()): #not self.__symbol_subnodes:
            # new implementation ignores multiple calls to this function - to simplify enclosing logic
            #assert(not self.__subnodes) # this function should only be called once, for initialization 
        
            # requires symbols to be unique... but they SHOULD be, since they're in a dict
            #self.__symbol_subnodes = { s: node_factory(self._type_for_symbol(s))
            #    for s in self._symbols() }
            for sym in self._symbols():
                if sym not in self.__symbol_subnodes.keys():
                    self.__symbol_subnodes[sym] = node_factory(self._type_for_symbol(sym))
                
            # the parent-child relationship is not currently expected to change, so it's not part of _bequeath()
            for subnode in self.__symbol_subnodes.values():
                if issubclass(type(subnode), LexicalNode):
                    subnode.set_parent(self) # for modifiers to query parent node for target           
            
            # hook up dependencies between NODES and their data - all nodes must have been instantiated first
            # add_dependency() should allow pronouns to work all the way across the tree...right?
            # TODO: move this to _bequeath()? should deps be allowed to change from transformations?
            for sym in self._symbols():
                for lang, dependents in self._per_lang_deps_for_symbol(sym):
                    for dep in dependents:
                        assert(self._get_symbol_subnode(dep) and self._get_symbol_subnode(sym))
                        self._get_symbol_subnode(sym).add_dependency(self._get_symbol_subnode(dep), lang=lang)
            
            self.__headnodes = [self._get_symbol_subnode(sym) for sym in self.__template.head_symbols()]
            assert(len(self.__headnodes) <= 1)            
            # TODO: alter head upon transformation
            
            # after a bit of ugliness in Template (and calls to it), all-lang deps can be specified in data now
            for sym in self._symbols():
                for dep in self._lang_indep_deps_for_symbol(sym):
                    self._get_symbol_subnode(sym).add_dependency(self._get_symbol_subnode(dep))

            self._bequeath_to_subnodes()

            
                        
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
    def _get_headnodes(self):
        return self.__headnodes
        
    def _get_symbol_subnode(self, symbol):
        return self.__symbol_subnodes.get(symbol)
        
    def _lang_indep_deps_for_symbol(self, symbol):
        return self.__template.lang_indep_deps_for_symbol(symbol)

    def _per_lang_deps_for_symbol(self, symbol):
        result = self.__template.per_lang_deps_for_symbol(symbol) #.items()        
        assert(all(type(item) is tuple for item in result))
        return result
        
    def _pop_symbol_subnode(self, symbol):
        return self.__symbol_subnodes.pop(symbol)
        

   
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
        
    def _set_template_id(self, id):
        self.__template_id = id

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
        
    def can_modify(self, lexical_target):
        return self.type() in lexical_target.compatible_modifier_types()
        
        
        
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
        #self.__ghostlinks = []
        
        self.__pending_transformations = []
        self.__finished_transformations = []
            
        
    def can_modify(self, target_head):
        assert(issubclass(type(target_head), LexicalNode)) # the alternative was to expose TemplatedNode.headnodes()... maybe that ain't so bad?
        
        # get base class out of the way
        if not ModifierNode.can_modify(self, target_head):
            return False
        
        # the tests below work for multiple targets, but do they make any sense??
        assert(len(self._ghost_targets()) <= 1) 
        
        # syntactic compatibility
        if not all(gt.type() == target_head.type()  or  gt.type() == target_head.parent().type()  for gt in self.__ghosttargets):
            return False

        # check tags on ghosted target nodes
        # TODO: can't FULLY check semantics here, since we haven't lexicalized yet...
            # here, we assume that all tags have been set on the target, and then reject if match is not guaranteed...
        # TODO: merge tags somehow before lexicalizing?
        target_tags = target_head.semantic_tags()
        for ghost_target in self._ghost_targets():
            ghost_tags = ghost_target.semantic_tags()
            for gtag in ghost_tags:            
                # the following passes: ghost target needs ['animal'], real target supplies ['person']
                if type(target_head) is Noun and not any(data.TAXONOMY.isa(ttag, gtag) for ttag in target_tags):
                    return False # other types may not go through the taxonomy...
                    
        return True
    
    def set_template(self, id, readonly=True):
        TemplatedNode.set_template(self, id, readonly)
        if self.__has_pending_transformations():
            self.apply_transformations()
    
    # this was a BAD and confusing idea. as a hack, though, it worked in a pinch
    #def template_id(self):
    #    '''Overrides base class'''
    #    if self.__transformations:
    #        assert(len(self.__transformations) is 1)
    #        return self.__transformations[0]
    #    else:
    #        return TemplatedNode.template_id(self)
    
    def add_transformation(self, transformation_str):        
        assert(not self._template_readonly)
        assert(type(transformation_str) is str)

        # keep a running list that can be queried
        self.__pending_transformations.append(transformation_str)
        
        if self._template():
            self.apply_transformations()
            
    # split off from add_transformation() to allow "queuing" transformations before templates are ready
    def apply_transformations(self):
        assert(self._template())
        assert(not self._template_readonly)
        
        for transformation_str in self.__pending_transformations:
            self.__apply_single_transformation(transformation_str)
        self.__finished_transformations += self.__pending_transformations
        self.__pending_transformations.clear()
        
        # re-run any bequests that were done in _create_subnodes() - but only if subnodes have already been created
        # this is getting a BIT overly complicated...
        if self._subnodes():
            self._bequeath_to_subnodes()
            
    def transformation_list(self):
        return self.__pending_transformations + self.__finished_transformations
        
    ### Direct node manipulation by tree builder ###
    def add_ghostnode(self, key, new_ghost, kind=None):
        __template = self._template()
        assert(__template)     
        assert(key not in __template.symbols())
        assert(key in __template.ghost_keys())
        assert(kind in ['target', 'linked'])
        
        if key not in self.__ghostnodes:        
            self.__ghostnodes[key] = new_ghost                  
            if kind == 'target':
                self.__ghosttargets.append(new_ghost)
            #elif kind == 'linked':
            #    self.__ghostlinks.append(new_ghost) # wait, why do I need to keep track of that?
            #else:
            #    raise Exception('Unsupported kind of ghost node', kind)
        else:
            raise Exception('Ghost node already exists', key)
            
    def convert_symbol_to_ghostnode(self, symbol, kind):
        self.add_ghostnode(symbol, self._pop_symbol_subnode(symbol), kind=kind)
        
    ### end Direct node manipulation by tree builder ###
            
    def _create_symbol_subnodes(self):   
        assert(not self.__pending_transformations) # pending transformations get cleared upon set_template()        

        TemplatedNode._create_symbol_subnodes(self)
        
        # create phantom node that just stores attributes for matching purposes?
        template = self._template()
        
        for key, kind in template.ghosts():# target_keys():
            assert(not self._get_symbol_subnode(key)) 

            if kind == 'target':
                options = dict(template.target_options_for_key(key)) # TODO: plug memory leak? (alternative is to trash template's data...)
            else:
                options = {}            
            
            if self.__ghostnodes.get(key):
                # existing ghost node - add target options
                self.__ghostnodes[key].add_options(options)            
            else:
                # create new (dummy) ghost node
                self.add_ghostnode(key, Node(**options), kind=kind)

            
        # this allows transformations for subnodes to be specified in data.
        # not moved to bequeath(), since this should only be called once...
        for symbol in self._symbols():
            transformations = self._transformations_for_subnode(symbol)#self.__verb_category.transformation_for_symbol(symbol)
            if transformations:
                assert(type(transformations) is list)
                for transform in transformations:
                    self._get_symbol_subnode(symbol).add_transformation(transform)

            
        
    def _ghost_symbols(self):
        return self.__ghostnodes.keys()
        
    def _ghost_targets(self):
        return self.__ghosttargets
        
    def _get_symbol_ghostnode(self, symbol):
        return self.__ghostnodes.get(symbol)
        
        
    # override as needed - for Clause, this reads from a VerbCategory
    def _transformations_for_subnode(self, symbol):
        pass # returns None
        
    def __apply_single_transformation(self, transformation_str):
        '''Applies transformation to Template'''
        transform = data.TRANSFORMATION_BANK.get_transformation_by_id(transformation_str)
        assert(transform) # although you'd never get here, since get_transformation() would throw KeyError...
        assert(type(transform) is data.Transformation)
        
        #assert(transformation_str not in self.__finished_transformations)
        if transformation_str in self.__finished_transformations: # allows more flexible ordering in main logic
            return
        
        # transformation will directly modify the template data structure
        __template = self._template()        
        
        if transform.input_type() and transform.input_type() != self.type():
            raise Exception('Tried to transform {} - expected {}'.format(self.type(), transform.input_type()))

        if transform.output_type():
            self._set_type(transform.output_type())
            
        if transform.output_template_id():
            self._set_template_id(transform.output_template_id())
        
        # convert symbol in template to ghosted target slot (Clause S V O -> Participle V O)
        #for symbol in transform.targets():
        #    __template.add_target(__template.pop_symbol(symbol)) # pop_symbol() also remove its traces from templates as a side effect
        if transform.conversions():
            __template.perform_conversions(transform.conversions()) # duh, delegate to template itself
            
         
        
            
        additional_data = transform.additions()
        if additional_data:
            __template.add_data(additional_data)
            
            
        # TODO: apply transformation operations to any existing nodes for bottom-up tree construction
            
    def __has_pending_transformations(self):
        return bool(self.__pending_transformations)
        

        

# now subclassing TransformableNode, to allow participles
class Clause(TransformableNode):
    '''A node that is headed by a verb'''
    def __init__(self, **kwargs): 
        TransformableNode.__init__(self, data.CLAUSE_TEMPLATE_BANK, **kwargs)
        
        self.__verb_category_id = ''
        self.__verb_category = None # VerbCategory
        
        
    # clauses really need to have semantics figured out before populating the next level down (except blank symbols in participles, etc.)
    def has_verb_category(self):
        return bool(self.__verb_category_id) and bool(self.__verb_category)
    def set_verb_category(self, id):    
        assert(id in data.VERBSET_BANK.categories())
        assert(self.__verb_category is None) # initialize only once
        
        # TODO: hmm, what if you want to specify semantic category first, or neither? (like with a participle)
        category = data.VERBSET_BANK.get_category(id)       # assume an explicitly-specified verb category is compatible     
        if self._template_id() == category.template_id() or id in self.__explicit_verb_categories():
            self.__verb_category_id = id
            self.__verb_category = category

            #assert(self._can_create_symbol_subnodes())
            if self._can_create_symbol_subnodes():
                self._create_symbol_subnodes()
                #self._bequeath_to_subnodes() # now called by _create_symbol_subnodes

        else:
            raise Exception('incompatible template', id, self._template_id(), category.template_id())
            # originally, verb category specifies one and only one template
            # but now, i want to do the "reverse" - pick a random semantic verb category, based on a custom clause template
                # i'm actually not totally sure this is going to work... the original assumption is in place,
                # BECAUSE the verb category assumes particular symbols
            
    def set_random_verb_category(self):
        category_candidates = data.VERBSET_BANK.get_categories_by_template(self._template_id())
        if category_candidates:
            category = utility.pick_random(category_candidates)
        else:
            category = utility.pick_random(self.__explicit_verb_categories())
        self.set_verb_category(category)
            
            
    def verb_category_id(self):
        return self.__verb_category_id
            
    def __explicit_verb_categories(self):
        '''Eligible verb categories, specified in data'''
        template = self._template()
        if template:
            return template.categories() or []
        else:
            return []
            
    
    
    # overrides
    def _can_create_symbol_subnodes(self):
        # although set_verb_category() now also triggers propagation to subnodes,
        # it's still useful to wait for has_verb_category(), since then you get a chance to perform template transformations:
        # e.g., set_template(); transform(); set_verb_category()
        return TransformableNode._can_create_symbol_subnodes(self) and self.has_verb_category() # and self.has_template()
    
    
    def _create_symbol_subnodes(self):
        # quick first attempt - additional bin-specific template overrides from data
        # note that for this to work, the clause has to be writable...
        # TODO: move add_data() to set_verb_category?.
        additional_data = self.__verb_category.additions()
        if additional_data:
            self._template().add_data(additional_data)        
    
        TransformableNode._create_symbol_subnodes(self)
        #self._bequeath_to_subnodes() # now called by superclass
        

        
        
        
    
    def _tags_for_symbol(self, symbol): 
        if self.__verb_category:
            semantic_tags = self.__verb_category.tags_for_symbol(symbol) or []
            assert(type(semantic_tags) is list)
            
            return TemplatedNode._tags_for_symbol(self, symbol) + semantic_tags
        else:
            return []
    
    def _transformations_for_subnode(self, symbol):
        return self.__verb_category.transformation_for_symbol(symbol)
    
    # hey, notice that you don't really have to order the symbols until generation time anyway, even if specified by templates
    def _bequeath_to_subnodes(self):
        TransformableNode._bequeath_to_subnodes(self)
        
        # head node gets special treatment
        # this is different from other TemplatedNodes because verbs have semantic sub-categories instead of just tags...
        # alternative: _create_nodes_subclass() call in base class and override here. 
        # TODO: use add_option instead somehow?
    
        # propagate category down to head verb
        assert(self._subnodes())
        V = self._get_symbol_subnode('V')
        if self.__verb_category and V:
            V.set_category(self.__verb_category)
            
            # propagate any other semantic tags from verb category down to other symbols
            for sym in self.__verb_category.tagged_symbols():
                tags = self.__verb_category.tags_for_symbol(sym)
                
                # TODO: doesn't this really belong in a superclass? or transformation code?
                if sym in self._symbols():
                    node = self._get_symbol_subnode(sym)
                elif sym in self._ghost_symbols(): # also propagate down to any ghost nodes, for semantic matching with real nodes
                    node = self._get_symbol_ghostnode(sym)
                else:
                    node = None
                    
                if node: #assert(node) # might legitimately have been ghosted out, e.g., participle
                    node.add_options({'tags': tags}) 



class PrepositionalPhrase(TransformableNode):
    WHY_TRANSFORMABLE = 'PrepositionalPhrase inherits TransformableNode for ghost node functionality, but should never be transformed...right?'
    
    def __init__(self, **kwargs): 
        TransformableNode.__init__(self, data.PP_TEMPLATE_BANK, **kwargs)
        self.__prep_category_id = ''
        self.__prep_category = None # PrepCategory
        
    def has_prep_category(self):
        return bool(self.__prep_category)
    def set_prep_category(self, id):
        assert(id in data.PREPSET_BANK.categories())
        assert(self.__prep_category is None)
    
        category = data.PREPSET_BANK.get_category(id)
        if self._template_id() == category.template_id():
            self.__prep_category_id = id
            self.__prep_category = category
            
            additional_data = category.additions()
            if additional_data:
                self._template().add_data(additional_data) 
                
            assert(self._can_create_symbol_subnodes())
            self._create_symbol_subnodes()
            
        else:
            raise Exception('incompatible template', id, self._template_id(), category.template_id())
            
            
    # TODO: DRY this out with Clause.set_random_verb_category()
    def set_random_category(self):
        category_candidates = data.PREPSET_BANK.get_categories_by_template(self._template_id())
        assert(category_candidates)
        category = utility.pick_random(category_candidates)
        self.set_prep_category(category)
    
        
    # overrides
    def add_lexical_target(self, target_node):
        ModifierNode.add_lexical_target(self, target_node)
        
        # TODO: for verb targets, you'd have to pick VerbCategory-compatible PPs at construction time
        if self.type() == 'ADJP':
            assert(self.template_id() == 'pp.adjp') # maybe switch this with the if test?
        
            new_tags = sum([gt.semantic_tags() for gt in self._ghost_targets()], [])

            # target's parent already calls this for every head in add_modifier() - no need to add tags to parent instead, right?
            # well, this way, the parent doesn't have these new tags... hmm...
            target_node.add_options({'tags': new_tags})
            #target_node.parent().add_options({'tags': new_tags})
        
    def can_modify(self, lexical_target):
        if not TransformableNode.can_modify(self, lexical_target):
            return False
        
        #assert(issubtype(type(target_node), GenericNoun)) # for verbs, you have to look at verb category...
        assert(lexical_target.type() == 'noun')
        current_tags = lexical_target.semantic_tags()
        requested_tags = sum([gt.semantic_tags() for gt in self._ghost_targets()], [])
        
        # don't muck with the taxonomy; just directly check whether any nouns exist fulfilling these tags (based on random np technology)        
        return bool(data.NOUNSET_BANK.find_tagged(current_tags + requested_tags))
        
    def set_template(self, id): #, readonly=True):
        TransformableNode.set_template(self, id, readonly=False) # always allow additions to PP from category

        # otherwise you'd have to work PP into the list of acceptable modifiers... but pp.adjp shouldn't modify verbs, etc.
        assert(id.startswith('pp.'))
        self._set_type(id.split('.')[1].upper())        
        assert(self.type() in ['ADJP', 'ADVP'])
        
    
    def _can_create_symbol_subnodes(self): # by analogy with Clause
        assert(not self.transformation_list())
        return TransformableNode._can_create_symbol_subnodes(self) and self.has_prep_category()
        
    def _create_symbol_subnodes(self):
        TransformableNode._create_symbol_subnodes(self)
    
        # annoying bit of white-box knowledge: can't just override _bequeath - have to wait for TransformableNode to create ghost nodes.
        assert(self._subnodes())
        assert(self._ghost_targets())
        P = self._get_symbol_subnode('P')
        P.set_category(self.__prep_category)
        
        # propagate semantic tags from category down to other symbols - same as for Clause
        category = self.__prep_category
        for sym in category.tagged_symbols():
            tags = category.tags_for_symbol(sym)
            if sym in self._symbols():
                node = self._get_symbol_subnode(sym)
            elif sym in self._ghost_symbols(): # also propagate down to any ghost nodes, for semantic matching with real nodes
                node = self._get_symbol_ghostnode(sym)
            else:
                raise Exception('''{} shouldn't have been ghosted out, unlike Clause - no transformations for PP'''.format(sym))                
            
            if node: 
                node.add_options({'tags': tags}) 

    def add_transformation(self, _):
        raise Exception(WHY_TRANSFORMABLE)
        
    def apply_transformations(self):
        raise Exception(WHY_TRANSFORMABLE)
            
        
        
class CustomTemplate(TemplatedNode):
    def __init__(self, **kwargs): 
        TemplatedNode.__init__(self, data.CUSTOM_TEMPLATE_BANK, **kwargs)
    
    def _create_symbol_subnodes(self):
        TemplatedNode._create_symbol_subnodes(self)
        #for sym in self._symbols(): # moved to superclass
        #    self.add_options(self._template().options_for_symbol(sym))
        # pass other language-independent options from template
        # TODO: refactor this into TemplatedNode and the awkward _tags/_deps system?
        
        # TODO: move this into Template. Custom was always meant to be down and dirty, though...
        __template_data = self._template()._Template__data
        for sub_symbol, sub_data in __template_data['symbols'].items():
            subnode = self._get_symbol_subnode(sub_symbol)
        
            sub_template = sub_data.get('template')
            if sub_template:
                subnode.set_template(sub_template)
                
            sub_target = sub_data.get('target')
            if sub_target:
                subnode.add_lexical_target(self._get_symbol_subnode(sub_target))

    
        
        
class NounPhrase(TemplatedNode):
    def __init__(self, **options):
        TemplatedNode.__init__(self, data.NP_TEMPLATE_BANK, **options)

    def lexical_tags(self):
        '''Reaches down deep into LexicalNodes to get concrete tags as antecedent for Pronoun'''
        headnodes = self._get_headnodes()
        headtags = [head.lexical_tags() for head in headnodes]
        return headtags
        
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
        
    #def _can_create_symbol_subnodes(self):
    #    return self.has_template()
        
        
        
class AdverbPhrase(ModifierNode):
    def __init__(self, **kwargs): 
        ModifierNode.__init__(self, data.ADVP_TEMPLATE_BANK, **kwargs)
        
    # moved to base class 
    #def _can_create_symbol_subnodes(self):
    #    return self.has_template()
        
        
        
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
        
    # public interface
    def fixed_form(self, lang):
        forms_option = self._get_option('forms')
        if forms_option:
            assert(type(forms_option) is list)
            forms = [item.get(lang, '') for item in forms_option]
            
            # TODO: overwrite forms instead in TemplatedNode._bequeath_to_subnodes
            #assert(len(forms) is 1)
            assert(len(forms) >= 1)
            return forms[-1]
            
        else:
            return ''
    
    def lexical_tags(self):
        '''Returns (language-independent, presumably semantic) tags from currently selected WordSet'''
        selected_wordset = self._sample_dataset()
        tags = selected_wordset.tags()
        assert(type(tags) is list and all(type(t) is str for t in tags)) # single word WordSets for now...
        return tags        
    
    def lexical_targets(self):
        return self.parent().lexical_targets()
    
    def num_samples(self):
        #if self.__datasets: # used to assume self.__datasets was only initialized once, but that's changed, with bottom-up metas... 
        #    #assert(self.__num_samples == len(self.__datasets))
        #    pass
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
            
    def tags_for_lang(self, lang):
        tags = self._get_option('tags')
        
        # start by grabbing any language-independent tags
        lang_tags = [tag for tag in tags if type(tag) is str]
        
        for item in tags:
            if item and type(item) is not str:
                lang_tags += item.get(lang, [])
        return lang_tags
        
            
    def total_num_datasets(self, lang): # TODO: rename this atrocity
        # OLD: each dataset object could contain more than one "dataset" (nameset, etc.), e.g., en: [Bob, Robert]
        #return sum(ds.num_words(lang) for ds in self.__datasets) 
        # NEW: just sampling ONE member of each dataset, for simplicity
        return len(self.__datasets)
        
     
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
       
    # this function is used to hack in literal words from templates.
    # has to be called EXPLICITLY from subclasses - 
    def word(self, lang): 
        # TODO: propagate words down from template into LexicalNode properly
        words_hack = self.parent()._get_option('words hack')
        if words_hack:
            assert(len(self.parent()._subnodes()) is 1) # fixed word from template is intended for this only child
            assert(self.total_num_datasets(lang) is 1) # not wasting tons of iterations on the same fixed word, fwiw
            return words_hack[0][lang]
        else:
            #return self._word(lang) # punt to subclass
            return self._sample_dataset().word(lang)
       
        
    # private - for internal use by this class only
    def __get_dataset_by_index(self, index):
        return self.__datasets[index]

     


class Adverb(LexicalNode):
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
    def compatible_modifier_types(self):
        return { 'ADVP' }
        
    def _get_lexical_candidates(self):
        tags = [t for t in (self._get_option('tags') or []) if type(t) is str]
        #assert(len(tags) <= 1)
       
        if tags:            
            candidates = data.ADJSET_BANK.find_tagged_with_any(tags)#find_tagged(tags)
        else:
            candidates = data.ADJSET_BANK.all_unrestricted_adjsets() # adjs are hacked slightly differently - see data.py
            
        return candidates
        
class Determiner(LexicalNode):
    #def add_modifier(self, _):
    #    raise Exception('do not modify Determiner nodes - are you trying PDT? how about hooking on a second DT?')
        
    def _get_lexical_candidates(self):
        tags = [t for t in (self._get_option('tags') or []) if type(t) is str]
        if tags:            
            candidates = data.DETSET_BANK.find_tagged(tags)
        else:
            candidates = data.DETSET_BANK.all_detsets()
        return candidates
        
        
        
class GenericNoun(LexicalNode): 
    '''Abstract base class to share code with Name, Noun, Pronoun, ...'''
    def number(self):
        #if 'plural' in self._get_option('tags'): # should this really be lumped with semantic tags? well, it is language-independent...
        number_options = self._get_option('number')        
        assert(not number_options or not('plural' in number_options and 'singular' in number_options)) # must be either unspecified or not overspecified
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
        
    def _get_lexical_candidates(self):
        assert(self._get_option('tags') is not None)
        semantic_tags = [tag for tag in self._get_option('tags') if type(tag) is str]
        #assert(len(semantic_tags) <= 1)
        
        if semantic_tags:
            candidates = data.NAME_BANK.find_tagged(semantic_tags)   
        else:
            candidates = data.NAME_BANK.all_namesets()
            
        return candidates

        
    
class Noun(GenericNoun):
    def compatible_modifier_types(self):
        return { 'ADJP' }
        
    def person(self):
        return 3
        
    def set_plural(self): # just not available in Name, although could call add_options directly, or on parent node...
        self.add_options({'number': ['plural']})
        
    def _get_lexical_candidates(self):
        semantic_tags = self.semantic_tags() #[tag for tag in self._get_option('tags') if type(tag) is str]  #

        #assert(len(semantic_tags) <= 1)
        if semantic_tags:
            candidates = data.NOUNSET_BANK.find_tagged(semantic_tags)   
        else:
            candidates = data.NOUNSET_BANK.all_nounsets()
            
        # hack to prevent noun-noun modifiers that look like VPs
        # TODO: is there any more principled way to do this?
        if self.parent().type() == 'ADJP':
            candidates = [can for can in candidates if 'activity' not in can.tags()]

        return candidates
        
class Pronoun(GenericNoun):
    #def __init__(self, **options):
    #    GenericNoun.__init__(self, **options)
        # TODO: specify person (I, you, he) externally using option pronoun.person (can't be a tag though - would clash with semantic check)
        
    # TODO: merge this with the "dependencies" system (is that relegated to template-specified dependencies at this point?)
    def has_antecedent(self):        
        return bool(self.__antecedent())
    def set_antecedent(self, node):
        assert(issubclass(type(node), NounPhrase) or (issubclass(type(node), TemplatedNode) and node.type() == 'NP'))
        if node.type() != 'NP':
            raise Exception('Pronoun must refer to a NounPhrase...right?')
            
        # TODO: allow longer antecedent chains? what if the cycle is really long? this would be hard in general.
        # TODO: check heads instead of all subnodes
        if any(sn.type() == 'pronoun' and sn.has_antecedent() for sn in node._subnodes()): 
            raise Exception('The proposed antecedent itself has an antecedent - currently forbidden, to prevent cyclic dependencies')
            
        assert(not self.has_antecedent())
        self.add_dependency(node)

    def word(self, lang):
        if self.has_antecedent():
            # have to figure out correct pronset from antecedent
            antecedent = self.__antecedent()
            assert(len(antecedent.lexical_tags()) is 1)
            antecedent_tags = antecedent.lexical_tags()[0]
            # can't merge antecedent's tags in, because this tree node might need to be reused with a different antecedent word...?
            
            if antecedent.person() is not 3: # it might be another pronoun
                # TODO: reflexives...
                pronset = data.PRONSET_BANK.find_by_person(antecedent.person())[0]
            elif any(data.TAXONOMY.isa(tag, 'man') for tag in antecedent_tags):
                pronset = data.PRONSET_BANK.find_tagged_third_person('man')[0]         # he
            elif any(data.TAXONOMY.isa(tag, 'woman') for tag in antecedent_tags):
                pronset = data.PRONSET_BANK.find_tagged_third_person('woman')[0]       # she
            elif any(data.TAXONOMY.isa(tag, 'person') for tag in antecedent_tags):
                pronset = data.PRONSET_BANK.find_tagged_third_person('man')[0]         # he
            else:
                pronset = data.PRONSET_BANK.find_tagged_third_person('nonhuman')[0]    # it
            
            result = pronset.word(lang)
        else:
            result = GenericNoun.word(self, lang)
        return result
        
        
    # overriding GenericNoun
    def number(self):
        if self.has_antecedent():
            return self.__antecedent().number()
        else:
            return GenericNoun.number(self)
    
    def person(self): 
        antecedent = self.__antecedent()
        if antecedent:
            assert(self.has_antecedent())
            # TODO: coordinated antecedent... (Alice and I, we ... )
            return antecedent.person()
        else:
            assert(self._sample_dataset())
            pronset = self._sample_dataset()
            return pronset.person() # TODO: here is where this can finally get set to something other than 3

            
    # overriding LexicalNode
    def num_samples(self):
        if self.has_antecedent():
            return 1
        else:
            return GenericNoun.num_samples(self)
    
    def select_sample(self, index):
        if self.has_antecedent():
            pass # will read tags from antecedent at generation time instead
        else:
            GenericNoun.select_sample(self, index)
        
    def _get_lexical_candidates(self):
        if self.has_antecedent():
            # currently should never get here; just read antecedent metadata at generation time
            raise Exception('currently unused')
            # OR maybe this should get called after all, but at generation time?
                # call _get_lexical_candidates() from pronoun()?
            
            # TODO: subject-verb semantic matching with antecedents?
                # to do this properly, should really pull tags from antecedent, then feed to VERB at lexicalization time...
                # for now, just rely on the tree writer to enforce that...
        else:
            return data.PRONSET_BANK.find_tagged(self.semantic_tags() or [])

    
    def _lexicalize(self):
        
        if self.has_antecedent(): 
            # with antecedent, this node is empty and just waits until generation time to read metadata from antecedent
            # - CANNOT lexicalize here without knowing the exact antecedent word being used.
                # - for example, pronoun(#animal) could be he, she, OR it, depending on what #animal gets chosen at generation time
            pass #raise Exception('Should not lexicalize pronoun with antecedent')            
            
        else:
            GenericNoun._lexicalize(self)
            
    def __antecedent(self):
        dependencies = self.get_dependencies()
        assert(len(dependencies) <= 1)
        assert(all(issubclass(type(node), NounPhrase) or (issubclass(type(node), TemplatedNode) and node.type() == 'NP') for node in dependencies))
        if dependencies:
            return dependencies[0] 
        else:
            return None
    

class Preposition(LexicalNode):
    '''Prepositions themselves have no real tags - like Verb, they just pull a word off of their Category'''
    def __init__(self, **kwargs):
        LexicalNode.__init__(self, **kwargs)
        self.__category = None # data.PrepCategory
        
    def set_category(self, category):
        assert(self.__category is None)
        self.__category = category
        
    def _get_lexical_candidates(self):
        return self.__category.all_prepsets()
    
class Verb(LexicalNode):
    def __init__(self, **kwargs):
        LexicalNode.__init__(self, **kwargs)
        self.__category = None # data.VerbCategory
        #self.__verbsets = [] # data.VerbSet
        
    #def get_verbset_by_index(self, index):
    #    return self.get_dataset_by_index(index) #self.__verbsets[index]
        
    def set_category(self, category):
        assert(self.__category is None or self.__category == category) # TODO: why is category getting set redundantly sometimes?
        self.__category = category

    def compatible_modifier_types(self):
        return { 'ADVP' }
        
    # TODO: does this really belong here, in a multilingual data structure? 
    # well, could tag different languages with different tenses, although that is assumed NOT to be the case below...
    def get_tense(self):
    
        # uh, this requires a suspiciously large amount of knowledge about the tag data structure...
        tags_per_lang = [item for item in self._get_option('tags') if type(item) is dict]
        assert(len(tags_per_lang) <= 1)
        if tags_per_lang:
            TENSE_PREFIX = 'tense.'
            tense_tags = [tag for lang in utility.LANGUAGES for tag in tags_per_lang[0][lang] if tag.startswith(TENSE_PREFIX)]
            if tense_tags:
                if all(tag == tense_tags[0] for tag in tense_tags[1:]):
                    return tense_tags[0][len(TENSE_PREFIX):]
                else:
                    raise Exception('Non-unique tense?', tense_tags)
                
        return 'present'
        
    def _get_lexical_candidates(self):
        # TODO: filter further by, say, semantic tags 
        return self.__category.all_verbsets()
        

        




    
FACTORY_MAP = {
    # Templated nodes
    'ADJP': AdjectivePhrase,
    'ADVP': AdverbPhrase,
    'Clause': Clause,
    'CustomTemplate': CustomTemplate,
    'NP': NounPhrase,
    'PP': PrepositionalPhrase,
    
    # lexical nodes
    'adjective': Adjective,
    'adverb': Adverb,
    'determiner': Determiner,
    'name': Name, 
    'noun': Noun,
    'preposition': Preposition,
    'pronoun': Pronoun,
    'verb': Verb
}

       
def node_factory(type, **kwargs):
    '''Object factory that will instantiate the appropriate class, with an optional dict of tags, etc.'''
    factory = FACTORY_MAP[type] # will raise KeyError if not found
    return factory(type=type, **kwargs)
        
        
        
        
    
    




