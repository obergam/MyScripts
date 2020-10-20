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


QXDM_PORT = 8888
CRASH_INFO_PORT = 8889
RAM_DUMP_PORT = 8890

# RAMDUMP defines
SAHARA_CMD_INVALID = 0x00  				# from:
SAHARA_CMD_HELLO = 0x01    				# Target
SAHARA_CMD_HELLO_RESP = 0x02  			# Host
SAHARA_CMD_READ_DATA = 0x03				# Target
SAHARA_CMD_END_TRANSFER_IMAGE = 0x04  	# Target
SAHARA_CMD_DONE = 0x05					# Host
SAHARA_CMD_DONE_RESP = 0x06  			# Target
SAHARA_CMD_RESET = 0x07  				# Host
SAHARA_CMD_RESET_RESP = 0x08  			# Target
SAHARA_CMD_MEMORY_DEBUG = 0x09  		# Target
SAHARA_CMD_MEMORY_READ = 0x0A  			# Host
SAHARA_CMD_CMD_READY = 0x0B  			# Target
SAHARA_CMD_CMD_SWITCH = 0x0C  			# Host
SAHARA_CMD_CMD_EXECUTE = 0x0D  			# Host
SAHARA_CMD_CMD_EXECUTE_RESP = 0x0E  	# Target
SAHARA_CMD_CMD_EXECUTE_DATA = 0x0F   	# Host

LEN_SAHARA_CMD_HELLO = 0x30
LEN_SAHARA_CMD_HELLO_RESPONSE = 0x30
LEN_SAHARA_CMD_READ_DATA = 0x14
LEN_SAHARA_CMD_END_IMAGE_TRANSFER = 0x10
LEN_SAHARA_CMD_DONE = 0x08
LEN_SAHARA_CMD_DONE_RESPONSE = 0x0C
LEN_SAHARA_CMD_RESET = 0x08
LEN_SAHARA_CMD_RESET_RESPONSE = 0x08
LEN_SAHARA_CMD_MEMORY_DEBUG = 0x10
LEN_SAHARA_CMD_MEMORY_READ = 0x10
LEN_SAHARA_CMD_COMMAND_READY = 0x08
LEN_SAHARA_CMD_COMMAND_SWITCH_MODE = 0x0C
LEN_SAHARA_CMD_COMMAND_EXECUTE = 0x0C
LEN_SAHARA_CMD_COMMAND_EXECUTE_RESPONSE = 0x10
LEN_SAHARA_CMD_COMMAND_EXECUTE_DATA = 0x0C

SAHARA_EXEC_CMD_SWI_BOOT_VERSION_READ = 0xFF01
SAHARA_EXEC_CMD_SWI_PRODUCT_MODEL_READ = 0xFF02
SAHARA_EXEC_CMD_SWI_SERIAL_NUM_READ = 0xFF03
SAHARA_EXEC_CMD_SWI_CRASH_INFO_READ = 0xFF04

SAHARA_MODE_COMMAND = 0x03
SAHARA_MODE_MEMORY_DEBUG = 0x02
SAHARA_MAX_MEM_READ_LEN = 0x07F0 #0x0FF0

# Sahara protocol versions
SAHARA_CURRENT_VERSION = 2
SAHARA_COMPATIBLE_VERSION = 1

SAHARA_MEM_REGION_NAME_SIZE = 20 # From Sierra - found by experiment

U32_SIZE = 4
BIN_MEMORY_REGION_SIZE = (3 * U32_SIZE) + (2 * SAHARA_MEM_REGION_NAME_SIZE)

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
		self.port = QXDM_PORT

	def get_cfg(self, pw, router_ip):
		get_qxdm_cfg = 'curl -s -u admin:{} --connect-timeout 10 -X GET http://{}/api/config/system/qxdmproxy'.format(pw,router_ip)
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
			self.log_base = "cp"
			self.log_count = 20
			self.log_size_in_mb = 10
			self.mode = "lan"
			print("Most likely talking to an older router that doesn't have as much of the config under /config/system/qxdmproxy, exception {}".format(e))
			return None, 1

	def pruneLogFiles(self):
		# enforce log_count
		while len(self.log_set_list) > self.log_count:
			print("max log files is {}, removing log file: {}".format(self.log_count, self.log_set_list[0]))
			os.remove(self.log_set_list.pop(0))

	def updateSetCount (self):
		#add the log set count
		try:
			files = fnmatch.filter(os.listdir('./'),  self.log_base + '*')
		except Exception as e:
			print('updateSetCount, exception: {}'.format(e))
			return

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

	def getRamdumpDir (self):
		# Look for files that match our log_base and end in *.qmdl
		files = []
		dir = './'
		try:
			files = fnmatch.filter(os.listdir(dir), self.log_base + '*.qmdl')
		except:
			pass
		finally:
			if not files:
				now = datetime.datetime.now()
				rd_dir = now.strftime('{}_%Y_%m_%d_%H_%M_%S'.format(self.log_base))
				print("No log file found, use default")
			else:
				files_w_path = [dir + f for f in files]
				latest_file = max(files_w_path, key=os.path.getctime)
				ftime = os.path.getctime(latest_file)
				curtime = time.time()
				age = curtime-ftime
				rd_dir = latest_file.replace('.qmdl', '')

		abspath = os.path.abspath('./' + rd_dir)
		isDir = os.path.isdir(abspath)
		if isDir == False:
			os.mkdir('./' + rd_dir, 0o777)

		return rd_dir

	def getPortStr (self, port):
		port_str = None
		if port == QXDM_PORT:
			return 'QXDM'
		elif port == CRASH_INFO_PORT:
			return 'CRASH INFO'
		elif port == RAM_DUMP_PORT:
			return 'RAM DUMP'
		else:
			return 'UNKNOWN'

	def rotatePort (self, port):
		new_port = QXDM_PORT

		if port == QXDM_PORT:
			new_port = CRASH_INFO_PORT
		elif port == CRASH_INFO_PORT:
			new_port = RAM_DUMP_PORT
		else:
			new_port = QXDM_PORT
		return new_port

class QXDMlog():

	def __init__(self, qxdm_logger):
		self.logger = qxdm_logger
		self.s = qxdm_logger.s

	def execute (self):
		try:
			log_size_in_mb_reached = False
			socket_closed = False

			if self.logger.filter != "" and self.logger.port != CRASH_INFO_PORT:
				try:
					print("Opening file {}".format(self.logger.filter))
					f = open(self.logger.filter, 'rb')

					buf = f.read()
					f.close()
				except Exception as e:
					self.s.close()
					print("Failed to open filter file: {}, error: {}".format(self.logger.filter, e))
					sys.exit(1)

				#skip over the version if sqf file
				if self.logger.filter.find('.sqf') != -1:
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

						self.s.send( cmd )
						response = self.s.recv(512)
						print('[IN]: ', end='')
						#print(response)
						#print(":".join("{0:x}".format(c) for c in response ))
						start = i + 1
				print("Done processing filter commands")
			else:
				if self.logger.port != CRASH_INFO_PORT:
					print('No filter file specified - LP4 model')
					if self.logger.legacy == True:
						print('If not LP4 modem you can specify the filter file on the command line: --filter_file=file.sqf')
					else:
						print('If not LP4 modem you can specify the filter file on the command line: --filter_file=file.sqf, or specify it in /config/system/qxdmproxy/filter')

			self.logger.updateSetCount()
			while socket_closed == False:
				now = datetime.datetime.now()
				if self.logger.port != CRASH_INFO_PORT:
					filename = now.strftime('{}{}_%Y_%m_%d_%H_%M_%S.qmdl'.format(self.logger.log_base, str(self.logger.set_cnt).zfill(3)))
					self.logger.log_set_list.append(filename)
					self.logger.pruneLogFiles()
				else:
					filename = now.strftime(self.logger.getRamdumpDir() + '/' + 'crashinfo.txt'.format(self.logger.log_base, str(self.logger.set_cnt).zfill(3)))

				print("\nSaving log data to file {}.\n".format(filename))
				with open(filename, 'wb') as of:
					total = 0
					while socket_closed == False and log_size_in_mb_reached == False:
						try:
							pkts = self.s.recv(1500)
							if len(pkts) == 0:
								print('\nsocket closed\n')
								socket_closed = True
								sys.stdout.flush()
								of.flush()
								os.fsync(of.fileno())
								break

							of.write(pkts)
							total = total + len(pkts)
							print("\rlogging %d bytes" % total, end='\r')

							# 0 indicates no max
							if self.logger.log_size_in_mb != 0:
								if total >= self.logger.log_size_in_mb * 1000000:
									print('File size hit {} bytes, rotating {}'.format(total, filename))
									log_size_in_mb_reached = True
									total = 0

									sys.stdout.flush()
									of.flush()
									os.fsync(of.fileno())
									break

						except KeyboardInterrupt:
							sys.stdout.flush()
							of.flush()
							os.fsync(of.fileno())
							print("User broke, closing log file and exiting")
							sys.exit(0)
							break

					log_size_in_mb_reached = False
			sys.stdout.flush()
			self.s.close()

		except Exception as e:
			print('QXDMLog execute exception {}'.format(e))
			self.s.close()

class MemoryRegion():
	save_pref = 0 # u32 # not sure what this field is used for? 
	addr = 0 # u32
	len = 0 # u32
	description = '' # char array [SAHARA_MEM_REGION_NAME_SIZE]
	filename = '' # char array[SAHARA_MEM_REGION_NAME_SIZE]
	next_read = 0;    # u32 # This is only used to keep track of memory read and is
                        # not counted when parsing memory region info from recvd packet

class MemoryInfo():
	current_region = 0 # u8
	max_num_region = 0 # u8
	protocolVer = 0 # u8
	protocolMin = 0 # u8
	maxWriteSize = 0 # u16
	total_mem_size = 0 # u32
	total_mem_read = 0 # u32
	mem_region = [] # MemoryRegion[MAX_MEM_REGIONS]
  

class RAMDump():
	raw_data = None
	pkt_err_cnt = 0
	last_read_len_req = 0
	#s = None # socket
	pkt = None
	recv_pkt = None
	mem_table_addr = None
	mem_table_len = 0
	mem_info = None
	of = None # output file
	reg_percent_complete = 0
	reg_prev_percent_complete = 0

	def __init__(self, **kwargs):
		self.mem_info = MemoryInfo()
		self.logger = qxdm_logger
		self.s = qxdm_logger.s

	def deinit(self):
		if self.s:
			self.s.close()
		if self.of:
			self.of.close()
	
	def is_recv_done(self):
		if not self.raw_data:
			if len(self.recv_pkt) >= 8:
				pkt_len = int.from_bytes(self.recv_pkt[4:8], 'little')
				if pkt_len == len(self.recv_pkt):
					# done with this packet
					return True
		else:
			if self.last_read_len_req == len(self.recv_pkt):
				# done with this packet
				return True

		return False


	def sahara_recv(self):
		cmd = None
		pkt_len = 0
		self.recv_pkt = bytearray()
		done = False
		try:
			while not done:
				rpkt = self.s.recv(SAHARA_MAX_MEM_READ_LEN)
				self.recv_pkt.extend(rpkt)
				done = self.is_recv_done()
		except Exception as e:
			print("error receiving: {}".format(e))
			# if timeout
			if len(self.recv_pkt) == 0:
				return 'recv error', None

		if len(self.recv_pkt) >= 8:
			cmd = int.from_bytes(self.recv_pkt[:4], 'little')
			pkt_len = int.from_bytes(self.recv_pkt[4:8], 'little')

		if not self.raw_data:
			if pkt_len != len(self.recv_pkt):
				self.pkt_err_cnt += 1
				return 'invalid len', cmd
			else:
				self.pkt_err_cnt = 0
		else:
			if SAHARA_CMD_END_TRANSFER_IMAGE == cmd and LEN_SAHARA_CMD_END_IMAGE_TRANSFER == pkt_len and LEN_SAHARA_CMD_END_IMAGE_TRANSFER == len(self.recv_pkt):
				print("sahara_recv - end transfer image error - pkt: {}".format(self.recv_pkt))
				# reset device
				return 'invalid end of image', cmd
			if self.last_read_len_req != len(self.recv_pkt):
				self.pkt_err_cnt += 1
				print("sahara_recv - req_len: {}, len: {}, cmd: {}".format(self.last_read_len_req, len(self.recv_pkt), hex(cmd)))
				return 'invalid len mismatch', cmd
			else:
				self.pkt_err_cnt = 0

		return 'ok', cmd

	def execute(self):
#		self.crashinfo() # get crash info for 5GB with AT!GCDUMP after ramdump and replug without power cycle"""
		self.ramdump()

		# send sahara reset packet
		print ("Resetting device")
		self.create_reset_pkt()
		self.s.send(self.pkt)
			
	def crashinfocmd(self, req_cmd):
		status = ''
		while status != 'ok':
			self.create_command_pkt(req_cmd)
			self.raw_data = False
			self.s.send(self.pkt)
			status, cmd = self.sahara_recv()
			if status != 'ok' or cmd != SAHARA_CMD_CMD_EXECUTE_RESP:
				print("crash info cmd: {} response - cmd: {}, status: {}".format(req_cmd, cmd, status))

		cmd = int.from_bytes(self.recv_pkt[8:12], 'little')
		len = int.from_bytes(self.recv_pkt[12:16], 'little')
		status = ''
		while status != 'ok':
			self.create_cmd_exec_data_pkt(cmd, len)
			self.raw_data = True
			self.s.send(self.pkt)
			status, cmd = self.sahara_recv()
			if status != 'ok':
				print("crash info data status: {}".format(status))

		return self.recv_pkt

	def crashinfo(self):
		print("Start collecting crashinfo")
		self.create_switch_mode_pkt(SAHARA_MODE_COMMAND)
		self.s.send(self.pkt)
		self.raw_data = False
		status, cmd = self.sahara_recv()
		if status != 'ok':
			print("HELLO CMD RECV FAIL - {}".format(status))
			return
		if SAHARA_CMD_HELLO != cmd:
			print("HELLO CMD FAIL - crashinfo protocol not supported")
			return

		self.create_hello_resp_pkt(SAHARA_MODE_COMMAND)
		self.s.send(self.pkt)
		status = ''
		while cmd != SAHARA_CMD_CMD_READY or status != 'ok':
			print("Waiting for SAHARA_CMD_CMD_READY")
			self.raw_data = False
			status,cmd = self.sahara_recv()
			if status != 'ok' or cmd != SAHARA_CMD_CMD_READY:
				print("waiting for cmd ready - status: {}, cmd: {}".format(status, cmd))

		try:
			print("opening file: {}".format("crashinfo.txt"))
			self.of = open(self.logger.getRamdumpDir() + '/' + 'crashinfo.txt', 'wb')
		except Exception as e:
			print("file open error: {}".format(e))
			return 'file open error'

		if self.of is None:
			return 'file error'

		print("Crash Summary")
		self.of.write(b'Crash Summary: \n')
		# start sending commands
		
		buf = self.crashinfocmd(SAHARA_EXEC_CMD_SWI_BOOT_VERSION_READ)
		print("SBL Version: {}".format(buf.decode()))
		self.of.write(b'SBL Version: ')
		self.of.write(buf)
		self.of.write(b'\n')
		
		buf = self.crashinfocmd(SAHARA_EXEC_CMD_SWI_PRODUCT_MODEL_READ)
		print("Product Model: {}".format(buf.decode()))
		self.of.write(b'Product Model: ')
		self.of.write(buf)
		self.of.write(b'\n')
		
		buf = self.crashinfocmd(SAHARA_EXEC_CMD_SWI_SERIAL_NUM_READ)
		print("Serial Num: {}".format(buf.decode()))
		self.of.write(b'Serial Num: ')
		self.of.write(buf)
		self.of.write(b'\n')

		buf = self.crashinfocmd(SAHARA_EXEC_CMD_SWI_CRASH_INFO_READ)
		print("Crash Info: {}".format(buf.decode()))
		self.of.write(b'Crash Info: ')
		self.of.write(buf)
		self.of.write(b'\n')

		print("End Basic Crash Information")
		self.of.write(b'End Basic Crash Information\n')

		self.of.flush()
		os.fsync(self.of.fileno())
		self.of.close()
		self.of = None

	def ramdump(self):
		print("Start collecting ramdump")
		self.create_switch_mode_pkt(SAHARA_MODE_MEMORY_DEBUG)
		self.s.send(self.pkt)
		self.raw_data = False
		status, cmd = self.sahara_recv()
		if status != 'ok':
			print("HELLO CMD2 RECV FAIL - {}".format(status))
			return
		if SAHARA_CMD_HELLO != cmd:
			print("HELLO CMD2 FAIL - ramdump protocol not supported")
			return

		self.create_hello_resp_pkt(SAHARA_MODE_MEMORY_DEBUG)
		self.s.send(self.pkt)
		status = ''
		while cmd != SAHARA_CMD_MEMORY_DEBUG or status != 'ok':
			print("Waiting for SAHARA_CMD_MEMORY_DEBUG")
			status,cmd = self.sahara_recv()
			if status != 'ok' or cmd != SAHARA_CMD_MEMORY_DEBUG:
				print("getting mem table addr/len - status: {}, cmd: {}".format(status, cmd))
		
		# skip cmd(u32) and len(u32)
		self.mem_table_addr = int.from_bytes(self.recv_pkt[8:12], 'little')
		self.mem_table_len = int.from_bytes(self.recv_pkt[12:16], 'little')

		# mem table request
		status = ''
		while status != 'ok':
			self.create_mem_read_pkt(self.mem_table_addr, self.mem_table_len)
			self.raw_data = True
			self.s.send(self.pkt)
			status, cmd = self.sahara_recv()
			if status != 'ok':
				print("mem table request status: {}".format(status))

		status = self.process_mem_table()
		self.raw_data = False
		
		if self.mem_info.current_region >= self.mem_info.max_num_region:
			print("invalid memory table")
			return

		# read memory data from each region
		while self.mem_info.current_region < self.mem_info.max_num_region:
			mem_region = self.mem_info.mem_region[self.mem_info.current_region]
			if mem_region.addr == 0 or mem_region.len == 0:
				self.of = open(self.logger.getRamdumpDir() + '/' + mem_region.filename, 'wb')
				self.of.close()
				self.of = None

				# Increment the memory region index
				self.mem_info.current_region += 1
				continue

			status = ''
			while status != 'ok' and status != 'invalid end of image':
				self.create_next_read_req_pkt()
				self.raw_data = True
				self.s.send(self.pkt)
				status, cmd = self.sahara_recv()
				self.raw_data = False
				if status != 'ok':
					print("file transfer status: {}".format(status))

			if status == 'invalid end of image':
				break

			resl = self.process_mem_region()
			if resl != 'ok' and resl != 'invalid':
				print("error processing memory regions: {}".format(resl))
				break

		print("end of memory regions")

	def create_command_pkt(self, cmd):
		self.pkt = bytearray()
		self.pkt.extend(SAHARA_CMD_CMD_EXECUTE.to_bytes(4, 'little'))
		self.pkt.extend(LEN_SAHARA_CMD_COMMAND_EXECUTE.to_bytes(4, 'little'))
		self.pkt.extend(cmd.to_bytes(4, 'little'))
		self.last_read_len_req = LEN_SAHARA_CMD_COMMAND_EXECUTE_RESPONSE

	def create_switch_mode_pkt(self, mode):
		self.pkt = bytearray()
		self.pkt.extend(SAHARA_CMD_CMD_SWITCH.to_bytes(4, 'little'))
		self.pkt.extend(LEN_SAHARA_CMD_COMMAND_SWITCH_MODE.to_bytes(4, 'little'))
		self.pkt.extend(mode.to_bytes(4, 'little'))
		self.last_read_len_req = LEN_SAHARA_CMD_HELLO

	def create_hello_resp_pkt(self, mode):
		self.pkt = bytearray()
		self.pkt.extend(SAHARA_CMD_HELLO_RESP.to_bytes(4, 'little'))
		self.pkt.extend(LEN_SAHARA_CMD_HELLO_RESPONSE.to_bytes(4, 'little'))
		self.pkt.extend(SAHARA_CURRENT_VERSION.to_bytes(4, 'little'))
		self.pkt.extend(SAHARA_COMPATIBLE_VERSION.to_bytes(4, 'little'))
		status = 0
		self.pkt.extend(status.to_bytes(4, 'little'))
		self.pkt.extend(mode.to_bytes(4, 'little'))
		reserved = 0
		self.pkt.extend(reserved.to_bytes(4, 'little'))
		self.pkt.extend(reserved.to_bytes(4, 'little'))
		self.pkt.extend(reserved.to_bytes(4, 'little'))
		self.pkt.extend(reserved.to_bytes(4, 'little'))
		self.pkt.extend(reserved.to_bytes(4, 'little'))
		self.pkt.extend(reserved.to_bytes(4, 'little'))

		self.last_read_len_req = LEN_SAHARA_CMD_MEMORY_DEBUG if mode == SAHARA_MODE_MEMORY_DEBUG else LEN_SAHARA_CMD_COMMAND_READY

	def create_cmd_exec_data_pkt(self, cmd, len):
		self.pkt = bytearray()
		self.pkt.extend(SAHARA_CMD_CMD_EXECUTE_DATA.to_bytes(4, 'little'))
		self.pkt.extend(LEN_SAHARA_CMD_COMMAND_EXECUTE_DATA.to_bytes(4, 'little'))
		self.pkt.extend(cmd.to_bytes(4, 'little'))
		self.last_read_len_req = len

	def create_mem_read_pkt(self, addr, length):
		self.pkt = bytearray()
		self.pkt.extend(SAHARA_CMD_MEMORY_READ.to_bytes(4, 'little'))
		self.pkt.extend(LEN_SAHARA_CMD_MEMORY_READ.to_bytes(4, 'little'))
		self.pkt.extend(addr.to_bytes(4, 'little'))
		self.pkt.extend(length.to_bytes(4, 'little'))
		self.last_read_len_req = length

	def create_next_read_req_pkt(self):
		read_len = 0
		addr = self.mem_info.mem_region[self.mem_info.current_region].next_read
		end_addr = self.mem_info.mem_region[self.mem_info.current_region].addr + self.mem_info.mem_region[self.mem_info.current_region].len
		if (end_addr - self.mem_info.mem_region[self.mem_info.current_region].next_read) > SAHARA_MAX_MEM_READ_LEN:
			read_len = SAHARA_MAX_MEM_READ_LEN
		else:
			read_len = end_addr - self.mem_info.mem_region[self.mem_info.current_region].next_read

		self.create_mem_read_pkt(addr, read_len)

	def create_reset_pkt(self):
		self.pkt = bytearray()
		self.pkt.extend(SAHARA_CMD_RESET.to_bytes(4, 'little'))
		self.pkt.extend(LEN_SAHARA_CMD_RESET.to_bytes(4, 'little'))
		selflast_read_len_req = LEN_SAHARA_CMD_RESET

	def process_mem_table(self):
		mem_size = 0
		mem_region_num = len(self.recv_pkt) / BIN_MEMORY_REGION_SIZE
		self.mem_info.max_num_region = int(mem_region_num)
		print("process_mem_table - max num regions: {}".format(mem_region_num))
		self.mem_info.current_region = 0
		for i in range(0, self.mem_info.max_num_region):
			pkt_memory_region = self.recv_pkt[i*BIN_MEMORY_REGION_SIZE:(i*BIN_MEMORY_REGION_SIZE) + (BIN_MEMORY_REGION_SIZE)]
			new_memory_region = MemoryRegion()
			new_memory_region.save_pref = int.from_bytes(pkt_memory_region[:4], 'little')
			new_memory_region.addr = int.from_bytes(pkt_memory_region[4:8], 'little')
			new_memory_region.len = int.from_bytes(pkt_memory_region[8:12], 'little')
			new_memory_region.description = pkt_memory_region[12:SAHARA_MEM_REGION_NAME_SIZE + 12].decode('utf-8').rstrip('\x00')
			new_memory_region.filename = pkt_memory_region[SAHARA_MEM_REGION_NAME_SIZE + 12: SAHARA_MEM_REGION_NAME_SIZE + 12 + SAHARA_MEM_REGION_NAME_SIZE].decode('utf-8').rstrip('\x00')
			new_memory_region.next_read = new_memory_region.addr
			mem_size += new_memory_region.len
			print("process_mem_table - region: {}, addr: {}, len: {}, filename:{}".format(i + 1, hex(new_memory_region.addr), new_memory_region.len, new_memory_region.filename))
			self.mem_info.mem_region.append(new_memory_region)

		self.mem_info.total_mem_size = mem_size
		self.mem_info.total_mem_read = 0

	def process_mem_region(self):
		mem_region = self.mem_info.mem_region[self.mem_info.current_region]
		end_addr = mem_region.addr + mem_region.len

		# The start address for this packet should have been mem_region.next_read
		# and the packet length should be len(self.pkt)

		# Open the file, if this is the first read
		if mem_region.addr == mem_region.next_read:
			# create output file
			try:
				print("opening file: {}".format(mem_region.filename))
				self.of = open(self.logger.getRamdumpDir() + '/' + mem_region.filename, 'wb')
			except Exception as e:
				print("file open error: {}".format(e))
				return 'file open error'

		if self.of is None:
			return 'file error'

		length = len(self.recv_pkt)
		self.of.write(self.recv_pkt)
		self.recv_pkt = None

		self.reg_percent_complete = int((((mem_region.next_read + length) - mem_region.addr) * 100) / mem_region.len)
		if (self.reg_percent_complete >= self.reg_prev_percent_complete + 10) or (self.reg_percent_complete == 100):
			print("region: {} of {} - {}% complete".format(self.mem_info.current_region + 1, self.mem_info.max_num_region, self.reg_percent_complete))
			self.reg_prev_percent_complete = self.reg_percent_complete

		self.mem_info.total_mem_read += length

	    # Close the file if this is the last read
		if (mem_region.next_read + length) >= end_addr:
			self.of.flush()
			os.fsync(self.of.fileno())
			self.of.close()
			self.of = None

			# Increment the memory region index, and reset the read pointer
			self.reg_percent_complete = 0
			self.reg_prev_percent_complete = 0
			self.mem_info.current_region += 1
		else:
        	# Increment the Read index
			mem_region.next_read += length
			#print("region: {}, next_read: {}".format(self.mem_info.current_region + 1, hex(mem_region.next_read)))

		return 'ok'

if __name__ == '__main__':
	# apt-get install python-argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("-p", "--pw", default=None)
	parser.add_argument("-f", "--filter_file", default=None)
	parser.add_argument("-r", "--router_ip", default='192.168.0.1')
	value = parser.parse_args()

	if value.pw == None:
		print("Usage: cp_qxdm_logger.py --pw=password [--filter_file=file.sqf]")
		print(" NOTE: you must enable the qxdm proxy on the router under /config/system/qxdmproxy")
		print('       set mode "lan"; set enabled true\n')
		sys.exit(1)

	if value.router_ip == None:
		print("Usage: cp_qxdm_logger.py --router_ip=192.168.0.1 [--filter_file=file.sqf]")
		print(" NOTE: you must enable the qxdm proxy on the router under /config/system/qxdmproxy")
		print('       set mode "lan"; set enabled true\n')
		sys.exit(1)

	qxdm_logger = QxdmLogger()	
	get_qxdm_cfg, res = qxdm_logger.get_cfg(value.pw, value.router_ip)
	if res != 1:
		print('Failed to get config, possible bad password or incompatible router version')
		sys.exit(1)

	#qxdm_logger.getRamdumpDir()
	#sys.exit(0)
	while True:
		try:
			if qxdm_logger.enabled != True:
				print('qxdm logging disabled on the router')
				sys.exit(1)

			if qxdm_logger.mode != 'lan':
				print('qxdm logging mode is not lan on router')
				sys.exit(1)

			if value.filter_file != None:
				qxdm_logger.filter = value.filter_file

			print ('attempting to connect on port {} to attempt {} logging'.format(qxdm_logger.port, qxdm_logger.getPortStr(qxdm_logger.port)))
			qxdm_logger.s=socket.socket()
			time.sleep (1)
			qxdm_logger.s.settimeout(10) # 10 second timeout for no response
			qxdm_logger.s.connect((value.router_ip, qxdm_logger.port))

			# QXDM and crash info are pretty much the same from the script side
			if qxdm_logger.port == QXDM_PORT or qxdm_logger.port == CRASH_INFO_PORT:
				qxdm = QXDMlog(qxdm_logger)
				resl = qxdm.execute()

			if qxdm_logger.port == RAM_DUMP_PORT:
				dump = RAMDump()
				resl = dump.execute()
				dump.deinit()

			# Try next port
			qxdm_logger.port = qxdm_logger.rotatePort(qxdm_logger.port)

		except Exception as e:
			print("Error for operation on port {}: {}, delay 1 second".format(qxdm_logger.port, e))
			qxdm_logger.port = qxdm_logger.rotatePort(qxdm_logger.port)

		time.sleep (1)



