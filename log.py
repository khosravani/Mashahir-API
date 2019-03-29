
import json
import config
import time

from flask import Response
from flask_api import status
from sqlalchemy import desc, asc
from db_interface import Logs
from utils import session_scope
from datetime import datetime, timedelta

logger = config.logging.getLogger(__name__)


def set_log(username, action, message, status_code, session):
    log = Logs()
    log.username = username
    log.action = action
    log.message = message
    log.status_code = status_code
    log.created_date = datetime.now()

    session.add(log)

    # query = session.query(Logs).filter(
    #     Logs.created_date < (datetime.today() - timedelta(days=int(config.general.log_age)))
    # ).delete()


def list_logs(args, current_user):
    with session_scope() as session:
        try:
            query = session.query(Logs)

            if 'username' in args and args['username']:
                query = query.filter(Logs.username.like('%' + args['username'] + '%'))

            if 'message' in args and args['message']:
                query = query.filter(Logs.message.like('%' + args['message'] + '%'))
            
            if 'action' in args and args['action']:
                query = query.filter(Logs.action.like('%' + args['action'] + '%'))
            
            if 'status_code' in args and args['status_code']:
                query = query.filter(Logs.status_code == int(args['status_code']))

            if 'created_date_from' in args and args['created_date_from']:
                st_date = datetime.fromtimestamp(int(args['created_date_from']))
                query = query.filter(Logs.created_date > st_date)

            if 'created_date_to' in args and args['created_date_to']:
                ed_date = datetime.fromtimestamp(int(args['created_date_to']))
                query = query.filter(Logs.created_date < ed_date)

            if 'sort_field' in args and args['sort_field'] in [c.key for c in Logs.__table__.c]:
                field = getattr(Logs, args['sort_field'])
            else:
                field = Logs.id

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

            logs = []
            for log in query:
                logs.append({
                    'username': log.username,
                    'action': log.action,
                    'message': log.message,
                    'status_code': log.status_code,
                    'created_date': time.mktime(log.created_date.timetuple())
                })
            set_log(
                current_user,
                "log/list",
                "list logs",
                status.HTTP_200_OK,
                session)
            logger.info("list logs")
            return Response(
                json.dumps({"msg": {"logs": logs, "count":count}}),
                status=status.HTTP_200_OK,
                mimetype='application/json')

        except Exception as e:
            set_log(
                current_user,
                "log/list",
                str(e.message),
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                session)
            logger.info(str(e.message))
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')
