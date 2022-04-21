openssl req -x509 -newkey rsa:4096 -keyout $1.pem -out $1.crt -sha256 -days 365 -nodes -subj "/C=IN/ST=KA/L=Bengaluru/O=SDE/OU=IT Department/CN=nxp.com"

