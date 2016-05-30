'''
Monolingual generators that finally convert data to sentences
'''
import data
import main # for sentence_case for capitalization hack...
import nodes 
import utility


# this does NOT look scalable!
PAST_TENSE_WHITELIST = {
    'action', # TODO: action* seems fine
    'action.creation',
    'change.appear.showup',
    'change.start',     
    'cognition.solve', 
    'communication.verbal.meta', 
    'motion.bring', 
    'motion.enter.into',
    'perception.vision', 
    'possession.give',
    'possession.obtain',
    'social.help'}

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
        self._pronoun_form_bank = data.PRONOUN_FORMS.get(self.LANG)
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
        

    # en abhors "car car", and "车车" sounds like baby talk
    # TODO: this doesn't fix the tree... it just prevents it from generating strings like that...
    def _can_modify_with_noun(self, target_node, noun_modifier_node):
        target_nouns = [child.generated_text(self.LANG) for child in target_node._get_headnodes()]
        return noun_modifier_node.generated_text(self.LANG) not in target_nouns
            
        
        
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
        if node_type == 'adjective':
            assert(self.LANG in ['en', 'zh'])
            self._generate_node_text(node, node.word(self.LANG))
        elif node_type == 'adverb':
            self._generate_node_text(node, node.word(self.LANG))
        elif node_type == 'determiner':
            self._generate_determiner(node)
        elif node_type == 'name':        
            # for multiple names (Alice, 爱丽丝): absent any guidance, should just pick the first (default) name?
                # ugh, I don't want to think about this right now... let's just "solve" this in data
            #assert(node.num_datasets(self.LANG) == 1)
            #self._generate_name(node) # neither language's names have dependencies right now
            assert(self.LANG in ['en', 'zh'])
            assert(node.number() == 'singular') # TODO: plural names, like Greeks? that would affect English subject-verb agreement
            name = node.word(self.LANG)
            self._generate_node_text(node, name)   
        elif node_type == 'noun':
            self._generate_noun(node) # punt to subclass
        elif node_type == 'pronoun':
            self._generate_pronoun(node)
        elif node_type == 'verb':
            assert(not node.has_modifiers()) # TODO: insert verb modifiers into Clause template
            self._generate_verb(node)
        else:
            raise Exception('Unimplemented generation for lexical node type ' + node_type)
            
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
            
        
            # TODO!!! handle modifiers here, right? need to insert them INTO the template... but in a language-dependent way...
            # so, modifiers are all fully generated - just have to figure out their ordering now
            # hmm, needs to check all subnodes for modifiers? 
            template = self._modify_template(node)
            
            # populate the template - get(key, default value)
            result = [generated_symbols.get(token, token) for token in template ]
            
            if node._get_option('capitalization hack'): # currently from custom_templates.yml/multiple
                result[0] = main.sentence_case(result[0])

            self._generate_node_text(node, ' '.join(result))
            
        else:
            raise Exception('in single-pass generation, should never get here')
        
    def _get_det_base(self, node):
        return node.word(self.LANG)        
    def _get_noun_base(self, node):
        return node.word(self.LANG)            
    def _get_verb_base(self, node):
        #assert(node.num_datasets(self.LANG) == 1)
        #verbset = node.sample_dataset() #get_dataset_by_index(0)#get_verbset_by_index(0)
        #return verbset.verb(self.LANG)
        return node.word(self.LANG)
        
    def _get_unmodified_template(self, node):
        template_text = node.get_template_text(self.LANG)
        return template_text.split() 
        
    def _modify_template(self, node):
        '''
        Example input template: [S V O]
        Example return value: [S quickly V O]
        '''
        assert(issubclass(type(node), nodes.TemplatedNode))
        
        # can't do this, because there might be language-dependent finishing touches for unmodified nodes
        #if not node.has_modifiers():
        #    result = self._get_unmodified_template(node)
        
        if node.type() == 'ADJP':
            result = self._modify_adjp(node) 
        elif node.type() == 'Clause':
            result = self._modify_clause(node) #['Generator._modify_template_Clause'] + self._get_unmodified_template(node)
        elif node.type() == 'NP':
            result = self._modify_np(node)
        elif node.type() in {'ADVP', 'CustomTemplate'}:
            assert(not node.has_modifiers())
            result = self._get_unmodified_template(node)
        else:
            raise Exception('Unimplemented template modification: tried to modify {}'.format(node.type()))
            
        # also handle any prewords and postwords here - since this IS "modify_template()" - although this is not QUITE linguistic modification...
        # TODO: move this to overridable subroutine, to allow for language-specific semantic checks
        prewords_per_symbol = node.template_prewords(self.LANG)
        for symbol, preword in prewords_per_symbol.items():
            if preword:
                symbol_index = result.index(symbol)
                result.insert(symbol_index, preword)
                
        # TODO: DRY this out with prewords...
        postwords_per_symbol = node.template_postwords(self.LANG)
        for symbol, postword in postwords_per_symbol.items():
            if postword:
                symbol_index = result.index(symbol)
                result.insert(symbol_index + 1, postword)
            
        assert(type(result) is list and all(type(item) is str for item in result))
        return result
        
        
    # zh and en can get away with sharing these for now...
    def _modify_adjp(self, node):
        result = self._get_unmodified_template(node)
        modifiers = list(node.modifiers())
        
        # no, need to check the LEXICAL target for compatibility...
        adverbs = self._pop_modifiers(modifiers, 'adverb')
        if adverbs:
            adverb_strings = [a.generated_text(self.LANG) for a in adverbs]
            assert(len(adverb_strings) is 1) # multiple adverbs doesn't work in zh? also, "very and quickly big" doesn't quite work
            result = adverb_strings + result #self.__conjunction(adverb_strings) + result
            
        if modifiers:
            raise Exception('TODO: unhandled modifiers - {}'.format(modifiers))
            
        return result

    # shared by language-specific subclasses
    def _modify_clause_with_adverbs(self, node, adverb_nodes, result):
        assert(type(result) is list and all(type(t) is str for t in result))

        # insert adverb before every head verb in the clause
        head_symbols = node.head_symbols()
        assert(all(node._type_for_symbol(head) == 'verb') for head in head_symbols)
        
        adv_strings = [a.generated_text(self.LANG) for a in adverb_nodes]
        assert(len(adv_strings) is 1) # multiple adverbs doesn't work here for zh...although it might for en? semantic-dep? 
        
        for head in head_symbols:
            head_index = result.index(head)
            
            result = result[:head_index] + adv_strings + result[head_index:] #self.__conjunction(adv_strings) + result[head_index:]
        return result

    def _modifiers_are_done(self, modifiers):
        '''This function should only be called during asserts...'''
        if len(modifiers) is 0:
            return True
        else: 
            error_message = 'TODO: unhandled modifiers - {}'.format([m.template_id() for m in modifiers])
            print(error_message)
            raise Exception(error_message) # or should I let it return?
            return False

              
    def _pop_modifiers(self, modifiers, id_to_pop):
        '''Removes modifiers with matching template ID (changes list in place) and returns them'''
        assert(type(modifiers) is list)
        assert(all(issubclass(type(m), nodes.ModifierNode) for m in modifiers))
        popped = [m for m in modifiers if m.template_id() == id_to_pop]
        for p in popped:
            modifiers.remove(p)
            assert(modifiers.count(p) is 0)
        return popped
        
        
    
    
    
class EnGenerator(Generator):
    LANG = 'en'
        
    def _generate_determiner(self, node):
        #assert(node.type() == 'determiner') # let's not do this - you'd have to do this for EVERY language...
        det_base = self._get_det_base(node)
        
        forms = self._det_form_bank.get(det_base) or {}
        
        lexical_targets = node.lexical_targets()
        assert(len(lexical_targets) is 1) # TODO: multiple targets - which would go by NEAREST? "this cat and dogs"? hmm
        det = forms.get(lexical_targets[0].number(), det_base)
        
        # singular or plural form of determiner?
        self._generate_node_text(node, det)
        
    def _generate_noun(self, node):
        noun_base = self._get_noun_base(node)  
        if node.number() == 'singular':
            noun = noun_base            
        else:
            noun = self.__pluralize_noun(noun_base)
        self._generate_node_text(node, noun)
      
    def _generate_pronoun(self, node):
        pron_base = node.word(self.LANG)
        pron_forms = self._pronoun_form_bank.get(pron_base)
        
        # so the logic here is language AND data dependent... but I guess I've been doing that the whole time
        tags = node.tags_for_lang(self.LANG)
        if 'subjective' in tags:
            case = 'subjective'
        elif 'objective' in tags:
            case = 'objective'
        else:
            raise Exception('Unsupported case', tags)
            
        if node.number() == 'singular':
            form = case
        else:
            assert(node.number() == 'plural')
            form = 'PRPS.' + case
            
        pronoun = pron_forms.get(form, pron_base)
        node.set_generated_text(self.LANG, pronoun)
        
    def _generate_verb(self, node):
        # should depend on subject
        # also depends on tense... presumed present for now
        dependencies = node.get_dependencies(lang=self.LANG)
        if not all(dep.has_generated_text(self.LANG) for dep in dependencies):
            #return # vestigial? was I overengineering some hypothetical case where you have to wait for dependency's generated surface form?
            pass
        
        # TODO: unified logic instead of just hackishly short-circuiting participles like this
        fixed_verb_form = node.fixed_form(self.LANG)
        if fixed_verb_form:
            self._generate_node_text(node, self._get_verb_from_form(node, fixed_verb_form))
            return

        assert(len(dependencies) is 1) # just subject-verb for now
        subject_node = dependencies[0]
        
        if node.get_tense() == 'present':
            self.__generate_verb_present(node, subject_node)
        else:
            raise Exception('Unsupported tense ' + node.get_tense())

    # TODO: move into Generator superclass?
    # TODO: DRY this out between _generate_verb() and _generate_verb_present
    # alternatively baking this into Verb would put language-dependent code in the tree (well, tree data is already lang-dep...)
    def _get_verb_from_form(self, verb_node, form):
        verb_base = self._get_verb_base(verb_node)
        if form == 'VB': # wasted an hour tracking down this "bug" (the design decision to just use VB as the base form and key)
            return verb_base
        else:
            verb_forms = self._verb_form_bank.get(verb_base)
            verb = verb_forms.get_form(form)
            if not verb:
                raise Exception('verb form not found', verb_base, form)
            return verb
            
    # TODO: move morphological logic into LexicalNode, which would then have language-dependent code, and grow with # languages?
        # the alternative, which is currently used, is to punch a new hole in LexicalNode every time you need more metadata...
    def __generate_verb_present(self, verb_node, subject_node):
        # person and number
        # need to choose between the forms of the verb's word
        verb_base = self._get_verb_base(verb_node)
        verb_forms = self._verb_form_bank.get(verb_base) # needed by is_regular() below
        if not verb_forms:
            raise Exception('Missing verb form', verb_base)

        if verb_forms.is_regular():

            # if subject third person and regular, then use VBZ
            if subject_node.number() == 'singular' and subject_node.person() == 3:
                verb = self._get_verb_from_form(verb_node, 'VBZ') #verb_forms.get_form('VBZ')
            else:
                verb = self._get_verb_from_form(verb_node, 'VBP') #verb_forms.get_form('VBP')
                
            self._generate_node_text(verb_node, verb)
            
        else:
            raise Exception('Unimplemented: irregular en verbs')
            
            
    
    def _modify_clause(self, node):
        # TODO: DRY this out into a 2-line base class function?
        result = self._get_unmodified_template(node)
        modifiers = list(node.modifiers())
        
        adverbs = self._pop_modifiers(modifiers, 'adverb')
        if adverbs:
            result = self._modify_clause_with_adverbs(node, adverbs, result) # shared from base class
            
        if modifiers:
            raise Exception('TODO: unhandled modifiers - {}'.format(modifiers))
        
        return result

            
    def _modify_np(self, node):
        template = self._get_unmodified_template(node)
        
        result = [] # most of this logic recycles nicely from the version where modifiers were owned by the LexicalNode itself
        modifiers = list(node.modifiers()) # make a copy (trashed immediately)
        
        # TODO there are semantics-related ordering issues.. it looks like this could get VERY complicated...
        
        # determiner goes at the very front
        # TODO: "forbidden" det-noun pairs like "every thing" and "no body"
        dets = self._pop_modifiers(modifiers, 'determiner')        
        assert(len(node._get_headnodes()) is 1)
        if dets: 
            assert(len(dets) is 1) # forget about PDTs ("all the gold") for now
            result.append(dets[0].generated_text(self.LANG))
        else:
            if node.number() == 'singular' and node.template_id() == 'noun':
                if any(data.TAXONOMY.isa(tag, 'object') for tag in node._get_option('tags') if type(tag) is str):
                    result.append('the')
                else:
                    raise Exception('TODO: unmodified singular noun that is not an #object')
                    
        # adjectives
        adjs = self._pop_modifiers(modifiers, 'adjective')
        if adjs:
            # TODO: adjective ordering
            # remove duplicate adjectives. TODO: fix the tree as well, instead of just suppressing output
            adj_strings = list(set(a.generated_text(self.LANG) for a in adjs)) # back-converted to list for use by conjunction
            result += self.__conjunction(adj_strings) 
            
        # nouns (clown car)
        nouns = self._pop_modifiers(modifiers, 'noun')
        #result += [n.generated_text(self.LANG) for n in nouns]   
        for n in nouns:
            if self._can_modify_with_noun(node, n):
                result.append(n.generated_text(self.LANG))
                    
        result += template

        # participles - postpend after the noun
        participles = self._pop_modifiers(modifiers, 'participle')
        if participles:
            assert(all(p.num_symbols() > 1 for p in participles)) # objectless? needs different order: "the kicking man"
            part_strings = [p.generated_text(self.LANG) for p in participles]
            result += self.__conjunction(part_strings)
        
        assert(self._modifiers_are_done(modifiers))

        return result
            

                    
        
    def __conjunction(self, strings):
        '''
        Input: list of strings
        Output: [str1, ',', str2, ',' ... , 'and', strN]
        '''
        # no serial comma, to facilitate generation
        # TODO: add user option for serial comma?
        assert(type(strings) is list)
        assert(all(type(s) is str for s in strings))
        
        result = []
        for s in strings[:-2]:
            result += [s, ',']
            
        if len(strings) >= 2:
            result += [strings[-2], 'and']
            
        result += [strings[-1]]
        
        return result
        
        
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
        lexical_targets = node.lexical_targets()
        assert(len(lexical_targets) is 1)
        assert(lexical_targets[0].type() == 'noun')
                
        words = self._get_det_base(node) # string instead of list, to enable segmentation antics
                
        target = lexical_targets[0]
        assert('object' in target._get_option('tags')) # so that "DT 些" has a plural meaning (*这 些 水). so horribly brittle...        
        
        if target.number() == 'singular':
            noun = self._get_noun_base(target)
            noun_form = self._noun_form_bank.get(noun)
            
            # TODO: allow measure word omission (e.g. 这 世界 - only allowed for some words?)
            measure_words_from_file = noun_form.get('M', '个')
            if measure_words_from_file == '个':
                measure_word = '个'
            else:
                # this should occur here and not in NounSet, because it's zh-specific, and I'm trying to keep all language-specific code in Generators
                # but unfortunately, it's also data-specific code...
                if type(measure_words_from_file) is str:
                    candidates = [measure_words_from_file]
                elif type(measure_words_from_file) is list:
                    assert(all(type(item) is str for item in measure_words_from_file))
                    candidates = measure_words_from_file
                else:
                    assert(type(measure_words_from_file) is dict) # I suppose it could be a number or a bool...
                    raise Exception('M: expected str or list (YAML)')
                    
                if utility.rand() <= 0.9:
                    measure_word = utility.pick_random(measure_words_from_file) # allows multiple M's per word
                else:
                    measure_word = '个'
            
            assert(type(measure_word) is str) 
            words += ' ' + measure_word
            
        else:
            words += '些'
        
        self._generate_node_text(node, words)
        
        
        # WARNING: this is using data from noun forms (nouns_zh.yml) as METADATA (not noun data per se)... but that's okay, right?
        
        
        # *每 个 这 个 东西
    
    def _generate_noun(self, node):
        noun = self._get_noun_base(node) # no inflections
        self._generate_node_text(node, noun)
        
    def _generate_pronoun(self, node):
        pronoun = node.word(self.LANG)
        if node.number() == 'plural':
            pronoun += '们'
        node.set_generated_text(self.LANG, pronoun)
        
    # ah, conjugation-free Chinese...
    def _generate_verb(self, node):
        verb = self._get_verb_base(node)
        self._generate_node_text(node, verb)

    def _modify_clause(self, node):
        # TODO: DRY this out into a 2-line base class function?
        result = self._get_unmodified_template(node)
        modifiers = list(node.modifiers())
        
        adverbs = self._pop_modifiers(modifiers, 'adverb')
        if adverbs:
            result = self._modify_clause_with_adverbs(node, adverbs, result) # shared from base class

        head_symbols = node.head_symbols()
        assert(len(head_symbols) is 1) # TODO: with multiple heads, verb category may vary between heads
        head = head_symbols[0]
        if 'tense.past' in node.syntax_tags_for_symbol(head, self.LANG):
            assert(node._get_symbol_subnode(head).get_tense() == 'past')
        
            # the same crude way that default determiners are handled...
            if node.verb_category_id() in PAST_TENSE_WHITELIST:
                result.insert(result.index(head) + 1, '了')
            elif not adverbs:
                # horrible hack: a topicalized time point phrase - use if desired...
                #raise Exception('TODO: something better than topicalized time point for zh non-action past tense?')
                result = ['当时'] + result
            else:
                raise Exception('TODO: check adverbs for time phrases')
          
        if modifiers:
            raise Exception('TODO: unhandled modifiers - {}'.format(modifiers))
        
        return result
        
    def _modify_np(self, node):
        template = self._get_unmodified_template(node)

        # based on EnGenerator.__modify_np() - hmmmm that's not very DRY...
        result = []
        modifiers = list(node.modifiers()) 
        
        
        # determiners
        dets = self._pop_modifiers(modifiers, 'determiner')
        if dets:
            assert(len(dets) is 1) 
            result.append(dets[0].generated_text(self.LANG))            
        else:
            if node.number() != 'singular' and node.template_id() == 'noun':
                assert('object' in node._get_option('tags')) # for now, assume countable? 一些时间 != times...
                #assert(not node.has_modifiers()) # TODO: check modifiers for "pluralizers" like CD
                result.append('一些')
        
        # participles - generally handle before adjectives, which could even be single-character...
        participles = self._pop_modifiers(modifiers, 'participle')
        if participles:
            for part in participles:
                text = part.generated_text(self.LANG)
                result += [text, '的']
        
        # adjectives
        adjs = self._pop_modifiers(modifiers, 'adjective')
        if adjs:
            # TODO: for more than 1 adj, might want to order them in a more semantically sensible order
            
            # single-character adj's go next to the target, and if multiple, with 和 intervening...
            adj_strings = [a.generated_text(self.LANG) for a in adjs]
            
            # TODO: handle duplicated adjectives correctly - would require changing tree
            # prevent redundant adjectives for now, which read differently in zh
            # note that this doesn't fix the tree - it just suppresses the output
            single_char_adjs = list(set(s for s in adj_strings if len(s) is 1))
            multi_char_adjs = list(set(s for s in adj_strings if s not in single_char_adjs))
            
            for adj_str in multi_char_adjs:
                result += [adj_str, '的']
                
            for adj_str in single_char_adjs[:-1]:
                result += [adj_str, '和']
                
            result += single_char_adjs[-1:]
                
                    
        # nouns (clown car)
        nouns = self._pop_modifiers(modifiers, 'noun')
        #result += [n.generated_text(self.LANG) for n in nouns]                
        for n in nouns:
            if self._can_modify_with_noun(node, n):
                result.append(n.generated_text(self.LANG))

        assert(self._modifiers_are_done(modifiers))
        
        result += template

        return result
    
        
    
    
def generator_factory(lang):
    '''Generates a SINGLETON generator that lives in this module'''
    assert(lang in utility.LANGUAGES)
    if lang == 'en':
        return EnGenerator()
    elif lang == 'zh':
        return ZhGenerator()
    else:
        raise Exception('Unimplemented generator for language:' + lang)




# module-level singletons
analyzer = Analyzer()
generators = { lang: generator_factory(lang) for lang in utility.LANGUAGES }
    
    
if __name__ == '__main__':
    print(EnGenerator().LANG)
    nodes.Node()