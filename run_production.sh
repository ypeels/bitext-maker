#!/bin/bash

# a multiprocess wrapper script for generating a LOT of examples

NUM_CORES=$(nproc --all)
num_threads=$((NUM_CORES * 1))

jobtime=$(date +%F-%H%M%S)
for thread in $(seq 1 $num_threads); do
    python3 main.py --output $jobtime.part$thread &
done
wait

for lang in en zh; do
    cat $jobtime.part*.$lang > $jobtime-generated.$lang
done
