'''
Monolingual generators that finally convert data to sentences
'''
from utility import LANGUAGES


import nodes 



class Generator:
    def __init__(self):
        self.__counter = None # int
        
    def generate(self, node):
        assert(isinstance(node, nodes.Node))
        
        # TODO: multiple entries in a node - store tuple of (node, count). do this here once, for all node types
        assert(node.num_datasets(self.LANG) == 1)
        
        node_type = node.type()
        if node_type == 'verb':
            self._generate_verb(node)
        elif node_type == 'name':
            self._generate_name(node)
        else:
            raise Exception('Unimplemented node type ' + node_type)
        
    def reset(self):
        self.__counter = 0 # for re-parsing a tree

    
    
    
class EnGenerator(Generator):
    LANG = 'en'

    def _generate_name(self, node):
        pass
        
        
        
    def _generate_verb(self, node):
        pass
        
    # UGH, i'm not quite sure the current flow of control handles MULTIPLE names gracefully, which was the whole POINT of this
      # and then there's the issue of dependencies to worry about (multiple passes through the tree, just for ONE name tuple choice)
      
    # well, a tree is PROBABLY the correct data structure for building sentences up
    # but at the same time, a linear data structure is probably better for 
        # but you CAN'T convert to a linear data structure until the last minute, right?
        # the generator has to wait until it knows EXACTLY what the words are before ordering them
        
    # another idea: run through the tree and find all the decision points
        # then somehow impose them on the tree, one at a time, and loop through them
            # but the tree was BUILT with candidate lists baked right in...
        # plus it would be nice if this whole scheme were thread-safe...
            # NOT currently thread-safe! writing "generated word" to the tree.
        
        # but in any case, just make a first pass to build a list of tuples [(Node, # choices)] in the Generator
            # (or even, in the first pass, always pick the first choice)
            # then for subsequent passes, specify 
        
            
    
class ZhGenerator(Generator):
    LANG = 'zh'    
    def _generate_name(self, node):
        pass
    def _generate_verb(self, node):
        pass
    
    
def generator_factory(lang):
    '''Generates a SINGLETON generator that lives in this module'''
    assert(lang in LANGUAGES)
    if lang == 'en':
        return EnGenerator()
    elif lang == 'zh':
        return ZhGenerator()
    else:
        raise Exception('Unimplemented generator for language:' + lang)




# module-level singletons
generators = { lang: generator_factory(lang) for lang in LANGUAGES }
    
    
if __name__ == '__main__':
    print(EnGenerator().LANG)
    nodes.Node()