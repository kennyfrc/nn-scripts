#!/bin/bash

python3 selfplay.py --games 20000 --engine lc0 --file_type plain --mode random --book books/unbal4moves.bin --nodes 1 --min_ply 15