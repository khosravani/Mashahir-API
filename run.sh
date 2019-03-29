#!/bin/bash
# Copyright  2018  Dezhafzar (Abbas Khosravani).

# This script is intended to voiceprints for a given audio file.
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:$PWD/lib
./bin/nnet3-xvector-compute-server-notoken --port=5002 --cache-capacity=1024 models/final.mdl
