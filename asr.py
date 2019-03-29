# -*- coding: utf-8 -*-

import tensorflow as tf
import keras
import keras.backend as K
from keras.models import Model, Sequential, model_from_json, load_model
from keras.layers import *
from keras.layers.merge import add
from keras.regularizers import l2
from keras.initializers import random_normal
from keras.utils.conv_utils import conv_output_length
from keras import backend as K
from keras.layers.recurrent import SimpleRNN
from keras.optimizers import SGD, adam
from keras.activations import relu
from keras.utils.generic_utils import get_custom_objects
from keras.preprocessing.sequence import pad_sequences

import types
import resource
import re
import kenlm
import itertools
import numpy as np
import python_speech_features as p
import scipy.io.wavfile as wav

from aubio import mfcc
from heapq import heapify
from pympler import muppy, summary, tracker, classtracker
from pympler.garbagegraph import GarbageGraph, start_debug_garbage
from pympler.web import start_profiler, start_in_background

MODEL = kenlm.Model('./models/text.bot')

char_map_str = u"""
<SPACE> 0
ا 1
ب 2
پ 3
ت 4
ث 5
ج 6
چ 7
ح 8
خ 9
د 10
ذ 11
ر 12
ز 13
ژ 14
س 15
ش 16
ص 17
ض 18
ط 19
ظ 20
ع 21
غ 22
ف 23
ق 24
ک 25
گ 26
ل 27
م 28
ن 29
و 30
ه 31
ی 32
آ 33
' 34

"""

char_map = {}
index_map = {}

for line in char_map_str.strip().split('\n'):
    ch, index = line.split()
    char_map[ch] = int(index)
    index_map[int(index)] = ch

index_map[0] = ' '

def int_to_text_sequence(seq):
    """ Use a index map and convert int to a text sequence
        >>> from utils import int_to_text_sequence
        >>> a = [2,22,10,11,21,2,13,11,6,1,21,2,8,20,17]
        >>> b = int_to_text_sequence(a)
    """
    text_sequence = []
    for c in seq:
        if c == 35: #ctc/pad char
            ch = ''
        else:
            ch = index_map[c]
        text_sequence.append(ch)
    return text_sequence

def selu(x):
    # from Keras 2.0.6 - does not exist in 2.0.4
    """Scaled Exponential Linear Unit. (Klambauer et al., 2017)
    # Arguments
       x: A tensor or variable to compute the activation function for.
    # References
       - [Self-Normalizing Neural Networks](https://arxiv.org/abs/1706.02515)
    """
    alpha = 1.6732632423543772848170429916717
    scale = 1.0507009873554804934193349852946
    return scale * K.elu(x, alpha)

def clipped_relu(x):
    return relu(x, max_value=20)

def ctc_lambda_func(args):
    y_pred, labels, input_length, label_length = args
    return K.ctc_batch_cost(labels, y_pred, input_length, label_length)

def ctc(y_true, y_pred):
    return y_pred

def load_model_checkpoint(path, summary=True):
    get_custom_objects().update({"clipped_relu": clipped_relu})
    get_custom_objects().update({"selu": selu})

    jsonfilename = path + ".json"
    weightsfilename = path + ".h5"

    json_file = open(jsonfilename, 'r')
    loaded_model_json = json_file.read()
    json_file.close()

    K.set_learning_phase(1)
    loaded_model = model_from_json(loaded_model_json)

    # load weights into loaded model
    loaded_model.load_weights(weightsfilename)
    return loaded_model

def wer(original, result):
    r"""
    The WER is defined as the editing/Levenshtein distance on word level
    divided by the amount of words in the original text.
    In case of the original having more words (N) than the result and both
    being totally different (all N words resulting in 1 edit operation each),
    the WER will always be 1 (N / N = 1).
    """
    # The WER ist calculated on word (and NOT on character) level.
    # Therefore we split the strings into words first:
    original = original.split()
    result = result.split()
    return levenshtein(original, result) / float(len(original))

def wers(originals, results):
    count = len(originals)
    try:
        assert count > 0
    except:
        print(originals)
        raise("ERROR assert count>0 - looks like data is missing")
    rates = []
    mean = 0.0
    assert count == len(results)
    for i in range(count):
        rate = wer(originals[i], results[i])
        mean = mean + rate
        rates.append(rate)
    return rates, mean / float(count)

def decode(test_func, words):
    ret = []
    output = test_func([words])[0]
    greedy = True
    merge_chars = True
    if greedy:
        out = output[0]
        best = list(np.argmax(out, axis=1))
        if merge_chars:
            merge = [k for k,g in itertools.groupby(best)]
        else:
            raise ("not implemented no merge")
    else:
        pass
        raise("not implemented beam")
    try:
        outStr = int_to_text_sequence(merge)
    except Exception as e:
        print("Unrecognised character on decode error:", e)
        outStr = "DECODE ERROR:"+str(best)
        raise("DECODE ERROR2")
    ret.append(''.join(outStr))
    return ret

def make_mfcc(filename, padlen=1000):
    fs, audio = wav.read(filename)
    r = p.mfcc(audio, samplerate=fs, numcep=26)
    t = np.transpose(r)
    X = pad_sequences(t, maxlen=padlen, dtype='float', padding='post', truncating='post').T
    return X

def load_model(model_path):
    model = load_model_checkpoint(model_path, summary=False)
    opt = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True, clipnorm=5)
    model.compile(optimizer=opt, loss=ctc)
    y_pred = model.get_layer('ctc').input[0]
    input_data = model.get_layer('the_input').input
    K.set_learning_phase(0)
    return K.function([input_data, K.learning_phase()], [y_pred])

def asr(model, file_name):
    X_data = make_mfcc(file_name, padlen=1000)
    decoded_res = decode(model, X_data[None,...])[0]
    # corrected = correction(decoded_res)
    corrected = decoded_res
    # K.clear_session()
    return u"{}".format(corrected).encode('utf-8')

# The following code is from: http://hetland.org/coding/python/levenshtein.py
def levenshtein(a, b):
    "Calculates the Levenshtein distance between a and b."
    n, m = len(a), len(b)
    if n > m:
        # Make sure n <= m, to use O(min(n,m)) space
        a,b = b,a
        n,m = m,n

    current = list(range(n+1))
    for i in range(1,m + 1):
        previous, current = current, [i]+[0]*n
        for j in range(1,n + 1):
            add, delete = previous[j] + 1, current[j-1] + 1
            change = previous[j-1]
            if a[j-1] != b[i-1]:
                change = change + 1
            current[j] = min(add, delete, change)

    return current[n]

def words(text):
    "List of words in text."
    return re.findall(r'\w+', text.lower(), flags=re.U)


def log_probability(sentence):
    "Log base 10 probability of `sentence`, a list of words"
    return MODEL.score(' '.join(sentence), bos=False, eos=False)


def correction(sentence):
    "Most probable spelling correction for sentence."
    BEAM_WIDTH = 1024
    layer = [(0, [])]
    for word in words(sentence):
        layer = [(-log_probability(node + [cword]), node + [cword]) for cword in candidate_words(word) for
                 priority, node in layer]
        heapify(layer)
        layer = layer[:BEAM_WIDTH]
    return ' '.join(layer[0][1])


def candidate_words(word):
    "Generate possible spelling corrections for word."
    return (known_words([word]) or known_words(edits1(word)) or known_words(edits2(word)) or [word])


def known_words(words):
    "The subset of `words` that appear in the dictionary of WORDS."
    return set(w for w in words if w in WORDS)


def edits1(word):
    "All edits that are one edit away from `word`."
    # letters = 'abcdefghijklmnopqrstuvwxyz'
    letters = u'ابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهیآ'
    splits = [(word[:i], word[i:]) for i in range(len(word) + 1)]
    deletes = [L + R[1:] for L, R in splits if R]
    transposes = [L + R[1] + R[0] + R[2:] for L, R in splits if len(R) > 1]
    replaces = [L + c + R[1:] for L, R in splits if R for c in letters]
    inserts = [L + c + R for L, R in splits for c in letters]
    return set(deletes + transposes + replaces + inserts)

def edits2(word):
    "All edits that are two edits away from `word`."
    return (e2 for e1 in edits1(word) for e2 in edits1(e1))

# Load known word set
with open('./models/text') as f:
    WORDS = set(words(f.read().decode("utf-8", "ignore")))
