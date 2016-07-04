'''
Convert tagged sentence pairs into YAML (custom) templates for generation

Example: The quick brown fox|NN#animal jumps

This goes back to my pre-YAML basic idea for template data format - now it's a meta-template of sorts.
'''
import collections


from utility import LANGUAGES
import yaml_reader
import yaml

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
    
    
def process_datum(datum):
    data_per_lang = { lang: process_tagged_sentence(datum[lang]) for lang in datum if lang in LANGUAGES }
    
    # all languages must have the same symbols
    assert('en') in data_per_lang
    symbol_set = set(data_per_lang['en']['symbols'])
    if any(set(data_per_lang[lang]['symbols']) != symbol_set for lang in data_per_lang.keys()):
        for lang in data_per_lang:
            print('{} symbols:'.format(lang), list(data_per_lang[lang]['symbols']))
        raise RuntimeError('symbol lists do not match (see above)') 

    # establish basic backbone - code after this just writes into it.
    # TODO: could (and probably should) read a blank template in from YAML instead...
        # but that would require having blank template PIECES for each symbol and each lang.
        # meh, with decent indentation, it resembles the YAML sufficiently
    result = { 
        'symbols': { 
            symbol: {
                'type': FORBIDDEN_YAML_DATA, # this entry must get filled in below
                'options': {
                    # TODO: number?
                    'tags': []
                }
            } for symbol in symbol_set 
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
    
        for symbol in symbol_set:
        
            hashtags = data_per_lang[lang]['symbols'][symbol]['hashtags']
            assert(type(hashtags) is list)
            if hashtags:
                result['symbols'][symbol]['options']['tags'] += hashtags # generator ignores duplicates, right?
                
            result['langs']
            formattags = data_per_lang[lang]['symbols'][symbol]['formattags']
            assert(type(formattags) is list)
            if formattags:
                result['langs'][lang]['tags'][symbol] = formattags
                
            
            
        # TODO: symbol type - infer this from the POS tags...
        
    
    print(yaml.dump(data_per_lang))
    
    # TODO: handle POS tags - depending on language and depending on POS, might want a literal form
        # can probably do this pretty easily by using a mapping from POS tags to 
        # but should also check POS tags as to whether or not to add lang-specific forms
    
    # TODO: store the original word in the template somehow
    return result #data_per_lang



    

def process_tagged_sentence(sentence):
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
            result['POS'] = pos
            
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
                result['symbols'][symbol] = { 'hashtags': hashtags, 'formattags': formattags, 'original word': word }
        
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