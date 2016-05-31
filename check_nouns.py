'''
Inspect nounsets.yml - intended for development use
'''

from data import NOUNSET_BANK, NOUN_FORMS
import collections
import utility

NONE_STR = '<None>'

def wrap_as_list(datum):
    if type(datum) is list:
        return datum
    else:
        return [datum]

# TODO: have these checkers use WordSet instead
if __name__ == '__main__':
    nounset__data = NOUNSET_BANK._data()
    
    finished_word_forms = { lang: NOUN_FORMS[lang]._data().keys() for lang in utility.LANGUAGES }
    missing_word_forms = collections.defaultdict(set)
    tag_counts = collections.Counter()    
    
    
    
    for nounset in nounset__data:
        #for tag in nounset['tags']:
        #    tag_counts[tag] += 1
        for tag in wrap_as_list(nounset.get('tags')):
            if tag: 
                if type(tag) is str:
                    tag_counts[tag] += 1
                elif type(tag) is list:
                    for subtag in tag:
                        assert(type(subtag) is str)
                        tag_counts[subtag] += 1
                else:
                    raise Exception('malformed tag? expected str or list', tag)
            elif tag is None:
                tag_counts[NONE_STR] += 1
            else:
                raise Exception('malformed tag? "False" but not None', tag)
            
        for lang in utility.LANGUAGES:
            try:
                word_data = nounset['nounset'][lang]
            except KeyError:
                print(nounset)
                raise
                
            for word in wrap_as_list(word_data):
                if word not in finished_word_forms[lang]: #.get(word):
                    missing_word_forms[lang].add(word)
            
    # record missing monolingual morphological forms 
    with open('missing_nouns.txt', 'w', encoding='utf8') as output:
        for lang, missing_list in missing_word_forms.items():
            output.write('\n\nWords missing from nouns_{}.yml\n'.format(lang))
            output.write('\n'.join(sorted(missing_list)))
            
    for tag, count in utility.nested_sort(tag_counts.items()):
        print('{:>9} {}'.format(count, tag))
        
    print('Total number of nounsets:', len(nounset__data))

        
    
        
    # TODO: syntax checking of individual yaml files