import subprocess
import sys
import os

def decrypt(pwd, f):
	print(pwd, f, decrypt)
	orig = f + '.orig '
	cmd = "echo " + pwd + "| gpg -d --batch --yes --passphrase-fd 0 " + f + " > " + orig
	os.system("mv " + orig + f)

def encrypt(pwd, f):
	print(pwd, f, decrypt)
	cmd = "echo " + pwd + "| gpg -c --batch --yes --passphrase-fd 0 " + f
	outfile = f + '.gpg '
	os.system(cmd)
	os.system("mv " + outfile + f)
	

try:
	crypt(passphrase, sys.argv[1], decrypt = False)
except:
	print("file name")

#passphrase = input("Enter passphrase:")
