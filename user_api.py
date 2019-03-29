from flask import Blueprint, request
from flask_jwt import jwt_required, current_identity
import user
import config


bp = Blueprint('user', __name__)

@bp.route('/add', methods=['POST'])
# @jwt_required()
def add_user():
    current_user = 'admin' #current_identity.get('username')
    return user.add_user(request.form, request.files, current_user)


@bp.route('/remove', methods=['GET'])
@jwt_required()
def remove_user():
    current_user = current_identity.get('username')
    return user.remove_user(request.args, current_user)


@bp.route('/update', methods=['POST'])
# @jwt_required()
def update_user():
    current_user = 'admin' #current_identity.get('username')
    return user.update_user(request.form, request.files, current_user)


@bp.route('/list', methods=['POST'])
@jwt_required()
def list_users():
    current_user = current_identity.get('username')
    return user.list_users(request.form, current_user)


@bp.route('/avatar/<string:username>', methods=['GET'])
def get_avatar(username):
    return user.get_avatar(username)


