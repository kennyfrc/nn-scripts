#!/bin/bash
# false skiploading eval is to help retrain existing steps

cd evalsave && find . -type f -name "*.bin" -delete && cd ..

NNUE=sf-trainer
THREADS=4
EVALFILE=gek-d8.nnue

options="uci
setoption name SkipLoadingEval value false
setoption name EvalFile value $EVALFILE
setoption name Threads value $THREADS
isready
learn targetdir train loop 35 batchsize 1000000 use_draw_in_training 1 use_draw_in_validation 1 lambda 1.0 eta 0.001 eval_limit 32000 nn_batch_size 50000 newbob_num_trials 4 newbob_decay 0.5 eval_save_interval 8000000 loss_output_interval 8000000 mirror_percentage 0 validation_set_file_name val/val.bin
quit
"

printf "$options" | $NNUE