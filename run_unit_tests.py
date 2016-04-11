'''Run all my unit tests'''


module_names = ['taxonomy', 'yaml_reader']
for name in module_names:
    module = __import__(name)
    module.test()
