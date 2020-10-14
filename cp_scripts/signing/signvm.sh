set -e

# This is not part of firmware signing

ROOT=$1
GRUB_FOLDER=$2
COCO_FILE=$3
OUT_FOLDER=$4
OUT_FILE=$OUT_FOLDER/verifyboot

# generate manifest file
find $GRUB_FOLDER -type f -exec sha256sum {} \; | sort -t' ' -k2 | sed 's/platform\/i386\//.\//' > $OUT_FILE.manifest
sha256sum $COCO_FILE | sed 's/platform\/i386\///' >> $OUT_FILE.manifest

# generate signature
openssl dgst -sha512 -sign $ROOT/signing/certs/cp-firmware-signing.key -out $OUT_FILE.manifest.sig $OUT_FILE.manifest
cp $ROOT/signing/certs/certificate.chain $OUT_FILE.chain

# verify
openssl x509 -in $ROOT/signing/certs/cp-firmware-signing.crt -pubkey -noout > pub
openssl dgst -sha512 -verify pub -signature $OUT_FILE.manifest.sig $OUT_FILE.manifest

