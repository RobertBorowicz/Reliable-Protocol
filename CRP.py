import socket
import sys
from enum import Enum
import zlib

class CRPStatus(Enum):
	CLOSED = 0
	LISTEN = 1
	CON_SENT = 2
	CON_RECEIVED = 3
	CONNECTED = 4
	END_ACK_WAIT = 5
	END_WAIT = 6
	TERMINATING = 7
	CLOSE_WAIT = 8
	END_ACK = 9
	TIMEOUT = 10

class CRPSocket():

	MAX_CRP_PACKET_SIZE = 1024

	def __init__(self, ipv6=False):

		self.mainSocket = None
		self.status = CRPStatus.CLOSED

		try:
			if ipv6:
				self.mainSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
			else:
				self.mainSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

			self.mainSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		except socket.error:
			print "Unable to establish a new CRP socket"
			sys.exit()

	def bind(self, address):
		try:
			self.mainSocket.bind(address)
		except socket.error
			print "Unable to bind to address: %s" % address

	def listen():
		# TODO
		pass

	def accept():
		# TODO
		pass

	def connect(address):
		# TODO
		pass

	def close():
		# TODO
		pass

	def sendData(data):
		# TODO
		pass

	def recvData(buff):
		# TODO
		pass

	def __packetizeData(data):
		# TODO
		pass

	def __generateHeader():
		# TODO
		pass

	def __generateChecksum(data):
		return zlib.adler32(data)