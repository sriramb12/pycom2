#Server side of file transfer using TLS
#Load Server Certificate to be shared via TLS handshake to client

import socket, ssl, pickle
import threading
from util import validateEmail, createLogger
import os
from os.path import exists
import random
import time
from conf import config
import string
import json

class MFTServer:
	def __init__(self):
		self.logger = createLogger("mft_server")
		self.lock = threading.Lock()
		self.gc = None
		self.allKeys = []
		self.loadRepoDb()
		self.handle = []
		certfile = config.get("Settings", "certfile")
		self.ttl  = int(config.get("Settings", "ttl"))
		keyfile = config.get("Settings", "keyfile")
		self.packetSize = int(config.get("Settings", "packetSize"))
		self.context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
		try:
			self.context.load_cert_chain(certfile=certfile, keyfile= keyfile)
		except:
			self.logger.error("error in loading cert")
			exit(0)

		#SSL version 2, 3 are insecure so they have been blocked
		self.context.options |= ssl.OP_NO_SSLv2
		self.context.options |= ssl.OP_NO_SSLv3

		#create socket object
		self.srvSocket = socket.socket()
		self.srvSocket.settimeout(1)
		#bind host name to socket on pot number
		self.serverPort = int(config.get("Settings", "icomServerPort"))
		#socket listening for up to 5 connections
		self.srvSocket.listen(5)
		self.repository = 'run/repo/'

		#create socket object
		self.sockServer = socket.socket()
		#bind host name to socket on pot number
		try:
			self.sockServer.bind(('0.0.0.0', self.serverPort))
		except:
			errStr = "Server already running on port:" + str(self.serverPort)
			self.logger.error(errStr)
			exit("Server already running on port:" + str(self.serverPort))
		#socket listening for up to 5 connections
		try:
			self.sockServer.listen()
		except:
			self.logger.error("listen error")
			exit("listen error")

	def loadRepoDb(self):
		self.repoDbFile = config.get("Settings", "repoDbFile")
		try:
			with open(self.repoDbFile, 'r') as self.repoDbHandle:
				self.repoDb = json.load(self.repoDbHandle)
				for entry in self.repoDb:
					self.allKeys.append(entry['fileHandle'])
					self.allKeys.append(entry['clientHandle'])
		except:
			self.repoDb = {}
			self.allKeys = []
			self.logger.info("init repo")

	def saveRepoDb(self):
		self.repoDbFile = config.get("Settings", "repoDbFile")
		jsonObj =  json.dumps(self.repoDb, indent = 4)
		with open(self.repoDbFile, 'w') as self.repoDbHandle:
			self.repoDbHandle.write(jsonObj)
		self.logger.error("repo saved")

	def genHandle(self):
		self.handle = []
		for i in range(2):
			while True:
				alph = random.sample(string.ascii_letters, 4)
				num = random.sample(string.digits,4)
				randstr = "".join(alph) + "".join(num) + 'X'
				if randstr not in self.allKeys:
					self.allKeys.append(randstr)
					self.handle.append(randstr)
					break
		self.logger.error("file handle " + self.handle[0] +"," + self.handle[1])
	def decryptFile(fileName,key):
		f = Fernet(key)
		file_data= ""
		encFile = fileName+ 'en'
		with open(fileName, "rb") as file:
			file_data = file.read()
			# decrypt data
		decrypted_data = f.decrypt(file_data)
		with open(encFile, "wb") as file:
			file.write(decrypted_data)
		return encFile

	def sendFile(self, streamSock):
		fileName = self.repository + self.header["fileName"]
		fh = None
		fh = open(fileName, 'rb')
		'''
		try:
			fh = open(fileName, 'rb')
		except:
			exit("no such file in repository: " + fileName)
		'''
		total= 0
		self.logger.error("sending file:" + fileName)
		while True:
			#send data to bound host
			#read remaining bytes until EOF
			data = fh.read(self.packetSize)
			total += len(data)
			if not total%1024:
				print(".")
			streamSock.send(data)
			if len(data) < self.packetSize:
					streamSock.close()
					fh.close()
					break
		print('File '+ fileName + ' sending complete :', total, ' bytes')


	def recvFile(self, stream):
		self.lock.acquire()
		self.genHandle()
		fname = self.repository + self.handle[0]
		f = open(fname, 'wb')
		sz = int(self.header['fileSize'])
		print(self.header)
		("recv file  ", fname, sz)
		rx = 0
		while True:
			try:
				data = stream.recv(self.packetSize)
				if len(data) <= 20:
					break
				rx += len(data)
				f.write(data)
		#		print("rx:", rx)
			except:
				#write data from stream.recv(..) to file
				break
		self.header['clientHandle'] = self.handle[1]
		self.repoDb[self.handle[0]] = self.header

		f.close()
		self.saveRepoDb()
		self.lock.release()
		d = {'fileHandle': self.handle[1]}
		msg = pickle.dumps(d)
		stream.send(msg)
		self.logger.error('End Of File received, closing connection...' + str(rx))

	def dumpRepo(self):
		print(self.repoDb)
	def approve(self, handle):
		self.logger.error("approve")
	def show(self, handle):
		self.logger.error("show")
		pass
	def reject(self, handle):
		self.logger.error("reject")
		pass

	def handleClient(self, stream):
		cmds = ['get', 'put', 'query', 'debug']
		MAX_SZ=1024*1024
		msg = stream.recv()
		print(len(msg))
		self.header = pickle.loads(msg)
		cmd = self.header["cmd"]
		print(self.header)
		print("--------")
		if cmd in cmds:
			print("cmd:", cmd)
		else:
			print("unknown cmd: "+ cmd)
			exit(0)
		if cmd == 'put':
			return self.recvFile(stream)
		if cmd == 'get':
			return self.sendFile(stream)

	def cleanupRepo(self):
		self.logger.info("Cleanup")
		delList = []
		self.lock.acquire()
		for k,v in self.repoDb.items():
			if int(time.time())  - int(v['txnTime']) > self.ttl:
				delList.append(k)
				self.logger.warning("Cleanup " + k)
				self.allKeys.remove(v['clientHandle'])
				self.allKeys.remove(k)
				try:
					fname = self.repository + k
					os.remove(fname)
				except:
					print(fname, " notfound")
		for i in delList:
			del self.repoDb[i]
		self.lock.release()
		threading.Timer(self.ttl, self.cleanupRepo).start()

	def startServer(self):
		self.cleanupRepo()
		while True:
			newSocket, fromaddr = self.sockServer.accept()
			streamSock = self.context.wrap_socket(newSocket, server_side=True)
			#open file to write data to
			#Prints IP address of Client
			print("'Connection established from " + str(fromaddr))
			try:
				#initalise thread to run handle_client(..) function
				p1 = threading.Thread(target=self.handleClient, args=[streamSock])
				#start thread
				p1.start()
			except Exception as err:
				print('\n Error in handling client\n', err)
				break
		print('\n-----------------------------------------')
		print('Server shutting down...\n')

def run():
	srv = MFTServer()
	srv.startServer()
def reject():
	return srv.reject()
def show():
	return srv.show()
def approve():
	return srv.approve()
serverobj =  None
if __name__ == '__main__':
	if not serverobj:
		serverObj =	run()
