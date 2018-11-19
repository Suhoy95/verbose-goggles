
all:
	echo "make ca"
	echo "make peer NAME=[peer name]"

ca:
	openssl genrsa -des3 -out rootCA.key 4096
	openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 1024 -out rootCA.crt

self-signed:
	if [ -z "$$NAME" ] ; then echo 'Sepcify NAME of peer' ; false ; fi
	mkdir $$NAME
	openssl genrsa -out $$NAME/$$NAME.key 4096
	openssl req -x509 -new -nodes -key $$NAME/$$NAME.key -sha256 -days 1024 -out $$NAME/$$NAME.crt


peer:
	if [ -z "$$NAME" ] ; then echo 'Sepcify NAME of peer' ; false ; fi
	echo "[MESSGAE] Craeating keypair for $$NAME"
	mkdir $$NAME

	openssl genrsa -out $$NAME/$$NAME.key 4096

	openssl req -new -sha256 \
		-key $$NAME/$$NAME.key \
		-subj "/C=RU/ST=Kazan/O=Innopolis/CN=$$NAME" \
		-out $$NAME/$$NAME.csr

	openssl x509 -req \
		-in $$NAME/$$NAME.csr \
		-CA rootCA.crt \
		-CAkey rootCA.key \
		-CAcreateserial \
		-out $$NAME/$$NAME.crt \
		-days 500 -sha256
