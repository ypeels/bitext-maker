'''
Inspect nounsets.yml - intended for development use
'''

from data import NOUNSET_BANK, NOUN_FORMS
import collections
import utility


if __name__ == '__main__':
    nounset__data = NOUNSET_BANK._data()
    
    finished_word_forms = { lang: NOUN_FORMS[lang]._data().keys() for lang in utility.LANGUAGES }
    missing_word_forms = collections.defaultdict(list)
    tag_counts = collections.Counter()    
    
    
    
    for nounset in nounset__data:
        for tag in nounset['tags']:
            tag_counts[tag] += 1
            
        for lang in utility.LANGUAGES:
            word = nounset['nounset'][lang]
            if word not in finished_word_forms[lang]: #.get(word):
                missing_word_forms[lang].append(word)
            
    # record missing monolingual morphological forms 
    with open('missing.txt', 'w', encoding='utf8') as output:
         for lang, missing_list in missing_word_forms.items():
             output.write('\n\nWords missing from nouns_{}.yml\n'.format(lang))
             output.write('\n'.join(sorted(missing_list)))
            
    for tag, count in utility.nested_sort(tag_counts.items()):
        print('{:>9} {}'.format(count, tag))
        
    
        
    # TODO: syntax checking of individual yaml files