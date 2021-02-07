#!/bin/bash
# chmod +x *.sh

# Usage:
# ./bintoplain.sh test.bin test.txt
# best for debugging bins

NNUE=sf-trainer

# $1 = input
# $2 = output
options="setoption name SkipLoadingEval value true
isready
learn convert_plain output_file_name $2 $1
quit
"

printf "$options" | $NNUE