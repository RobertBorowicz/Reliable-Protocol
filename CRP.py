import socket
import sys
import zlib
from struct import *
from random import randint

class CRPState:
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

class CRPFlag:
	END_FLAG = 0x1  #000001
	CON_FLAG = 0x2  #000010
	DTA_FLAG = 0x4  #000100
	WIN_FLAG = 0x8  #001000
	RST_FLAG = 0x10 #010000
	ACK_FLAG = 0x20 #100000

class StateError(Exception):
	def __init__(self, msg):
		self.msg = msg

class ChecksumError(Exception):
	def __init__(self):
		self.msg = ""

class UnableToConnectException(Exception):
	def __init__(self):
		self.msg = "Unable to connect"

class CRPSocket():

	MAX_CRP_PACKET_SIZE = 1024
	CRP_WINDOW_SIZE = 1
	CRP_MAX_SEQ_NUM = 65535
	CRP_MAX_ACK_NUM = 65535
	CRP_HEADER_LENGTH = 12 #length in bytes
	CRP_MAX_ATTEMPTS = 3
	CRP_TIMEOUT = 0.25

	def __init__(self, ipv6=False):

		self.mainSocket = None
		self.state = CRPState.CLOSED
		self.useIPv6 = ipv6
		self.clientAddr = 'localhost'

		self.seqNum = 0
		self.ackNum = 0
		self.winSize = self.CRP_WINDOW_SIZE

		try:
			print "Init"
			if ipv6:
				self.mainSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
			else:
				self.mainSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			print "Made Socket"
			#self.mainSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		except socket.error:
			print "Unable to establish a new CRP socket"
			sys.exit()
		print "Done"

	def bind(self, address):
		try:
			self.mainSocket.bind(address)
		except socket.error:
			print "Unable to bind to address: %s" % address

	def listen(self):
		self.state = CRPState.LISTEN

	def accept(self):
		if self.state != CRPState.LISTEN:
			raise StateError("The socket is not yet listening for connections")

		flags = {}
		while CRPFlag.CON_FLAG not in flags:
			packet, addr = self.mainSocket.recvfrom(1024)
			
			try:
				headerInfo, data = self.__parsePacket(packet)
			except ChecksumError:
				# Drops bad packets
				continue
			flags = headerInfo["FLG"]
			
			# If we have received a connection request
			if CRPFlag.CON_FLAG in flags:
				print "Received connection request"
				conn = CRPSocket(self.useIPv6)
				conn.seqNum = randint(0, self.CRP_MAX_SEQ_NUM)
				conn.ackNum = headerInfo["SEQ"] + 1
				if conn.ackNum > self.CRP_MAX_ACK_NUM:
					conn.ackNum = 0
				conn.state = CRPState.CON_RECEIVED
				conn.winSize = headerInfo["WIN"]
				conn.clientAddr = addr

				connFlags = CRPFlag.CON_FLAG | CRPFlag.ACK_FLAG
				conackHeader = conn.__generateHeader(connFlags)
				CONACK = conn.__packPacket(conackHeader)

				attempts = self.CRP_MAX_ATTEMPTS
				self.mainSocket.settimeout(self.CRP_TIMEOUT)
				while (attempts > 0):
					try:
						self.mainSocket.sendto(CONACK, conn.clientAddr)

						response, respAddr = self.mainSocket.recvfrom(1024)
						if respAddr != conn.clientAddr:
							# Drop packets that aren't part of this connection esatblishment
							continue
						try:
							respInfo, data = self.__parsePacket(response)
							respFlags = respInfo["FLG"]
							if CRPFlag.ACK_FLAG in respFlags:
								conn.seqNum += 1
								if (respInfo["ACK"] == conn.seqNum) and (respInfo["SEQ"] == conn.ackNum):
									conn.state = CRPState.CONNECTED
									print "CONNECTED"
									conn.bind((conn.clientAddr[0], 5001))
									print conn.mainSocket.getsockname()
									return conn, conn.clientAddr

						except ChecksumError:
							continue

					except socket.timeout:
						attempts -= 1

			else:
				# Ignore requests that aren't for a connection
				print "Received other stuff"
				continue

	def connect(self, address):
		
		print "Hello"

		self.clientAddr = address

		attempts = self.CRP_MAX_ATTEMPTS

		flags = CRPFlag.CON_FLAG
		self.seqNum = randint(0, self.CRP_MAX_SEQ_NUM)
		header = self.__generateHeader(flags)
		conPacket = self.__packPacket(header)
		self.state = CRPState.CON_SENT

		while (attempts > 0):
			self.mainSocket.settimeout(self.CRP_TIMEOUT)
			try:
				self.mainSocket.sendto(conPacket, address)

				response, respAddr = self.mainSocket.recvfrom(1024)
				
				respHeader = self.__parsePacket(response)[0]
				respFlags = respHeader["FLG"]
				if (CRPFlag.CON_FLAG in respFlags) and (CRPFlag.ACK_FLAG in respFlags):
					self.__incrementSequence(1)
					if self.seqNum == respHeader["ACK"]:
						self.ackNum = (respHeader["SEQ"] + 1) % self.CRP_MAX_ACK_NUM
						self.state = CRPState.CONNECTED
						ackHeader = self.__generateHeader(CRPFlag.ACK_FLAG)
						ackPacket = self.__packPacket(ackHeader)
						self.mainSocket.sendto(ackPacket, respAddr)
						print "CONNECTED"
						break

			except:
				attempts -= 1

		print "Goodbye"
		return

	def __incrementSequence(self, amount):
		self.seqNum += amount
		if self.seqNum > self.CRP_MAX_SEQ_NUM:
			self.seqNum %= self.CRP_MAX_SEQ_NUM

	def close(self):
		# TODO
		pass

	def sendData(self, data):
		self.mainSocket.sendto(data, self.clientAddr)

	def recvData(self, buff):
		response = None
		try:
			response, respAddr = self.mainSocket.recvfrom(4096)
		except socket.error as err:
			print err
		return response

	def __packetizeData(self, data):
		"""Split the input data into CRP sized packets
		This ensures that packets are of maximum size 1024
		Any trailing segment that is less than 1024 bytes will
		be retained at its original length
		Returned as a list of data segments
		"""
		segments = []
		base = 0

		while (base < len(data)):
			segment = data[base:base+self.MAX_CRP_PACKET_SIZE]
			segments.append(segment)
			base += self.MAX_CRP_PACKET_SIZE

		return segments

	def __parsePacket(self, packet):
		header = packet[:self.CRP_HEADER_LENGTH]
		headerInfo, packedHeader = self.__parseHeader(header)

		checksum = self.__generateChecksum(packedHeader)

		data = None
		if CRPFlag.DTA_FLAG in headerInfo["FLG"]:
			data = packet[12:]
			checksum = self.__generateChecksum(data, checksum)

		if headerInfo["CHK"] != checksum:
			raise ChecksumError()
		else:
			return headerInfo, data


	def __generateHeader(self, flags):
		"""
		+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
		|        Sequence Number        |     Acknowledgment Number     |
		+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
		|                               |    |   Data   |    |A|W|D|C|E||
		|         Window Length         |x000|  Offset  |x000|C|I|T|O|N||
		|                               |    |          |    |K|N|A|N|D||
		+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
		|                           Checksum                            |
		+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
		Generates the header without the checksum. The checksum is calculated later
		"""
		# Combine offset and flags into 16-bit chunk for packing purposes
		try:
			header = pack("<HHHh", self.seqNum, self.ackNum, self.winSize, flags)
			return header
		except:
			return None

	def __packPacket(self, header, payload=None):
		"""Packs a packet into a single message
		Calculates checksum for packet and stores in header
		If there is data, this is used in checksum calculation
		Data is appended to the final packet
		"""
		if payload:
			checksum = self.__generateChecksum(header+payload)
		else:
			checksum = self.__generateChecksum(header)

		packedHeader, = unpack("<q", header)
		fullPacket = pack("<qi", packedHeader, checksum)

		if payload:
			fullPacket += payload

		return fullPacket

	def __parseHeader(self, header):
		headerInfo = {}

		if len(header) != self.CRP_HEADER_LENGTH:
			return None

		seq, ack, win, flags, checksum = unpack("<HHHhi", header)
		headerInfo["SEQ"] = seq & 0xffff
		headerInfo["ACK"] = ack & 0xffff
		headerInfo["WIN"] = win & 0xffff
		headerInfo["FLG"] = self.__parseFlags(flags & 0xff)
		headerInfo["CHK"] = checksum
		packedHeader = pack("HHHh", seq, ack, win, flags)

		return headerInfo, packedHeader

	def __parseFlags(self, flags):
		setFlags = []

		if CRPFlag.END_FLAG & flags:
			setFlags.append(CRPFlag.END_FLAG)
		if CRPFlag.CON_FLAG & flags:
			setFlags.append(CRPFlag.CON_FLAG)
		if CRPFlag.DTA_FLAG & flags:
			setFlags.append(CRPFlag.DTA_FLAG)
		if CRPFlag.WIN_FLAG & flags:
			setFlags.append(CRPFlag.WIN_FLAG)
		if CRPFlag.RST_FLAG & flags:
			setFlags.append(CRPFlag.RST_FLAG)
		if CRPFlag.ACK_FLAG & flags:
			setFlags.append(CRPFlag.ACK_FLAG)

		return setFlags

	def __generateChecksum(self, data, value=None):
		if not value:
			return zlib.adler32(data)
		return zlib.adler32(data, value)

	def __validateChecksum(self, checksum, data):
		if checksum != self.__generateChecksum(data):
			return False
		return True

"""crp = CRPSocket()
total = 0
with open("R:\Documents\Fall 2016\CS 3251\Written_3\Ladder.png", "rb") as f:
	while True:
		data = f.read(4096)
		if data:
			packets = crp.packetizeData(data)
			p = len(packets)
			total += p
			print p, total
		else:
			break"""

"""crp = CRPSocket()
crp.bind(('', 5000))
crp.listen()
crp.accept()"""
"""seq = 3500
ack = 4500
win = 5
flags = 0x32
packed = pack("<hhhh", seq, ack, win, flags)
csum = zlib.adler32(packed)
print csum
print packed
string = "This packet now has a data payload"
s = packed + string
csum = zlib.adler32(string)
print csum
q, = unpack("q", packed)
print len(packed)
p = pack("<qi", q, csum)
print len(p)
print unpack("<hhhh", packed[0:8])"""