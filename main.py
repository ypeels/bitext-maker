import os

import data # may take a while, depending on data set size

import datetime
import generator
import nodes
import random
import utility
from utility import LANGUAGES, seed_rng


# collected flags for quick toggling during testing
if utility.PRODUCTION:
    FIXED_ROLL = FIXED_TEMPLATE = MUTE_OLD_TEST = None
    NUM_RANDOM_TEST = 1
else:
    FIXED_ROLL = FIXED_TEMPLATE = MUTE_OLD_TEST = None
    #FIXED_ROLL = 0.75 # 0-0.8 for Clause, 0.8-0.9 for Custom, 0.9-1.0 for C1 C2 - see make_random_sentence()
    #FIXED_TEMPLATE = '把'
    MUTE_OLD_TEST = True
    NUM_RANDOM_TEST = 50

    

#assert(__name__ == '__main__') # for now # disabled for capitalization hack


#seed_rng() # output still not deterministic? loops over dicts are still random

def get_verb_category_by_template(template):
    verb_categories = data.VERBSET_BANK.get_categories_by_template(template)
    if utility.USE_RANDOM:
        category = random.choice(verb_categories)
    else:
        category = verb_categories[0]
    return category


### 1. Specify sentences ###

# where will this logic live??
# actually, i think it should commute - user CAN specify certain constraints, then object specifies the rest
    # I suppose this is important for transformed Clauses, for which you specify "empty subject" or something
    # BUT, don't you have to create a public API with which you reach down into the tree?
# I think that ideally there would be some kind of metadata format that can specify all this 
    
# initial test harness functions 
def make_transitive_clause(**kwargs):   
    clause = nodes.node_factory('Clause')
    return configure_transitive_clause(clause, **kwargs)
    
# broken off for reuse in make_meta()
def configure_transitive_clause(clause, number='singular', subject_type='noun', object_type='noun',
                        modifiers=[], transformations=[], template_readonly=True, **kwargs):    
    clause.set_template('transitive', readonly=template_readonly)
    assert(not clause._subnodes())
    
    # oops, this should be called before subnodes are created
    if transformations and not template_readonly:
        for trans in transformations:
            clause.add_transformation(trans)
    
    # must be called after set_template() now, due to current transformation implementation...
    # subnodes are generated after both template and verb category have been set.
    # this gives transformations the chance to modify the template.
    category = get_verb_category_by_template('transitive')
    clause.set_verb_category(category)  #'action.possession')#
    assert(clause._subnodes())

    S, V, O = [clause._get_symbol_subnode(sym) for sym in 'SVO']
    if S: 
        S.set_template(subject_type); #S.add_options({'tags': ['person']})#, 'number': 'plural'})
        if subject_type in ['noun', 'pronoun']:
            S.add_options({'tags': ['animal']})
            
        if subject_type in ['pronoun']:
            S.add_options({'number': [number]})
    #S.set_template('name'); #O.add_options({'tags': ['man']})
    #S.set_template('name'); #O.add_options({'tags': ['man']})
    #O.set_template('name')
    #S.set_template('noun'); #S.add_options({'tags': ['animal']})
    
    O.set_template(object_type); 
    if object_type == 'noun':
        O.add_options({'tags': ['object']})
    O.add_options({'number': [number]}) # TODO: how to pluralize more robustly?? set_plural() would not be scalable to other options...
        
    #A, B = [np._get_subnode('N') for np in [S, O]] # calling "protected" functions externally is a bad sign/smell]
    #A.add_options({'tags': ['woman']})
    #S.add_options({'tags': ['woman']}) # gets propagated down now, even if called AFTER A and B have been created
    #B.add_options({'tags': ['man']}) # hmm... 
    #if A.type() == 'noun': A.set_plural()
    #if B.type() == 'noun': B.set_plural() # this would raise AttributeError on Name anyway
    #if type(B) is nodes.Noun: B.set_plural() # alternative using Python types; more brittle?
    
    #A.set_num_samples(2)
    #B.set_num_samples(5)
    
    # looks like you should be able to add a modifier to S or O, and it would get transferred down to the head child
    
    # add a participle...
    if 'participle' in modifiers:
        assert(modifiers.count('participle') is 1)
        participle = nodes.node_factory('Clause', manually_create_subnodes=True)
        participle.set_template('transitive', readonly=False)
        
        # TODO: some verbs don't seem to work as participles ("the man having the car") - need to blacklist somehow...
        participle.set_verb_category('emotion.desire')
        
        # currently must be run AFTER set_verb_category(), or else it breaks template matching with verb_category...
        participle.add_transformation('participle') 
        participle.create_symbol_subnodes_manually()
        

        
        PO = participle._get_symbol_subnode('O') # note that current test harness requires all NP's to have specified templates...
        PO.set_template(kwargs.get('participle_object_type', 'noun')); 
        if PO.template_id() == 'noun':
            PO.add_options({'tags': ['object']})
        if S and S.template_id() == 'noun': 
            S.add_modifier(participle)
            if object_type == 'pronoun':
                O._get_symbol_subnode('P').set_antecedent(PO)
        else:
            assert(not O.template_id() == 'pronoun')
            O.add_modifier(participle)
    
    
    # add a determiner. oooooo
    # TODO: does this logic really belong here?
    for mod in modifiers:
        if mod in ['determiner', 'adjective', 'noun']:
            adjp = nodes.node_factory('ADJP') 
            adjp.set_template(mod)
            if mod == 'determiner':
                adjp.add_options({'tags': ['demonstrative']})
            O.add_modifier(adjp)

    # add adverb - to both verb and adjective (if present)
    if 'adverb' in modifiers:
        advp = nodes.node_factory('ADVP')
        advp.set_template('adverb')
        clause.add_modifier(advp)
        
        
    # add adverb to adjective (if present)
    if 'adverb' in modifiers and 'adjective' in modifiers:
        # TODO: should i just expose "get_all_nodes()"?
        adjective_phrases = {a.parent() for a in clause.get_all_lexical_nodes() if a.type() == 'adjective'}
        assert(all(ap.type() == 'ADJP' for ap in adjective_phrases))
        
        for adjp in adjective_phrases:
            advp = nodes.node_factory('ADVP')
            advp.set_template('adverb')
            adjp.add_modifier(advp)
        
        
        
            
            
    
    lexical_nodes = clause.get_all_lexical_nodes() # n.b. you would have to rerun this every time you modified the tree... 
    determiners = [n for n in lexical_nodes if n.type() == 'determiner']
    #assert(len(determiners) is 1)
    for d in determiners:
        d.set_num_samples(5)
        
    for node in lexical_nodes:
        if node.type() == 'pronoun':
            node.set_num_samples(10)
    
    

    
    

    #clause.lexicalize_all() # uses tags/constraints from above to choose namesets, verbsets, etc. to be sampled
    
    return clause
 
def make_custom(number='singular', modifiers=[]):
    '''Experimenting with large, custom template'''
    custom = nodes.node_factory('CustomTemplate')
    custom.set_template('test')
    
    noun_phrases = [n for n in custom.get_all_lexical_nodes() if n.type() == 'NP']    
    X = custom._get_symbol_subnode('X')
    X.set_template('noun')
    #X.add_options({'tags': ['object']})
    #X.add_options({'number': [number]}) # shouldn't be trying to pluralize "it can be a very complicated thing, X"
    #for word in custom.get_all_lexical_nodes():
    #    word.set_num_samples(10)
        
    for mod in modifiers:
        adjp = nodes.node_factory('ADJP') 
        adjp.set_template(mod)
        if mod == 'determiner':
            adjp.add_options({'tags': ['demonstrative']})
        X.add_modifier(adjp)
        
    #custom.lexicalize_all()
    return custom
 
 
def make_meta(bottom_up=False, **kwargs): # n.b. these are kwargs for INTERNAL use, not to be passed to node_factory
    meta = nodes.node_factory('Clause')
    meta.set_template('meta', readonly=False) # writable to allow verb-bin-specific additions from data
    
    assert(not meta._subnodes())
    if bottom_up:
        C = make_transitive_clause(template_readonly=False, **kwargs)
        meta.add_symbol_subnode('C', C)    
    category = get_verb_category_by_template('meta')
    meta.set_verb_category(category)#'emotion.desire.meta') #'cognition.knowledge')  
    assert(meta._subnodes())
 
    S, C = [meta._get_symbol_subnode(sym) for sym in 'SC']
    #S.set_template('noun');
    S.set_template('name'); #S.add_options({'tags': ['person']})#, 'number': 'plural'})
    
    if not bottom_up:
        configure_transitive_clause(C, template_readonly=False, **kwargs)
    #C.add_transformation('infinitive.clause') # hey, this works! even though subnodes have already been created
    #C.add_transformation('remove punctuation') # considered this, but removing the wrapping meta's punctuation for now
    
    #raise Exception('TODO: C-template change for things like "I forced HIM TO VB"')
    
    #meta.lexicalize_all() # - moved to generate_all and analyze_all() this is SO easy to forget, and it doesn't give you a descriptive error message...
    
    return meta


    
def make_modal_topdown(**kwargs):

    # OKAY, I see - there are actually TWO versions of this
        # top-down: initialize S directly - no need to migrate it from C. MAYBE set a link to outer S from C
        # bottom-up: S is initialized from C, then it's ghosted out and then added to outer modal before its (other) subnodes are created

    # top-down
    modal = nodes.node_factory('Clause')
    modal.set_template('modal')
    category = get_verb_category_by_template('modal')
    modal.set_verb_category(category)#'emotion.desire.modal')
    assert(modal._subnodes())
    
    S, C = [modal._get_symbol_subnode(sym) for sym in 'SC']
    S.set_template('noun'); #S.add_options({'tags': ['object']})
    C.set_template('transitive', readonly=False)
    
    # semantic matching between outer S and the ghost S from the VP is enforced by the ghost node mechanism (I think)
    C.add_ghostnode('S', S, kind='linked')
    C.set_verb_category('action')
    
    O = C._get_symbol_subnode('O')
    O.set_template('noun'); O.add_options({'tags': ['object']})
    
    return modal
    
    
# moved down to allow a call to generate_all() in the middle of the building
def make_modal_bottomup(**kwargs):
        
    # bottom-up version
    vp = nodes.node_factory('Clause')#, manually_create_subnodes=True)
    vp.set_template('transitive', readonly=False)
    #vp.add_transformation('infinitive.vp')
    category = get_verb_category_by_template('transitive')
    vp.set_verb_category(category)
    #vp.create_symbol_subnodes_manually()
    #
    S, O = [vp._get_symbol_subnode(sym) for sym in 'SO']
    S.set_template('name')
    O.set_template('name'); 
    #vp._get_symbol_subnode('O').set_template('name')    
    print('"derivation intermediate" - ', end='')
    generate_all(vp)
    
    modal = nodes.node_factory('Clause')
    modal.set_template('modal', readonly=False)
    modal.add_symbol_subnode('C', vp) 
    modal.add_symbol_subnode('S', S)
    vp.add_transformation('infinitive.vp')
    vp.convert_symbol_to_ghostnode('S', 'target') 
    #modal.set_verb_category('emotion.desire.modal') # this performs vp.add_transformation(infinitive.vp) via template
    modal.set_verb_category(get_verb_category_by_template('modal'))
    print('"derivation intermediate" - ', end='')
    generate_all(modal)
    
    # currently needs to be done after set_verb_category(), which propagates transformations down to subnodes in create_symbol_subnodes
    # TODO must I do this externally? it's definitely easier, but...
    
    modal2 = nodes.node_factory('Clause')
    modal2.set_template('modal')
    modal2.add_symbol_subnode('C', modal) 
    modal2.add_symbol_subnode('S', S)
    modal.add_transformation('infinitive.vp')
    modal.convert_symbol_to_ghostnode('S', 'target') 
    #modal2.set_verb_category('emotion.desire.modal')
    modal2.set_verb_category(get_verb_category_by_template('modal'))
    
    return modal2
    
    
####################################################################################    
# generating lots of random sentences (top-down)
 
def modifiable_template_ids():
    '''
    ad hoc list of clause templates that can be made writable - forbid transformations
    - this is a hack to let me hook untransformable custom clauses into the rest of Clause infrastructure
    '''
    return ['meta', 'modal', 'transitive']
 
#def verb_categories_per_template(template_id):
#    if template_id == '把': # TODO: this really belongs in data, but need to design optimal infrastructure there
#        return ['action']
#    else:
#        return data.VERBSET_BANK.categories()
 
def make_random_sentence():
    '''Make a random clause or custom, and modify it in random places too.'''
    roll = utility.rand()
    if FIXED_ROLL:
        roll = FIXED_ROLL
        
    if roll <= 0.8:
        clause = nodes.node_factory('Clause')    
        randomly_configure_clause(clause)
        return clause
    elif 0.8 < roll <= 0.9:
        custom = nodes.node_factory('CustomTemplate')
        randomly_configure_custom(custom)
        return custom        
    else:
        # C1 C2 - multiple sentences on a line, TED-style
        clause = nodes.node_factory('Clause')    
        randomly_configure_clause(clause)
    
        line = nodes.node_factory('CustomTemplate', manually_create_subnodes=True)
        line.set_template('multiple')
        line.add_symbol_subnode('C1', clause)        
        line.create_symbol_subnodes_manually()
        
        clause2 = line._get_symbol_subnode('C2')
        assert(clause2)
        randomly_configure_clause(clause2)
        
        return line
    
def randomly_configure_node(node, **kwargs):  
    assert(not issubclass(type(node), nodes.LexicalNode))
    if node.type() == 'Clause':
        randomly_configure_clause(node, **kwargs)
    elif node.type() == 'NP':
        randomly_configure_np(node, **kwargs)
    #elif node.type() == 'ADJP':
    #    randomly_configure_adjp(node, **kwargs)
    else:
        raise Exception('Unhandled node type, presumably non-lexical', type(node))
        
        
        
def randomly_configure_clause(clause, stack_depth=1, **kwargs):
    # allow non-modifiable clauses only at the outer level - some metas require transformation - I want him to have the world
    if stack_depth is 1:
        candidates = data.CLAUSE_TEMPLATE_BANK.all_template_ids()
    else:
        candidates = modifiable_template_ids()
        
    # don't go too deep down the rabbit hole (human speakers and writers typically don't)
    if stack_depth > 2:
        candidates.remove('meta')
        candidates.remove('modal')
        
    # add back in some custom templates as desired... not very scalable...
    if stack_depth > 1 and len(clause.transformation_list()) is 0:
        candidates += ['把']
        
    template_id = utility.pick_random(candidates)
    if FIXED_TEMPLATE:
        template_id = FIXED_TEMPLATE
    
    # randomly add a transformation, like topicalization or past tense
    # in current implementation, topicalization breaks if this is done after verb_category is set 
        # probably need to redo something involving subnode creation    
    readonly = template_id not in modifiable_template_ids()
    if not readonly and utility.rand() <= 0.25: # overall transformation rate           
        if utility.rand() <= 0.75 and clause.verb_category_id() in generator.PAST_TENSE_WHITELIST:
            clause.add_transformation('tense.past')
        # syntactically, topicalization should only be done at the top level, right? (the code fails anyway at lower levels with meta/modal?)
        elif utility.rand() <= 0.5 and template_id in ['transitive'] and stack_depth is 1:
            clause.add_transformation('topicalization')    
    
    # TODO: nested modals with same verb read like duplicated verbs in zh... should be alleviated by scaling # verbs up...    
    clause.set_template(template_id, readonly=readonly)
    clause.set_random_verb_category()  
    
    templated_subnodes = [sn for sn in clause._subnodes() if issubclass(type(sn), nodes.TemplatedNode)]
    for subnode in templated_subnodes:
        randomly_configure_node(subnode, stack_depth=stack_depth+1, **kwargs)
    
    
    
def randomly_configure_np(np, **kwargs):
    # pure rand() doesn't give fine-grained control over the distribution
    #template_id = utility.pick_random(data.NP_TEMPLATE_BANK.all_template_ids())
    
    # TODO: patch this data-reading code through data.py. currently breaks abstraction, for the sake of rapid development
    try:
        forbidden_templates = np._get_option('forbidden templates')
    except KeyError:
        forbidden_templates = []
        
    roll = utility.rand()
    if roll < 0.05 and 'pronoun' not in forbidden_templates:
        template_id = 'pronoun'
    elif 0.05 <= roll < 0.2:
        assert('name' not in forbidden_templates)
        template_id = 'name' # shouldn't make it THAT common        
    else: 
        template_id = 'noun'
            
    np.set_template(template_id)
    
    # generator only supports objects right now (otherwise determiners get tricky... like "water" or "cloth")
    if template_id == 'noun':
        np.add_options({'tags': ['object']})
        
        # at most one determiner (syntactic constraint)
        if utility.rand() <= 0.5:
            np.add_modifier(make_random_determiner(**kwargs))
        
        
        # TODO: disallow multiple identical adjectives (the big and big person)
        for i in range(5): # TODO: zh gets awkward with more than 2 adjectives, esp. single-char...
            if utility.rand() < 0.2: 
                modifier = make_random_adjp(np, **kwargs)
                if modifier:
                    assert(all(modifier.can_modify(head) for head in np._get_headnodes()))
                    np.add_modifier(modifier)
            
        # at most one participle (practical constraint)
        # TODO: disallow ambiguous participle attachment? the man seeing the woman holding the umbrella
        if kwargs.get('stack_depth') < 3 and utility.rand() <= 0.25:
            participle = make_random_participle(np, **kwargs)
            assert(participle)
            if participle:
                np.add_modifier(participle)
    
    
    
def make_random_adjp(target, **kwargs):
    adjp = nodes.node_factory('ADJP')
    randomly_configure_adjp(adjp, target=target, **kwargs)
    return adjp

def randomly_configure_adjp(adjp, target=None, **kwargs):
    # first determine the type you want - determiners done separately
    if utility.rand() <= 0.9:
        template_id = 'adjective'
    else:
        template_id = 'noun' 
        
    adjp.set_template(template_id)
    # TODO: semantic adjective tags - probably just a very loose mapping here for now, like object: [color, size, ...]

def make_random_determiner(**kwargs):
    det = nodes.node_factory('ADJP')
    det.set_template('determiner')
    #adjp.add_options({'tags': ['demonstrative']})
    return det

    
    
def make_random_participle(target, max_runs=10, stack_depth=1, **kwargs):
    assert(target.type() == 'NP')
    PARTICIPLE_BLACKLIST = {'possession'} # TODO: maybe a whitelist is more in order?
    
    target_heads = target._get_headnodes()
    
    target_verb_agreement = False
    for i in range(max_runs):
        participle = nodes.node_factory('Clause', manually_create_subnodes=True)
        participle.set_template('transitive', readonly=False)        
        
        candidate_categories = data.VERBSET_BANK.get_categories_by_template('transitive')
        category = utility.pick_random([cat for cat in candidate_categories if cat not in PARTICIPLE_BLACKLIST])
        participle.set_verb_category(category)
        
        # could in principle use head_symbols() and _get_symbol_subnodes(), but that breaks "encapsulation" too
        participle.add_transformation('participle')        
        
        if all(participle.can_modify(head) for head in target_heads):
            participle.create_symbol_subnodes_manually()
            randomly_configure_node(participle._get_symbol_subnode('O'), stack_depth=stack_depth+1, **kwargs)
            return participle
            
    return None
        
        
def randomly_configure_custom(custom):
    candidates = [id for id in data.CUSTOM_TEMPLATE_BANK.all_template_ids() 
                    if id not in { 'multiple' }] # blacklist some that are not intended for random generation here...
                    
    template_id = random.choice(candidates)
    if FIXED_TEMPLATE:
        template_id = FIXED_TEMPLATE
    custom.set_template(template_id)
    
    templated_subnodes = [sn for sn in custom._subnodes() if issubclass(type(sn), nodes.TemplatedNode)]
    for subnode in templated_subnodes:
        if not subnode.has_template(): # might have specified template manually in data
            randomly_configure_node(subnode, stack_depth=2)
    


    

### 2. Generate sentences ###

# this is a BIT more flexible than making it a member of Analyzer, since it can also be called externally
def count_digits(bases):
    '''
    Exhaustively loop through "variable-base" number, where each digit has a different base, little-endian
    
    TODO: nested bases, like [(3, (4, 5))], or however it is that I decide to represent language-specific synsets
    '''
    assert(all(type(d) is int and d > 1 for d in bases))
    
    digits = [0] * len(bases)
    overflow = False
    while not overflow: # alternative: extra carry digit for termination 
        yield tuple(digits) 
        
        # += 1, long-addition
        place = 0   
        carry = True        
        while carry and place < len(digits):
            carry = False        
            digits[place] += 1
            if digits[place] >= bases[place]:
                assert(digits[place] == bases[place])
                digits[place] = 0
                place += 1
                carry = True
        
        assert(0 <= place <= len(digits))
        overflow = (place == len(digits))


def generate_all(clause, outputs=None, blow_it_up=False):
    # TODO: only need to analyze # samples for a SINGLE language? well, this more general way permits different sample numbers for different langs
        # but then you'd have to have nested indices... still, it's doable in principle.
    # this would be required to reuse analyzer  for multiple trees...should this go in Node.analyze_all()?
    
    if blow_it_up:
        nodes = clause.get_all_lexical_nodes()
        for n in nodes:
            n.set_num_samples(100) # blow this sucker up. how many lines do I get? (this is largely for morale)
    
    analyzer.reset_num_samples() 
    
    try:
        clause.analyze_all(analyzer)
    except Exception as e: # allows access to root node for debugging
        import pdb; pdb.set_trace()
        raise


    # note that you opt into multisampling via set_num_samples ABOVE - and that determines the length of the list passed to select_samples() 
    max_selections = analyzer.num_samples()

    # currently generating ALL samples
    for t in count_digits(max_selections):
        clause.ungenerate_all()

        analyzer.select_samples(t)

        # TODO: wrap this in a giant loop that takes into account all candidate madlib choices
        # generate a single sentence (a single choice of madlibs)
        while not all(clause.has_generated_text(lang) for lang in LANGUAGES):
            #print('taking another pass through the tree')
            
            # TODO: this is now vestigial, right? don't really need this if it's always just a single pass....
            # reset the generators' counters for a pass through the whole tree
            for g in generators.values():
                g.reset_generated_counter()

            clause.generate_all(generators)
            if not all(clause.has_generated_text(lang) for lang in LANGUAGES) or not all(g.num_generated() > 0 for g in generators.values()):
                raise Exception('full pass through tree did not generate anything - cyclic dependencies?')
                
            # multipass was actually vestigial - single pass should suffice now, right? (EnGenerator._generate_verb())
            # I guess now I'm assuming all metadata has been set before even entering the generation phase... horribly inflexible?
            assert(all(clause.has_generated_text(lang) for lang in LANGUAGES))
            break
                
            
        # TODO: do this somewhere else instead of tacking it on at the end??
        # ugh, sentence casing is important for multi-sentence lines... 
        if not utility.PRODUCTION:
            print(sentence_case(clause.generated_text('en')))

        if outputs:
            for lang in LANGUAGES:
                outputs[lang].write(sentence_case(clause.generated_text(lang)) + '\n')
    
def sentence_case(sentence):
    return sentence[:1].upper() + sentence[1:]

    
def make_test_clauses():
    # clauses to test the overall generation system
    test_clauses = [ None
        , make_transitive_clause()
        , make_transitive_clause(template_readonly=False, transformations=['tense.past'])
        #, make_transitive_clause(template_readonly=False).add_transformation('tense.past') # doesn't work since add_transformation() returns None
        ##, make_transitive_clause(number='plural')
        ##, make_transitive_clause(modifiers=['determiner'])
        ##, make_transitive_clause(number='plural', modifiers=['determiner'])
        , make_transitive_clause(modifiers=['adjective'])
        , make_transitive_clause(modifiers=['adjective', 'determiner'])
        , make_transitive_clause(modifiers=['noun'])
        ###, make_transitive_clause(modifiers=['adjective', 'determiner', 'adjective']) # works, but has awkward repeated adjs right now
        ###, make_transitive_clause(modifiers=['adjective', 'determiner', 'adjective', 'adjective'])
        , make_transitive_clause(number='plural', modifiers=['adjective', 'determiner'])
        , make_transitive_clause(number='plural', modifiers=['adjective', 'determiner', 'participle'])
        , make_transitive_clause(modifiers=['adjective', 'adverb'])
        , make_meta(modifiers=['adjective', 'determiner'])
        , make_meta(modifiers=['adjective', 'determiner'], bottom_up=True)
        , make_modal_topdown()
        , make_modal_bottomup()
        , make_transitive_clause(number='plural', modifiers=['adjective', 'determiner'])
        #, make_transitive_clause(subject_type='pronoun')
        #, make_transitive_clause(subject_type='pronoun', number='plural')
        #, make_transitive_clause(object_type='pronoun', modifiers=['participle'])
        #, make_transitive_clause(object_type='pronoun', modifiers=['participle'], participle_object_type='name')
        , make_transitive_clause(transformations=['topicalization'], template_readonly=False)
        #, make_custom()
        #, make_custom(number='plural')
        #, make_custom(modifiers=['determiner'])
        #, make_custom(number='plural', modifiers=['determiner']) 
        ]
        
    return test_clauses
        
        
def run_test():
    test_clauses = make_test_clauses()
    if MUTE_OLD_TEST:
        test_clauses = []

    # clauses that test the data set
    random_clauses = [make_random_sentence() for i in range(NUM_RANDOM_TEST)] 
    #random_clauses = []

    clauses = test_clauses + random_clauses
    
    outputs = { lang: open('output_{}.txt'.format(lang), 'w', encoding='utf8') for lang in LANGUAGES }
    for c in clauses:
        if c:
            generate_all(c, outputs)#, blow_it_up=True)
    for o in outputs.values():
        o.close()
        
        
def run_production():
    output_prefix = datetime.datetime.isoformat(datetime.datetime.now()).replace('T', '-').replace(':', '')[:-7]
    outputs = { lang: open('{}-generated.{}'.format(output_prefix, lang), 'w', encoding='utf8') for lang in LANGUAGES }
    for i in range(1, 100001): # for large corpus, you want to "stream" the trees instead of storing them all
        # TODO: pick, say, just one random lexical node (make sure it's Noun/Verb/Adj) and blow it up - guarantee some "parallel" sentences
        generate_all(make_random_sentence(), outputs)
        if i % 1000 is 0:
            print(i)
            
    for o in outputs.values():
        o.close()
    
    
if __name__ == '__main__':
    #seed_rng() # for reproducibility? meh, doesn't work since I loop over dict keys, which is not deterministic

    # hmm, should I really be using singletons for this?
    analyzer = generator.analyzer
    generators = generator.generators
    assert(set(generator.generators.keys()) == set(LANGUAGES))

    if utility.PRODUCTION:
        run_production()
    else:
        run_test()
    




# TODO: enforce distinctness of names? well, can do that with man/woman... and noun list should be long enough for few repeats

# TODO: external mapping of noun classes (animal, person, object) to eligible adjectives (color, etc.) - internal would take longer

#
## TODO: have the Clause grab its own data from a TemplateBank
## well, it should really do this
#clause.set_template(template['syntax'], template['semantics'][0])

# putting logic outside the class seems like a BAD idea - it kind of defeats the whole point of encapsulation
#print(clause.symbols_needed())