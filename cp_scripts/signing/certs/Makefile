#
# Product certificate chain build tools
#
# == Options ==
#
# make - builds all chains
# make test - test created chains
#
# To create a new conversion package:
# make FILE=path-to-file sign-file

CNSTR=DEBUG

.PHONY: test clean sign-file

all: certificate.chain

.SECONDARY:

index:
	touch index

serial:
	echo 1000 > serial

%.key:
	openssl genrsa -out $@ 2048

%.csr: %.key
	openssl req -new -sha256 -key $*.key -out $@ -subj /C=US/ST=ID/L=Boise/O=Cradlepoint,\ Inc/OU=Engineering/CN=$@\ $(CNSTR)/emailAddress=$${USER}@cradlepoint.com

cp-rootca.crt: cp-rootca.key
	openssl req -extensions v3_ca -sha256 -new -x509 -days 36500 -key cp-rootca.key -out cp-rootca.crt -subj /C=US/ST=ID/L=Boise/O=Cradlepoint,\ Inc/OU=Engineering/CN=Cradlepoint\ ROOTCA\ $(CNSTR)/emailAddress=$${USER}@cradlepoint.com

cp-fw-intermediate.crt: cp-fw-intermediate.csr cp-rootca.key cp-rootca.crt ca.conf | index serial
	openssl ca -extensions v3_ca -in cp-fw-intermediate.csr -out $@ -keyfile cp-rootca.key -cert cp-rootca.crt -outdir ./ -config ca.conf -batch

cp-firmware-signing.crt: cp-firmware-signing.csr cp-firmware-signing.key cp-fw-intermediate.crt ca.conf | index serial
	openssl ca -in cp-firmware-signing.csr -out $@ -keyfile cp-fw-intermediate.key -cert cp-fw-intermediate.crt -outdir ./ -config ca.conf -batch

certificate.chain: cp-firmware-signing.crt cp-fw-intermediate.crt cp-rootca.crt
	sed -n -e '/-----BEGIN CERTIFICATE-----/,$$p' < cp-firmware-signing.crt > $@
	sed -n -e '/-----BEGIN CERTIFICATE-----/,$$p' < cp-fw-intermediate.crt >> $@
	sed -n -e '/-----BEGIN CERTIFICATE-----/,$$p' < cp-rootca.crt >> $@
	cat cp-firmware-signing.crt cp-fw-intermediate.crt cp-rootca.crt > $@.long  # create chain with detailed info for convenience


test: cp-firmware-signing.crt cp-fw-intermediate.crt cp-rootca.crt
	if [ "`openssl x509 -noout -modulus -in cp-firmware-signing.crt | openssl md5`" != "`openssl rsa -noout -modulus -in cp-firmware-signing.key | openssl md5`" ]; then \
		exit 1; \
	fi
	openssl verify -CAfile cp-rootca.crt -untrusted certificate.chain cp-firmware-signing.crt
	openssl verify -CAfile cp-rootca.crt -untrusted certificate.chain certificate.chain
	echo "adrian" > test
	openssl dgst -sha512 -sign cp-firmware-signing.key -out test.sig test
	openssl x509 -in cp-firmware-signing.crt -pubkey -noout -out pub
	openssl dgst -sha512 -verify pub -signature test.sig test
	rm test* pub

clean:
	rm -fr *.list *.crt *.csr *.key *.pem *.chain *.test *.long
	rm -fr index* serial*


OUTDIR=./sign-file
sign-file:
	# This rule will create sign-file folder, copy your file to it, and generate signature
	mkdir -p $(OUTDIR)
	rm -rf $(OUTDIR)/*
	cp $(FILE) $(OUTDIR)/altrootca.crt
	cp certificate.chain $(OUTDIR)/chain
	openssl dgst -sha512 -sign cp-firmware-signing.key -out $(OUTDIR)/sig $(FILE)
	# validate
	openssl verify -CAfile cp-rootca.crt -untrusted $(OUTDIR)/chain $(OUTDIR)/chain
	awk 'split_after == 1 {n++;split_after=0} /-----END CERTIFICATE-----/ {split_after=1} {print > "crt" n ".pem"}' < $(OUTDIR)/chain
	openssl x509 -in crt.pem -pubkey -noout -out pub
	openssl dgst -sha512 -verify pub -signature $(OUTDIR)/sig $(FILE)
	#cleanup
	rm *pem pub

	
	
