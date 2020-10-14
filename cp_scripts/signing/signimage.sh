#!/bin/bash

# tools/signing/signimage.sh
#
# Copyright (c) 2018 CradlePoint, Inc. <www.cradlepoint.com>
# All rights reserved.
#
# This file contains confidential information of CradlePoint, Inc. and your
# use of this file is subject to the CradlePoint Software License Agreement
# distributed with this file. Unauthorized reproduction or distribution of
# this file is subject to civil and criminal penalties
#

#
# Following script adds the following parts to the end of the firmware image.
#
# |                 |
# |  coconut.lzma   |
# |                 |
# |                 |
# +-----------------+
# | MAGIC (8 bytes) |
# +-----------------+
# | SIGNATURE of    |
# | coconut.lzma    |
# | (256 bytes)     |
# +-----------------+
# |                 |
# | CERT CHAIN      |
# | (5000 bytes)    |
# |                 |
# |                 |
# |                 |
# |                 |
# +-----------------+
#

set -e

ROOT=$1 # path to where signing folder is located
INFILE=$2 # file to sign
BUILD_TYPE=$3 # CPDEBUG or CPRELEASE

CHAINFILE=$ROOT/signing/certs/certificate.chain

check_expiration()
{
    FILE=$1
    NAME=$2
    VALID_DAYS=$3
    EXP_DATE=`openssl x509 -in $FILE -text -noout | grep "Not After" | cut -c 25-`
    EXP_DAYS=`echo "(" $(date -d "$EXP_DATE" +%s) - $(date -d "now" +%s) ")" / 86400 | bc`
    if (( $EXP_DAYS < $VALID_DAYS )); then
        printf "\n\n\n"
        echo `openssl x509 -in $FILE -text -noout | grep Subject:`
        printf "$NAME certificate will expire in $EXP_DAYS days! That is very soon, so you better do something about it.\n\n\n"
        if [ $BUILD_TYPE = "CPRELEASE" ]; then
            exit 1
        fi
    else
        DAYS_LEFT=`echo "$EXP_DAYS-$VALID_DAYS" | bc`
        echo "$NAME certificate is valid for another $EXP_DAYS days. (generate new in $DAYS_LEFT days)"
fi
}

# split the chain file into three certs
awk 'split_after == 1 {n++;split_after=0} /-----END CERTIFICATE-----/ {split_after=1} {print > "tmp" n ".crt"}' < $CHAINFILE

# make sure all certificates are valid for the right duration
check_expiration tmp.crt "Signing" 500 # signing cert needs to be valid for 1.5 years, but we'll be
                                       # using it after it gets generated and before it gets released
                                       # so substract about a month from that
check_expiration tmp1.crt "Intermediate" 900 # intermediate certs needs to be valid for 5 years, so update it
                                             # after about 2.5 years
check_expiration tmp2.crt "Root CA" 18000 # rootca is valid for a 100 years, so update it after about
                                          # 50 years
rm tmp*.crt

# generate hash of the uImage file
sha512sum < $INFILE | cut -c 1-128 > $INFILE.sha512

# sign the hash with rsa key
openssl dgst -sha512 -sign $ROOT/signing/certs/cp-firmware-signing.key -out $INFILE.sha512.sig $INFILE.sha512

# verify signature
openssl x509 -in $ROOT/signing/certs/cp-firmware-signing.crt -pubkey -noout > pub
openssl dgst -sha512 -verify pub -signature $INFILE.sha512.sig $INFILE.sha512

# append coconut.lzma with the following: magic bytes, 512 bytes of signture, certificate chain padded to 5000 bytes
cat $INFILE > $INFILE.signed
echo -e '\x27\x05\x19\x56' >> $INFILE.signed  # signature magic bytes with \n (5 bytes)
cat $INFILE.sha512.sig >> $INFILE.signed  # signature (512 bytes)
cp $CHAINFILE chain
CHAINLEN=`stat -c "%s" chain`
dd if=/dev/zero of=chain bs=1 count=`echo 5000 - $CHAINLEN | bc` seek=$CHAINLEN # pad the chain to expected length
cat chain >> $INFILE.signed # certificate chain (5000 bytes)

#verify
$ROOT/cppython/cppython $ROOT/signing/testsignedimage.py $ROOT $INFILE.signed
