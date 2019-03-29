#!/bin/bash
# Copyright  2018  Dezhafzar (Abbas Khosravani).

# This script is intended to provide similarity score for a given speaker compared with the reference speakers.

path=$PWD
export LC_ALL=C
export PATH=$path/bin/:$PATH
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:$path/lib

data=$1

# Path to models and configurations
models=$path/models # path to the models used by speaker ID system
log=$data/debug.log

ivector-plda-scoring \
    --normalize-length=true \
    "ivector-copy-plda --smoothing=0.0 ${models}/plda - |" \
    "ark:ivector-subtract-global-mean ${models}/mean.vec ark:${data}/xvector_enroll.ark ark:- | transform-vec ${models}/transform.mat ark:- ark:- | ivector-normalize-length ark:- ark:- |" \
    "ark:ivector-subtract-global-mean ${models}/mean.vec ark:${data}/xvector_test.ark ark:- | transform-vec ${models}/transform.mat ark:- ark:- | ivector-normalize-length ark:- ark:- |" \
    "cat '${data}/trials' |" ${data}/score 2>>$log

sort -rn -k3 $data/score -o $data/score
echo `awk '{printf("%s %s %0.2f ", $1, $2, $3);}' $data/score`

rm -rf $data
exit 0