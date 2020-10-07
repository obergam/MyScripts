#!/usr/bin/python3
import sys
import datetime
import socket
import os
VERSION_LEN = 3
ASYNC_HDLC_FLAG = 0x7e
#DM ='/dev/ttyUSB0'

if len(sys.argv) == 1:
	print("Usage: cp_qxdm_logger.py <filter file>.sqf")
	print(" NOTE: you must enable the qxdm proxy on the router under /config/system/qxdmproxy")
	filter_file = None
else:
	filter_file = sys.argv[1]

if filter_file:
	try:
		print("Opening file {}".format(filter_file))
		f = open(filter_file, 'rb')
		buf = f.read()
	except Exception as e:
		print("Failed to open file: {}, error: {}".format(filter_file, e))
		sys.exit(1)

#Open TCP socket to 192.168.0.1 port 8888
print("Opening TCP port 8888 on 10.11.49.189")
s=socket.socket()
try:
	s.connect(('10.11.49.189', 8888))
except Exception as e:
	print("Failed to open socket, error: {}".format(e))
	sys.exit(1)

if filter_file:
	#skip over the version
	buf = buf[VERSION_LEN:]
	#cmds = buf.split( ASYNC_HDLC_FLAG )[:-1]
	print("buf len: {}".format(len(buf)))
	start = 0
	for i in range(0, len(buf)):
		#print(buf[i])
		if buf[i] == ASYNC_HDLC_FLAG:
			print("Found next command from start: {} to end: {}".format(start, i+1))
			cmd = buf[start:i+1]
			print('[OUT]: ',end='')
			print (":".join("{0:x}".format(c) for c in cmd ))
		
			s.send( cmd )
			response = s.recv(512)
			print('[IN]: ', end='')
			print(response)
			print(":".join("{0:x}".format(c) for c in response ))
			start = i + 1
	print("Done processing filter commands")

now = datetime.datetime.now()
filename = now.strftime('cp_qxdm_log_%Y_%m_%d_%H_%M.bin')

print("\nSaving log data to file {}. \n\nHit ctrl-c when done...".format(filename))

with open(filename, 'wb') as of:
	total = 0
	while 1:
		try:
			pkts = s.recv(1500)
			of.write(pkts)
			total = total + len(pkts)
			print("\rlogging %d bytes" % total, end='\r')
			#sys.stdout.flush()
			#of.flush()
			#os.fsync(of.fileno())
		except KeyboardInterrupt:
			sys.stdout.flush()
			of.flush()
			os.fsync(of.fileno())
			break
print("Closing log file and exiting")
sys.stdout.flush()
#of.flush()
#os.fsync(of.fileno())
#of.close()
s.close()
sys.exit(0)
