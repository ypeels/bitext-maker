from data import VERBSET_BANK, VERB_FORMS
import collections
import utility

UNCONJUGATED_LANGUAGES = ['zh']
LANGS = [lang for lang in utility.LANGUAGES if lang not in UNCONJUGATED_LANGUAGES]


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
            word = vs[lang]
            if word not in finished_word_forms[lang]:
                missing_word_forms[lang].add(word)
        
    with open('missing_verbs.txt', 'w', encoding='utf8') as output:
         for lang, missing_list in missing_word_forms.items():
             output.write('\n\nWords missing from verbs_{}.yml\n'.format(lang))
             output.write('\n'.join(sorted(missing_list)))