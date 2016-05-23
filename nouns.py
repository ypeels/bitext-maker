'''
Inspect nounsets.yml
'''

from data import NOUNSET_BANK
import collections
import utility


if __name__ == '__main__':
    nounset__data = NOUNSET_BANK._data()
    #import yaml; print(yaml.dump(nounset__data))
    
    tag_counts = collections.Counter()
    
    for nounset in nounset__data:
        for tag in nounset['tags']:
            tag_counts[tag] += 1
            
    for tag, count in utility.nested_sort(tag_counts.items()):
        print('{:>9} {}'.format(count, tag))
        
    # TODO: syntax checking