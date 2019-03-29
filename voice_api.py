from flask import Blueprint, request
from flask_jwt import jwt_required, current_identity
import voice
import config

bp = Blueprint('voice', __name__)

@bp.route('/enroll', methods=['POST'])
@jwt_required()
def enrollment():
    current_user = current_identity.get('username')
    return voice.enrollment(request.form, request.files, current_user)


@bp.route('/ref/remove', methods=['GET'])
@jwt_required()
def remove_references():
    current_user = current_identity.get('username')
    return voice.remove_references(request.args, current_user)


# @bp.route('/ref/update', methods=['GET'])
# @jwt_required()
# def update_references():
#     current_user = current_identity.get('username')
#     return voice.update_references(current_user)


@bp.route('/ref/download', methods=["GET"])
# @jwt_required()
def download_reference():
    current_user = 'admin'
    return voice.download_reference(request.args, current_user)


@bp.route('/ref/list', methods=['POST'])
@jwt_required()
def list_references():
    current_user = current_identity.get('username')
    return voice.list_references(request.form, current_user)

@bp.route('/eval/remove', methods=['GET'])
@jwt_required()
def remove_evaluations():
    current_user = current_identity.get('username')
    return voice.remove_evaluations(request.args, current_user)


@bp.route('/eval/download', methods=["GET"])
@jwt_required()
def download_evaluation():
    current_user = current_identity.get('username')
    return voice.download_evaluation(request.args, current_user)


@bp.route('/eval/list', methods=['POST'])
@jwt_required()
def list_evaluations():
    current_user = current_identity.get('username')
    return voice.list_evaluations(request.form, current_user)
