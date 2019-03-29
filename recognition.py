# -*- coding: utf8 -*-
import sys
import subprocess
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"]="3"
os.environ["PBR_VERSION"]='4.0.2'

import asr
import json
import prompt
import config
import numpy as np
import spkver_server as api
from flask import Response
from log import set_log
from datetime import datetime, timedelta
from utils import generate_voiceprint, session_scope
from sqlalchemy import desc
from flask_api import status
from db_interface import Prompts, Users, Requests, References, Evaluations
from sqlalchemy.sql.expression import func
from kaldi_io import write_vec_flt

logger = config.logging.getLogger(__name__)

asr_model = asr.load_model('./models/model')


def get_prompt(args):
    with session_scope() as session:
        try:
            if not ('username' in args and args['username']):
                set_log(
                    None,
                    "recognition/prompt",
                    "required field not provided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("required field not provided")
                return Response(
                    json.dumps({"error": "required field not provided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            user = session.query(Users).filter_by(username=args['username'], active=True).first()
            if not user:
                set_log(
                    None,
                    "recognition/prompt",
                    "username {} not active".format(args['username']),
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("username {} not active".format(args['username']))
                return Response(
                    json.dumps({"error": "username not active"}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

            if not user._references:
                set_log(
                    user.username,
                    "recognition/prompt",
                    "user is not enrolled",
                    status.HTTP_417_EXPECTATION_FAILED,
                    session)
                logger.error("user is not enrolled")
                return Response(
                    json.dumps({"error": "user is not enrolled yet!"}),
                    status=status.HTTP_417_EXPECTATION_FAILED,
                    mimetype='application/json')

            request = session.query(Requests).filter_by(
                username=args['username'],
                status=status.HTTP_201_CREATED).first()
            if request:
                if request.expiration > datetime.now():
                    set_log(
                        user.username,
                        "recognition/prompt",
                        "request is in progress",
                        status.HTTP_429_TOO_MANY_REQUESTS,
                        session)
                    logger.error("request is in progress")
                    return Response(
                        json.dumps({'error': 'request is in progress'}),
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                        mimetype='application/json')
                else:
                    request.status = status.HTTP_408_REQUEST_TIMEOUT
                    request.last_edited_date = datetime.now()

            prompts = session.query(Prompts).order_by(func.rand()).slice(0, int(config.general.word_count)).all()

            request = Requests()
            request.status = status.HTTP_201_CREATED
            request.username = user.username
            request.prompt = ' '.join([prompt.text for prompt in prompts])
            request.expiration = datetime.now() + timedelta(seconds=int(config.general.request_expiration))
            request.created_date = datetime.now()
            
            session.add(request)
            session.commit()

            set_log(
                user.username,
                "recognition/prompt",
                "Propmt: " + request.prompt,
                status.HTTP_200_OK,
                session)
            logger.info(request.prompt)
            return Response(
                json.dumps({"msg": {"prompt": request.prompt}}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                None,
                "recognition/prompt",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')                


def identify(args, files):
    with session_scope() as session:
        try:
            if not ('username' in args and args['username']):
                set_log(
                    None,
                    "recognition/identify",
                    "username not found",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("username not found")
                return Response(
                    json.dumps({"error": "username not found"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            if not ('audio' in files and files['audio'] and files['audio'].filename):
                set_log(
                    None,
                    "recognition/identify",
                    "file not found",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("file not found")
                return Response(
                    json.dumps({"error": "file not found"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')
            
            user = session.query(Users).filter_by(username=args['username'], active=True).first()
            if not user:
                set_log(
                    None,
                    "recognition/identify",
                    "invalid username",
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("invalid username")
                return Response(
                    json.dumps({"error": "invalid username"}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

            request = session.query(Requests).filter_by(
                username=args['username'],
                status=status.HTTP_201_CREATED).first()
            if request:
                if request.expiration > datetime.now():
                    set_log(
                        user.username,
                        "recognition/identify",
                        "request is in progress",
                        status.HTTP_429_TOO_MANY_REQUESTS,
                        session)
                    logger.error("request is in progress")
                    return Response(
                        json.dumps({'error': 'request is in progress'}),
                        status=status.HTTP_429_TOO_MANY_REQUESTS,
                        mimetype='application/json')
                else:
                    request.status = status.HTTP_408_REQUEST_TIMEOUT
                    request.last_edited_date = datetime.now()

            request = Requests()
            request.status = status.HTTP_201_CREATED
            request.username = user.username
            request.prompt = args['prompt'] if 'prompt' in args and args['prompt'] else None
            request.expiration = datetime.now() + timedelta(seconds=int(config.general.request_expiration))
            request.created_date = datetime.now()
            request.last_edited_date = datetime.now()
            
            session.add(request)
            session.commit()
            audio_type =  (files['audio'].content_type).split('/')[1]
            if files['audio'].content_type in ["audio/wav","audio/wave", "audio/mpeg","audio/ogg", "audio/x-flac", "audio/x-ms-wma",
                                                "audio/flac", "video/3gpp", "audio/au", "audio/opus", "application/octet-stream", "audio/mp4"]:
                audio_ext = audio_ext = os.path.splitext(files['audio'].filename)[1]
                file_path = os.path.join(
                    api.app.config['UPLOAD_FOLDER'],
                    'identify_' + request.username + '_' + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + audio_ext)
                files['audio'].save(file_path)
                voiceprint = generate_voiceprint(file_path, audio_type)
                if voiceprint is None:
                    set_log(
                        request.username,
                        "recognition/identify",
                        "voiceprint can not be computed",
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                        session)
                    logger.error("voiceprint can not be computed")
                    return Response(
                        json.dumps({"error": "voiceprint can not be computed"}),
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        mimetype='application/json')

            else:
                request.status = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
                request.last_edited_date = datetime.now()
                set_log(
                    request.username,
                    "recognition/identify",
                    "audio file not supported",
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    session)
                logger.error("audio file not supported")
                return Response(
                    json.dumps({"error": "audio file not supported"}),
                    status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    mimetype='applicatoin/json')  
            
            evaluation = Evaluations()
            evaluation.request_id = request.id
            evaluation.audio = file_path
            evaluation.file_id = args['file_id'] if 'file_id' in args and args['file_id'] else None
            evaluation.file_id = args['message_id'] if 'message_id' in args and args['message_id'] else None
            evaluation.voiceprint = json.dumps(voiceprint)
            evaluation.created_date = datetime.now()
            evaluation.size = os.stat(file_path).st_size
            session.add(evaluation)
            
            user_type = args['type'] if 'type' in args and args['type'] else "user"

            users = session.query(Users).filter_by(active=True,type=user_type).filter(
                Users._references.any(References.voiceprint != None)).all()
            results = []
            if users:
                info, models = {}, {}   
                for user in users:
                    models[user.username] = np.average([json.loads(ref.voiceprint) for ref in user._references], axis=0)
                    info[user.username] = {
                        'fullname': user.fullname, 
                        'file_id': user._references[0].file_id,
                        'ref_id': user._references[0].id,
                        'avatar_id':  user.avatar}

                scores = verification_score(models, {request.username: np.array(voiceprint)})
                if scores is None:
                    set_log(
                        request.username,
                        "recognition/identify",
                        "score can not be computed",
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                        session)
                    logger.error("score can not be computed")
                    return Response(
                        json.dumps({"error": "score can not be computed"}),
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        mimetype='application/json')

                scores = scores.split()
                a = float(config.general.identify_a)
                b = float(config.general.identify_b)
                for i in range(0, len(scores), 3):
                    score = float(scores[i + 2])
                    if score > float(config.general.identify_theshold):
                        results.append({
                            'username': scores[i],
                            'fullname': info[scores[i]]['fullname'],
                            'file_id': info[scores[i]]['file_id'],
                            'ref_id': info[scores[i]]['ref_id'],
                            'avatar_id': info[scores[i]]['avatar_id'],
                            'score': round( 100. / (1. + np.exp( -1. * a * (score - b))), 2) })
                    if len(results) >= int(config.general.identify_maxcount):
                        break

            request.status = status.HTTP_200_OK
            request.last_edited_date = datetime.now()

            if results:
                set_log(
                    request.username,
                    "recognition/identify",
                    "identify " + scores[0] + ": " + scores[2],
                    status.HTTP_200_OK,
                    session)
                logger.info("identify " + scores[0] + ": " + scores[2])
            else:
                set_log(
                    request.username,
                    "recognition/identify",
                    "no results",
                    status.HTTP_200_OK,
                    session)
                logger.info("no results")

            return Response(
                json.dumps({"msg": {"results": results}}),
                status=status.HTTP_200_OK,
                mimetype='applicatoin/json')

        except Exception as e:
            set_log(
                None,
                "recognition/identify",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def authentication(args, files):
    with session_scope() as session:
        try:
            if not ('username' in args and args['username']):
                set_log(
                    None,
                    "recognition/authenticate",
                    "required field is not provided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("required field is not provided")
                return Response(
                    json.dumps({"error": "required field is not provided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')
            if not ('audio' in files and files['audio'] and files['audio'].filename):
                set_log(
                    None,
                    "recognition/authenticate",
                    "file not found",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("file not found")
                return Response(
                    json.dumps({"error": "file not found"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            request = session.query(Requests).filter_by(
                username=args['username'],
                status=status.HTTP_201_CREATED).first()
            if not request:
                set_log(
                    None,
                    "recognition/authenticate",
                    "invalid request",
                    status.HTTP_401_UNAUTHORIZED,
                    session)
                logger.error("invalid request")
                return Response(
                    json.dumps({"error": "invalid request"}),
                    status=status.HTTP_401_UNAUTHORIZED,
                    mimetype='application/json')

            if request.expiration < datetime.now():
                request.status = status.HTTP_408_REQUEST_TIMEOUT
                request.last_edited_date = datetime.now()
                set_log(
                    request.username,
                    "recognition/authenticate",
                    "request time out",
                    status.HTTP_408_REQUEST_TIMEOUT,
                    session)
                logger.error("request time out")
                return Response(
                    json.dumps({"error": "request time out"}),
                    status=status.HTTP_408_REQUEST_TIMEOUT,
                    mimetype='application/json')

            if files['audio'].content_type in ["audio/wav", "audio/wave"]:
                file_path = os.path.join(
                    api.app.config['UPLOAD_FOLDER'],
                    'auth_' + request.username + '_' + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.wav')
                
                files['audio'].save(file_path)
                audio_type =  (files['audio'].content_type).split('/')[1]
                voiceprint = generate_voiceprint(file_path, audio_type)

                if voiceprint is None:
                    set_log(
                        request.username,
                        "recognition/authenticate",
                        "voiceprint can not be computed",
                        status.HTTP_500_INTERNAL_SERVER_ERROR,
                        session)
                    logger.error("voiceprint can not be computed")
                    return Response(
                        json.dumps({"error": "voiceprint can not be computed"}),
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        mimetype='application/json')
            else:
                set_log(
                    request.username,
                    "recognition/authenticate",
                    "audio file not supported",
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    session)
                logger.error("audio file not supported")
                return Response(
                    json.dumps({"error": "audio file not supported"}),
                    status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    mimetype='applicatoin/json')  

            evaluation = Evaluations()
            evaluation.request_id = request.id
            evaluation.audio = file_path
            evaluation.voiceprint = json.dumps(voiceprint)
            evaluation.created_date = datetime.now()
            evaluation.size = os.stat(file_path).st_size
            session.add(evaluation)
            session.commit()

            spoof_status = check_spoof(request)
            asr_status, wer, transcription = check_asr(request)
            
            model = np.average([json.loads(ref.voiceprint) for ref in request._user._references], axis=0)
            score = verification_score(
                {request.username: model},
                {'evaluation': np.array(voiceprint)})
                
            if score is None:
                set_log(
                    request.username,
                    "recognition/authenticate",
                    "score can not be computed",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    session)
                logger.error("score can not be computed")
                return Response(
                    json.dumps({"error": "score can not be computed"}),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    mimetype='application/json')

            score = float(score.split()[-1])
            request.score = score
            asv_status = score > float(config.general.auth_threshold)

            if spoof_status:
                request.status = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
            elif not asr_status:
                request.status = status.HTTP_203_NON_AUTHORITATIVE_INFORMATION
            elif not asv_status:
                request.status = status.HTTP_401_UNAUTHORIZED
            else:
                request.status = status.HTTP_202_ACCEPTED
                if score > float(config.general.auth_add_model):
                    query = session.query(References).filter_by(username=request.username, type='evaluation')
                    if query.count() >= int(config.general.auth_add_count):
                        query = query.order_by(desc(References.created_date)).all()
                        for row in query[int(config.general.auth_add_count)-1:]:
                            session.delete(row)

                    reference = References()
                    reference.username = request.username
                    reference.prompt = request.prompt
                    reference.audio = file_path
                    reference.type = 'eval'
                    reference.voiceprint = json.dumps(voiceprint)
                    reference.created_admin = 'admin'
                    reference.last_edited_admin = 'admin'
                    reference.created_date = datetime.now()
                    reference.last_edited_date = datetime.now()
                    session.add(reference)

            request.last_edited_date = datetime.now()

            set_log(
                request.username,
                "recognition/authenticate",
                "status: {}, wer: {}, score:{}, spoof:{}".format(request.status, round(wer * 100, 0), round(score, 2), False),
                request.status,
                session)
            logger.info("status: {}, wer: {}, score:{}, spoof:{}".format(request.status, round(wer * 100, 0), round(score, 2), False))
            return Response(
                json.dumps({"msg": {"status": request.status}}),
                status=status.HTTP_200_OK,
                mimetype='applicatoin/json')  

        except Exception as e:
            set_log(
                None,
                "recognition/authenticate",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def check_spoof(request):
    return False


def check_asr(request):
    transcription = asr.asr(asr_model, request._evaluation.audio).decode('utf8')
    logger.info("Transcription: " + transcription)
    wer = np.clip(asr.wer(request.prompt, transcription), 0, 1)
    if wer > float(config.general.wer):
        return False, wer, transcription

    return True, wer, transcription


def verification_score(enroll, test):
    try:
        data_path = '/tmp/.tmp' + str(100000 + np.random.randint(100000)) + '/'
        os.makedirs(os.path.dirname(data_path))
        with open(data_path + '/xvector_enroll.ark', 'w') as f:
            for key in enroll:
                write_vec_flt(f, enroll[key], key=key)
        with open(data_path + '/xvector_test.ark','w') as f:
            for key in test:
                write_vec_flt(f, test[key], key=key)
        with open(data_path + '/trials','w') as f:
            for ekey in enroll:
                for tkey in test:
                    f.write(ekey + " " + tkey + "\n")
    except:
        return None
    
    results = subprocess.Popen(
        ['bash', os.getcwd() + '/scoring.sh', data_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    score, err = results.communicate()
    if err:
        return None
    return score
