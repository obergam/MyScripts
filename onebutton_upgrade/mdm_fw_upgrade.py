#!/usr/bin/env python3
import sys
import subprocess
import random
import re
import time
from time import strftime, sleep 
import json
import os
import socket


class modem_device:
	def __init__ (self, dev_name, mdm_model, mdm_pkg, mdm_port = None):
		self.dev_name = dev_name  #uid
		self.mdm_model = mdm_model
		self.mdm_pkg = mdm_pkg
		self.mdm_port = mdm_port

class upgrade_info:
	def __init__(self, mdm_model, mdm_pkg):
		self.mdm_model = mdm_model
		self.mdm_pkg = mdm_pkg

class mdm_fw_upgrade(object):
	def __init__(self, router_password):
		self.router_password = router_password
		self.pc_ipaddr = None
		self.http_server = None

	def log(self, log_str):
		print("Log: {}".format(log_str))

	def sleep_delay(self, seconds):
		#print("Sleeping for %d seconds"%(seconds))
		orig = seconds
		while seconds != 0:
			print("Sleeping for %d seconds ( %04d )"%(orig, seconds), end='\r')
			sys.stdout.flush()
			sleep(1)
			seconds-=1
		print("")

	def get_val(self,pth,timeout=20):
		get_req = 'curl -s  -u admin:{} --connect-timeout {} -X GET http://192.168.0.1/api/{}'.format(self.router_password, timeout, pth)
		proc = subprocess.Popen(get_req.split(),stdout=subprocess.PIPE)
		resp = proc.communicate()[0]
		#communicate returns a bytes array. Need to convert to string so we can do a regular expression match
		try:
			resp = resp.decode("utf-8")
		except Exception as e:
			self.log("get_val, no decode")
			return None, -1

		try:
			json_data = json.loads(resp)
			if json_data == None:
				self.log("get_val, no json")
				return None, -1
			if json_data['success'] == False:
				#self.log("get_val, returned false")
				return None, 0
			else:
				#self.log("get_val, returned true")
				return json_data['data'],1
		except:
			self.log("get_val, exception")
			return None,-1


	def put_val(self,pth,val,timeout=20):
		put_req = 'curl -s  -u admin:{} --connect-timeout {} -X PUT http://192.168.0.1/api/{} -d data={}'.format(self.router_password,timeout,pth,val)
		proc = subprocess.Popen(put_req.split(),stdout=subprocess.PIPE)
		resp = proc.communicate()[0]
		#communicate returns a bytes array. Need to convert to string so we can do a regular expression match
		try:
			resp = resp.decode("utf-8")
		except Exception as e:
			return None,-1

		try:
			json_data = json.loads(resp)
			if json_data == None:
				return None,-1
			if 'success' not in json_data:
				return None,-1

			if json_data['success'] == False:
				return None,0
			else:
				data = json_data['data']
				return data,1
		except:
			return None,-1

	def get_upgrade_info(self):
		# read the json files from the httpserver directory ( MODEM/firmware-xxx.json )
		# create list of modules we have files for and return it
		upgradeinfo = []
		base_path = "./MODEM"
		files = os.listdir("./MODEM")
		self.log("Searching MODEM subdirectory for update files. Files found: {}".format(files))
		for file in files:
			if file.endswith(".json"):
				#print("File: {}".format(file))
				#grab the module name
				try:
					fd = open(base_path + '/' + file,"r")
				except:
					self.log("Error, could not open file: {}".format(file))
					continue
				data = fd.read()
				json_data = json.loads(data)

				update_json = False
				if "over_write" not in json_data:
					json_data['over_write'] = True
					update_json = True
				if 'cradlepoint' in json_data['url']:
					url = json_data['url']
					new_url = self.make_url(url)
					json_data['url'] = new_url
					update_json = True
				if update_json:
					write_data = json.dumps(json_data)
					fd.close()
					fd = open(base_path + '/' + file,"w")
					fd.write(write_data)
					fd.close()

				#TODO: should add over_write to json as well as update the url to point to our local server in the json file if needed
				model = json_data['product_name']
				
				#not all update files have pkg versions.
				pkg = None
				try:
					pkg = json_data['package_version']
				except:
					pass
				upgrade = upgrade_info(model, pkg)
				self.log("Found update files for model: {}".format(model))
				upgradeinfo.append(upgrade)
		return upgradeinfo

	def enable_lan_gateway(self):
		# TODO: see if gateway is already set, if so don't set again to save on flash writes
		# 
		# set /config/system/internal_svcs/use_route to true and set gateway to address of the computer this script is running on
		#lan_gateway_req_enable = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '-X', 'PUT', 'http://192.168.0.1/api/config/system/internal_svcs/use_route', '-d', 'data=true']
		try:
			pth = 'config/system/internal_svcs/use_route'
			val = 'true'
			data,resp = self.put_val(pth,val)
			if resp != 1:
				return False
	
			#lan_gateway_req_ipaddr = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '-X', 'PUT', 'http://192.168.0.1/api/config/system/internal_svcs/gateway', '-d', 'data=\"{}\"'.format(self.pc_ipaddr)]
			pth = 'config/system/internal_svcs/gateway'
			val = '\"{}\"'.format(self.pc_ipaddr)
			data,resp = self.put_val(pth,val)
			if resp != 1:
				return False
			self.log("Enabled LAN gateway")
			return True
		except Exception as e:
			self.log("enable_lan_gateway failed: {}".format(e))
			return False

	def make_url(self, cur_url):
		#skip http:// and then do a split on the '/' char to get the directory parts
		parts = cur_url[7:].split('/')
		new_url = 'http://{}:8000/{}/{}'.format(self.pc_ipaddr, parts[len(parts)-2], parts[len(parts)-1])  
		self.log("cur_url: {}, new_url: {}".format(cur_url, new_url)) 
		return new_url

	def modify_upgrade_url(self):
		try:
			# read current upgrade url from /config/system/admin/upgrade_url
			#  example: http://www.cradlepoint.com/files/uploads/MBR1400v2/firmware-mbr1400v2.json
			# modify it to point to the local server
			#  example: http://192.168.50.112:8000/MBR1400v2/firmware-mbr1400v2.json
			#get_url_req = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '-X', 'GET', 'http://192.168.0.1/api/config/system/admin/upgrade_url']
			pth = 'config/system/admin/upgrade_url'
			data, resp = self.get_val(pth)
			if resp != 1:
				return False
	
			#take the URL apart and put back together
			url = data
			new_url = self.make_url(url)   
			if self.pc_ipaddr in url:
				self.log("url already set, don't set again")
				return True
	
			#self.log("cur upgrade_url: {}, new upgrade_url: {}".format(url,new_url))
			#put_url_req = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '-X', 'PUT', 'http://192.168.0.1/api/config/system/admin/upgrade_url', '-d', 'data=\"{}\"'.format(new_url)]
			pth = 'config/system/admin/upgrade_url'
			val = '\"{}\"'.format(new_url)
			data,resp = self.put_val(pth,val)
			if resp == 1:
				return True
			else:
				return False
		except Exception as e:
			self.log("modify_upgrade_url failed: {}".format(e))
			return False

	def launch_http_server(self):
		self.log("Launch http server")
		http_url = "python3 ./http_server.py"
		print("ssh_url: {}".format(ssh_url))
		try:
			self.http_server = subprocess.Popen(http_url.split())
			return True
		except Exception as e:
			self.log("Failed to launch http server: {}".format(e))
			return False

	def kill_http_server(self):
		if self.http_server:
			self.log("Kill http server")
			self.http_server.terminate()

	def get_attached_modem_devices(self):
		# get list of modules currently plugged on router
		#wan_devices_request = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '-X', 'GET', 'http://192.168.0.1/api/status/wan/devices']

		pth = 'status/wan/devices'
		data, resp = self.get_val(pth)
		devices = data
		attached_devices = []
		for dev in devices:
			#print("device: {}".format(dev))
			#print("data: {}".format(devices[dev]))
			if 'ethernet-wan' not in dev and 'wwan' not in dev:
				self.log("found attached device: {}".format(dev))
				pth = 'status/wan/devices/{}'.format(dev)
				data, resp = self.get_val(pth)
				#wan_device_req = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '-X', 'GET', 'http://192.168.0.1/api/status/wan/devices/{}'.format(dev)]
				device_data = data
				#self.log("Device data: {}".format(device_data))
				try:
					mdl = device_data['info']['mfg_model']
				except:
					self.log("No model found for device {}, skipping".format(dev))
					continue

				pkg = None
				try:
					pkg = device_data['diagnostics']['VER_PKG']
				except:
					self.log("No package version found for device {}, not mandatory, keep going".format(dev))
				
				port = None
				try:
					port = device_data['info']['port']
				except:
					self.log("Did not find a port for device {}, not needed, keep going")
				mdm_dev = modem_device(dev, mdl, pkg, mdm_port = port)
				attached_devices.append(mdm_dev)

		return attached_devices

	def get_carrier_from_pkg(self, pkg_string):
		# not all modules add the carrier load into their pkg string. If they support carrier switching they do.
		# sample string: "05.05.16.02_VZW,005.013_100"
		carrier = None
		pieces = pkg_string.split(',') #fw version and PRI are separated by comma
		pieces = pieces[0].split('_') # fw version and carrier load are separated by underscore
		if len(pieces) > 1:
			carrier = pieces[1]
		#self.log("Carrier: {}".format(carrier))
		return carrier

	def reconcile(self, upgrade_info, attached_devices):
		# compare attached devices to supported modules to find any matches
		# if there is an attached device that supports upgrade but doesn't have matching supported, log it
		# return list of attached_devices that we need to test
		devices_to_test = []
		for mdm_device in attached_devices:
			#grab whether device supports upgrad
			#supports_upgrade_request = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '-X', 'GET', 'http://192.168.0.1/api/status/wan/devices/{}/info/supports_mdm_upgrade'.format(mdm_device.dev_name)]
			pth = 'status/wan/devices/{}/info/supports_mdm_upgrade'.format(mdm_device.dev_name)
			data, resp = self.get_val(pth) 
			if resp != 1:
				self.log("ERROR: Could not read supports_mdm_upgrade from device: {}, skipping".format(mdm_device))
				continue
			supports_upgrade = data
			#self.log("modem: {}, supports upgrade: {}".format(model,supports_upgrade))
			if supports_upgrade:
				for info in upgrade_info:
					if info.mdm_model == mdm_device.mdm_model:
						if info.mdm_pkg:
							upgrade_carrier = self.get_carrier_from_pkg(info.mdm_pkg)
							module_carrier = self.get_carrier_from_pkg(mdm_device.mdm_pkg)
							if upgrade_carrier not in module_carrier:
								self.log("Did not find matching carrier. Upgrade carrier: {}, module carrier: {}".format(upgrade_carrier, module_carrier))
								continue
						self.log("Reconcile, add modem device: {}, model: {} , pkg: {} to updateable list".format(mdm_device.dev_name, mdm_device.mdm_model,info.mdm_pkg))
						devices_to_test.append(mdm_device)

		return devices_to_test

	def test_for_update_available(self, device):
		try:
			pth = 'status/wan/devices/{}/ob_upgrade/check'.format(device.dev_name)
			val = 1
			data,resp = self.put_val(pth,val)
			self.log("test_for_update_available: data: {}, resp: {}".format(data, resp))
			if resp == 1 and data:
				if "update_available" not in data:
					return False
				return True
			else:
				return False
			#put_url_req = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '-X', 'PUT', 'http://192.168.0.1/api/status/wan/devices/{}/ob_upgrade/check'.format(device.dev_name), '-d', 'data=1']
		except Exception as e:
			self.log("test_for_update_available failed: {}".format(e))
			return False

	def run_upgrade(self, mdm_device):
		try:
			#Make sure an upgrade isn't already running
			self.log("\r\n========================= Begin fw upgrade for device: {}, with modem module: {} ========================\r\n".format(mdm_device.dev_name, mdm_device.mdm_model))
			start_time = time.time()
			#upgrade_status_request = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '--connect-timeout', '20', '-X', 'GET', 'http://192.168.0.1/api/status/system/fw_upgrade']
			pth_upgrade = 'status/system/fw_upgrade'
			data, resp = self.get_val(pth_upgrade)
			if resp == 1 and data:
				self.log("ERROR: upgrade already running, reboot router first. Upgrade status: {}, data: {}".format(resp, data))
				return False
						
	
			#put_path = 'http://192.168.0.1/api/status/wan/devices/{}/ob_upgrade/fw_update'.format(mdm_device.dev_name)
			#put_data = 'data={\"ts\":12345}'
			pth = 'status/wan/devices/{}/ob_upgrade/fw_update'.format(mdm_device.dev_name)
			val = '{\"ts\":12345}'
			data,resp = self.put_val(pth,val)
			#put_url_req = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '--connect-timeout', '20', '-X', 'PUT', put_path, '-d', put_data]
			#self.log("upgrade put url req: {}".format(put_url_req))
			if resp != 1:
				self.log("ERROR: failed to launch upgrade")
				return False
			if "ts" not in data:
				self.log("ERROR: failed to launch upgrade, data: {}, resp: {}".format(data, resp))
				return False
			done = False
			temp_count = 0
			while not done:
				cur_time = time.time()
				elapsed_time = int(cur_time - start_time)

				self.log("Elapsed time: {} seconds".format(elapsed_time))
				data, resp = self.get_val(pth_upgrade)
				if resp != -1:
					if data:
						status = "state:{}".format(data['state']) 
						if 'progress' in data:
							progress = data['progress']
							progress = int(float(data['progress'])*100)
							status += ", progress: {}%".format(progress)
						self.log("upgrade status: {}, data: {}".format(status,data))
					else:
						self.log("upgrade status: waiting for it to start")
						if elapsed_time > 60:
							self.log("ERROR: modem did not start updating within 60 seconds, bailing")
							return False
					self.sleep_delay(10)
				else:
					self.log("No router response, assume upgrade finished and router is rebooting")
					done = True
		
			#search only for the specific device
			devices_found = self.wait_for_router_ready(mdm_device.dev_name)
			result = None
			if len(devices_found) > 0:
				self.log("Modem upgraded and plugged successfully")
				result = True
			else:
				self.log("Modem failed to plug after upgrade, check logs")
				restult = False
			self.log("\r\n========================= END fw upgrade for device: {}, with modem module: {}, success: {} ========================\r\n".format(mdm_device.dev_name, mdm_device.mdm_model, result))
			return result
		except Exception as e:
			self.log("run_upgrade failed: {}".format(e))
			return False


	def wait_for_router_ready(self, find_device=None):
		# Make sure router is up and all modems have finished configuring
		# Return a list of all the devices found
		start_time = time.time()
		done = False
		found_devices = []
		iters = 0
		while not done:
			if iters > 0:
				self.sleep_delay(5)
			iters+=1
			cur_time = time.time()
			self.log("Trying to find router and ready modem(s) for {} seconds so far.".format(int(cur_time-start_time)))
			found_devices = []
			if cur_time - start_time > 300:
				self.log("Not ready after 5 minutes, giving up.")
				return []

			pth = 'status/wan/devices'
			data, resp = self.get_val(pth)
			#wan_devices_request = ['curl', '-s','', '-u', 'admin:%s'%self.router_password, '--connect-timeout', '20', '-X', 'GET', 'http://192.168.0.1/api/status/wan/devices']
			#self.log("wait_for_router_ready data: {}, resp: {}".format(data, resp))
			if resp == -1 or data is None or len(data) == 0:
				self.log("Router not up yet, wait")
				continue
			devices = data
			ready_count = 0
			not_ready_count = 0
			for dev in devices:
				#print("device: {}".format(dev))
				#print("data: {}".format(devices[dev]))
				if 'ethernet-wan' not in dev and 'wwan' not in dev:
					#self.log("found device: {}".format(dev))
					status = devices[dev]['status']['summary']
					statii = ['unconfigured', 'unplugged']
					if status in statii:
						self.log("Found device {} not ready, state: {}".format(dev,status))
						not_ready_count += 1
					else:
						self.log("Found device {} ready".format(dev))
						if find_device == None or dev == find_device:
							found_devices.append(dev)
							ready_count += 1

			if not_ready_count > 0:
				self.log("Some modems still plugging, wait for a bit")
				continue
			if ready_count == 0:
				if find_device:
					self.log("Device {} not yet found, wait for a bit".format(find_device))
				else:
					self.log("No ready modems found, wait for a bit")
				continue

			if find_device and find_device not in found_devices:
				self.log("Have not found the desired device {} yet".format(find_device))
				continue

			done = True
		return found_devices

	def get_ipv4_address(self):
		"""
		Returns IP address(es) of current machine.
		:return:
		"""

		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		s.connect(("8.8.8.8", 80))
		addr = s.getsockname()[0]
		s.close()
		return addr
		"""
		p = subprocess.Popen(["ifconfig"], stdout=subprocess.PIPE)
		ifc_resp = p.communicate()
		ifc_data = ifc_resp[0].decode("utf-8")

		patt = re.compile(r'inet\s*\w*\S*:\s*(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
		resp = patt.findall(ifc_data)
		print("addrs: {}".format(resp))
		for addr in resp:
			if '192.168.0' in addr:
				print("pc_ipaddr: {}".format(addr))
				return addr
		return None
		"""

	def run_ssh (self):
		password = '1415'+self.router_password[4:8]
		ssh_url = "sshpass -p {} ssh cproot@192.168.0.1".format(password)
		print("ssh_url: {}".format(ssh_url))
		p = subprocess.Popen(ssh_url.split(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		#self.log("open")
		#print(p.communicate(input=password.encode("utf-8")))
		self.log("com1")
		try:
			print(p.communicate(input='ls\r\n', timeout=10))
		except:
			pass
		#print(p.communicate(input='ls\r\n'.encode("utf-8")))
		#print(p.communicate(input='ls\r\n'.encode("utf-8")))
		p.terminate()
		self.log("com2")

	def run_test(self):

		#self.run_ssh()
		#return False

		self.pc_ipaddr = self.get_ipv4_address()
		if self.pc_ipaddr is None:
			self.log("Error, could not get ipv4 address for this PC")
			return False

		devices_found = self.wait_for_router_ready()
		if len(devices_found) == 0:
			self.log("Error, didn't find any modems")
			return False

		upgrade_info = self.get_upgrade_info()
		if len(upgrade_info) == 0:
			self.log("Error, didn't find any upgrade files")
			return False
		attached_devices = self.get_attached_modem_devices()
		devices_to_test = self.reconcile(upgrade_info, attached_devices)
		if len(devices_to_test) == 0:
			self.log("Error, no modules found to test")
			return False

		res = self.enable_lan_gateway()
		if res == False:
			self.log("Error, failed to enable lan gateway")
			return False

		res = self.modify_upgrade_url()
		if res == False:
			self.log("Error, failed to modify upgrade url")
			return False

		res = self.launch_http_server()
		if res == False:
			self.log("Error, failed to launch http server")
			return False

		update_fail_count = 0
		for mdm_device in devices_to_test:
			#self.log("Current device to test, device name: {}, modem model: {}".format(mdm_device.dev_name, mdm_device.mdm_model))
			if self.test_for_update_available(mdm_device) == False:
				self.log("ERROR: Device {} failed to find an upgrade file!".format(mdm_device.dev_name))
				update_fail_count+=1
				continue

			resl = self.run_upgrade(mdm_device)
			if resl == False:
				self.log("Error, failed to update device {}".format(mdm_device.dev_name))
				update_fail_count+=1
				continue

			#router reboots between each module update, make sure it is back up
			self.wait_for_router_ready()

		try:
			self.kill_http_server()
		except:
			pass

		if update_fail_count > 0:
			self.log("Done with errors")
			return False
		self.log("Done")
		return True


if __name__ == "__main__":
	admin_password = ''
	if len(sys.argv) == 2:
		admin_password = sys.argv[1]
	else:
		#admin_password = input('Enter admin password: ')
		#for testing only - override password
		admin_password = '442cfedd'
	
	#get pc ip address

	tester = mdm_fw_upgrade(admin_password)
	res = tester.run_test()
	if res == False:
		tester.log("ERROR: test failed")
	else:
		tester.log("SUCCESS")


