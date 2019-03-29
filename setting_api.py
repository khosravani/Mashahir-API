from flask import Blueprint, request
from flask_jwt import jwt_required, current_identity
import setting
import config


bp = Blueprint('settings', __name__)


@bp.route('/config', methods=['POST'])
@jwt_required()
def add_user():
    current_user = current_identity.get('username')
    return setting.modify_config(request.form, current_user)


@bp.route('/backupdb', methods=['GET'])
@jwt_required()
def remove_user():
    current_user = current_identity.get('username')
    return setting.backup_db(current_user)


@bp.route('/restoredb', methods=['POST'])
@jwt_required()
def update_user():
    current_user = current_identity.get('username')
    return setting.restore_db(request.form, current_user)


