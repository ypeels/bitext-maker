'''
Monolingual generators that finally convert data to sentences
'''
from utility import LANGUAGES

import data
import nodes 


class Analyzer:
    '''
    Analyzes the tree and makes nonlocal decisions
    - select_samples(): makes a concrete selection at nodes with multiple samples [Alice, Bob]
    '''
    def __init__(self):
        self.__num_samples_per_node = None # list
        
    def analyze(self, node):
        '''
        Given a tree node as input, stores that node's max # samples if it's greater than 1
        - this information is used by the external loop, which varies the lexical choices globally.
        '''
        #print('Generator.analyze', node.type())
        #if isinstance(node, nodes.LexicalNode):
        #    print('\tnum_samples:',  node.num_samples())
        
        if isinstance(node, nodes.LexicalNode) and node.num_samples() > 1:
            self.__num_samples_per_node.append(
                #(node, node.num_samples()))
                {'node': node, 'max': node.num_samples()})
                
    def num_samples(self):
        return [d['max'] for d in self.__num_samples_per_node]
        
    def select_samples(self, selections):
        assert(len(selections) is len(self.__num_samples_per_node))
        for selection, d in zip(selections, self.__num_samples_per_node):
            assert(0 <= selection < d['max'])
            d['node'].select_sample(selection)
            
    def reset_num_samples(self):
        self.__num_samples_per_node = []
        

class Generator:
    def __init__(self):
        self.__counter = None # int
        # would ensure same condition on startup as on manual reset
        # but omitting it forces the caller to remember to reset before use...
        #self.reset_generated_counter() 
        
        self._det_form_bank = data.DET_FORMS.get(self.LANG)
        self._noun_form_bank = data.NOUN_FORMS.get(self.LANG)
        self._verb_form_bank = data.VERB_FORMS.get(self.LANG)
        
        
    def generate(self, node):
        if isinstance(node, nodes.LexicalNode):
            self._generate_lexical(node)
        elif isinstance(node, nodes.TemplatedNode):
            self._generate_templated(node)
        else:
            raise Exception('Unsupported node type: ' + type(node))
            
    def num_generated(self):
        return self.__counter
            
    def reset_generated_counter(self):
        self.__counter = 0 # for multiple passes through the tree (generating dependencies)
        

        
        
    def _generate_lexical(self, node):
        # TODO: multiple entries in a node - store tuple of (node, count). do this here once, for all node types
            # - permit multiple names for now and just take the first one as a default
        #print('generator _generate_lexical', node)
                
        
        #raise Exception('here is where I COULD select the sample from the LexicalNode ')
            # actually, shouldn't the samples have been selected elsewhere in a separate step?
                # no, it MUST be selected elsewhere, to make sure the translation is consistent
                # you could make a SECONDARY selection up until here, within a nameset/nounset, etc.
            # yeah, this is just the latest possible point where I could do that
            # pretty hackish/ad hoc, but i think it should work...
        
        
        node_type = node.type()
        if node_type == 'determiner':
            self._generate_determiner(node)
        elif node_type == 'name':        
            # for multiple names (Alice, 爱丽丝): absent any guidance, should just pick the first (default) name?
                # ugh, I don't want to think about this right now... let's just "solve" this in data
            #assert(node.num_datasets(self.LANG) == 1)
            #self._generate_name(node) # neither language's names have dependencies right now
            assert(node.number() == 'singular') # TODO: plural names, like Greeks? that would affect English subject-verb agreement
            name = node.name(self.LANG)
            self._generate_node_text(node, name)   
        elif node_type == 'noun':
            self._generate_noun(node) # punt to subclass            
        elif node_type == 'verb':
            self._generate_verb(node)
        else:
            raise Exception('Unimplemented node type ' + node_type)
            
    def _generate_node_text(self, node, text):
        node.set_generated_text(self.LANG, text)
        self.__counter += 1 # for multipass purposes

    def _generate_templated(self, node):
        lang = self.LANG
        generated_symbols = node.generated_symbols(lang)
        if len(generated_symbols) == node.num_symbols():
            
            # TODO: wrap symbols with delimiters like <S>, to allow symbol-looking words/names like "L"?
                # adding modifiers MAY introduce collisions
                # another concern is how transformations would affect this
            
            
            template_text = node.get_template_text(lang)
            template = template_text.split()
        
            # TODO!!! handle modifiers here, right? need to insert them INTO the template... but in a language-dependent way...
            
            # populate the template - get(key, default value)
            result = [generated_symbols.get(token, token) for token in template ]
            
            node.set_generated_text(lang, ' '.join(result))
        
    def _get_det_base(self, node):
        return node.determiner(self.LANG)
        
    def _get_noun_base(self, node):
        return node.noun(self.LANG)

            
    def _get_verb_base(self, node):
        #assert(node.num_datasets(self.LANG) == 1)
        #verbset = node.sample_dataset() #get_dataset_by_index(0)#get_verbset_by_index(0)
        #return verbset.verb(self.LANG)
        return node.verb(self.LANG)
                    
        
    
    
    
class EnGenerator(Generator):
    LANG = 'en'
        
    def _generate_determiner(self, node):
        #assert(node.type() == 'determiner') # let's not do this - you'd have to do this for EVERY language...
        det_base = self._get_det_base(node)
        
        forms = self._det_form_bank.get(det_base) or {}
        
        targets = node.targets()
        assert(len(targets) is 1) # TODO: multiple targets - which would go by NEAREST? "this cat and dogs"? hmm
        
        #import pdb; pdb.set_trace()
        det = forms.get(targets[0].number(), det_base)
        
        
        # singular or plural form of determiner?
        self._generate_node_text(node, det)
        
    def _generate_noun(self, node):
        noun_base = self._get_noun_base(node)  
        if node.number() == 'singular':
            noun = noun_base
        else:
            noun = self.__pluralize_noun(noun_base)
        modified_noun = self.__modify_noun(node, noun)
        self._generate_node_text(node, modified_noun)
      
        
        
    def _generate_verb(self, node):
        # should depend on subject
        # also depends on tense... presumed present for now
        dependencies = node.get_dependencies(lang=self.LANG)
        if not all(dep.has_generated_text(self.LANG) for dep in dependencies):
            return
            
        assert(len(dependencies) <= 1) # just subject-verb for now
        subject_node = dependencies[0]
        
        if node.get_tense() == 'present':
            self.__generate_verb_present(node, subject_node)
        else:
            raise Exception('Unsupported tense ' + node.get_tense())

            
    def __generate_verb_present(self, verb_node, subject_node):
        verb_base = self._get_verb_base(verb_node)
        verb_forms = self._verb_form_bank.get(verb_base)
        
        # person and number
        # need to choose between the forms of the verb's word
        if verb_forms.is_regular():
            
            # if subject third person and regular, then use VBZ
            if subject_node.number() == 'singular' and subject_node.person() == 3:
                verb = verb_forms.get_form('VBZ')
            else:
                verb = verb_forms.get_form('VBP')
                
            self._generate_node_text(verb_node, verb)
            
        else:
            raise Exception('Unimplemented: irregular en verbs')
            
            
    def __modify_noun(self, node, noun):
        '''Precondition: noun is passed in fully inflected (e.g., pluralized)'''        
        # this subroutine would have to play the role of a template, setting the order of modifiers and their targets
            # this is because templates as currently implemented cannot handle variable numbers of symbols
            # also, there are semantics-related ordering issues..
            
            # it looks like this could get VERY complicated...

        words = []
        
        # ADJP's... should I reach deeper down instead, to get more complete info from the real modifier, instead of these placeholder?
        modifiers = list(node.modifiers()) # make a copy (trashed immediately)

        # determiner goes at the very front
        dets = [m for m in modifiers if m.template_id() == 'determiner']
        modifiers = [m for m in modifiers if m not in dets]
        if dets: 
            assert(len(dets) is 1) # forget about PDTs ("all the gold") for now
            words.append(dets[0].generated_text(self.LANG))
        else:
            if node.number() == 'singular':
                if 'object' in node._get_option('tags'):
                    words.append('the')
                else:
                    raise Exception('TODO: unmodified singular noun that is not an #object')

        
        if len(modifiers) > 0:
            raise Exception('TODO: handle other modifiers')
                    
        words.append(noun)
                    
        return ' '.join(words)
                    
        
        
        
    def __pluralize_noun(self, noun_base):
        noun_forms = self._noun_form_bank.get(noun_base)
        if noun_forms and noun_forms.get('NNS'):
            return noun_forms.get('NNS')
        else:
            return noun_base + 's'
            
            
    # name modification is actually kind of annoying
        # Envious, Alice killed Bob.
            # this ordering is only available to the SUBJECT...
        # Alice, envious, killed Bob.
            
        
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
    
    def _generate_determiner(self, node):
        targets = node.targets()
        assert(len(targets) is 1)
        assert(targets[0].type() == 'noun')
                
        words = self._get_det_base(node) # string instead of list, to enable segmentation antics
                
        target = targets[0]
        assert('object' in target._get_option('tags')) # so that "DT 些" has a plural meaning (*这 些 水). so horribly brittle...        
        
        if target.number() == 'singular':
            noun = self._get_noun_base(target)
            noun_form = self._noun_form_bank.get(noun)
            measure_word = noun_form.get('M')
            assert(type(measure_word) is str) # TODO: allow multiple measure words, like using 个 instead of 件 from time to time
            words += ' ' + measure_word
            
        else:
            words += '些'
        
        self._generate_node_text(node, words)
        
        
        # WARNING: this is using data from noun forms (nouns_zh.yml) as METADATA (not noun data per se)... but that's okay, right?
        
        
        # *每 个 这 个 东西
    
    def _generate_noun(self, node):
        noun = self._get_noun_base(node) # no inflections
        self._generate_node_text(node, noun)
        
        # based on EnGenerator.__modify_noun() - hmmmm that's not very DRY...
        words = []
        modifiers = list(node.modifiers()) 
        
        dets = [m for m in modifiers if m.template_id() == 'determiner']
        modifiers = [m for m in modifiers if m not in dets]
        
        if dets:
            assert(len(dets) is 1) 
            words.append(dets[0].generated_text(self.LANG))
            
        else:
            if node.number() != 'singular':
                assert('object' in node._get_option('tags')) # for now, assume countable? 一些时间 != times...
                assert(not node.has_modifiers()) # would need to check modifiers for "pluralizers" like CD
                words.append('一些')

        words.append(noun)
        
        self._generate_node_text(node, ' '.join(words))

        
        
    # ah, conjugation-free Chinese...
    def _generate_verb(self, node):
        verb = self._get_verb_base(node)
        self._generate_node_text(node, verb)
        
    
        
    
    
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
analyzer = Analyzer()
generators = { lang: generator_factory(lang) for lang in LANGUAGES }
    
    
if __name__ == '__main__':
    print(EnGenerator().LANG)
    nodes.Node()