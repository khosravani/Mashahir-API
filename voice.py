
import json
import time
import os
import config
import spkver_server as api
from sqlalchemy.orm import load_only
from db_interface import Requests, References, Evaluations, Users
from datetime import datetime
from flask import send_file, Response
from flask_api import status
from log import set_log
from utils import session_scope, generate_voiceprint
from sqlalchemy import desc, asc, func
from sqlalchemy.ext import baked

logger = config.logging.getLogger(__name__)


def enrollment(args, files, current_user):
    with session_scope() as session:
        try:
            if not all(k in args and args[k] for k in ('username', 'prompt')):
                set_log(
                    current_user,
                    "voice/enroll",
                    "required fields not provided", 
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("required fields not provided")
                return Response(
                    json.dumps({'error': 'required fields not provided'}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            if not ('audio' in files and files['audio'] and files['audio'].filename):
                set_log(
                    current_user,
                    "voice/enroll",
                    "file not found", 
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("file not found")
                return Response(
                    json.dumps({'error': 'file not found'}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

            user = session.query(Users).filter_by(username=args['username'], active=True).first()
            if not user:
                set_log(
                    current_user,
                    "voice/enroll",
                    "user not found", 
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("user not found")
                return Response(
                    json.dumps({'error': 'user not found'}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

            if files['audio'].content_type in ["audio/wav", "audio/wave"]:
                reference = References()
                reference.username = args['username']
                reference.prompt = args['prompt']
                reference.type = 'reference'
                reference.audio = os.path.join(
                    api.app.config['UPLOAD_FOLDER'], 
                    'enroll_' + args['username'] + '_' + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + '.wav')
                files['audio'].save(reference.audio)
                reference.size = os.stat(reference.audio).st_size
            else:
                set_log(
                    current_user,
                    "voice/enroll",
                    "audio file not supported",
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    session)
                logger.error("audio file not supported")
                return Response(
                    json.dumps({"error": "audio file not supported"}),
                    status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    mimetype='applicatoin/json')      
            audio_type =  (files['audio'].content_type).split('/')[1]
            model = generate_voiceprint(reference.audio, audio_type)
            if model is None:
                set_log(
                    current_user,
                    "voice/enroll",
                    "voiceprint can not be computed",
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    session)
                logger.error("voiceprint can not be computed")
                return Response(
                    json.dumps({"error": "voiceprint can not be computed"}),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    mimetype='application/json')

            reference.voiceprint = json.dumps(model)
            reference.created_admin = current_user
            reference.last_edited_admin = current_user
            reference.created_date = datetime.now()
            reference.last_edited_date = datetime.now()
            session.add(reference)

            set_log(
                current_user,
                "voice/enroll",
                "user enrolled",
                status.HTTP_200_OK,
                session)
            logger.info("user enrolled")
            return Response(
                json.dumps({"msg": {'id': reference.id}}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "voice/enroll",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def download_reference(args, current_user):
    with session_scope() as session:
        try:
            if not ('id' in args and args['id']):
                set_log(
                    current_user,
                    "voice/ref/download",
                    "required field is not porvided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("required field is not porvided")
                return Response(
                    json.dumps({"error": "required field is not porvided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            try:
                id = int(args['id'])
                pass
            except:
                set_log(
                    current_user,
                    "voice/ref/download",
                    "not a valid input value",
                    status.HTTP_406_NOT_ACCEPTABLE,
                    session)
                logger.error("not a valid input value")
                return Response(
                    json.dumps({"error": "not a valid input value"}),
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                    mimetype='application/json')

            reference = session.query(References).filter_by(id=id).first()
            if not (reference and os.path.exists(reference.audio)):
                set_log(
                    current_user,
                    "voice/ref/download",
                    "audio file not found",
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("audio file not found")
                return Response(
                    json.dumps({"error": "audio file not found"}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

            set_log(
                current_user,
                "voice/ref/download",
                "audio file sent",
                status.HTTP_200_OK,
                session)
            logger.info("audio file sent")
            return send_file(reference.audio, as_attachment=True)

        except Exception as e:
            set_log(
                current_user,
                "voice/ref/download",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def list_references(args, current_user):
    with session_scope() as session:
        try:
            query = session.query(References)
            if 'username' in args and args['username']:
                query = query.filter(References.username.like('%' + args['username'] + '%'))
            
            if 'prompt' in args and args['prompt']:
                query = query.filter(References.prompt.like('%' + args['prompt'] + '%'))
            
            if 'type' in args and args['type'] and isinstance(args['type'], list):
                query = query.filter(References.type.in_(args['type']))

            if 'dur_from' in args and args['dur_from']:
                query = query.filter(References.dur >= float(args['dur_from']))
            if 'dur_to' in args and args['dur_to']:
                query = query.filter(References.dur < float(args['dur_to']))
            
            if 'size_from' in args and args['size_from']:
                query = query.filter(References.size >= float(args['size_from']))
            if 'size_to' in args and args['size_to']:
                query = query.filter(References.size < float(args['size_to']))

            if 'created_admin' in args and args['created_admin']:
                query = query.filter(References.created_admin.like('%' + args['created_admin'] + '%'))

            if 'created_date_from' in args and args['created_date_from']:
                st_date = datetime.fromtimestamp(int(args['created_date_from']))
                query = query.filter(References.created_date > st_date)
            if 'created_date_to' in args and args['created_date_to']:
                ed_date = datetime.fromtimestamp(int(args['created_date_to']))
                query = query.filter(References.created_date < ed_date)
    
            if 'last_edited_date_from' in args and args['last_edited_date_from']:
                st_date = datetime.fromtimestamp(int(args['last_edited_date_from']))
                query = query.filter(References.last_edited_date > st_date)
            if 'last_edited_date_to' in args and args['last_edited_date_to']:
                ed_date = datetime.fromtimestamp(int(args['last_edited_date_to']))
                query = query.filter(References.last_edited_date < ed_date)

            if 'sort_field' in args and args['sort_field'] in [c.key for c in References.__table__.c]:
                field = getattr(References, args['sort_field'])
            else:
                field = References.id

            if 'sort_order' in args and args['sort_order'] == "asc":
                field = asc(field)
            else:
                field = desc(field)

            query = query.order_by(field)
            count = query.count()

            if 'per_page' in args and args['per_page'] and 'page_num' in args and args['page_num']:
                query = query.slice((int(args['page_num']) - 1) * int(args['per_page']),
                                    int(args['page_num']) * int(args['per_page']))
            else:
                query = query.slice(0, 10)

            query = query.all()

            references = []
            for ref in query:
                references.append({
                    'id': ref.id,
                    'username': ref.username,
                    'prompt': ref.prompt,
                    'voiceprint': ref.voiceprint is not None,
                    'size': ref.size,
                    'type': ref.type,
                    'created_admin': ref.created_admin,
                    'created_date': time.mktime(ref.created_date.timetuple()) if ref.created_date else None,
                    'last_edited_admin': ref.last_edited_admin,
                    'last_edited_date': time.mktime(ref.last_edited_date.timetuple()) if ref.last_edited_date else None
                })

            set_log(
                current_user,
                "voice/ref/list",
                "references listed",
                status.HTTP_200_OK,
                session)
            logger.info("references listed")
            return Response(
                json.dumps({"msg": {"references": references, "count": count}}), 
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "voice/ref/list",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.info("operation failed in server side")
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def remove_references(args, current_user):
    with session_scope() as session:
        try:
            if not ('ids' in args and args['ids']):
                set_log(
                    current_user,
                    "voice/ref/remove",
                    "required field is not porvided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("required field is not porvided")
                return Response(
                    json.dumps({"error": "required field is not porvided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')
            
            try:
                ids = [int(id) for id in args['ids'].split(',')]
                pass
            except:
                set_log(
                    current_user,
                    "voice/ref/remove",
                    "not a valid input",
                    status.HTTP_417_EXPECTATION_FAILED,
                    session)
                logger.error("not a valid input")
                return Response(
                    json.dumps({"error": "not a valid input"}),
                    status=status.HTTP_417_EXPECTATION_FAILED,
                    mimetype='application/json')

            references = session.query(References).filter(References.id.in_(ids)).all()
            if not references:
                set_log(
                    current_user,
                    "voice/ref/remove",
                    "reference ids not found",
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("reference ids not found")
                return Response(
                    json.dumps({'msg': "reference ids not found"}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

            for ref in references:
                session.delete(ref)
            
            set_log(
                current_user,
                "voice/ref/remove",
                "reference ids removed",
                status.HTTP_200_OK,
                session)
            logger.info("reference ids removed")
            return Response(
                json.dumps({'msg': 'reference ids removed'}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "voice/ref/remove",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def update_references(current_user):
    with session_scope() as session:
        try:
            references = session.query(References).all()
            for ref in references:
                if ref.audio and os.path.exists(ref.audio):
                    model = generate_voiceprint(ref.audio)
                    if model is None:
                        set_log(
                            current_user,
                            "voice/ref/update",
                            "voiceprint can not be computed",
                            status.HTTP_500_INTERNAL_SERVER_ERROR,
                            session)
                        logger.error("voiceprint can not be computed")
                        return Response(
                            json.dumps({"error": "voiceprint can not be computed"}),
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            mimetype='application/json')
                            
                    ref.voiceprint = json.dumps(model)
                    ref.last_edited_admin = current_user
                    ref.last_edited_date = datetime.now()

            set_log(
                current_user,
                "voice/ref/update",
                "models updated",
                status.HTTP_200_OK,
                session)
            logger.info("models updated")
            return Response(
                json.dumps({"msg": {}}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "voice/ref/update",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def download_evaluation(args, current_user):
    with session_scope() as session:
        try:
            if not ('id' in args and args['id']):
                set_log(
                    current_user,
                    "voice/eval/download",
                    "required field is not porvided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("required field is not porvided")
                return Response(
                    json.dumps({"error": "required field is not porvided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            try:
                id = int(args['id'])
                pass
            except:
                set_log(
                    current_user,
                    "voice/eval/download",
                    "not a valid input value",
                    status.HTTP_406_NOT_ACCEPTABLE,
                    session)
                logger.error("not a valid input value")
                return Response(
                    json.dumps({"error": "not a valid input value"}),
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                    mimetype='application/json')

            evaluation = session.query(Evaluations).filter_by(id=id).first()
            if not (evaluation and os.path.exists(evaluation.audio)):
                set_log(
                    current_user,
                    "voice/eval/download",
                    "audio file not found",
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("audio file not found")
                return Response(
                    json.dumps({"error": "audio file not found"}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

            set_log(
                current_user,
                "voice/eval/download",
                "audio file sent",
                status.HTTP_200_OK,
                session)
            logger.info("audio file sent")
            return send_file(evaluation.audio, as_attachment=True)

        except Exception as e:
            set_log(
                current_user,
                "voice/eval/download",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def list_evaluations(args, current_user):
    with session_scope() as session:
        try:
            query = session.query(Evaluations)
            if 'username' in args and args['username']:
                query = query.filter(Evaluations._request.has(Requests.username.like('%' + args['username'] + '%')))
            
            if 'prompt' in args and args['prompt']:
                query = query.filter(Evaluations._request.has(Requests.prompt.like('%' + args['prompt'] + '%')))
            
            if 'status' in args and args['status']:
                query = query.filter(Evaluations._request.has(Requests.status == int(args['status'])))

            if 'dur_from' in args and args['dur_from']:
                query = query.filter(Evaluations.dur >= float(args['dur_from']))
            if 'dur_to' in args and args['dur_to']:
                query = query.filter(Evaluations.dur < float(args['dur_to']))
            
            if 'size_from' in args and args['size_from']:
                query = query.filter(Evaluations.size >= float(args['size_from']))
            if 'size_to' in args and args['size_to']:
                query = query.filter(Evaluations.size < float(args['size_to']))

            if 'created_date_from' in args and args['created_date_from']:
                st_date = datetime.fromtimestamp(int(args['created_date_from']))
                query = query.filter(Evaluations.created_date > st_date)
            if 'created_date_to' in args and args['created_date_to']:
                ed_date = datetime.fromtimestamp(int(args['created_date_to']))
                query = query.filter(Evaluations.created_date < ed_date)
            
            if 'last_edited_date_from' in args and args['last_edited_date_from']:
                st_date = datetime.fromtimestamp(int(args['last_edited_date_from']))
                query = query.filter(Evaluations.last_edited_date > st_date)
            if 'last_edited_date_to' in args and args['last_edited_date_to']:
                ed_date = datetime.fromtimestamp(int(args['last_edited_date_to']))
                query = query.filter(Evaluations.last_edited_date < ed_date)

            if 'sort_field' in args and args['sort_field'] in [c.key for c in Evaluations.__table__.c]:
                field = getattr(Evaluations, args['sort_field'])
            else:
                field = Evaluations.id

            if 'sort_order' in args and args['sort_order'] == "asc":
                field = asc(field)
            else:
                field = desc(field)

            query = query.order_by(field)
            count = query.count()

            if 'per_page' in args and args['per_page'] and 'page_num' in args and args['page_num']:
                query = query.slice((int(args['page_num']) - 1) * int(args['per_page']),
                                    int(args['page_num']) * int(args['per_page']))
            else:
                query = query.slice(0, 10)

            query = query.all()

            evaluations = []
            for evaluation in query:
                evaluations.append({
                    'id': evaluation.id,
                    'username': evaluation._request.username,
                    'prompt': evaluation._request.prompt,
                    'voiceprint': evaluation.voiceprint is not None,
                    'size': evaluation.size,
                    'status': evaluation._request.status,
                    'created_date': time.mktime(evaluation.created_date.timetuple()) if evaluation.created_date else None,
                    'last_edited_date': time.mktime(evaluation.last_edited_date.timetuple()) if evaluation.last_edited_date else None,
                })

            set_log(
                current_user,
                "voice/eval/list",
                "evaluations listed",
                status.HTTP_200_OK,
                session)
            logger.info("evaluations listed")
            return Response(
                json.dumps({"msg": {"evaluations": evaluations, "count":count}}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "voice/eval/list",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def remove_evaluations(args, current_user):
    with session_scope() as session:
        try:
            if not ('ids' in args and args['ids']):
                set_log(
                    current_user,
                    "voice/eval/remove",
                    "required field is not porvided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("required field is not porvided")
                return Response(
                    json.dumps({"error": "required field is not porvided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')
            
            try:
                ids = [int(id) for id in args['ids'].split(',')]
                pass
            except:
                set_log(
                    current_user,
                    "voice/eval/remove",
                    "not a valid input",
                    status.HTTP_417_EXPECTATION_FAILED,
                    session)
                logger.error("not a valid input")
                return Response(
                    json.dumps({"error": "not a valid input"}),
                    status=status.HTTP_417_EXPECTATION_FAILED,
                    mimetype='application/json')

            evaluations = session.query(Evaluations).filter(Evaluations.id.in_(ids)).all()
            if not evaluations:
                set_log(
                    current_user,
                    "voice/eval/remove",
                    "evaluation ids not found",
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("evaluation ids not found")
                return Response(
                    json.dumps({'msg': "evaluation ids not found"}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

            for evaluation in evaluations:
                session.delete(evaluation)
            
            set_log(
                current_user,
                "voice/eval/remove",
                "evaluation ids removed",
                status.HTTP_200_OK,
                session)
            logger.info("evaluation ids removed")
            return Response(
                json.dumps({'msg': 'evaluation ids removed'}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "voice/eval/remove",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')
