#!/bin/bash

# a multiprocess wrapper script for generating a LOT of examples

NUM_CORES=$(nproc --all)
num_threads=$((NUM_CORES * 1))

jobtime=$(date +%F-%H%M%S)
for thread in $(seq 1 $num_threads); do
    python3 main.py --output /tmp/$jobtime.part$thread &
done
wait

for lang in en zh; do
    cat /tmp/$jobtime.part*.$lang > $jobtime-generated.$lang
done
