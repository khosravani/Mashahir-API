import base64
import hashlib
import json
import config
import numpy as np
from datetime import datetime, timedelta
from db_interface import Admins
from flask_api import status
from flask import Response
from log import set_log
from utils import session_scope
from sqlalchemy import inspect, asc, desc

logger = config.logging.getLogger(__name__)

def add_admin(data, expiration=2):
    with session_scope() as session:
        try:
            if not all(k in data and data[k] for k in ('username', 'fullname', 'password')):
                resp = {"error": "username, fullname and password required"}
                set_log("__", "add_admin", "username, fullname and password required", status.HTTP_400_BAD_REQUEST)
                logger.error( "__ --> add_admin" + "--> username, fullname and password required")
                return Response(json.dumps(resp), status=status.HTTP_400_BAD_REQUEST, mimetype='application/json')

            username = data['username']
            password = data['password']
            fullname = data['fullname']
            company = data['company'] if 'company' in data else None
            description = data['description'] if 'description' in data else None

            resp_uname = check_username(username)
            resp_pass = check_password(password)

            if resp_uname.get('error'):
                set_log("__", "add_admin", resp_uname.get('error'), status.HTTP_400_BAD_REQUEST)
                return Response(json.dumps(resp_uname),status=status.HTTP_400_BAD_REQUEST, mimetype='application/json')
            # elif resp_pass.get('error'):
            #     return Response(json.dumps(resp_pass), status=status.HTTP_400_BAD_REQUEST, mimetype='application/json')

            query = session.query(db.Admins).filter_by(username=username).first()

            if not query:
                admin = db.Admins()
                admin.fullname = fullname
                admin.username = username
                admin.password = base64.b64encode(hashlib.sha1(password).digest())
                admin.description = description
                admin.company = company
                admin.time = datetime.now()

                session.add(admin)
                session.commit()

                resp = {"msg": {"admin_id": admin.id}}
                set_log("__", "add_admin", "True", status.HTTP_200_OK)
                logger.info("__--> add_admin --> True")
                return Response(json.dumps(resp), status=status.HTTP_200_OK, mimetype='application/json')

            else:
                resp = {"error": "username is used "}
                set_log("__", "add_admin", "username is used", status.HTTP_400_BAD_REQUEST)
                logger.error("--> add_admin" + "--> username is used")
                return Response(json.dumps(resp), status=status.HTTP_400_BAD_REQUEST, mimetype='application/json')

        except Exception as e:

            set_log("__", "add_admin", str(e.message), status.HTTP_500_INTERNAL_SERVER_ERROR)
            logger.exception("-->%s - add_admin"%(__name__) + "--> "+str(e.message))
            resp = {"error": "operation failed in server side"}
            return Response(json.dumps(resp), status=status.HTTP_500_INTERNAL_SERVER_ERROR, mimetype='application/json')


def list_admins(data, current_user):

    with session_scope() as session:
        try:

            query = session.query(db.Admins)

            if 'username' in data and data['username']:
                query = query.filter(db.Admins.username.like('%' + data['username'] + '%'))

            if 'fullname' in data and data['fullname']:
                query = query.filter(db.Admins.fullname.like('%' + data['fullname'] + '%'))

            if 'company' in data and data['company']:
                query = query.filter(db.Admins.company.like('%' + data['company'] + '%'))

            if 'created_date_from' in data and data['created_date_from']:
                start = datetime.fromtimestamp(float(data['created_date_from']))
                query = query.filter(db.Admins.time > start)

            if 'created_date_to' in data and data['created_date_to']:
                end = datetime.fromtimestamp(float(data['created_date_to']))
                query = query.filter(db.Admins.time < end)

            if 'modified_date_from' in data and data['modified_date_from']:
                start = datetime.fromtimestamp(float(data['modified_date_from']))
                query = query.filter(db.Admins.modified_time > start)

            if 'modified_date_to' in data and data['modified_date_to']:
                end = datetime.fromtimestamp(float(data['modified_date_to']))
                query = query.filter(db.Admins.modified_time < end)

            if 'sort_field' in data and data['sort_field'] in [c.key for c in db.Admins.__table__.c]:
                field = getattr(db.Admins, data['sort_field'])
            else:
                field = db.Admins.id

            if 'sort_order' in data and data['sort_order'] == "desc":
                field = desc(field)
            else:
                field = asc(field)

            query = query.order_by(field)
            count = query.count()

            if 'per_page' in data and data['per_page'] and 'page_num' in data and data['page_num']:
                query = query.slice((int(data['page_num']) - 1) * int(data['per_page']),
                                    int(data['page_num']) * int(data['per_page']))
            else:
                query = query.slice(0, 10)

            query = query.all()

            admins = []
            for admin in query:
                admins.append({
                    'id': admin.id,
                    'username': admin.username,
                    'fullname': admin.fullname,
                    'company': admin.company,
                    'description': admin.description,
                    'created_date': str(admin.time),
                    'modified_date': str(admin.modified_time)

                })

            # search_attr = db.Admins.username
            # requested_fields = ["id", "username", "fullname", "company", "description", "modified_time"]
            # result = search(db.Admins, data, search_attr, requested_fields)

            resp = {"msg": {"admins": admins, "count": count}}
            set_log(current_user,"list_admins", "True", status.HTTP_200_OK)
            logger.info(current_user + "--> list_admins" + "--> True")
            return Response(json.dumps(resp), status=status.HTTP_200_OK, mimetype='application/json')

        except Exception as e:
            set_log(current_user, "list_admins", str(e.message), status.HTTP_500_INTERNAL_SERVER_ERROR)
            logger.exception("list_admins","-->%s - list_admins" % (__name__) + "--> " + str(e.message))
            resp = {"error": "operation failed in server side"}
            return Response(json.dumps(resp), status=status.HTTP_500_INTERNAL_SERVER_ERROR, mimetype='application/json')


def change_password(args, current_user):
    with session_scope() as session:
        try:
            if not all(k in args and args[k] for k in ('curr_password', 'new_password')):
                set_log(
                    current_user,
                    "admin/password",
                    "required fields not provided",
                    status.HTTP_412_PRECONDITION_FAILED,
                    session)
                logger.warning("required fields not provided")
                return Response(
                    json.dumps({"error": "required fields not provided"}), 
                    status=status.HTTP_412_PRECONDITION_FAILED, 
                    mimetype='application/json')

            admin = session.query(Admins).filter_by(username=current_user).first()

            if not (admin and admin.password == args['curr_password']):
                set_log(
                    current_user,
                    "admin/password",
                    "username or password is wrong",
                    status.HTTP_404_NOT_FOUND,
                    session)
                logger.warning("username or password is wrong")
                return Response(
                    json.dumps({"error": "username or password is wrong"}),
                    status=status.HTTP_404_NOT_FOUND,
                    mimetype='application/json')

            admin.password = args['new_password']
            admin.last_edited_date = datetime.now()
 
            set_log(
                current_user,
                "admin/password",
                "password changed successfully",
                status.HTTP_200_OK,
                session)
            logger.info("password changed successfully")
            return Response(
                json.dumps({"msg": "password changed successfully"}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "change_password",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.error(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')


def fetch_admin(id=None, username=None):
    with session_scope() as session:
        if id is not None:
            admin = session.query(Admins).filter_by(active=True, id=id).first()
        else:
            admin = session.query(Admins).filter_by(active=True, username=username).first()

        return {"id": admin.id, "username": admin.username}


def validate_admin(username, password):
    with session_scope() as session:
        admin = session.query(Admins).filter_by(active=True, username=username).first()
        if not admin:
            return False
        return admin.password == password
