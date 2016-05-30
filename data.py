'''
Data module - global read-only data, and their related interface classes

- if you want to test some code quickly, maybe it would just be easier to change DATA_DIR to a folder with small test data
'''
import collections
import copy # for deepcopy (modifying templates...)
import os
import random

from taxonomy import Taxonomy
from utility import DATA_DIR, LANGUAGES, pick_random # kept in separate file for fast unit testing
from yaml_reader import read_file

UNIMPLEMENTED_EXCEPTION = Exception('Needs to be implemented in derived class')

def wrap_as_list(item):
    if type(item) is list:
        return item
    else:
        return [item]

# TODO: put Bank classes into their own file(s) once the interface is stable enough
class Bank:
    '''Base class that reads a single YAML file'''
    def __init__(self, filename):
        self.__data = read_file(filename) # TODO: self.__data, and access in derived classes via self._Bank__data? (discourage interactive access)

    def _data(self):
        '''expose to derived classes'''
        return self.__data
        
        
class WordSetBank(Bank):
    '''Root data structure is a list'''
    def __init__(self, filename):
        '''Removes empty/dummy data entries'''
        Bank.__init__(self, filename)
        __data = self._data()
        
        # discard dummy entries
        # TODO: save them elsewhere, if I ever wanted to make them available programmatically - otherwise, they're just glorified comments...
        for i in range(len(__data)-1, -1, -1):
            if self._is_dummy(__data[i]):
                __data.pop(i)

        self.__all_tags = None # set
                
    def all_tags(self):
        if self.__all_tags is None: # lazy initialization to avoid choking on unimplemented _all_datasets()
            self.__all_tags = set.union(*[set(item.tags()) for item in self._all_datasets() if item.tags()])
        return self.__all_tags.copy() # gets trashed all OVER the place downstream. this was an insidious bug.
                
    #def _all_datasets(self): # duck typing will raise a more informative exception (tells you WHICH subclass needs implementing)
    #    raise UNIMPLEMENTED_EXCEPTION


class AdjectiveSetBank(WordSetBank):

    # adjsets effectively have two types of tags
    # the standard tag types, which you are eliminated via find_tagged (all_tags() would return "big", but find_tagged('color') would not)
    # adjective sets with tags like "target.inanimate" can ONLY be found through find_tagged('target.inanimate')
        # in other words, there are certain adjectives that you can only opt INTO, not just opt out of
    def all_unrestricted_adjsets(self):
        #result = [AdjectiveSet(item) for item in self._data()]
        result = [adjset for adjset in self.__all_adjsets() if not any(t.startswith('target.') for t in adjset.tags())]
        assert(len(result) > 0)
        return result
        
    #def find_tagged(self, target_tags):
    #    #raise Exception('TODO: unimplemented stub') # n.b. the "tags" key is currently optional in adjsets.yml
    #    return [adjset for adjset in self.__all_adjsets() #
    #            if all(tt in adjset.tags() for tt in target_tags)]# or not adjset.tags()] 
       
    def __all_adjsets(self):
        return [AdjectiveSet(item) for item in self._data()]
      
    # I don't think I should use this - it's way too confusing
    def find_tagged_with_any(self, target_tags):
        '''
        Unlike NounSetBank and VerbSetBank, this returns the "union" of all tags instead of the intersection.
        This is because adjectives are generally specified w.r.t. an existing target, which can take many possible modifier types (color, size, etc.)
        '''
        return [adjset for adjset in self.__all_adjsets() #AdjectiveSet(item) for item in self._data() 
                if any(tt in adjset.tags() for tt in target_tags) or not adjset.tags()]        
        
    # overrides (concrete implementations)
    def _all_datasets(self):
        return self.__all_adjsets()
        
    def _is_dummy(self, datum):
        return all(adj == None for adj in datum['adjset'].values())
        
class AdverbSetBank(WordSetBank):
    def all_advsets(self):
        result = [AdverbSet(item) for item in self._data()] # breaks symmetry with other WordSetBanks! 
        assert(len(result) > 0)
        return result

    def _is_dummy(self, datum):
        return all(adj == None for adj in datum['advset'].values())        
        
class DeterminerSetBank(WordSetBank):
    def all_detsets(self):
        result = self.find_tagged([]) #[DeterminerSet(item) for item in self._data()]
        assert(len(result) > 0)
        return result
        
    def find_tagged(self, target_tags):
        assert(len(target_tags) <= 1) # determiners are currently all single-tag... quantifier/demonstrative/etc. ("a" may need 2+?)
        return [DeterminerSet(item) for item in self._data() if all(tt in item['tags'] for tt in target_tags)]        
        
    # overrides (concrete implementations)
    def _all_datasets(self):
        return self.all_detsets()
    
    def _is_dummy(self, datum):
        return all(adj == None for adj in datum['detset'].values())  
        
class NameSetBank(WordSetBank):    
    def __init__(self, filename):
        WordSetBank.__init__(self, filename)
        
        __data = self._data()
        
        # normalize single-item entries to be lists
        for item in __data:
            if type(item['tags']) is str:
                item['tags'] = [item['tags']]
        
    #def _makeN(self, item):
    #    raise Exception('Unimplemented in abstract base class' + __class__)
        
    def all_namesets(self):
        return [NameSet(item) for item in self._data()]
        
    def find_tagged(self, target_tags):
        # TODO: handle single-tag case where it's not even a list?
        # TODO: share code with NounSetBank? is it worth sacrificing clarity just to DRY out 2 lines?
        return [NameSet(item) for item in self._data() 
            for tag in item['tags'] if all(TAXONOMY.isa(tag, tt) for tt in target_tags)]
            
    def _is_dummy(self, datum):
        return all(adj == None for adj in datum['nameset'].values()) 
            
class NounSetBank(WordSetBank):
    def all_nounsets(self):
        result = self.find_tagged([]) #[NounSet(item) for item in self._data()]
        assert(len(result) > 0)
        return result
        
    def find_tagged(self, target_tags):
        '''
        Returns all noun synsets satisfying ALL target tags.
        '''
        return [NounSet(item) for item in self._data()
            #for tag in item['tags'] if all(TAXONOMY.isa(tag, tt) for tt in target_tags)] # listcomps are really prone to subtle logic errors
            if all( any(TAXONOMY.isa(tag, tt) for tag in (item.get('tags') or [])) for tt in target_tags ) or not item.get('tags')]
            
    # overrides (concrete implementations)
    def _all_datasets(self):
        return self.all_nounsets()
        
    def _is_dummy(self, datum):
        return all(adj == None for adj in datum['nounset'].values())  
        
class PronounSetBank(WordSetBank):
    # useful when just inserting a random dangling pronoun (sentence level)
    #def all_nounsets(self):
    #    result = [NounSet(item['nounset']) for item in self._data()]
    #    assert(len(result) > 0)
    #    return result
    def all_pronsets(self): # PronounSet wraps the whole list item, not just the 'pronounset' subkey
        return self.find_tagged([]) #[PronounSet(item) for item in self._data()]
        # TODO: backport this intraclass DRYing to other WordSetBanks
    
    # TODO: queryable function that just takes metadata and returns the right pronset - for referential pronouns
    
    def find_by_person(self, person):
        return [PronounSet(item) for item in self._data() if item['person'] is person]
    
    def find_tagged(self, target_tags):
        return [PronounSet(item) for item in self._data() 
            for tag in item.get('tags', []) if all(TAXONOMY.isa(tag, tt) for tt in target_tags)]
            
    def find_tagged_third_person(self, target_tag):
        return [PronounSet(item) for item in self._data()  
            for tag in item['tags'] if TAXONOMY.isa(tag, target_tag) and item['person'] is 3]
    
            
    def _is_dummy(self, datum):
        return all(adj == None for adj in datum['pronounset'].values()) 

            
class TemplateBank(Bank):
    def all_template_ids(self):
        return tuple(self._data().keys())

    def get_template_by_id(self, id, readonly=True):
        return Template(self._data()[id], readonly)
       
class TransformationBank(Bank):
    def get_transformation_by_id(self, id):
        return Transformation(self._data()[id])



class WordFormBank(Bank):
    def get(self, word):
        wf = self._data().get(word)
        if wf:
            return self.DATA_FACTORY(wf)
        else:
            return None
        
# TODO: need these to implement comparatives/superlatives for en
class AdjectiveFormBank(WordFormBank):
    def __init__(self, filename):
        WordFormBank.__init__(self, filename)
        
        for key in list(self._data()):
            if key == '__dummy__':
                self._data().pop(key)
    
class AdverbFormBank(WordFormBank):
    pass
    

        
class DeterminerFormBank(WordFormBank):
    def __init__(self, filename):
        WordFormBank.__init__(self, filename)
        self.DATA_FACTORY = DeterminerForms
    #def get(self, word):
    #    df = self._data().get(word)
    #    if df:
    #        return DeterminerForms(df)
    #    else:
    #        return None
        
class NounFormBank(WordFormBank):
    def __init__(self, filename):
        WordFormBank.__init__(self, filename)
        self.DATA_FACTORY = NounForms
    #def get(self, word):
    #    nf = self._data().get(word)
    #    if nf:
    #        return NounForms(nf)
    #    else:
    #        return None
            
class PronounFormBank(WordFormBank):
    # need to differentiate between key with empty entry and a missing key
    # TODO: backport this into WordFormBank? does it work with other subclasses?
    def get(self, word):
        if word in self._data():
            return PronounForms(self._data().get(word))
        else:
            return None
        
class VerbFormBank(WordFormBank):
    def __init__(self, filename):
        WordFormBank.__init__(self, filename)
        self.DATA_FACTORY = VerbForms
    

# not currently inheriting Bank, since this is (potentially) multi-file...
class VerbSetBank:
    def __init__(self, path):
        self.__data = {}        
        if os.path.isdir(path):  
            for basename in os.listdir(path):
                if basename.endswith('.yml'):
                    self.__add_file(path + basename)  
        elif os.path.isfile(path):
            self.__add_file(path)
        else:
            raise Exception('A path that is neither dir nor file - how zen...', path)
            
        self.__all_templates = { datum['template'] for datum in self.__data.values() }

    def all_templates(self):
        '''Returns all available templates - mainly for testing purposes (tiny verbset list)'''
        return self.__all_templates.copy()
            
    def categories(self):
        return list(self.__data.keys())
       
    def get_category(self, category):
        return VerbCategory(self.__data[category])
        
    def get_categories_by_template(self, template_id):
        return sorted([cat for cat in self.categories() if self.__data[cat]['template'] == template_id])
    
    def __add_file(self, filename):
        new_data = read_file(filename)
        
        # error-checking (TODO: dedicated error-checking test file)
        assert(type(new_data) is dict)
        assert(not any(key in self.__data.keys() for key in new_data.keys()))        
        self.__data.update(new_data)
            
            

            
# chunks of data files that nevertheless should be isolated into objects
# this way, if/when the data format changes, ONLY these classes would need to be changed.
# this is a LITTLE different from typical object-oriented programming, since the data files impose external constraints

# as thin as possible to begin with - just the raw data + whatever accessors you need
# then add processing, etc... wait a second, isn't that just standard object-oriented programming??
    # well, this is still important, since it separates Data-level logic from Linguistics-level logic
class Template:
    '''
    Clause and NP syntax
    most of the logic has ended up being only for clauses though...
    '''
    def __init__(self, data, readonly=True):
        # "declarations"
        self.__data = {}
        self.__symbols = {}
        self.__writable = bool(not readonly)
        
        self.__forms_per_symbol = collections.defaultdict(dict) # { V: { en: VBG } }
        self.__lang_indep_deps_per_symbol = collections.defaultdict(list)
        self.__per_lang_deps_per_symbol = collections.defaultdict(dict)
        self.__syntax_tags_per_symbol = collections.defaultdict(dict)  # { en: { S: subjective } }      
                
        # comprehensive list of data structures to be reparsed on template change
        if self._writable():
            self.__parsed = [self.__forms_per_symbol, 
                             self.__lang_indep_deps_per_symbol,
                             self.__per_lang_deps_per_symbol, 
                             self.__syntax_tags_per_symbol]

        
        #self.__symbol_metadata = collections.defaultdict(collections.defaultdict(dict))
        # e.g., symbol_metadata[symbol]['tags']
        
        if readonly:
            self.__data = data        
        else:
            self.__data = copy.deepcopy(data)
            
        self.__parse()
        
    def __str__(self):
        return 'Template({})'.format(self.__data)
        
    def categories(self):
        '''This is primarily for Clauses (verb category)'''
        categories = self.__data.get('categories')
        if categories:
            return wrap_as_list(categories)
        else:
            return []
        
    def description_for_symbol(self, symbol):
        return self.__data['symbols'][symbol].get('description') or []

    def form_for_symbol(self, symbol, lang):
        forms_per_lang = self.__forms_per_symbol.get(symbol, {}) 
        return forms_per_lang.get(lang) 
        
    def ghosts(self):    
        result = {}
        for key in self.ghost_keys():
            assert(not result.get(key))
            if key in self.__linked_keys():
                result[key] = 'linked'
            elif key in self.__target_keys():
                result[key] = 'target'
            else:
                raise Exception('Unknown ghost key ' + key)
        return result.items()
        
    def ghost_keys(self):
        return self.__linked_keys() + self.__target_keys()
        
    def head_symbols(self):
        return [s for s in self.symbols() if 'head' in self.description_for_symbol(s)]
      
    def lang_indep_deps_for_symbol(self, symbol):
        return self.__lang_indep_deps_per_symbol[symbol]
        
    def options_for_symbol(self, symbol):
        #return self.__data['symbols'][symbol]['options']
        symbol_data = self.__data['symbols'].get(symbol, {})
        return symbol_data.get('options', {})
        
    
    def per_lang_deps_for_symbol(self, symbol):
        return self.__per_lang_deps_per_symbol[symbol].items()
    
    def prewords(self, lang):
        #return self.__data['langs'][lang].get('prewords', {})
        return self.__pre_or_post_words(lang, 'prewords')
    def postwords(self, lang):
        #return self.__data['langs'][lang].get('postwords', {})
        return self.__pre_or_post_words(lang, 'postwords')        
    def __pre_or_post_words(self, lang, kind):
        assert(kind == 'prewords' or kind == 'postwords')
        
        raw_data = self.__data['langs'][lang].get(kind, {})
        assert(type(raw_data) is dict)
        
        result = {}
        for symbol, value in raw_data.items():
            if type(value) is str:
                result[symbol] = value
            elif type(value) is list:
                assert(all(type(subvalue) is str for subvalue in value))
                result[symbol] = pick_random(value)
            else:
                assert(type(value) is dict) # YAML
                raise Exception('preword/postword data should be list or str')
                
        return result
                
        
    
    def symbols(self):
        return self.__symbols.keys()
        
    def syntax_tags_for_symbol(self, symbol):
        '''
        Returns { 'en': [<en tags>], ... }
        This is a reconstituted data structure (the innermost lists might be shallow copies)
        '''
        return self.__syntax_tags_per_symbol[symbol]
        
    def target_options_for_key(self, key):
        return self.__data['targets'][key]
        
    def template_text(self, lang):
        '''Public version always includes trailing punctuation'''
        return self._template_text(lang, with_punc=True)
        
    def type_for_symbol(self, symbol):
        return self.__data['symbols'][symbol]['type']

        
    def _template_text(self, lang, with_punc=False):
        '''Internal version typically doesn't include trailing punctuation'''
        text = self.__data['langs'][lang]['template']        
        if with_punc:
            punctuation = self.__punctuation(lang)
            if punctuation:
                #import pdb; pdb.set_trace()
                text += ' ' + punctuation
        return text
        
    def _writable(self):
        return self.__writable
       
    def __parse(self):
        # parse symbols
        assert(type(self.__data['symbols']) == dict)
        self.__symbols = self.__data['symbols']
        
        # clear old entries and re-parse 
        if self._writable(): 
            for dest in self.__parsed:
                dest.clear()
        
        # parse tags for each symbol - a bit of non-trivial inversion, so do it here at load time, once-only
        # imperative style is just a bit more DRY and flexible for something like this...
        
        # language-specific tags
        for lang, metadata in self.__data['langs'].items():
            if lang in LANGUAGES:                
                for symbol, tags in metadata.get('tags', {}).items():
                    self.__syntax_tags_per_symbol[symbol][lang] = wrap_as_list(tags)
                    
                for symbol, deps in metadata.get('dependencies', {}).items():
                    deps_list = wrap_as_list(deps)
                    assert(all(d in self.symbols() for d in deps_list)) # ok again? ghost nodes get stripped from dependencies
                    self.__per_lang_deps_per_symbol[symbol][lang] = deps_list
                    
                for symbol, form in metadata.get('forms', {}).items():
                    assert(type(form) is str)
                    self.__forms_per_symbol[symbol][lang] = form
                    
        # also append language-independent data
        for symbol in self.symbols():
            syntax_tags = self.__data['symbols'][symbol].get('syntax tags')
            if syntax_tags:
                for lang in LANGUAGES:
                    old_tags = self.__syntax_tags_per_symbol[symbol].get(lang, [])
                    self.__syntax_tags_per_symbol[symbol][lang] = old_tags + wrap_as_list(syntax_tags)

            deps = self.__data['symbols'][symbol].get('dependencies')
            if deps:
                self.__lang_indep_deps_per_symbol[symbol] = wrap_as_list(deps)
            

    def __linked_keys(self):
        linked = self.__data.get('linked')
        if linked:
            return list(linked.keys())
        else:
            return []                    
           
    def __punctuation(self, lang):
        return self.__data['langs'][lang].get('punctuation')
    def __set_punctuation(self, lang, punctuation):
        self.__data['langs'][lang]['punctuation'] = punctuation
    
    def __target_keys(self):
        targets = self.__data.get('targets')
        if targets:
            return list(targets.keys())
        else:
            return []
           
           
           
    ### operations that modify the template ###
    def add_data(self, new_data):
        assert(self._writable())
        assert(type(new_data) is dict)
        self.__merge_dict(self.__data, new_data)
        self.__parse()
    
    #def add_target(self, target_data):
    #    assert(self._writable())
    #    assert(not self.__data.get('targets')) # assuming only single target for now, at least in a template... when would multiple occur?
    #    self.__data['targets'] = target_data # hey this would clobber older targets!
    #    self.__parse() 
    
    def perform_conversions(self, conversions):
        assert(self._writable())
        assert(type(conversions) is dict)
        
        for symbol, new_type in conversions.items():
            assert(type(symbol) is str)
            assert(type(new_type) is str)
            assert(symbol in self.symbols())
            
            popped_data = self.__pop_symbol(symbol)
            assert(len(popped_data) is 1 and list(popped_data.keys())[0] == symbol)
            
            if not self.__data.get(new_type):
                self.__data[new_type] = popped_data
            else:
                assert(not self.__data.get(new_type).get(symbol))
                self.__data[new_type].update(popped_data)
        
        self.__parse()
            
        
    def remove_trailing_punctuation(self):
        assert(self._writable())
        
        for lang in LANGUAGES:
            if self.__punctuation(lang):
                self.__set_punctuation(lang, None)
                
        self.__parse()
        assert(all(not self.__punctuation(lang) for lang in LANGUAGES))
        
    def _set_template_text(self, lang, text):
        assert(self._writable())
        self.__data['langs'][lang]['template'] = text # is there any way to DRY this out with template_text()?
        self.__parse()
        assert(self._template_text(lang) == text) # this is no longer true, since trailing punctuation is treated separately


    def __pop_symbol(self, symbol):
        '''
        Removes all traces of a symbol, even from dependencies.
        Return value: symbol signature (from "symbols" dict)
        '''
        assert(self._writable())
        if symbol not in self.symbols():
            raise Exception('Symbol {} not found in {}'.format(symbol, self.symbols()))
        
        # all be isolated in function calls, to facilitate modification if data structure changes (unlikely at this point)
        self.__remove_symbol_from_template_text(symbol)
        self.__remove_symbol_from_syntax_tags(symbol)
        self.__remove_symbol_from_dependencies(symbol)
        
        popped = { symbol: self.__data['symbols'].pop(symbol) }
        
        self.__parse()
        assert(not self.syntax_tags_for_symbol(symbol))
        assert(not self.per_lang_deps_for_symbol(symbol) and not self.lang_indep_deps_for_symbol(symbol))
        
        return popped        
        
    def __remove_symbol_from_template_text(self, symbol):
        assert(self._writable())
        assert(symbol in self.symbols())
        for lang in LANGUAGES:#, template_data in self.__data['langs']:
            template_text = self._template_text(lang)
            tokens = template_text.split()
            assert(tokens.count(symbol) is 1)
            tokens.remove(symbol)
            self._set_template_text(lang, ' '.join(tokens))
        # don't have to __parse() just yet, since this function is only meant to be called internally    
            
    def __remove_symbol_from_syntax_tags(self, symbol):
        assert(self._writable())
        assert(symbol in self.symbols())
        #assert(self.syntax_tags_for_symbol(symbol)) # also, can't just pop(), since the template itself needs to change
        
        # this looks disturbingly brittle...
        for lang in LANGUAGES:            
            lang_data = self.__data['langs'][lang]
            tags = lang_data.get('tags')
            if tags and tags.get(symbol):
                tags.pop(symbol)
        
        #assert(not self.syntax_tags_for_symbol(symbol)) saving this for later, since __parse() is not quite necessary here
        
    def __remove_symbol_from_dependencies(self, symbol):
        assert(self._writable())
        assert(symbol in self.symbols())

        self.__data['symbols']
        for other_symbol in self.symbols():
            other_deps = self.__data['symbols'][other_symbol].get('dependencies')
            if other_deps:
                while symbol in other_deps: # TODO: DRY this out with the language-dependent symbol removal code below? it's just 2 lines...
                    other_deps.remove(symbol)
        
        for lang in LANGUAGES:
            lang_data = self.__data['langs'][lang]
            deps_for_all_symbols = lang_data.get('dependencies')
            if deps_for_all_symbols:
                for other_symbol, other_deps in list(deps_for_all_symbols.items()):
                    other_deps = wrap_as_list(other_deps)
                    while symbol in other_deps:
                        other_deps.remove(symbol)
                    deps_for_all_symbols[other_symbol] = other_deps
            
   
    # i'm not totally sure descriptions are going to stay fixed
    # let's just go with symbols for now, for want of a better idea...
    
                
    def __merge_dict(self, destination, input):
        '''precondition: destination and input are both nested dicts, except for leaf nodes'''
        assert(self._writable())
        assert(type(destination) is dict and type(input) is dict)
        for key, value in input.items():
            # YAML: dicts, lists, and scalars.
            if key in destination.keys():
                if type(value) is dict:
                    assert(type(destination.get(key)) is dict)
                    self.__merge_dict(destination.get(key), value)   
                elif type(value) is list:
                    # append to existing list. make it a list if it's originally a scalar (allows for sloppy yaml coding)
                    if type(destination[key]) is list:
                        destination[key] += value
                    else:
                        destination[key] = [destination[key]] + value                    
                else: # must be a scalar - no need to deepcopy
                    assert(type(destination.get(key)) not in [list, dict])
                    destination[key] = value
                
            else: # safe to copy in - there's nothing to clobber
                destination[key] = copy.deepcopy(value) # deepcopy JUST in case...
    # assert(self._writable())


    



        
class Transformation:
    def __init__(self, data):
        self.__data = data
        
    def additions(self):
        return self.__data.get('additions') # don't need deepcopy, because you need to do a "deep merge" anyway to avoid destroying old Template
        
    def conversions(self):
        return self.__data.get('conversions', {})
        
    def input_type(self):
        return self.__data['input']

    def output_template_id(self):
        return self.__data.get('output template')
        
    def output_type(self):
        return self.__data['output']

    #def remove_trailing_punctuation(self):
    #    return 'remove trailing punctuation' in self.__data['options']
        
    #def targets(self):
    #    conversions = self.__data.get('conversions', {})
    #    return [symbol for symbol, new_type in conversions.items() if new_type == 'target']
    
    
    
     
   
# polylingual lexical "Sets" - e.g., { 'en': 'Alice', 'zh': ... }
class VerbCategory:
    '''Verb semantics - responsible for choosing a verb synset for generation'''
    def __init__(self, data):
        self.__data = data
        self.__randomly_picked_symbol_tags = {}
        self.__randomly_picked_symbol_transformations = {}
    
    def __str__(self):
        return str(self.__data)
        
    def additions(self):
        return self.__data.get('additions')
        
    def all_verbsets(self):
        return [VerbSet(item) for item in self.__data['verbsets']]
        
    def tags_for_symbol(self, symbol):
        tags = self.__data.get('tags') or {}
        symbol_tags = tags.get(symbol) # TODO: just change wrap_as_list to check for None... but that would affect a LOT of other code
        if symbol_tags:
            symbol_tags = wrap_as_list(symbol_tags)
        else:
            symbol_tags = []
        
        if all(type(tag) is str for tag in symbol_tags):
            result = symbol_tags
        else:
            # a workaround to choose one of multiple tagsets from data
            assert(symbol_tags) # all([]) == True, so an empty list should be in the other branch
            assert(all(type(tag) is list for tag in symbol_tags))
            
            # cache so that repeated queries are NOT inconsistent.
            # should be okay, since VERBSET_BANK re-instantiates for every query...
            if symbol not in self.__randomly_picked_symbol_tags:
                self.__randomly_picked_symbol_tags[symbol] = pick_random(symbol_tags).copy()
                
            result = self.__randomly_picked_symbol_tags[symbol]
        
        return result #tags.get(symbol)
        
    def tagged_symbols(self):
        tags = self.__data.get('tags') or {}
        return tags.keys()
        
    def template_id(self):
        return self.__data['template']

    # this whole function is analogous to tags_for_symbol. tempting to refactor, but data format is subject to change...
    def transformation_for_symbol(self, symbol):
        transforms = self.__data.get('transformations', {})
        symbol_transforms = transforms.get(symbol)
        if symbol_transforms:
            symbol_transforms = wrap_as_list(symbol_transforms)
        else:
            symbol_transforms = []
            
        if all(type(transform) is str for transform in symbol_transforms):
            result = symbol_transforms
        else:
            assert(symbol_transforms)
            assert(all(type(transform) is list for transform in symbol_transforms))
            
            if symbol not in self.__randomly_picked_symbol_transformations:
                self.__randomly_picked_symbol_transformations[symbol] = pick_random(symbol_transforms).copy()
                
            result = self.__randomly_picked_symbol_transformations[symbol]
        
        return result #transforms.get(symbol)

        
class WordForms:
    '''Language-specific morphological forms (e.g., nouns_en.yml)'''
    def __init__(self, data):
        self.__data = data or {}
        
    def __repr__(self): # meh, this is okay, right? it's pretty definitive (no other data)...
        return "{}({})".format(self.__class__, self.__data.__repr__())
        
    def _get(self, key, default=None):
        return self.__data.get(key, default)

        
class DeterminerForms(WordForms):
    def get(self, key, default=None):
        return self._get(key, default)
        
class NounForms(WordForms):
    def get(self, key, default=None):        
        try:
            result = self._get(key, default) # hmm, all this does is expose the base class's raw accessor...
        except AttributeError:
            assert(type(self._WordForms__data) is str)
            result = default # allow keys with scalars, like 人: ren2
        return result            
        
class PronounForms(WordForms):
    def get(self, key, default=None):
        return self._get(key, default)
        
class VerbForms(WordForms):       
    def get_form(self, form):        
        return self._get(form)
        
    def is_regular(self):
        return not bool(self._get('irregular'))


class WordSet:     
    '''Multilingual synsets (e.g., nounsets.yml)'''
    def __init__(self, data):
        self.__data = data
        self.__words = {}
        
    def __repr__(self): # TODO: get lists of NameSets to print info using __str__ instead of __repr__?
        return "WordSet({})".format(self.__data.__repr__())

    # currently unused and irrelevant - for a synset with multiple candidates, __get_word just picks one (count on outermost loop sampling many trees)
    #def num_words(self, lang):
    #    '''This function returns >1 if the WordSet for a language contains a LIST of candidates (e.g., { en: [man, person] ...}'''
    #    words = self._words(lang)
    #    if type(words) is str:
    #        return 1
    #    else:
    #        return len(words)
            
    def tags(self):
        # don't have to worry about multiple synsets here, since semantic tags apply to all words in the synset
        tags = self._data().get('tags')
        if tags:
            return wrap_as_list(tags)
        else:
            return [] # if you try to return wrap(data.get('tags', [])), you can wind up with [[]]        
            
    def word(self, lang):
        if lang not in self.__words:
            word_data = self._get_word_data(lang)
            if type(word_data) is str:
                self.__words[lang] = word_data
            elif type(word_data) is list: # if wordset has multiple entries [man, person, ...], just pick one at random for WordSet's lifetime
                assert(word_data)
                assert(all(type(item) is str for item in word_data))
                self.__words[lang] = pick_random(word_data)            
            else:
                assert(type(word_data) is dict) # YAML
                raise Exception('per-lang verb data should be string or list of strings')

        assert(type(self.__words[lang]) is str)
        return self.__words[lang]
        
    # ugh, expose to derived classes...
    def _data(self):
        return self.__data
        
class AdjectiveSet(WordSet):
    def _get_word_data(self, lang): # give subclasses something more transparently concrete to do
        return self._data()['adjset'][lang] or []    # TODO: handle langs for which data entry hasn't been done yet        

class AdverbSet(WordSet):
    def compatible_lexical_targets(self):
        return self._data()['targets']
        
    # TODO: refactor other WordSets to allow additional fields like this? actually, just rewriting this low-level primitive seemed to work?
    def _get_word_data(self, lang):
        return self._data()['advset'][lang] or []
        
class DeterminerSet(WordSet):
    def _get_word_data(self, lang):
        return self._data()['detset'][lang] or []
        
class NameSet(WordSet):
    def _get_word_data(self, lang):
        return self._data()['nameset'][lang] or []
        
class NounSet(WordSet):
    def _get_word_data(self, lang):
        return self._data()['nounset'][lang] or []
        
class PronounSet(WordSet):
    '''Unlike NounSet, etc., this is the entire list item - duck typing + reach a little deeper'''
    def person(self):
        return self._data()['person']
       
    def _get_word_data(self, lang):
        return self._data()['pronounset'][lang] or []       
        
class VerbSet(WordSet):
    # verb categories' structure is different 
    def _get_word_data(self, lang):            
        return self._data()[lang]
            
            
### module-level variables (intended to be read-only after initialization) ###
# TODO: move classes to a separate file, if they ever want to be used externally without having to load all these files
    # but that seems unlikely, since these are FILE INTERFACE classes

# adjectives and adverbs are not inflected in en, but there are still comparative/superlative forms (JJR, JJS)
ADJSET_BANK = AdjectiveSetBank(DATA_DIR + 'adjsets.yml')
ADJ_FORMS = { lang: AdjectiveFormBank(DATA_DIR + 'adjs_{}.yml'.format(lang)) for lang in LANGUAGES }

ADVSET_BANK = AdverbSetBank(DATA_DIR + 'advsets.yml')
ADV_FORMS = { lang: AdverbFormBank(DATA_DIR + 'advs_{}.yml'.format(lang)) for lang in LANGUAGES }
    
DETSET_BANK = DeterminerSetBank(DATA_DIR + 'detsets.yml')
DET_FORMS = { lang: DeterminerFormBank(DATA_DIR + 'dets_{}.yml'.format(lang)) for lang in LANGUAGES }
    
NAME_BANK = NameSetBank(DATA_DIR + 'namesets.yml')
# TODO: load language-specific name files, for any languages that might have noun declensions

NOUNSET_BANK = NounSetBank(DATA_DIR + 'nounsets.yml')
NOUN_FORMS = { lang: NounFormBank(DATA_DIR + 'nouns_{}.yml'.format(lang)) for lang in LANGUAGES }

PRONSET_BANK = PronounSetBank(DATA_DIR + 'pronsets.yml')
PRONOUN_FORMS = { lang: PronounFormBank(DATA_DIR + 'prons_{}.yml'.format(lang)) for lang in LANGUAGES }

TAXONOMY = Taxonomy(DATA_DIR + 'taxonomy.yml')

#VERBSET_BANK = VerbSetBank(DATA_DIR + 'verbsets/')
VERBSET_BANK = VerbSetBank(DATA_DIR + 'verbsets.yml')
VERB_FORMS = { lang: VerbFormBank(DATA_DIR + 'verbs_{}.yml'.format(lang)) for lang in LANGUAGES }


TEMPLATE_DIR = DATA_DIR + 'templates/'
ADJP_TEMPLATE_BANK = TemplateBank(TEMPLATE_DIR + 'adjp_templates.yml')
ADVP_TEMPLATE_BANK = TemplateBank(TEMPLATE_DIR + 'advp_templates.yml')
CLAUSE_TEMPLATE_BANK = TemplateBank(TEMPLATE_DIR + 'clause_templates.yml')
CUSTOM_TEMPLATE_BANK = TemplateBank(TEMPLATE_DIR + 'custom_templates.yml')
NP_TEMPLATE_BANK = TemplateBank(TEMPLATE_DIR + 'np_templates.yml')
TRANSFORMATION_BANK = TransformationBank(TEMPLATE_DIR + 'transformations.yml')



    