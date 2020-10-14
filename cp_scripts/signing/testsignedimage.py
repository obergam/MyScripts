# tools/signing/testsignedimage.py
#
# Copyright (c) 2018 CradlePoint, Inc. <www.cradlepoint.com>
# All rights reserved.
#
# This file contains confidential information of CradlePoint, Inc. and your
# use of this file is subject to the CradlePoint Software License Agreement
# distributed with this file. Unauthorized reproduction or distribution of
# this file is subject to civil and criminal penalties.
#

import os
import sys
import hashlib
import subprocess
from cp import rsa

root = sys.argv[1]
infile = sys.argv[2]

# signature validation constants
SIG_MAGIC_LEN = 5 # len of _MAGIC_BYTES
SIG_LEN = 256 # len of signature
SIG_CHAIN_LEN = 5000 # len of certificate chain
TOTAL_LEN = SIG_MAGIC_LEN + SIG_LEN + SIG_CHAIN_LEN
_MAGIC_BYTES = b'\x27\x05\x19\x56'

rootca_path = "../image/romfs/etc/rootca.crt"

all_bits = open("{}/../image/{}".format(root, infile), "rb").read()
signature_bits = all_bits[-1*TOTAL_LEN:]
magic_bits = signature_bits[0:4]
sig_bits = signature_bits[SIG_MAGIC_LEN:SIG_MAGIC_LEN+SIG_LEN]
chain_bits = signature_bits[-1*SIG_CHAIN_LEN:]

def openssl_dump_publickey_from_crt(crt_bits):
	path = "./"
	cmd = "openssl x509 -in {}/crt -pubkey -noout"
	with open("%s/crt" % path, "wb") as f:
		f.write(crt_bits)
	try:
		pubkey = subprocess.check_output(cmd.format(path).split())
		os.remove("%s/crt" % path);
		return pubkey
	except subprocess.CalledProcessError as e:
		print("This file is garbage: %s" % e)
		return False

def openssl_verify_chain_and_crt(path_to_ca, untrusted_chain_bits, crt_bits):
	path = "./"
	cmd = "openssl verify -CAfile {} -untrusted {}/untrusted_chain {}/crt"
	with open("%s/untrusted_chain" % path, "wb") as f:
		f.write(untrusted_chain_bits)
	with open("%s/crt" % path, "wb") as f:
		f.write(crt_bits)
	try:
		ret = subprocess.check_output(cmd.format(path_to_ca, path, path).split())
		os.remove("%s/untrusted_chain" % path);
		os.remove("%s/crt" % path);
	except subprocess.CalledProcessError as e:
		print("Certificate failed to verify: %s" % e)
		return False
	return True

if not magic_bits == _MAGIC_BYTES:
	print("{}: Can't find magic bytes.".format(infile))
	sys.exit(1)

if not openssl_verify_chain_and_crt("{}/{}".format(root,rootca_path), chain_bits, chain_bits):
	print("{}: Certificate chain did not validate".format(infile))
	sys.exit(1)

pubkey = openssl_dump_publickey_from_crt(chain_bits[0:chain_bits.find(b'\n-----BEGIN CERTIFICATE-----')+1])
if not pubkey:
	print("{}: Can't parse public key".format(infile))
	sys.exit(1)

hash = hashlib.sha512()
hash.update(all_bits[0:-1*(SIG_CHAIN_LEN+SIG_LEN+SIG_MAGIC_LEN)])

if not rsa.verify(pubkey, hash.hexdigest().encode()+b'\n', sig_bits):
	print("{}: Signature failed to verify".format(infile))
	sys.exit(1)

print("{} Verified OK".format(infile))
sys.exit(0)


