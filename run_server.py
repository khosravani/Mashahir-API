#!/usr/bin/python
from gevent import monkey
monkey.patch_all()

import sys
import spkver_server as api
from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import FallbackHandler, RequestHandler, Application
from tornado.httpserver import HTTPServer
from gevent.pywsgi import WSGIServer
import config
import os
import const
import pymysql
import subprocess

logger = config.logging.getLogger(__name__)

class getToken(RequestHandler):
    def get(self):
        self.write("hello")

if config.general.enable_tornado:
    tr = WSGIContainer(api.app)
    application = Application([
        (r"/tornado", getToken),
        (r".*", FallbackHandler, dict(fallback=tr)),
    ])

    http_server = HTTPServer(
        application,
        max_buffer_size=0.5*1024*30000,
        ssl_options={
            "certfile": os.path.abspath("certificate.pem"),
            "keyfile": os.path.abspath("privateKey.key")}
        )
    http_server.listen(int(config.general.port))
    logger.info('%s version %s with Tornado server is started.' % (const.APP_NAME, const.VERSION))
    IOLoop.instance().start()

else:
    # add WSGI only for fixing sse problem
    server = WSGIServer(
        ('0.0.0.0', int(config.general.port)),
        api.app,
        keyfile=os.path.abspath("privateKey.key"),
        certfile=os.path.abspath("certificate.pem")
    )
    logger.info('%s version %s with WSGI server is started.' % (const.APP_NAME, const.VERSION))
    server.serve_forever()

asr.K.clear_session()