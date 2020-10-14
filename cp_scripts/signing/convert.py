# tools/signing/convert.py
#
# Copyright (c) 2018 CradlePoint, Inc. <www.cradlepoint.com>.
# All rights reserved.
#
# This file contains confidential information of CradlePoint, Inc. and your
# use of this file is subject to the CradlePoint Software License Agreement
# distributed with this file. Unauthorized reproduction or distribution of
# this file is subject to civil and criminal penalties.
#

import os
import sys
import argparse
import sendfiletorouter

script_path = os.path.dirname(os.path.realpath(__file__))
filestosend = ("altrootca.crt", "sig", "chain")

parser = argparse.ArgumentParser()
parser.add_argument("-i", dest="hostip", default="192.168.0.5")
parser.add_argument("-p", dest="hostport", type=int, default=8000)
parser.add_argument("-r", dest="routerip", default="192.168.0.1")
parser.add_argument("-s", dest="sshport", type=int, default=22)
parser.add_argument("-a", dest="adminpwd", required=True)
parser.add_argument("-l", dest="licensefile", default=script_path + "/techsupport.lic")

args = parser.parse_args(sys.argv[1:])

cert_types = sendfiletorouter.get_cert_types(args.routerip, args.adminpwd, args.sshport).split('\n')[1]
if "DEBUG" in cert_types and "RELEASE" not in cert_types:
    packdir = "/convert/package-release/"
elif "DEBUG" not in cert_types and "RELEASE" in cert_types:
    packdir = "/convert/package-debug/"
elif "DEBUG" not in cert_types and "RELEASE" not in cert_types:
    print("Problem occurred when checking cert types on device.")
    sys.exit()
else:
    print("The device is already able to accept DEBUG and RELEASE signed packages.")
    sys.exit()

sendfiletorouter.send_file(args.hostip, args.hostport, [script_path+packdir+x for x in filestosend], args.routerip, args.adminpwd, "/var/tmp/altcerts", args.sshport, args.licensefile)

cert_types = sendfiletorouter.get_cert_types(args.routerip, args.adminpwd, args.sshport)
print("Available certificates on device: {}".format(cert_types.split("\n")[1]))

