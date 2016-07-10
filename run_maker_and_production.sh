#!/bin/bash

trainbase=/home/jonathan/Desktop/corpus/processed/20160709b.IWSLT15.TED.train.zh-en.fixed.tok

echo Making templates from short meta-templates
python3 template_maker.py
if [[ ! -s datasets/templates/custom_postedited.yml ]]; then
    echo template_maker failed
    exit 1
fi

echo Running generator
rm -f output_zh.txt output_en.txt
python3 main.py --output output
if [[ ! -s output-generated.en ]] || [[ ! -s output-generated.zh ]]; then
    echo generator failed
    exit 1
fi

for lang in zh en; do
    output=/home/jonathan/Desktop/corpus/$(basename $trainbase.generated_templates.$lang)
    echo Concatenating $lang corpora to $output
    cat $trainbase.$lang output-generated.$lang > $output
done



echo goodbye world

