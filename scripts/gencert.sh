openssl req -nodes -newkey rsa:2048 -keyout $1.key -out $1.crt -subj "/C=IN/ST=KA/L=Bengaluru/O=SDE/OU=IT Department/CN=nxp.com"
