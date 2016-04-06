import yaml

# CSafeLoader: "LibYAML bindings, which are much faster than the pure Python version" (PyYAML documentation)
# Miniconda's PyYAML doesn't include libyaml
# also note that yaml.safe_load() cannot switch to CSafeLoader (prevents switching to unsafe loader)
try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader as SafeLoader

    
    
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

            
            
if __name__ == '__main__': 
    
    # some light testing
    testfile = 'dict/names.yml'
    print('Reading', testfile)
    boo = read_file(testfile)
    print(boo[:3])