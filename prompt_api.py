from flask import Blueprint, request, Response
from flask_jwt import jwt_required, current_identity
import prompt
import config

bp = Blueprint('prompt',__name__)

@bp.route('/add', methods=['POST'])
@jwt_required()
def add_text():
    current_user = current_identity.get('username')
    return prompt.add_text(request.form, current_user)


@bp.route('/remove', methods=['GET'])
@jwt_required()
def remove_texts():
    current_user = current_identity.get('username')
    return prompt.remove_texts(request.form, current_user)


@bp.route('/list', methods=['POST'])
@jwt_required()
def list_texts():
    current_user = current_identity.get('username')
    return prompt.list_texts(request.form, current_user)

@bp.route('/get', methods=['GET'])
# @jwt_required()
def get_prompt():
    current_user = 'admin' #current_identity.get('username')
    return prompt.get_prompt(current_user)

@bp.route('/ref', methods=['GET'])
@jwt_required()
def get_text():
    current_user = current_identity.get('username')
    return prompt.get_text(current_user)

