#!/bin/bash

NETS=$1
STR="./c-chess-cli -each tc=4+0.04 option.Hash=8 option.Threads=1 -engine cmd=./sf.master name=sf.master "

for net in $1/*.nnue;
do
    STR+="-engine cmd=./sf.master name=sf.${net} option.EvalFile=${net} "
done

STR+="-games 200 -concurrency 16 -openings file=../books/noob_3moves.epd order=random -repeat -gauntlet -rounds 1 -resign count=3 score=700 -draw count=8 score=10 -pgn $1/out.pgn 0"

eval $STR