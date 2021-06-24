#!/bin/bash

if [ -z "$1"]
then
    echo "InputError: Pass the folder that contains the nets (e.g. ./run.sh nets)"
else
    NETS=$1
    STR="./c-chess-cli -each tc=4+0.04 option.Hash=8 option.Threads=1 -engine cmd=stockfish name=sf.master "

    for net in $1/*.nnue;
    do
        STR+="-engine cmd=stockfish name=sf.${net:2} option.EvalFile=${net} "
    done

    STR+="-games 200 -concurrency 16 -openings file=noob_3moves.epd order=random -repeat -gauntlet -rounds 1 -resign 3 700 -draw 8 10 -pgn out.pgn 0"

    eval $STR
fi


