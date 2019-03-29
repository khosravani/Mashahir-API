
import json
import os
import time
import config
import spkver_server as api
from db_interface import Users
from flask import Response, send_file
from flask_api import status
from datetime import datetime

from log import set_log
from utils import check_username, session_scope
from sqlalchemy import or_, desc, asc


logger = config.logging.getLogger(__name__)

def add_user(args, files, current_user):
    with session_scope() as session:
        try:
            if not all(k in args and args[k] for k in ('username', 'fullname', 'type')):
                set_log(
                    current_user,
                    "user/add",
                    "required fields not provided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.warning("required fields not provided")
                return Response(
                    json.dumps({"error": "required fields not provided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            if not check_username(args['username']):
                set_log(
                    current_user,
                    "user/add",
                    "username is not valid",
                    status.HTTP_406_NOT_ACCEPTABLE,
                    session)
                logger.warning("required fields not provided")
                return Response(
                    json.dumps({"error": "username is not valid"}),
                    status=status.HTTP_406_NOT_ACCEPTABLE,
                    mimetype='applicatoin/json')

            user = session.query(Users).filter_by(username=args['username']).first()
            if not user:
                user = Users()
                user.created_admin = current_user
                user.created_date = datetime.now()

                user.fullname = args['fullname']
                user.username = args['username']
                user.type = args['type']

                if 'description' in args and args['description']:
                    user.description = args['description']

                if 'avatar' in files and files['avatar'] and files['avatar'].filename:
                    if files['avatar'].content_type in ['image/png', 'image/jpeg', 'image/jpg']:
                        ext = files['avatar'].content_type.rsplit('/', 1)[1].lower()
                        user.avatar = os.path.join(api.app.config['AVATAR_FOLDER'], args['username'] + '.' + ext)
                        files['avatar'].save(user.avatar)
                    else:
                        set_log(
                            current_user,
                            "user/add",
                            "avatar file not supported",
                            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            session)
                        logger.error("avatar file not supported")
                        return Response(
                            json.dumps({"error": "avatar file not supported"}),
                            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            mimetype='applicatoin/json')                        

                user.active = True
                user.last_edited_admin = current_user
                user.last_edited_date = datetime.now()

                session.add(user)
                session.commit()

                set_log(
                    current_user,
                    "user/add",
                    "user added",
                    status.HTTP_200_OK,
                    session)
                logger.info("user added")
                return Response(
                    json.dumps({"msg": {"id" :user.id}}),
                    status=status.HTTP_200_OK,
                    mimetype='application/json')

            else:
                set_log(
                    current_user,
                    "user/add",
                    "username is used",
                    status.HTTP_400_BAD_REQUEST,
                    session)
                logger.error("user added")
                return Response(
                    json.dumps({"error": "username is used"}), 
                    status=status.HTTP_400_BAD_REQUEST,
                    mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "user/add",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def remove_user(args, current_user):
    with session_scope() as session:
        try:
            if not ('username' in args and args['username']):
                set_log(
                    current_user,
                    "user/delete",
                    "username is required",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("username is required")
                return Response(
                    json.dumps({"error": "username is required"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            user = session.query(Users).filter_by(username=args['username']).first()
            if not user or user.username == 'root':
                set_log(
                    current_user,
                    "user/remove",
                    "user not found",
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("user not found")
                return Response(
                    json.dumps({'msg': "user not found"}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')
            else:
                session.delete(user)
                set_log(
                    current_user,
                    "user/remove",
                    "user removed",
                    status.HTTP_200_OK,
                    session)
                logger.error("user removed")
                return Response(
                    json.dumps({'msg': 'user removed'}),
                    status=status.HTTP_200_OK,
                    mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "user/remove",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def update_user(args, files, current_user):
    with session_scope() as session:
        try:
            if not ('username' in args and args['username']):
                set_log(
                    current_user,
                    "user/update",
                    "required field not provided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("required field not provided")
                return Response(
                    json.dumps({"error": "required field not provided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            user = session.query(Users).filter_by(username=args['username']).first()
            if user and user.username != 'root':
                if 'fullname' in args and args['fullname']:
                    user.fullname = args['fullname']
                if 'type' in args and args['type']:
                    user.type = args['type']
                if 'active' in args and args['active']:
                    user.active = bool(args['active'])
                if 'description' in args and args['description']:
                    user.description = args['description']
                # if 'avatar_id' in args and args['avatar_id']:
                #     user.avatar_id = args['avatar_id']

                if 'avatar' in files and files['avatar'] and files['avatar'].filename:
                    if files['avatar'].content_type in ['image/png', 'image/jpeg', 'image/jpg']:
                        ext = files['avatar'].content_type.rsplit('/', 1)[1].lower()
                        user.avatar = os.path.join(api.app.config['AVATAR_FOLDER'], args['username'] + '.' + ext)
                        files['avatar'].save(user.avatar)
                    else:
                        set_log(
                            current_user,
                            "user/update",
                            "avatar file type not supported",
                            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            session)
                        logger.error("avatar file type not supported")
                        return Response(
                            json.dumps({"error": "avatar file type not supported"}),
                            status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            mimetype='applicatoin/json')                        

                user.last_edited_admin = current_user
                user.last_edited_date = datetime.now()

                set_log(
                    current_user,
                    "user/update",
                    "user updated",
                    status.HTTP_200_OK,
                    session)
                logger.info("user updated")
                return Response(
                    json.dumps({"msg": {}}),
                    status=status.HTTP_200_OK,
                    mimetype='application/json')

            else:
                set_log(
                    current_user,
                    "user/update",
                    "username not found",
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.error("username not found")
                return Response(
                    json.dumps({"error": "username not found"}), 
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "user/update",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def list_users(args, current_user):
    with session_scope() as session:
        try:
            query = session.query(Users).filter_by(active=True)
            if 'fullname' in args and args['fullname']:
                query = query.filter(Users.fullname.like('%' + args['fullname'] + '%'))
            if 'username' in args and args['username']:
                query = query.filter(Users.username.like('%' + args['username'] + '%'))
            if 'type' in args and args['type']:
                query = query.filter(Users.type.like('%' + args['type'] + '%'))
            if 'active' in args and args['active']:
                query = query.filter(Users.active == bool(args['active']))
            if 'created_date_from' in args and args['created_date_from']:
                st_date = datetime.fromtimestamp(int(args['created_date_from']))
                query = query.filter(Users.created_date > st_date)
            if 'created_date_to' in args and args['created_date_to']:
                ed_date = datetime.fromtimestamp(int(args['created_date_to']))
                query = query.filter(Users.created_date < ed_date)

            if 'sort_field' in args and args['sort_field'] in [c.key for c in Users.__table__.c]:
                field = getattr(Users, args['sort_field'])
            else:
                field = Users.id

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

            users = []
            for user in query:
                users.append({
                    'username': user.username,
                    'fullname': user.fullname,
                    'type': user.type,
                    'active': user.active,
                    'description': user.description,
                    'created_admin': user.created_admin,
                    'created_date': time.mktime(user.created_date.timetuple()) if user.created_date else None,
                    'last_edited_admin': user.last_edited_admin,
                    'last_edited_date': time.mktime(user.last_edited_date.timetuple()) if user.last_edited_date else None,
                })

            set_log(
                current_user,
                "user/list",
                "list users",
                status.HTTP_200_OK,
                session)
            logger.info("list users")
            return Response(
                json.dumps({"msg": {"users": users, "count": count}}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "user/list",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def get_avatar(username):
    try:
        with session_scope() as session:
            if not username:
                set_log(
                    None,
                    "avatar/" + username,
                    "required field not provided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.error("required field not provided")
                return Response(
                    json.dumps({"error": "required fields not provided"}),
                    status=status.HTTP_412_PRECONDITION_FAILED,
                    mimetype='application/json')

            user = session.query(Users).filter_by(username=username, active=True).first()
            if user and user.avatar:
                # set_log(
                #     user.username,
                #     "avatar/" + username,
                #     "avatar sent",
                #     status.HTTP_200_OK,
                #     session)
                logger.info("avatar sent")
                return send_file(user.avatar)
            else:
                # set_log(
                #     None,
                #     "avatar/" + username,
                #     "avatar not set",
                #     status.HTTP_200_OK,
                #     session)
                logger.error("avatar not set")
                return Response(
                    json.dumps({"warning": "avatar not set"}),
                    status=status.HTTP_200_OK,
                    mimetype='application/json')

    except Exception as e:
        set_log(
            None,
            "avatar/" + username,
            "operation failed in server side",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            session)
        logger.error("operation failed in server side")
        return Response(
            json.dumps({"error": "operation failed in server side"}),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            mimetype='application/json')
