#!/usr/bin/python3
import sys
import subprocess
import datetime
import socket
import os
import time
import argparse
import json
import fnmatch

VERSION_LEN = 3
ASYNC_HDLC_FLAG = 0x7e
#DM ='/dev/ttyUSB0'

class QxdmLogger():

	def __init__(self):
		self.set_cnt = 1
		self.log_set_list = []
		self.enabled = False
		self.filter = ""
		self.log_base = ""
		self.log_count = 20
		self.log_size_in_mb = 10
		self.mode = "lan"
		self.legacy = False
		

	def get_cfg(self, pw):
		get_qxdm_cfg = 'curl -s -u admin:{} --connect-timeout 5 -X GET http://192.168.0.1/api/config/system/qxdmproxy'.format(pw)
		proc = subprocess.Popen(get_qxdm_cfg.split(),stdout=subprocess.PIPE)
		resp = proc.communicate()[0]
		#communicate returns a bytes array. Need to convert to string so we can do a regular expression match
		try:
			resp = resp.decode("utf-8")
		except Exception as e:
			print("get_val, no decode")
			return None, -1

		try:
			json_data = json.loads(resp)
			if json_data == None:
				print("get_val, no json")
				return None, -1
			if json_data['success'] == False:
				#print("get_val, returned false")
				return None, 0
			else:
				data = json_data['data']
				print('Router configuration:\n')
				for attribute, value in data.items():
					print(attribute, value) # example usage

				print('\n')
				self.enabled = data['enabled']
				self.log_base = data['log_base']
				self.log_count = int(data['log_count'])
				self.log_size_in_mb = int(data['log_size_in_mb'])
				self.filter = data['filter']
				return data, 1
		except Exception as e:
			# Most likely talking to an older router that doesn't have as much of the config under /config/system/qxdmproxy
			self.legacy = True
			self.enabled = True
			self.log_base = ""
			self.log_count = 20
			self.log_size_in_mb = 10
			self.mode = "lan"
			print("Most likely talking to an older router that doesn't have as much of the config under /config/system/qxdmproxy, exception {}".format(e))
			return None, 1

	def pruneLogFiles(self):
		# enforce log_count
		while len(self.log_set_list) > self.log_count:
			print("max log files is %d, removing log file: %s", self.log_count, self.log_set_list[0])
			os.remove(self.log_set_list.pop(0))

	def updateSetCount (self):
		#add the log set count
		try:
			files = fnmatch.filter(os.listdir('./'),  self.log_base + '*')
		except Exception as e:
			print('updateSetCount, exception: {}'.format(e))
			return

		print('files={}'.format(files))
		self.set_cnt = 1
		if files:
			# find the next set count
			files = [f.split(self.log_base)[1] for f in files] # remove the base log filename
			sets = [f.split('_')[0] for f in files] # save the set counts
			sets = [s for s in sets if len(s) == 3]
			if sets:
				sets.sort()
				self.set_cnt = int(sets.pop()) + 1

		# print('setcount: %d' % self.set_cnt)
		# new set - clear log_set_list
		self.log_set_list.clear()
		return

if __name__ == '__main__':
	# apt-get install python-argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("--pw", default=None)
	value = parser.parse_args()

	if value.pw == None:
		print("Usage: cp_modem_crash.py --pw=password")
		print(" NOTE: you must enable the qxdm proxy on the router under /config/system/qxdmproxy")
		print('       set mode "lan"; set enabled true\n')
		sys.exit(1)

	log_size_in_mb_reached = False
	connected = False
	socket_closed = False
	init_set_count = False

	qxdm_logger = QxdmLogger()

	#Open TCP socket to 192.168.0.1 port 8888
	print("Opening TCP port 8888 on 192.168.0.1\n")

	while socket_closed == False:
		while connected == False:
			try:
				get_qxdm_cfg, res = qxdm_logger.get_cfg(value.pw)

				if res != 1:
					print('Failed to get config, possible bad password or incompatible router version')
					sys.exit(1)

				if qxdm_logger.enabled != True:
					print('qxdm logging disabled on the router')
					sys.exit(1)

				if qxdm_logger.mode != 'lan':
					print('qxdm logging mode is not lan on router')
					sys.exit(1)

				if value.filter_file != None:
					qxdm_logger.filter = value.filter_file

				print ('connecting')
				s=socket.socket()
				time.sleep (1)
				s.connect(('192.168.0.1', 8888))
				connected = True
				
				# send command to crash modem
				cmd = b'\x4b\x25\x03\x00\x92\x3a\x7e'
				s.send( cmd )
					
				# wait forever
				print('waiting forever')
				while(1):
					time.sleep(1)


			except Exception as e:
				print("Failed to open socket or cfg error: {}, delay 1 second".format(e))
				#sys.exit(1)
				time.sleep (1)

		if qxdm_logger.filter != "":
			try:
				print("Opening file {}".format(qxdm_logger.filter))
				f = open(qxdm_logger.filter, 'rb')
				buf = f.read()
				f.close()
			except Exception as e:
				s.close()
				print("Failed to open file: {}, error: {}".format(qxdm_logger.filter, e))
				sys.exit(1)

			#skip over the version
			buf = buf[VERSION_LEN:]
			print("buf len: {}".format(len(buf)))
			start = 0
			for i in range(0, len(buf)):
				#print(buf[i])
				if buf[i] == ASYNC_HDLC_FLAG:
					print("Found next command from start: {} to end: {}".format(start, i + 1))
					cmd = buf[start:i+1]
					#print('[OUT]: ',end='')
					#print (":".join("{0:x}".format(c) for c in cmd ))
				
					s.send( cmd )
					response = s.recv(512)
					print('[IN]: ', end='')
					#print(response)
					#print(":".join("{0:x}".format(c) for c in response ))
					start = i + 1
			print("Done processing filter commands")
		else:
			print('No filter file specified - LP4 model')
			if qxdm_logger.legacy == True:
				print('If not LP4 modem you can specify the filter file on the command line: --filter_file=file.sqf')
			else:
				print('If not LP4 modem you can specify the filter file on the command line: --filter_file=file.sqf, or specify it in /config/system/qxdmproxy/filter')

		now = datetime.datetime.now()
		if init_set_count == False:
			qxdm_logger.updateSetCount()
			init_set_count = True

		filename = now.strftime('{}{}_%Y_%m_%d_%H_%M_%S.qmdl'.format(qxdm_logger.log_base, str(qxdm_logger.set_cnt).zfill(3)))
		qxdm_logger.log_set_list.append(filename)
		qxdm_logger.pruneLogFiles()

		print("\nSaving log data to file {}. \n\nHit ctrl-c when done...".format(filename))
		with open(filename, 'wb') as of:
			total = 0
			while 1:
				try:
					pkts = s.recv(1500)
					if len(pkts) == 0:
						print('socket closed')
						socket_closed = True
						sys.stdout.flush()
						of.flush()
						os.fsync(of.fileno())
						break

					of.write(pkts)
					total = total + len(pkts)
					print("\rlogging %d bytes" % total, end='\r')

					# 0 indicates no max
					if qxdm_logger.log_size_in_mb != 0:
						if total >= qxdm_logger.log_size_in_mb * 1000000:
							print('File size hit {} bytes, rotating {}'.format(total, filename))
							log_size_in_mb_reached = True
							socket_closed = True
							total = 0

							sys.stdout.flush()
							of.flush()
							os.fsync(of.fileno())
							break

				except KeyboardInterrupt:
					sys.stdout.flush()
					of.flush()
					os.fsync(of.fileno())
					break

		sys.stdout.flush()
		#of.flush()
		#os.fsync(of.fileno())
		s.close()

		if socket_closed == False:
			print("Closing log file and exiting")
			sys.exit(0)
		else:
			if log_size_in_mb_reached != True:
				qxdm_logger.set_cnt += 1

			socket_closed = False
			connected = False
			log_size_in_mb_reached = False

