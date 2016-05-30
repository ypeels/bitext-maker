from data import ADJSET_BANK, ADJ_FORMS
import collections
import utility

UNINFLECTED_LANGUAGES = ['zh']
LANGS = [lang for lang in utility.LANGUAGES if lang not in UNINFLECTED_LANGUAGES]
NONE_STR = '<None>'

def wrap_as_list(datum):
    if type(datum) is list:
        return datum
    else:
        return [datum]


if __name__ == '__main__':
    adjset__data = ADJSET_BANK._data()
    adjform__data = { lang: ADJ_FORMS[lang]._data() for lang in LANGS }
    
    finished_word_forms = { lang: adjform__data[lang].keys() for lang in LANGS  }
    missing_word_forms = collections.defaultdict(set)
    untagged_word_forms = collections.defaultdict(set)
    tag_counts = collections.Counter()    
    
    adjsets = []
    for adjset in adjset__data:
        for tag in wrap_as_list(adjset.get('tags')):
            if tag: 
                tag_counts[tag] += 1
            elif tag is None:
                tag_counts[NONE_STR] += 1
            else:
                raise Exception('malformed tag?', tag)
            
        # this would double-count, right?
        #if not adjset.get('tags'):
        #    tag_counts[NONE_STR] += 1
            
        for lang in LANGS:
            adjset = adjset['adjset']            
            try:
                word_data = adjset[lang]
            except KeyError:
                print(adjset)
                raise
            
            assert(word_data)
            for word in wrap_as_list(word_data):
                if word not in finished_word_forms[lang]: #.get(word):
                    missing_word_forms[lang].add(word)
                if not adjset.get('tags'):
                    untagged_word_forms[lang].add(word)
                    
                    
    # output results                    
    print()
    for tag, count in utility.nested_sort(tag_counts.items()):
        print('{:>9} {}'.format(count, tag))

    print('\n"Boolean" adjs in en that have explicitly forbidden JJR and JJS')
    for en_word, word_data in sorted(adjform__data['en'].items()):
        if word_data and any(form in word_data and word_data[form] is None  for form in ['JJR', 'JJS']):
            print(en_word)
    
    if untagged_word_forms['en']:
        print('\nUntagged words (en) - consult WordNet?')
        for word in sorted(list(untagged_word_forms['en'])):
            print(word)
                    
    with open('missing_adjs.txt', 'w', encoding='utf8') as output:
        for lang, missing_list in missing_word_forms.items():
            missing_str = '\n\nWords missing from adjs_{}.yml\n'.format(lang) + '\n'.join(sorted(missing_list))
            output.write(missing_str)
            print(missing_str)



            
    

