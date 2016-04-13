import os

import data # may take a while

import generator
import nodes
from utility import LANGUAGES

#make_node('NP', tags=['man', 'plural'])
        




assert(__name__ == '__main__') # for now





### 2. Generate sentences ###

## some quickie testing
#names = data.NAME_BANK
#women = names.find_tagged('woman')
##men = names.find_tagged('man')
#people = names.find_tagged('person')

# hmm, should I make these singletons instead? otherwise, I could have just created one per node...
#generators = { lang: get_generator(lang) for lang in data.LANGUAGES }

#def hello():
#template = RAW_CLAUSE_TEMPLATES[1]

# where will this logic live??
# actually, i think it should commute - user CAN specify certain constraints, then object specifies the rest
    # I suppose this is important for transformed Clauses, for which you specify "empty subject" or something
    # BUT, don't you have to create a public API with which you reach down into the tree?
clause = nodes.node_factory('Clause')
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



clause.lexicalize_all()


#def generate_all(self):

# okay, i think this is the best tradeoff: Node knows its internal data structure (tree), while Generator knows how to generate
  # looping through languages? no, can just do all languages in parallel

generators = generator.generators
assert(set(generator.generators.keys()) == set(LANGUAGES))

# TODO: wrap this in a giant loop that takes into account all candidate madlib choices
# generate a single sentence (a single choice of madlibs)
while not all(clause.has_generated_text(lang) for lang in LANGUAGES):
    # reset the generators' counters for a pass through the whole tree
    for g in generators.values():
        g.reset()

    clause.generate_all(generators)
    if not all(clause.has_generated_text(lang) or generators[lang].num_generated() > 0 for lang in LANGUAGES):
        raise Exception('full pass through tree did not generate anything - cyclic dependencies?')
        
        
    
    # after the whole pass, 
        # if root node has been generated for all langs, just spit out the result
        # else not all the symbols have been generated, check to see how many generations were made this pass.
            # if something WAS generated, make another pass
            # else FAILURE - cyclic dependency? could output placeholders like V(S) instead of the real words


with open('output.txt', 'w', encoding='utf8') as output:
    for lang in LANGUAGES:
        output.write(clause.generated_text(lang) + '\n')


    
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