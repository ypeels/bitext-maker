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
    
clause = nodes.node_factory('Clause')
clause.set_template('transitive')
clause.set_verb_category('action.possession') 
clause._create_subnodes()


S, V, O = [clause._get_subnode(sym) for sym in 'SVO']

for n in [S, O]:
    n.set_template('name')
    n._create_subnodes()
    
A, B = [np._get_subnode('N') for np in [S, O]]
#A.add_options({'tags': ['woman']})
S.add_options({'tags': ['woman']}) # gets propagated down now, even if called AFTER A and B have been created
#B.add_options({'tags': ['man']}) # hmm... 


A.set_num_samples(10)
B.set_num_samples(10)


clause.lexicalize_all() # uses tags/constraints from above to choose namesets, verbsets, etc. to be sampled


### 2. Generate sentences ###

# hmm, should I really be using singletons for this?
analyzer = generator.analyzer
generators = generator.generators
assert(set(generator.generators.keys()) == set(LANGUAGES))

# TODO: only need to analyze # samples for a SINGLE language? well, this more general way permits different sample numbers for different langs
    # but then you'd have to have nested indices... still, it's doable in principle.
# this would be required to reuse analyzer  for multiple trees...should this go in Node.analyze_all()?
analyzer.reset_num_samples() 
clause.analyze_all(analyzer)


# note that you opt into multisampling via set_num_samples ABOVE - and that determines the length of the list passed to select_samples() 
max_selections = analyzer.num_samples()

# this is a BIT more flexible than making it a member of Analyzer, since it can also be called externally
def count_digits(bases):
    '''Loop through "variable-base" number, where each digit has a different base, little-endian'''
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
            
        
        
outputs = { lang: open('output_{}.txt'.format(lang), 'w', encoding='utf8') for lang in LANGUAGES }

# currently generating ALL samples
for t in count_digits(max_selections):
    clause.ungenerate_all()

    analyzer.select_samples(t)

    # TODO: wrap this in a giant loop that takes into account all candidate madlib choices
    # generate a single sentence (a single choice of madlibs)
    while not all(clause.has_generated_text(lang) for lang in LANGUAGES):
        #print('taking another pass through the tree')
        
        # reset the generators' counters for a pass through the whole tree
        for g in generators.values():
            g.reset_generated_counter()

        clause.generate_all(generators)
        if not all(clause.has_generated_text(lang) or generators[lang].num_generated() > 0 for lang in LANGUAGES):
            raise Exception('full pass through tree did not generate anything - cyclic dependencies?')
        
    print(clause.generated_text('en'))
    
    for lang in LANGUAGES:
        outputs[lang].write(clause.generated_text(lang) + '\n')
    

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