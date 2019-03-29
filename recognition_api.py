
from flask import Blueprint, request
import recognition

bp = Blueprint('recognition', __name__)


@bp.route('/prompt', methods=['GET'])
def get_prompt():
    return recognition.get_prompt(request.args)


@bp.route('/authenticate', methods=['POST'])
def authentication():
    return recognition.authentication(request.form, request.files)


@bp.route('/identify', methods=['POST'])
def identify():
    return recognition.identify(request.form, request.files)