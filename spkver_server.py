
import base64
import datetime
import json
import api
import hashlib
import os
import config
from flask_cors import CORS
from admin import validate_admin, fetch_admin
from flask_jwt import JWT, jwt_required, current_identity, JWTError
from flask_api import status
from flask import Flask, request, Response, jsonify, send_file, send_from_directory
from log import set_log
from utils import session_scope
from functools import wraps
from flask_api import parsers, renderers

logger = config.logging.getLogger(__name__)
 

def authenticate(username, password):
    if validate_admin(username, password):
        return fetch_admin(username=username)

def identity(payload):
    return fetch_admin(id=payload['identity'])

expiration_time = int(config.general.token_expiration)

app = Flask(__name__, static_url_path='')
cors = CORS(app, resources={r"/*": {"origins": "*"}})

# app.debug = True
# app.logger.addHandler(logger)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True
app.config['JWT_EXPIRATION_DELTA'] = datetime.timedelta(seconds=expiration_time)
app.config['JWT_NOT_BEFORE_DELTA'] = datetime.timedelta(seconds=1)
app.config['UPLOAD_FOLDER'] = "uploads"
app.config['AVATAR_FOLDER'] = "uploads/avatar"
app.config['ALLOWED_EXTENSIONS'] = set(['png', 'jpg', 'jpeg'])
app.config['ALLOWED_AUDIO_EXTENSIONS'] = set(['wav'])
app.config['MAX_CONTENT_LENGTH'] = 30 * 1024 * 1024
app.config['SECRET_KEY'] = 'super-secret'
app.config['JWT_AUTH_URL_RULE']='/generateToken'
app.config['JWT_VERIFY_CLAIMS'] = ['iss','exp','signature']
app.config['JWT_AUTH_HEADER_PREFIX'] = 'JWT'

jwt = JWT(app, authenticate, identity)
# jwt.auth_request_callback = auth_request_callback

def handle_user_exception_again(e):
    with session_scope() as session:
        if isinstance(e, JWTError):
            # set_log(
            #     None,
            #     'handle_user_exception_again', 
            #     e.description,
            #     e.status_code,
            #     session)
            return Response(
                json.dumps({"error": e.description}),
                status=e.status_code,
                mimetype='application/json')
        else:
            # set_log(
            #     None,
            #     'handle_user_exception_again',
            #     str(e),
            #     status.HTTP_500_INTERNAL_SERVER_ERROR,
            #     session)
            return Response(
                json.dumps({"error": "operation failed in server side"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                mimetype='application/json')

app.handle_user_exception = handle_user_exception_again

def return_json(f):
	@wraps(f)
	def inner(*a, **k):
		return json.dumps(f(*a, **k))
	return inner

@jwt.auth_response_handler
@return_json
# @cross_origin()
def response_handler(token, identity):
    with session_scope() as session:
        set_log(
            identity['username'],
            'login',
            'successful login',
            status.HTTP_202_ACCEPTED,
            session)
        return {'token': token, 'username': identity['username']}

@jwt.jwt_payload_handler
def payload_handler(identity):
    iat = datetime.datetime.utcnow()
    exp = iat + app.config.get('JWT_EXPIRATION_DELTA')
    nbf = iat + app.config.get('JWT_NOT_BEFORE_DELTA')
    return {'iss':request.remote_addr, 'exp': exp, 'iat': iat, 'nbf': nbf, 'identity': identity['id']}


@app.route('/')
def index():
    return send_file(os.path.abspath('static/index.html'))

@app.errorhandler(404)
def page_not_found(e):
    return send_file(os.path.abspath('static/index.html'))
    
@app.route('/static/<path:url>')
def static_url(url):
    if not os.path.isfile('static/' + url):
        return Response(
            None,
            status=status.HTTP_204_NO_CONTENT)
    return send_from_directory('static', url)

@app.route('/app/<path:url>')
def static_app(url):
    if not os.path.isfile('static/app/' + url):
        return Response(
            None,
            status=status.HTTP_204_NO_CONTENT)
    return send_from_directory('static/app/', url)

@app.route('/assets/<path:url>')
def static_assets(url):
    if not os.path.isfile('static/assets/' + url):
        return Response(
            None,
            status=status.HTTP_204_NO_CONTENT)
    return send_from_directory('static/assets/', url)

app.register_blueprint(api.prompt_api.bp, url_prefix='/prompt')
app.register_blueprint(api.user_api.bp,url_prefix='/user')
app.register_blueprint(api.admin_api.bp,url_prefix='/admin')
app.register_blueprint(api.voice_api.bp, url_prefix='/voice')
app.register_blueprint(api.recognition_api.bp, url_prefix='/recognition')
app.register_blueprint(api.log_api.bp, url_prefix='/log')
app.register_blueprint(api.setting_api.bp, url_prefix='/settings')
