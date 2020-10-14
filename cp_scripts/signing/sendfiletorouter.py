# tools/signing/sendfiletorouter.py
#
# Copyright (c) 2020 CradlePoint, Inc. <www.cradlepoint.com>.
# All rights reserved.
#
# This file contains confidential information of CradlePoint, Inc. and your
# use of this file is subject to the CradlePoint Software License Agreement
# distributed with this file. Unauthorized reproduction or distribution of

# this file is subject to civil and criminal penalties.
#

import os
import sys
import time
import getopt
import paramiko
import threading

try:
    from http.server import HTTPServer, SimpleHTTPRequestHandler # Python 3
except ImportError:
    from SimpleHTTPServer import BaseHTTPServer
    HTTPServer = BaseHTTPServer.HTTPServer
    from SimpleHTTPServer import SimpleHTTPRequestHandler # Python 2

script_path = os.path.dirname(os.path.realpath(__file__))

http_client_py = "echo -e \"import sys, argparse, urllib.request \n\
parser = argparse.ArgumentParser() \n\
parser.add_argument('-f', dest='from_url', required=True) \n\
parser.add_argument('-t', dest='to_path', required=True) \n\
args = parser.parse_args(sys.argv[1:]) \n\
urllib.request.urlretrieve(args.from_url, args.to_path) \n\
\" > {}/http_client.py\n"


def recv(sh):
    buf = ''
    while not buf.endswith(' # ') and not buf.endswith(']$'):
        a = sh.recv(1)
        try:
            buf += a.decode()

        except AttributeError:
            buf += a

    if "err" in buf.lower():
        print(buf)
    #print("recv:", buf)
    return buf

def get_cert_types(routerip, adminpwd, sshport):
    print("- Opening SSH connection to router at {}:{}...".format(routerip, sshport))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(routerip, port=sshport, username="admin", password=adminpwd)
    sh = ssh.invoke_shell()
    recv(sh)

    sh.send("cat /status/fw_info/sign_cert_types\n")
    return recv(sh)

def send_file(hostip, hostport, localfiles, routerip, adminpwd, remotedst, sshport, licensefile):

    # get location of file
    localfile_path = os.path.dirname(os.path.realpath(localfiles[0]))
    os.chdir(localfile_path)

    print("- Starting HTTP file server on port {}...".format(hostport))
    server = HTTPServer(('', hostport), SimpleHTTPRequestHandler)
    thread = threading.Thread(target = server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        print("- Reading techsupport license from '" + str(licensefile) + "'")
        cf = open(licensefile, "r")
    except:
        print("File not found. Please specify the correct path to techsupport license file, i.e. -l '" + str(licensefile) + "'\n")
        sys.exit(1)

    cert_blob = cf.read()
    cf.close()
    lic_start = cert_blob.find("{")
    cert_blob = cert_blob[lic_start:].replace("\n", "").replace("\r", "").replace("  ", "")
    if "Enable TechSupportAccess" not in cert_blob:
        print('TechSupportAccess license not found in file provided.')
        sys.exit(2)

    print("- Opening SSH connection to router at {}:{}...".format(routerip, sshport))
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(routerip, port=sshport, username="admin", password=adminpwd)
    sh = ssh.invoke_shell()
    recv(sh)
    sh.send('put /control/system/techsupport_access ' + cert_blob + '\n')
    lic_out = recv(sh)
    time.sleep(1)
    if "Invalid value" in lic_out:
        print('Problem applying license to techsupport_access control node: \n' + str(lic_out))
    sh.send('su-cmds\n')
    su_out = recv(sh)
    if "False" in su_out:
        sh.send('su-cmds\n')
        su_out = recv(sh)
        # Because su-cmds will toggle su privilege reported, need to verify a second attempt reports False before exiting.
        if "False" in su_out:
            print('Applying TechsupportAccess license was unsuccessful, su-cmds returns: ' + str(su_out))
            sys.exit(3)
    sh.send("sh\n")
    recv(sh)

    sh.send("mkdir -p {}\n".format(remotedst))
    recv(sh)

    sh.send(http_client_py.format(remotedst))

    for f in localfiles:
        if not os.path.isfile(f):
            print("File {} does not exist.".format(f))
            sys.exit(1)
        filename = os.path.basename(f)
        print("- Transfering {} to {}/{}".format(filename, remotedst, filename))
        sh.send("cppython {}/http_client.py -f http://{}:{}/{} -t {}/{}\n".format(remotedst, hostip, hostport, filename, \
                remotedst, filename))
        recv(sh)

    for x in range(3):
        sh.send("ls {}\n".format(remotedst))
        ret = recv(sh)
        done = True
        for f in localfiles:
            name = os.path.basename(f)
            if not name in ret:
                    done = False
        if done:
            print("- File transfer complete")
            break

    if not done:
            print("FAILED TO TRANSFER FILES")

    server.shutdown()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", dest="hostip", default="192.168.0.5")
    parser.add_argument("-p", dest="hostport", type=int, default=8000)
    parser.add_argument("-s", dest="sshport", type=int, default=22)
    parser.add_argument("-f", dest="sourcefile", required=True)
    parser.add_argument("-r", dest="routerip", default="192.168.0.1")
    parser.add_argument("-a", dest="adminpwd", required=True)
    parser.add_argument("-d", dest="remotedest", default="/var/tmp")
    parser.add_argument("-l", dest="licensefile", default=script_path + "/techsupport.lic")    

    args = parser.parse_args(sys.argv[1:])

    print("Downloading file form http://{}:{} ({}) to {} ({})".format( \
        args.hostip, args.hostport, args.sourcefile, \
        args.routerip, args.remotedest))

    send_file(args.hostip, args.hostport, (args.sourcefile,), args.routerip, args.adminpwd, args.remotedest, args.sshport, args.licensefile)
