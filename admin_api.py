from flask import Blueprint, request
from flask_jwt import jwt_required, current_identity
import admin
import config

bp = Blueprint('admin',__name__)


@bp.route('/passwd',methods=['POST'])
@jwt_required()
def change_password():
    current_user = current_identity.get('username')
    return admin.change_password(request.form, current_user)
