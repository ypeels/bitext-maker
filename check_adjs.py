from data import ADJSET_BANK, ADJ_FORMS
import collections
import utility

UNINFLECTED_LANGUAGES = ['zh']
LANGS = [lang for lang in utility.LANGUAGES if lang not in UNINFLECTED_LANGUAGES]


if __name__ == '__main__':
    adjset__data = ADJSET_BANK._data()
    adjform__data = { lang: ADJ_FORMS[lang]._data() for lang in LANGS }
    
    finished_word_forms = { lang: adjform__data[lang].keys() for lang in LANGS  }
    missing_word_forms = collections.defaultdict(set)
    #tag_counts = collections.Counter()    
    
    adjsets = []
    for adjset in adjset__data:
        #for tag in nounset['tags']:
        #    tag_counts[tag] += 1
            
        for lang in LANGS:
            word = adjset['adjset'][lang]
            if word not in finished_word_forms[lang]: #.get(word):
                missing_word_forms[lang].add(word)

    with open('missing_adjs.txt', 'w', encoding='utf8') as output:
        for lang, missing_list in missing_word_forms.items():
             missing_str = '\n\nWords missing from adjs_{}.yml\n'.format(lang) + '\n'.join(sorted(missing_list))
             output.write(missing_str)
             print(missing_str)