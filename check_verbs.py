from data import VERBSET_BANK, VERB_FORMS
import collections
import utility

UNCONJUGATED_LANGUAGES = ['zh']
LANGS = [lang for lang in utility.LANGUAGES if lang not in UNCONJUGATED_LANGUAGES]

def wrap_as_list(item):
    if type(item) is list:
        return item
    else:
        return [item]

if __name__ == '__main__':
    verbset__data = VERBSET_BANK._VerbSetBank__data
    verbform__data = { lang: VERB_FORMS[lang]._data() for lang in LANGS }
    
    finished_word_forms = { lang: verbform__data[lang].keys() for lang in LANGS  }
    missing_word_forms = collections.defaultdict(set)
    #tag_counts = collections.Counter()    
    
    verbsets = []
    for verb_category_data in verbset__data.values():
        verbsets += verb_category_data['verbsets']

    for vs in verbsets:
        for lang in LANGS:
            try:
                words = vs[lang]
            except KeyError:
                print(vs)
                raise
            for word in wrap_as_list(words):
                if word not in finished_word_forms[lang]:
                    missing_word_forms[lang].add(word)

    print('\nVerb categories')
    print('\n'.join(sorted(verbset__data.keys())))
                
    with open('missing_verbs.txt', 'w', encoding='utf8') as output:
        for lang, missing_list in missing_word_forms.items():
            missing_str = '\n\nWords missing from verbs_{}.yml\n'.format(lang) + '\n'.join(sorted(missing_list))
            output.write(missing_str)
            print(missing_str)
            
