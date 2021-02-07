#!/bin/bash

NNUE=sf-trainer
THREADS=4

options="setoption name SkipLoadingEval value true
setoption name Threads value $THREADS
isready
learn targetdir train loop 50 batchsize 1000000 use_draw_in_training 1 use_draw_in_validation 1 lambda 1.0 eta 1.0 eval_limit 32000 nn_batch_size 1000 newbob_num_trials 4 newbob_decay 0.1 eval_save_interval 1200000 loss_output_interval 1200000 mirror_percentage 50 validation_set_file_name val/val.bin
quit
"

printf "$options" | $NNUE