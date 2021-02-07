#!/bin/bash
# usage: convert.sh raw.txt raw.bin
# That way you can script the trainer.

NNUE=sf-trainer

options="setoption name SkipLoadingEval value true
isready
learn convert_bin output_file_name $2 $1
quit
"

printf "$options" | $NNUE