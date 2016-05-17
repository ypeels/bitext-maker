import os

import data # may take a while

import generator
import nodes
from utility import LANGUAGES, seed_rng



assert(__name__ == '__main__') # for now


#seed_rng() # output still not deterministic? loops over dicts are still random



### 1. Specify sentences ###

# where will this logic live??
# actually, i think it should commute - user CAN specify certain constraints, then object specifies the rest
    # I suppose this is important for transformed Clauses, for which you specify "empty subject" or something
    # BUT, don't you have to create a public API with which you reach down into the tree?
# I think that ideally there would be some kind of metadata format that can specify all this 
    
def make_transitive_clause(**kwargs):   
    clause = nodes.node_factory('Clause')
    return configure_transitive_clause(clause, **kwargs)
    
# broken off for reuse in make_meta()
def configure_transitive_clause(clause, number='singular', modifiers=[], transformations=[], template_readonly=True):
    clause.set_template('transitive', readonly=template_readonly)
    assert(not clause._subnodes())
    
    # must be called after set_template() now, due to current transformation implementation...
    # subnodes are generated after both template and verb category have been set.
    # this gives transformations the chance to modify the template.
    clause.set_verb_category('action')  #'action.possession')#
    assert(clause._subnodes())
    
    if transformations and not template_readonly:
        for trans in transformations:
            clause.add_transformation(trans)

    S, V, O = [clause._get_symbol_subnode(sym) for sym in 'SVO']
    if S: S.set_template('noun'); S.add_options({'tags': ['person']})#, 'number': 'plural'})
    #S.set_template('name'); #O.add_options({'tags': ['man']})
    #S.set_template('name'); #O.add_options({'tags': ['man']})
    #O.set_template('name')
    #S.set_template('noun'); #S.add_options({'tags': ['animal']})
    
    O.set_template('noun'); O.add_options({'tags': ['object']})
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
        #modifiers.remove('participle')
        participle = nodes.node_factory('Clause', manually_create_subnodes=True)
        participle.set_template('transitive', readonly=False)
        
        # TODO: some verbs don't seem to work as participles ("the man having the car") - need to blacklist somehow...
        participle.set_verb_category('emotion.desire')
        
        # currently must be run AFTER set_verb_category(), or else it breaks template matching with verb_category...
        participle.add_transformation('participle') 
        participle.create_symbol_subnodes_manually()
        

        
        PO = participle._get_symbol_subnode('O') # note that current test harness requires all NP's to have specified templates...
        PO.set_template('noun'); PO.add_options({'tags': ['object']})
        if S: S.add_modifier(participle)
    
    
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
        
    #for node in lexical_nodes:
    #    if node.type() == 'name':
    #        node.set_num_samples(5)
    
    

    
    

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
    meta.set_verb_category('emotion.desire.meta') #'cognition.knowledge')  
    assert(meta._subnodes())
 
    S, C = [meta._get_symbol_subnode(sym) for sym in 'SC']
    #S.set_template('noun');
    S.set_template('name'); #S.add_options({'tags': ['person']})#, 'number': 'plural'})
    
    if not bottom_up:
        configure_transitive_clause(C, template_readonly=False, **kwargs)
    #C.add_transformation('infinitive.clause') # hey, this works! even though subnodes have already been created
    #C.add_transformation('remove punctuation')
    
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
    modal.set_verb_category('emotion.desire.modal')
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
    vp.set_verb_category('action')
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
    modal.set_verb_category('emotion.desire.modal') # this performs vp.add_transformation(infinitive.vp) via template
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
    modal2.set_verb_category('emotion.desire.modal')
    
    return modal2
    
    
    

  

    
    

    

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


def generate_all(clause, outputs=None):
    # TODO: only need to analyze # samples for a SINGLE language? well, this more general way permits different sample numbers for different langs
        # but then you'd have to have nested indices... still, it's doable in principle.
    # this would be required to reuse analyzer  for multiple trees...should this go in Node.analyze_all()?
    analyzer.reset_num_samples() 
    clause.analyze_all(analyzer)


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
        print(sentence_case(clause.generated_text('en')))
        
        if outputs:
            for lang in LANGUAGES:
                outputs[lang].write(sentence_case(clause.generated_text(lang)) + '\n')
    
def sentence_case(sentence):
    return sentence[:1].upper() + sentence[1:]
    
    
if __name__ == '__main__':
    # hmm, should I really be using singletons for this?
    analyzer = generator.analyzer
    generators = generator.generators
    assert(set(generator.generators.keys()) == set(LANGUAGES))

    clauses = [ None
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
        #, make_custom()
        #, make_custom(number='plural')
        #, make_custom(modifiers=['determiner'])
        #, make_custom(number='plural', modifiers=['determiner'])    
        ]
    
    outputs = { lang: open('output_{}.txt'.format(lang), 'w', encoding='utf8') for lang in LANGUAGES }
    for c in clauses:
        if c:
            generate_all(c, outputs)
    for o in outputs.values():
        o.close()


#with open('output.txt', 'w', encoding='utf8') as output:
#    for lang in LANGUAGES:
#        output.write(clause.generated_text(lang) + '\n')


    
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