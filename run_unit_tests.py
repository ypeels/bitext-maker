'''Run all tests'''
# TODO: rename to "run_tests.py" and add some integration tests

def run_unit_tests():
    module_names = ['taxonomy', 'yaml_reader']
    for name in module_names:
        module = __import__(name)
        module.test()

if __name__ == '__main__':
    run_unit_tests()