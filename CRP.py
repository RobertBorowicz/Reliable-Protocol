import socket
import sys
import zlib
from struct import *

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

class CRPSocket():

	MAX_CRP_PACKET_SIZE = 1024
	CRP_WINDOW_SIZE = 1
	CRP_MAX_SEQ_NUM = 65535
	CRP_MAX_ACK_NUM = 65535
	CRP_HEADER_LENGTH = 12 #length in bytes

	def __init__(self, ipv6=False):

		self.mainSocket = None
		self.state = CRPState.CLOSED

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
		except socket.error:
			print "Unable to bind to address: %s" % address

	def listen(self):
		# TODO
		pass

	def accept(self):
		# TODO
		pass

	def connect(self, address):
		# TODO
		pass

	def close(self):
		# TODO
		pass

	def sendData(self, data):
		# TODO
		pass

	def recvData(self, buff):
		# TODO
		pass

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

	def __handlePacket(self, packet):
		header = packet[:12]
		headerInfo, packedHeader = self.__parseHeader

		data = None
		if CRPFlag.DTA_FLAG in headerInfo["FLG"]:
			data = packet[12:]


	def __generateHeader(self, seq, ack, win, flags):
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
			header = pack("<HHHh", seq, ack, win, flags)
			return header
		except:
			return None

	def __packPacket(self, header, payload):
		if payload:
			checksum = self.generateChecksum(header+payload)
			fullHeader = pack("<qi", header, checksum)
			fullPacket = fullHeader + payload
			return fullPacket
		else:
			checksum = self.generateChecksum(header)
			fullHeader = pack("<qi", header, checksum)
			return fullHeader

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
seq = 3500
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