#!/bin/bash
# chmod +x *.sh

# Usage:
# ./pgntofen.sh input.pgn output.txt

PGNEXTRACT=/usr/local/bin/pgn-extract

# $2 = output
# $1 = input
$PGNEXTRACT --fencomments -Wlalg --nochecks --nomovenumbers --noresults -w500000 -N -V -s -o $2 $1

# pgn-extract --fencomments -Wlalg --nochecks --nomovenumbers --noresults -w500000 -N -V -o output.txt input.pgn