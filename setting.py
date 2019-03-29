import json
import subprocess
import config
import jdatetime
from datetime import datetime
from flask_api import status
from flask import Response
from utils import session_scope
from log import set_log

logger = config.logging.getLogger(__name__)


def backup_db(current_user):

	with session_scope() as session:

		dump_command = 'mysqldump  --user=root --password={0} {1} --result-file=./db_backups/db_back 2>&1 | grep -v Warning 1>&2'. \
			format(
			config.database.password,
			config.database.dbname)

		script = subprocess.Popen(dump_command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		output, error = script.communicate()
		
		if not error:
			time = str(jdatetime.datetime.now().date())+ '-' + \
			       str(jdatetime.datetime.now().time().replace(second=0, microsecond=0)).replace(':', '-')
			
			gzip_command = 'gzip -9 -c ./db_backups/db_back > ./db_backups/{0}-{1}.sql.gz | rm -f ./db_backups/db_back'. \
				format(
				config.database.dbname,
				time)

			script = subprocess.Popen(gzip_command, stdin=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			output, error = script.communicate()

			set_log(
				current_user,
				"setting/backupdb",
				"backup created successfully",
				status.HTTP_200_OK,
				session)
			return Response(
				json.dumps({"msg": "backup created successfully"}),
				status=status.HTTP_200_OK,
				mimetype='application/json')

		else:
			set_log(
				current_user,
				"setting/backupdb",
				"can not backup database",
				status.HTTP_500_INTERNAL_SERVER_ERROR,
				session)
			return Response(
				json.dumps({"error": "can not backup database"}),
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
				mimetype='application/json')


def restore_db(args, current_user):

	with session_scope() as session:

		if not ('date' in args and args['date'] and 'db' in args and args['db']):
			set_log(
				current_user,
				"setting/restoredb",
				"required field not provided",
				status.HTTP_412_PRECONDITION_FAILED,
				session)
			logger.error("required field not provided")
			return Response(
				json.dumps({"error": "required field not provided"}),
				status=status.HTTP_412_PRECONDITION_FAILED,
				mimetype='application/json')

		bashCommand = 'gunzip < ./db_backups/{0}-{1}.sql.gz | mysql --user=root --password={2} {3} 2>&1 | grep -v Warning' \
			.format(
			config.database.dbname,
			args['date'],
			config.database.password,
			args['db'])

		script = subprocess.Popen(
			bashCommand,
			stdin=subprocess.PIPE,
			stderr=subprocess.PIPE,
			stdout=subprocess.PIPE,
			shell=True)
		output, error = script.communicate()

		if not error:
			set_log(
				current_user,
				"setting/restoredb",
				"database restored successfully",
				status.HTTP_200_OK,
				session)
			return Response(
				json.dumps({"msg": "database restored successfully"}),
				status=status.HTTP_200_OK,
				mimetype='application/json')

		else:
			set_log(
				current_user,
				"setting/restoredb",
				"can not restore database.",
				status.HTTP_500_INTERNAL_SERVER_ERROR,
				session)
			return Response(
				json.dumps({"error": "can not restore database"}),
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
				mimetype='application/json')


def modify_config(args, current_user):

	with session_scope() as session:
		try:

			if 'word_count' in args and args['word_count']:
				config.general.word_count = args['word_count']
				config.Config.set('General', 'word_count', args['word_count'])
				

			if 'log_age' in args and args['log_age']:
				config.general.log_age = args['log_age']
				config.Config.set('General', 'log_age', args['log_age'])
			
			if 'auth_threshold' in args and args['auth_threshold']:
				config.general.auth_threshold = args['auth_threshold']
				config.Config.set('General', 'auth_threshold', args['auth_threshold'])

			if 'auth_add_model' in args and args['auth_add_model']:
				config.general.auth_add_model = args['auth_add_model']
				config.Config.set('General', 'auth_add_model', args['auth_add_model'])

			if 'auth_add_count' in args and args['auth_add_count']:
				config.general.auth_add_count = args['auth_add_count']
				config.Config.set('General', 'auth_add_count', args['auth_add_count'])

			if 'wer' in args and args['wer']:
				config.general.wer = args['wer']
				config.Config.set('General', 'wer', args['wer'])

			if 'identify_theshold' in args and args['identify_theshold']:
				config.general.identify_theshold = args['identify_theshold']
				config.Config.set('General', 'identify_theshold', args['identify_theshold'])

			if 'identify_maxcount' in args and args['identify_maxcount']:
				config.general.identify_maxcount = args['identify_maxcount']
				config.Config.set('General', 'identify_maxcount', args['identify_maxcount'])
			
			with open('config.ini', 'wb') as configfile:
					config.Config.write(configfile)

			set_log(
				current_user,
				"setting/conf",
				"config file updated",
				status.HTTP_200_OK,
				session)
			logger.info("config file updated")
			return Response(
				json.dumps({"msg":"config file updated"}),
				status=status.HTTP_200_OK,
				mimetype='application/json')
		
		except Exception as e:
			set_log(
				current_user,
				"setting/conf",
				str(e.message),
				status.HTTP_500_INTERNAL_SERVER_ERROR,
				session)
			logger.info(str(e.message))
			return Response(
				json.dumps({"error": "operation failed in server side"}),
				status=status.HTTP_500_INTERNAL_SERVER_ERROR,
				mimetype='application/json')