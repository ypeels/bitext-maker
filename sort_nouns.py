'''
Sort "growth" files like nounsets.yml while preserving comments
'''

import yaml

#import data

FILENAME = 'nounsets'
INPUT_FILE = 'datasets/{}.yml'.format(FILENAME)
OUTPUT_FILE = 'datasets/{}-sorted.yml'.format(FILENAME)


def starts_nounset(line):
    return '- tags:' in line or '- nounset:' in line
    
    
def nounset_key(nounset):
    assert(type(nounset) is tuple)  
    
    ## nice try, but this chokes on fully-commented lines. unfortunately, this would have to evolve if data format changes
    #nounset_data = data.NounSet(yaml.load(''.join(nounset), Loader=yaml.SafeLoader)[0])

    key_lines = [line for line in nounset if 'en:' in line]
    assert(len(key_lines) is 1)
    
    value = key_lines[0].split(':', maxsplit=1)[1]
    datum = yaml.load(value.strip(), Loader=yaml.SafeLoader)
    if type(datum) is str:
        result = datum
    elif type(datum) is list:
        result = datum[0]
    else:
        result = ''

    return result
    
    
# TODO: preserve line endings
def write(line, output):
    output.write(line)
    
    # extra newline to handle corner case of a line that was chomped from the end of file, and file didn't end with newline
    if not line.endswith('\n'):
        output.write('\n') 
        
        

if __name__ == '__main__':
    if OUTPUT_FILE == INPUT_FILE:
        raise Exception('Error: this would overwrite the input file') # add a --force option or something?
    
    with open(INPUT_FILE, 'r', encoding='utf8') as input:
        lines = input.readlines()
        
    i = 0
    nounsets = []
    comments = []
    while i < len(lines):
        current_line = lines[i]
        if starts_nounset(current_line): 
            # allow stride to vary - not all nounsets may have been filled in for all languages
            stride = 1
            while i+stride < len(lines) and not starts_nounset(lines[i+stride]):
                stride += 1
                assert(stride <= 1000) # JUST in case there's an infinite loop/bad data file
        
            # strip out blank lines for uniformity
            nounset_lines = tuple([line for line in lines[i : i+stride] if line.strip()])
        
            nounsets.append(nounset_lines)
            i += stride
        else:
            comments.append(lines[i])
            i += 1 # this all seems too "custom" to do with a listcomp
            
    
    # newline='' keyword preserves line ending format
    with open(OUTPUT_FILE, 'w', encoding='utf8', newline='') as output:
        for line in comments:
            write(line, output)
            
        for nounset in sorted(nounsets, key=nounset_key):
            for line in nounset:
                write(line, output)
            
    