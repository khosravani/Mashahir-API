
import time
import json
import os
import re
import subprocess
import config
from datetime import datetime
from functools import wraps
from flask_api import status
from flask import Response
from contextlib import contextmanager
from db_interface import Session, Logs
logger = config.logging.getLogger(__name__)

username_regex = re.compile(r"""
    ^                       # beginning of string
    (?!_$)                  # no only _
    (?![-.])                # no - or . at the beginning
    (?!.*[_.-]{2})          # no __ or _. or ._ or .. or -- inside
    [a-zA-Z0-9_.#@!-]+         # allowed characters, atleast one must be present
    (?<![.-])               # no - or . at the end
    $                       # end of string
    """, re.X)

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def check_username(username):
    if len(username) not in range(5, 50) or not re.match(username_regex, username):
        return False
    return True

def check_password(password):

    """
    Verify the strength of 'password'
    Returns a dict indicating the wrong criteria
    A password is considered strong if:
        8 characters length or more
        1 digit or more OR 1 lowercase letter or more
        1 symbol or more
        1 uppercase letter or more

    """

    # calculating the length
    if len(password) < 8:
        return False, "password must have 8 characters length or more"

    # searching for uppercase
    elif re.search(r"[A-Z]", password) is None:
        return False, "password must contain at least one uppercase character"

    # searching for lowercase
    elif re.search(r"[a-z]", password) is None or re.search(r"\d", password) is None:
        return False, "password must contain at least one lowercase character or a digit"

    # searching for symbols
    elif re.search(r"[ !#$%&'()*+-./[\\\]^_{|}"+r'"]', password) is None:
        return False, "password must contain at least one symbol"

    return True, 'ok'

def generate_voiceprint(audio_path, audio_type):
    script = subprocess.Popen(
        ["bash", os.getcwd() + "/extract_model.sh", audio_path, config.general.voiceprint_port, audio_type],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    voiceprint, err = script.communicate()
    if not ('error' in voiceprint and err):
        try:
            voiceprint = [float(i) for i in voiceprint.split()]
            pass
        except:
            voiceprint = None
        return voiceprint
    else:
        return None