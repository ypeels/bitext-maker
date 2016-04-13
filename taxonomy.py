'''
Invert (hash) taxonomy tree into easily-queried format.
Tree needs to be traversed only once, but with increased storage costs
'''
import collections

import utility
import yaml_reader

class Taxonomy:
    '''
    Input: YAML nested mapping of the form { animal: { mammal: cat } }
    Output: Queryable object such that query(cat) = [animal, mammal]
    '''
    def __init__(self, filename):
        self.__data = collections.defaultdict(set)
        tree = yaml_reader.read_file(filename)
        self.__index_tree(tree, set())
        
    # not thread safe - writes to self.__data - but you wouldn't want to multithread this...
    def __index_tree(self, tree, parents):        
        for key, subtree in tree.items():
            genealogy = parents.union({key})
            self.__data[key].update(genealogy)
            if subtree:
                self.__index_tree(subtree, genealogy)
        
    def isa(self, item, ancestor):
        '''Is <ancestor> a (non-strict) "hypernym" of <item>?'''
        return ancestor in self.__data[item]
        
    #def categories(self, item):
        
        
        
        
        
        
        
        
# really belongs in its own file, where it absolutely would not gunk up production files...
    # plus, pass/fail summary is much harder to read when run on its own
def test():
    from utility import DATA_DIR
    import unittest
    
    class TestCase(unittest.TestCase):
        '''some quickie unit testing'''
        def test_isa(self):
            t = Taxonomy(DATA_DIR + 'taxonomy.yml')
            self.assertTrue(t.isa('man', 'animal'))
            self.assertTrue(t.isa('man', 'man'))
            self.assertFalse(t.isa('man', 'woman'))
            
      
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCase)
    unittest.TextTestRunner().run(suite)
    

        

if __name__ == '__main__':
    test()

