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
    
def make_transitive_clause(number='singular', modifiers=[]):    
    clause = nodes.node_factory('Clause')
    clause.set_template('transitive', readonly=False)
    
    clause.set_transformation('participle')
    
    # must be called after set_template() now, due to current transformation implementation...
    clause.set_verb_category('emotion.desire') #'action.possession') 

    S, V, O = [clause._get_symbol_subnode(sym) for sym in 'SVO']
    #S.set_template('noun'); #S.add_options({'tags': ['object']})#, 'number': 'plural'})
    S.set_template('name'); #O.add_options({'tags': ['man']})
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
    
    
    # add a determiner. oooooo
    # TODO: does this logic really belong here?
    for mod in modifiers:
        assert(mod in ['determiner', 'adjective'])
        adjp = nodes.node_factory('ADJP') 
        adjp.set_template(mod)
        if mod == 'determiner':
            adjp.add_options({'tags': ['demonstrative']})
        O.add_modifier(adjp)
    
    lexical_nodes = clause.get_all_lexical_nodes() # n.b. you would have to rerun this every time you modified the tree... 
    determiners = [n for n in lexical_nodes if n.type() == 'determiner']
    #assert(len(determiners) is 1)
    for d in determiners:
        d.set_num_samples(5)
        
    #for node in lexical_nodes:
    #    if node.type() == 'name':
    #        node.set_num_samples(5)
    
    

    
    

    clause.lexicalize_all() # uses tags/constraints from above to choose namesets, verbsets, etc. to be sampled
    
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
        
    custom.lexicalize_all()
    return custom
 
 
 
clauses = [ None
    , make_transitive_clause()
    #, make_transitive_clause(number='plural')
    #, make_transitive_clause(modifiers=['determiner'])
    #, make_transitive_clause(number='plural', modifiers=['determiner'])
    #, make_transitive_clause(modifiers=['adjective'])
    #, make_transitive_clause(modifiers=['adjective', 'determiner'])
    ##, make_transitive_clause(modifiers=['adjective', 'determiner', 'adjective']) # works, but has awkward repeated adjs right now
    ##, make_transitive_clause(modifiers=['adjective', 'determiner', 'adjective', 'adjective'])
    , make_transitive_clause(number='plural', modifiers=['adjective', 'determiner'])
    #, make_custom()
    #, make_custom(number='plural')
    #, make_custom(modifiers=['determiner'])
    #, make_custom(number='plural', modifiers=['determiner'])
    ]
    

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


def generate_all(clause, outputs):
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
            
            
        print(clause.generated_text('en'))
        
        for lang in LANGUAGES:
            outputs[lang].write(clause.generated_text(lang) + '\n')
    
    
# hmm, should I really be using singletons for this?
analyzer = generator.analyzer
generators = generator.generators
assert(set(generator.generators.keys()) == set(LANGUAGES))

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