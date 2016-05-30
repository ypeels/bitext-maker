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
        #tree = yaml_reader.read_file(filename)
        #self.__index_tree(tree, set())
        
        tree_list = yaml_reader.read_file(filename)
        for tree in tree_list:
            self.__index_tree(tree, set())
        
    # not thread safe - writes to self.__data - but you wouldn't want to multithread this...
    def __index_tree(self, tree, parents):        
        for key, subtree in tree.items():
            genealogy = parents.union({key})
            
            # data['cat'] = { cat, mammal, animal, ... }
            self.__data[key].update(genealogy)
            
            if subtree:
                self.__index_tree(subtree, genealogy)
        
    def isa(self, item, ancestor):
        '''Is <ancestor> a (non-strict) "hypernym" of <item>?'''
        #return ancestor in self.__data[item]
        
        # allows items to occur in multiple trees - the ancestor of my ancestor is also my ancestor
        # - slower at runtime than trying to figure this all out at load time, but no multi-pass antics
        #genealogy = self.__data[item]
        #return any(ancestor in self.__data[x] for x in genealogy)
        return ancestor in self._ancestors(item)
        
    def canbe(self, item1, item2):
        return (self.isa(item1, item2) or # clearly a cat can be an animal
                self.isa(item2, item1) or # but can an animal be a cat? current logic: yes, because it already is.
                self._common_ancestors(item1, item2) == set())# corner case where they are in totally different trees - for adding a new tag
        
    def _ancestors(self, item):
        genealogy = self.__data[item]
        assert(genealogy)
        #ancestor_list = 

        #print('taxonomy.ancestors', genealogy, item)
        return set.union(*[self.__data[x] for x in genealogy])
        
    def _common_ancestors(self, item1, item2):
        ancestors = [self._ancestors(i) for i in (item1, item2)]
        
        return set.intersection(*ancestors) #self.__data[item1], self.__data[item2])
        
    #def categories(self, item):
        
        
        
        
        
        
        
        
# really belongs in its own file, where it absolutely would not gunk up production files...
    # plus, pass/fail summary is much harder to read when run on its own
def test():
    from utility import DATA_DIR
    import unittest
    
    class TestCase(unittest.TestCase):
        '''some quickie unit testing'''
        #def __init__(self):
        #    unittest.TestCase.__init__(self) # needs another argument
            
        __t = Taxonomy(DATA_DIR + 'taxonomy.yml')
        def test_isa(self):
            #t = Taxonomy(DATA_DIR + 'taxonomy.yml')
            t = self.__t
            self.assertTrue(t.isa('man', 'animal'))
            self.assertTrue(t.isa('man', 'man'))
            self.assertFalse(t.isa('man', 'woman'))
            self.assertTrue(t.isa('man', 'animate'))
            self.assertTrue(t.isa('man', 'physical.object'))
            self.assertTrue(t.isa('physical.object', 'object'))
            self.assertTrue(t.isa('man', 'object'))
            
        def test__common_ancestors(self):
            self.assertTrue('physical' in self.__t._common_ancestors('organ', 'animal'))
            
        def test_canbe(self):
            # the tree seems REALLY brittle... make sure to rerun this test suite every time it's changed...
            self.assertTrue(self.__t.canbe('animal', 'man'))
            self.assertTrue(self.__t.canbe('man', 'animal'))
            self.assertFalse(self.__t.canbe('man', 'nonhuman'))
            self.assertTrue(self.__t.canbe('man', 'unused'))
            self.assertTrue(self.__t.canbe('organ', 'inanimate'))
            self.assertFalse(self.__t.canbe('inanimate', 'person'))
            self.assertFalse(self.__t.canbe('person', 'inanimate'))
            self.assertTrue(self.__t.canbe('object', 'organ'))
            self.assertFalse(self.__t.canbe('event', 'physical'))
            self.assertFalse(self.__t.canbe('organ', 'abstract'))
            
            
      
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCase)
    unittest.TextTestRunner().run(suite)
    

        

if __name__ == '__main__':
    test()

