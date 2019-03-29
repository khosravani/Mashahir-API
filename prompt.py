
import json
import random
import config
from db_interface import Prompts
from datetime import datetime
from log import set_log
from utils import session_scope
from flask_api import status
from flask import Response
from sqlalchemy import asc, desc

logger = config.logging.getLogger(__name__)


def add_text(args, current_user):
    with session_scope() as session:
        try:
            if not ('text' in args and args['text']):
                set_log(
                    current_user,
                    "prompt/add",
                    "required field is not provided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.warning("required field is not provided")
                return Response(
                    json.dumps({"error": "required field is not provided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')
                    
            query = session.query(Prompts).filter_by(text=args['text']).first()
            if not query:
                prompt = Prompts()
                prompt.text = args['text']

                prompt.created_admin = current_user
                prompt.last_edited_admin = current_user
                prompt.created_date = datetime.now()
                prompt.last_edited_date = datetime.now()

                session.add(prompt)
                session.commit()

                set_log(
                    current_user,
                    "prompt/add",
                    "text added",
                    status.HTTP_200_OK,
                    session)
                logger.info("text added")
                return Response(
                    json.dumps({"msg": {"id": prompt.id}}),
                    status=status.HTTP_200_OK,
                    mimetype='application/json')
            else:
                set_log(
                    current_user,
                    "prompt/add",
                    "text already exists",
                    status.HTTP_409_CONFLICT,
                    session)
                logger.warning("text already exists")
                return Response(
                    json.dumps({"error": "text already exists"}),
                    status=status.HTTP_409_CONFLICT,
                    mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "prompt/add",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def remove_texts(args, current_user):
    with session_scope() as session:
        try:
            if not ('ids' in args and args['ids']):
                set_log(
                    current_user,
                    "prompt/remove",
                    "required field not provided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.warning("required field not provided")
                return Response(
                    json.dumps({"error": "required field not provided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            try:
                ids = [int(id) for id in args['ids'].split(',')]
                pass
            except:
                set_log(
                    current_user,
                    "prompt/remove",
                    "not a valid input",
                    status.HTTP_417_EXPECTATION_FAILED,
                    session)
                logger.warning("not a valid input")
                return Response(
                    json.dumps({"error": "not a valid input"}),
                    status=status.HTTP_417_EXPECTATION_FAILED,
                    mimetype='application/json')
                
            prompts = session.query(Prompts).filter(Prompts.id.in_(ids)).all()
            if prompts:
                for prompt in prompts:
                    session.delete(prompt)
                
                set_log(
                    current_user,
                    "prompt/remove",
                    "texts removed successfully",
                    status.HTTP_200_OK,
                    session)
                logger.warning("texts removed successfully")
                return Response(
                    json.dumps({'msg': {}}),
                    status=status.HTTP_400_BAD_REQUEST,
                    mimetype='application/json')

            else:
                set_log(
                    current_user,
                    "prompt/remove",
                    "no id found",
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.warning("no id found")
                return Response(
                    json.dumps({'error': 'no id found'}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "prompt/remove",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.warning(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def list_texts(args, current_user):
    with session_scope() as session:
        try:
            query = session.query(Prompts)
            if 'text' in args and args['text']:
                query = query.filter(Prompts.text.like('%' + args['text'] + '%'))

            if 'sort_field' in args and args['sort_field'] in [c.key for c in Prompts.__table__.c]:
                field = getattr(Prompts, args['sort_field'])
            else:
                field = Prompts.id

            if 'sort_order' in args and args['sort_order'] == "asc":
                field = asc(field)
            else:
                field = desc(field)

            query = query.order_by(field)
            count = query.count()

            if 'per_page' in args and args['per_page'] and 'page_num' in args and args['page_num']:
                query = query.slice((int(args['page_num']) - 1) * int(args['per_page']), int(args['page_num']) * int(args['per_page']))
            else:
                query = query.slice(0, 10)

            query = query.all()

            texts = []
            for prompt in query:
                texts.append({'id' : prompt.id, 'text': prompt.text})

            set_log(
                current_user,
                "prompts/list",
                "list texts",
                status.HTTP_200_OK,
                session)
            logger.info("list texts")
            return Response(
                json.dumps({"msg": {"texts": texts, "count": count}}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "prompt/list",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def get_text(current_user):
    with session_scope() as session:
        try:
            with open('models/long_texts') as f:
                texts = f.readlines()

            set_log(
                current_user,
                "prompts/ref",
                "get reference text",
                status.HTTP_200_OK,
                session)
            logger.info("get reference text")
            return Response(
                json.dumps({"msg": {"text": random.sample(texts, 1)}}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "prompt/ref",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def get_prompt(word_count=8):
    with session_scope() as session:
        texts = {}
        for prompt in session.query(Prompts).all():
            texts[prompt.id] = prompt.text

        count = len(texts)
        word_count = 8 if word_count > count else count

        prompt = []
        for id in random.sample(texts.keys(), word_count):
            prompt.append(texts[id])
        
        return Response(
            json.dumps({"msg": {"prompt": ' '.join(prompt)}}),
            status=status.HTTP_200_OK,
            mimetype='application/json')
