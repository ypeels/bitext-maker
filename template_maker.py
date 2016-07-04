'''
Convert tagged sentence pairs into YAML (custom) templates for generation

Example: The quick brown fox|NN#animal jumps

This goes back to my pre-YAML basic idea for template data format - now it's a meta-template of sorts.
'''
import collections
import yaml # useful for debugging as well as error messages

from utility import LANGUAGES
import yaml_reader


FORBIDDEN_YAML_DATA = Exception('FORBIDDEN_YAML_DATA') # just anything that will raise an error if you try to write it to YAML
TAG_SEPARATOR = '|'

INPUT_FILE = 'template_input.yml'

    # also need to specify symbol names, since you can't just go in order!
    # TODO: does this belong in data.py? but this is like a METAdata format...

    
    

def find_symbol(tags):
    candidates = [t for t in tags if t.startswith('@')]
    assert(len(candidates) is 1)
    return candidates[0][1:]
    
def find_hashtags(tags):
    return [t[1:] for t in tags if t.startswith('#')]
    
def find_formattags(tags):
    return [t[1:] for t in tags if t.startswith('%')]
    
def get_type_from_pos(pos, lang):
    #return POS_TO_TYPE_MAPPING[lang][pos] # meh, this would actually be less DRY - can't "combine" switch statements
    if lang == 'en':
        if pos in ['JJ', 'JJR', 'JJS']:
            return 'adjective'
        elif pos in ['NN', 'NNS']:
            return 'noun'
        elif pos in ['NNP', 'NNPS']:
            return 'name'
        elif pos in ['VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ']:
            return 'verb'
        else:
            raise RuntimeError('Unsupported English POS tag: ' + pos)
    elif lang == 'zh':
        if pos in ['JJ', 'VA']:
            return 'adjective'
        elif pos == 'NN':
            return 'noun'
        elif pos == 'VV':
            return 'verb'
        else:
            raise RuntimeError('Unsupported Chinese POS tag: ' + pos)
    else:
        raise RuntimeError('Unsupported language: ' + lang)
        
    
    
# TODO: DRY out dict accessors...
def process_datum(datum):
    data_per_lang = { lang: process_tagged_sentence(datum[lang], lang) for lang in datum if lang in LANGUAGES }

    # this is much cleaner if you write things from a data-centric perspective/style
    symbols_per_lang = { 
        lang: {
            sym: data_per_lang[lang]['symbols'][sym]['type'] for sym in data_per_lang[lang]['symbols']        
        } for lang in data_per_lang
    }
    
    assert('en' in symbols_per_lang)
    symbol_types = symbols_per_lang['en']
    symbols = set(symbol_types.keys())
    
    # symbol declarations and types must match for all languages
    if (    any(set(symbols_per_lang[lang].keys()) != symbols for lang in data_per_lang) or
            any(symbols_per_lang[lang][sym] != symbol_types[sym] for sym in symbols for lang in data_per_lang)):
        raise RuntimeError('symbol declaration or type mismatch\n{}'.format(yaml.dump(symbols_per_lang))) 
    

    # establish basic backbone - code after this just writes into it.
    # TODO: could (and probably should) read a blank template in from YAML instead...
        # but that would require having blank template PIECES for each symbol and each lang.
        # meh, with decent indentation, it resembles the YAML sufficiently
    result = { 
        'symbols': { 
            sym: {
                'type': symbol_types[sym], # these entries must get filled in below
                'options': {
                    # TODO: number?
                    'tags': []
                }
            } for sym in symbols 
        },
        
        'langs': { 
            lang: { 
                'template': FORBIDDEN_YAML_DATA,
                'tags': {} 
            } for lang in data_per_lang 
        }
    }
        
    for lang in data_per_lang:
        result['langs'][lang]['template'] = data_per_lang[lang]['template']
    
        for sym in symbols:
        
            hashtags = data_per_lang[lang]['symbols'][sym]['hashtags']
            assert(type(hashtags) is list)
            if hashtags:
                result['symbols'][sym]['options']['tags'] += hashtags # generator ignores duplicates, right?
                
            result['langs']
            formattags = data_per_lang[lang]['symbols'][sym]['formattags']
            assert(type(formattags) is list)
            if formattags:
                result['langs'][lang]['tags'][sym] = formattags
                
            
            # TODO: for particular types, specify literal forms
        
    
    print(yaml.dump(data_per_lang))
    
    # TODO: handle POS tags - depending on language and depending on POS, might want a literal form
        # can probably do this pretty easily by using a mapping from POS tags to 
        # but should also check POS tags as to whether or not to add lang-specific forms
    
    # TODO: store the original word in the template somehow
    return result #data_per_lang



    

def process_tagged_sentence(sentence, lang):
    assert(type(sentence) is str)
    tokens = sentence.split()
    
    result = collections.defaultdict(dict) # wait, do i need defaultdict? YES. otherwise have to allocate on first
    
    template_words = []
    for tok in tokens:
        if TAG_SEPARATOR in tok: # tagged 
            tok_pieces = tok.split(TAG_SEPARATOR)
            word, pos = tok_pieces[0:2]
            assert(pos[0] not in '#@%')
            assert(pos) # not empty
            
            if len(tok_pieces) is 2: # just word|POS - no post-editing was done - just revert to untagged word             
                template_words.append(word)
            else:      
                tags = tok_pieces[2:]
                symbol = find_symbol(tags)
                template_words.append(symbol)
                
                hashtags = find_hashtags(tags)
                formattags = find_formattags(tags)
                
                # TODO: number? (just use NN/NNS?)
                
                assert(1 + len(hashtags) + len(formattags) == len(tags))
                
                assert(symbol not in result['symbols'])
                result['symbols'][symbol] = { 
                        'hashtags': hashtags, 
                        'formattags': formattags, 
                        'original word': word,
                        'POS': pos,
                        'type': get_type_from_pos(pos, lang) }
        
        else: # bare word
            template_words.append(tok)
            # TODO: convert punctuation to a separate field? or just eat it for now? (custom templates, after all)
    
    assert('template' not in result)
    result['template'] = ' '.join(template_words) # hey, this works! you can override the default with a different data type
    
    return dict(result)
            


if __name__ == '__main__':
    input_data = yaml_reader.read_file(INPUT_FILE)
    output_data = {}
    for (key, value) in input_data.items():
        try:
            output_data[key] = process_datum(value)
        except RuntimeError as e:
            #assert(type(e.args[0]) is str)
            raise Exception('Error processing {} - key {} - {}'.format(INPUT_FILE, key, e.args[0]))
            #import pdb; pdb.set_trace()
            
    yaml_reader.write_file('test.yml', output_data)