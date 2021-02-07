#!/bin/bash
# chmod +x *.sh

# Usage:
# ./fentobin.sh input.txt output.bin

NNUE=sf-trainer

# $1 = input
# $2 = output
options="setoption name SkipLoadingEval value true
isready
learn convert_bin_from_pgn-extract pgn_eval_side_to_move 1 output_file_name $2 $1
quit
"

printf "$options" | $NNUE

# pgn-extract --fencomments -Wlalg --nochecks --nomovenumbers --noresults -w500000 -N -V -o Fishtest.txt Fishtest.pgn
# stockfish.exe
# learn convert_bin_from_pgn-extract pgn_eval_side_to_move 1 output_file_name converted.bin Fishtest.txt