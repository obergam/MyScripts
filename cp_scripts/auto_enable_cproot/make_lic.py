#!/usr/bin/env python3
import requests
from _signing_cert import SIGNING_CERT as my_signing_cert


url = 'http://license-server.cp.local/cert/new/signed'

def create_license(mac_addr):
    data = {'duration': "1",
        'macs': (None, mac_addr),
        'features':(None, "f0c200da-ff54-11e9-96a9-acde48001122"),
        'signing_cert' : ('filename', my_signing_cert, 'application/pkix-cert')}

    r = requests.post(url, files=data);
    return r.text

if __name__ == "__main__":
    import sys
    print(create_license(sys.argv[1]))
