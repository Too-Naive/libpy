# -*- coding: utf-8 -*-
# BackupSQL.py
# Copyright (C) 2017-2018 Too-Naive and contributors
#
# This module is part of libpy and is released under
# the AGPL v3 License: https://www.gnu.org/licenses/agpl-3.0.txt
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
from __future__ import unicode_literals
import time
import os,shutil
import libpy.Log as Log
from threading import Thread
from libpy.Config import Config
from libpy.Gitlib import pygitlib
from base64 import b64encode,b64decode
from libpy.MainDatabase import MainDatabase
from libpy.SQLexport import func_backup_sql
from libpy.Encrypt import b64encrypt,b64decrypt
from libpy.util import current_join_path,sql_clear_comment


def custom_diff(diff1,diff2):
	d1 = []
	d2 = []
	with open(diff1) as fin:
		r = fin.readlines()
	for x in r:
		if x[:2] != '--':
			d1.append(x)
	with open(diff2) as fin:
		r = fin.readlines()
	for x in r:
		if x[:2] != '--':
			d2.append(x)
	Log.debug(3, '[d1 == d2 = {}]', d1 == d2)
	Log.debug(3, '[d1 = {}]', d1)
	Log.debug(3, '[d2 = {}]', d2)
	return d1 == d2

def backup_and_encrypt(target_database_name=Config.database.db_name,
		workingdir='workingdir',sub_folder_name='sqlbkup'):
	Log.debug(2,'Entering backup_and_encrypt()')
	need_add = True
	func_backup_sql(target_database_name,DATETIME=sub_folder_name)

	# clear auto created comment
	sql_clear_comment(current_join_path(sub_folder_name, target_database_name+'.sql'))

	# Check is first backup
	if os.path.isfile(current_join_path(workingdir,Config.git.filename)):
		# Open old file and decrypt it
		with open(current_join_path(workingdir,Config.git.filename)) as fin:
			r = fin.read().split('\\\\n')
			with open(os.path.join('.','temp.sql'),'w') as fout:
				fout.write(b64decrypt(r[0],r[1],r[2]))

		# Check file different
		need_add = not custom_diff(
			current_join_path(sub_folder_name, target_database_name+'.sql'),
			os.path.join('.','temp.sql'))

		os.remove(os.path.join('.','temp.sql')) # Remove decrypted file

	Log.debug(3, '[need_add = {}]', need_add)

	if need_add:
		with open(current_join_path(sub_folder_name, target_database_name+'.sql')) as fin:
			raw = fin.read()
		with open(current_join_path(workingdir, Config.git.filename),'w') as fout:
			a, b, c=b64encrypt(raw)
			fout.write(a+'\\\\n'+b+'\\\\n'+c)

	if os.path.isdir(sub_folder_name):
		shutil.rmtree(sub_folder_name)
	Log.debug(2,'Exiting backup_and_encrypt()')
	return need_add

def restore_sql(
		target_database_name=Config.database.db_name,
		workingdir='workingdir'):
	Log.debug(2,'Entering restore_sql()')
	git = pygitlib(workingdir,init=True)
	with open(current_join_path(workingdir,Config.git.filename)) as fin:
		r = fin.read().split('\\\\n')
	with open(os.path.join('.','temp.sql'),'w') as fout:
		fout.write(b64decrypt(r[0],r[1],r[2]))
	__execute_sql()
	os.remove(os.path.join('.','temp.sql'))
	Log.debug(2,'Exiting restore_sql()')

def __execute_sql(sql_filename='temp.sql'):
	with open(os.path.join('.',sql_filename)) as fin:
		with MainDatabase() as db:
			for x in fin.read().split(';'):
				db.execute(x)

class sql_backup_daemon(Thread):
	def __init__(
		self,
		target_dir='workingdir',
		DB_NAME=Config.database.db_name,
		sub_folder_name='sqlbkup'):
		Log.debug(2,'Entering sql_backup_daemon.__init__()')
		Thread.__init__(self)
		if os.path.isdir(target_dir):
			self.git = pygitlib(target_dir,init=True)
			self.git.configure_create()
			self.git.fetch()
			self.git.pull()
			self.git.revert_configure()
		else:
			self.git = pygitlib(target_dir,True)
		self.target_dir = target_dir
		self.DB_NAME = DB_NAME
		self.daemon = True
		self.sub_folder_name = sub_folder_name
		#self.Lock = Lock()
		Log.debug(2,'Exiting sql_backup_daemon.__init__()')

	def run(self):
		Log.debug(2,'Start sql_backup_daemon Thread')
		while True:
			Log.debug(2,'[Daemon] Starting backup')
			if backup_and_encrypt(self.DB_NAME,self.target_dir,self.sub_folder_name):
				self.git.add([Config.git.filename])
				self.git.commit('Daily backup');
				self.git.configure_create()
				self.git.push()
				self.git.revert_configure()
				Log.debug(2,'[Daemon] Backup successful')
			else:
				Log.debug(2,'[Daemon] Backup successful (no update)')
			time.sleep(Config.git.backup_cycle)
