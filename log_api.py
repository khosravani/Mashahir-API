from flask import Blueprint, request
from flask_jwt import jwt_required, current_identity
import log


bp = Blueprint('log', __name__)

@bp.route('/list', methods = ['POST'])
@jwt_required()
def list_logs():
    current_user = current_identity.get('username')
    return log.list_logs(request.form, current_user)
