import yaml

# CSafeLoader: "LibYAML bindings, which are much faster than the pure Python version" (PyYAML documentation)
# Miniconda's PyYAML doesn't include libyaml
# also note that yaml.safe_load() cannot switch to CSafeLoader (prevents switching to unsafe loader)
try:
    from yaml import CSafeLoader as SafeLoader, CSafeDumper as SafeDumper
except ImportError:
    from yaml import SafeLoader as SafeLoader, SafeDumper as SafeDumper

    
    
def read_file(filename):
    '''
    Input: YAML file
    Output: all data objects from file (no extra outer list for single-document file)
    '''
    with open(filename, 'r', encoding='utf8') as input:
        result = [item for item in yaml.load_all(input, Loader=SafeLoader)]
        if len(result) == 1:
            return result[0]
        else:
            return result

            
def write_file(filename, data):
    with open(filename, 'w', encoding='utf8') as output:
        output.write(yaml.dump(data, Dumper=SafeDumper
                , allow_unicode=True # otherwise gets written out as \u1234, etc.
                , default_flow_style=False # one entry per line - for readability, post-editing
                #, width=40 # newlines in dict entries are ignored, as long as you indent far enough
                ))
                #encoding='utf-8', ))
            
            
def test():
    '''some quickie testing - not even really unit testing, since pass/fail criteria aren't defined'''
    from utility import DATA_DIR
    testfile = DATA_DIR + 'namesets.yml'
    print('Reading', testfile)
    boo = read_file(testfile)
    print(boo[:3])
            
            
if __name__ == '__main__': 
    test()
    
