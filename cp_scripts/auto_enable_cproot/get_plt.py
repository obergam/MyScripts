#!/usr/bin/env python3

import requests
import xml.etree.ElementTree as ET
import sys

from _plt_client_key import client_key


def get_plt(router_ip):
    def xml_to_dict(xml_tree):
        d = {}
        for e in xml_tree:
            d[e.tag.lower()] = e.text
        return d
    key = client_key

    r = requests.post('http://{}/secured_plt'.format(router_ip), params= {'key' : key})
    if r.status_code == 200:
       return xml_to_dict(ET.fromstring(r.text))
    print('Failed to get PLT from {}'.format(router_ip))

if __name__ == "__main__":
    root = get_plt(sys.argv[1])
    for k,v in root.items():
        print("{} : {}".format(k.upper(),v))
    try:
        print("{}".format(root['default_password']))
    except KeyError:
        print("{}".format(root['wlan_mac'].replace(':', '')[-8:]))

