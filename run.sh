#!/bin/bash

python3 -O selfplay.py --games 10000 --engine lc0 --multipv 1 --file_type pgn --mode random --book books/unbal4moves.bin --nodes 1 --min_ply 30