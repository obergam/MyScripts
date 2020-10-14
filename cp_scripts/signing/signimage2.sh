#!/bin/bash

# tools/signing/signimage2.sh
#
# Copyright (c) 2019 CradlePoint, Inc. <www.cradlepoint.com>
# All rights reserved.
#
# This file contains confidential information of CradlePoint, Inc. and your
# use of this file is subject to the CradlePoint Software License Agreement
# distributed with this file. Unauthorized reproduction or distribution of
# this file is subject to civil and criminal penalties
#

#
# Following script builds an image consisting of the following pieces:


#+----------------------+
#    encrypted with     |
#    product            |
#    symmetric key      |
#                       |
#  +-----------------+  |
#  |                 |  |
#  | CERT CHAIN      |  |
#  | (5000 bytes)    |  |
#  |                 |  |
#  |                 |  |
#  |                 |  |
#  |                 |  |
#  +-----------------+  |
#  | SIGNATURE of    |  |
#  | coconut.uImage  |  |
#  | (256 bytes)     |  |
#  +-----------------+  |
#  | SIGNATURE of    |  |
#  | uboot header    |  |
#  | (256 bytes)     |  |
#  +-----------------+  |
#  | +-------------+ |  |
#  | | uboot header| |  |
#  | | (64 bytes ) | |  |
#  | +-------------+ |  |
#  |                 |  |
#  | coconut.uImage  |  |
#  |                 |  |
#
#          ...
#
#  |                 |  |
#  |                 |  |
#  +-----------------+  |
#+----------------------+

set -e

function usage()
{
    echo "
         Usage: $0 -r -c -k -e -u [-m -i -b]
         -r Path to root directory of coconut repo
         -m Use if signing a multi-image
         -c If set to CPRELEASE, script will return error if
               signing certificates are within expiration limit
         -k Path to signing key
         -e Path to certificate chain
         -i Path to multi-image.uImage (required if -m selected)
         -u Path to coconut.uImage
         -b Path to multi-image bin folder (required if -m selected)" >&2
}

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

IS_MULTI=0

while getopts "r:c:k:e:mi:u:b:" OPT; do
    case "$OPT" in
    r)
        ROOT=$OPTARG
        ;;
    m)
        IS_MULTI=1
        ;;
    c)
        BUILD_TYPE=$OPTARG
        ;;
    k)
        SIGN_KEY=$OPTARG
        ;;
    e)
        CHAIN=$OPTARG
        ;;
    i)
        MULTI_UIMAGE=$OPTARG
        ;;
    u)
        COCONUT_UIMAGE=$OPTARG
        ;;
    b)
        #select all .bin files in the folder
        BINS=$OPTARG/*.bin
        ;;
    *)
        usage
        exit 1
        ;;
    esac
done
shift "$(($OPTIND -1))"

if [ -z "$ROOT" ] || [ -z "$BUILD_TYPE" ] || [ -z "$SIGN_KEY" ] || [ -z "$CHAIN" ] || [ -z "$COCONUT_UIMAGE" ]; then
    usage
    exit 1
fi

if [ -z "$BUILD_TYPE" ]; then
    usage
    exit 1
fi

# split the chain file into three certs
awk 'split_after == 1 {n++;split_after=0} /-----END CERTIFICATE-----/ {split_after=1} {print > "tmp" n ".crt"}' < $CHAIN

# make sure all certificates are valid for the right duration
check_expiration tmp.crt "Signing" 500 # signing cert needs to be valid for 1.5 years, but we'll be
                                       # using it after it gets generated and before it gets released
                                       # so substract about a month from that
check_expiration tmp1.crt "Intermediate" 900 # intermediate certs needs to be valid for 5 years, so update it
                                             # after about 2.5 years
check_expiration tmp2.crt "Root CA" 18000 # rootca is valid for a 100 years, so update it after about
                                          # 50 years
rm tmp*.crt


if [ $IS_MULTI -eq 1 ]; then
   if [ -z "$MULTI_UIMAGE" ] || [ -z "$BINS" ]; then
       usage
       exit 1
   fi

   echo "Signing multi-image uImage file."

   INFILE=$MULTI_UIMAGE

   # use math to calculate full multi-image header size
   MULTI_UIMAGE_SIZE=`stat -c "%s" $MULTI_UIMAGE`
   UIMAGE_SIZE=`stat -c "%s" $COCONUT_UIMAGE`
   BINS_SIZE=`stat -c "%s" $BINS | paste -s -d+ - | bc`
   HEADER_SIZE=`echo $MULTI_UIMAGE_SIZE - $UIMAGE_SIZE - $BINS_SIZE + 64 | bc`

   # generate hash of the single-image uImage filie
   sha512sum < $COCONUT_UIMAGE | cut -c 1-128 > $INFILE.sha512
else
   echo "Signing single-image uImage file."

   INFILE=$COCONUT_UIMAGE

   HEADER_SIZE=64

   # generate hash of the uImage file
   sha512sum < $INFILE | cut -c 1-128 > $INFILE.sha512
fi


# sign the uImage hash with rsa key
openssl dgst -sha512 -sign $SIGN_KEY -out $INFILE.sha512.sig $INFILE.sha512

# generate hash of the uboot header in the uImage file
dd if=$INFILE of=uboot count=1 bs=$HEADER_SIZE
sha512sum < uboot | cut -c 1-128 > uboot.sha512

# sign the uboot header hash with rsa key
openssl dgst -sha512 -sign $SIGN_KEY -out uboot.sha512.sig uboot.sha512

# pad the chain to expected length
cp $CHAIN chain
CHAINLEN=`stat -c "%s" chain`
dd if=/dev/zero of=chain bs=1 count=`echo 5000 - $CHAINLEN | bc` seek=$CHAINLEN

# put together final image
cat chain > $INFILE.signed
cat $INFILE.sha512.sig >> $INFILE.signed
cat uboot.sha512.sig >> $INFILE.signed
cat $INFILE >> $INFILE.signed

# cleanup
rm -f uboot* chain *.sig *.sha512


