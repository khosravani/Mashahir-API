#!/bin/bash
# Copyright 2018 Abbas Khosravani.

# This script is intended to extract xvectors for a given audio file.

path=$PWD
export LC_ALL=C
export PATH=$path/bin/:$PATH
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:$path/lib

# Begin configuration section.

if [ $# != 3 ]; then
  echo "Usage: $0 [opts] <audio-file> <port>"
  exit 1;
fi

data=${path}/.tmp$RANDOM
wavfile=$1
port=$2
type=$3

# Speaker model parameters
min_chunk_size=25
max_chunk_size=100
chunk_size=10000
use_gpu=no
cache_capacity=1024

# Path to models and configurations
model=$path/models # path to the models used by speaker ID system
conf=$path/conf # path to configuration folder
log=$data/debug.log

rm -rf $data 
mkdir -p $data

wavpath=`readlink -f $wavfile` || { echo "error readlink"; exit 1; }
# echo $wavpath "sox" $wavpath "-r 8000 --bits=16 -t wav - |" > $data/wav.scp
if [ $type = 'mpeg' ] || [ $type = 'flac' ] || [ $type = 'ogg' ] || [ $type = 'mp4' ] || [ $type = 'au' ] || [ $type = '3gpp' ] || [ $type = 'x-ms-wma' ]
then
  echo $wavpath "ffmpeg -i" $wavpath " -ar 16000 -f wav - |" >> $data/wav.scp
## this is telegram audio mime type --> application/octet-stream
elif [ $type = 'octet-stream' ]
then
  echo $wavpath "opusdec " $wavfile " --rate 16000 --force-wav --packet-loss 0 - |" >> $data/wav.scp
else
  echo $wavpath "sox" $wavpath "-r 16000 --bits=16 -t wav - |" >> $data/wav.scp
fi

compute-mfcc-feats --config=$conf/mfcc.conf scp:$data/wav.scp ark:$data/feats.ark 2>>$log || { echo "error feature-extraction"; exit 1; }

compute-vad --config=$conf/vad.conf ark:$data/feats.ark ark:$data/vad.ark 2>>$log || { echo "error sad"; exit 1; }

apply-cmvn-sliding --norm-vars=false --center=true --cmn-window=300 ark:$data/feats.ark ark:- 2>>$log \
| select-voiced-frames ark:- ark:$data/vad.ark ark:$data/pfeat.ark 2>>$log

feat-to-len ark:$data/pfeat.ark ark,t:$data/pfeat.len 2>>$log
if [ `awk '{print $2;}' $data/pfeat.len` -lt 200 ]; then
  echo "error short-speech";
  exit 1
fi

curl -s -X POST http://127.0.0.1:$port/json -d "{
    \"feature_rspecifier\": \"ark:$data/pfeat.ark\",
    \"vector_wspecifier\": \"ark,t:$data/xvector.ark\"}" 1>>$log

echo `awk '{for(i=3; i < NF; i++) print $i;}' $data/xvector.ark`

# clean up
rm -rf $data
exit 0

