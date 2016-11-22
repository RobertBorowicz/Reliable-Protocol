import socket
import sys
import zlib
from struct import *
from random import randint
import time

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
    WIN_FLAG = 0x8  #001000 Now unused in this implementation
    RST_FLAG = 0x10 #010000
    ACK_FLAG = 0x20 #100000

class StateError(Exception):
    def __init__(self, msg):
        self.msg = msg

class ChecksumError(Exception):
    def __init__(self):
        self.msg = ""

class UnableToConnectException(Exception):
    def __init__(self, msg):
        self.msg = msg

class CRPSocket():

    CRP_MAX_PACKET_SIZE = 1024
    CRP_WINDOW_SIZE = 5
    CRP_MAX_SEQ_NUM = 65536
    CRP_MAX_ACK_NUM = 65536
    CRP_HEADER_LENGTH = 12 #length in bytes
    
    CRP_MAX_ATTEMPTS = 3
    
    CRP_RECV_TIMEOUT = 0.2
    CRP_CON_TIMEOUT = 0.5
    CRP_PACKET_TIMEOUT = 0.1
    CRP_END_TIMEOUT = 2
    
    CRP_MAX_WINSIZE = 0xffff

    def __init__(self, ipv6=False):

        self.mainSocket = None
        self.state = CRPState.CLOSED
        self.useIPv6 = ipv6
        self.clientAddr = 'localhost'
        self.nextPort = 5000

        self.seqNum = 0
        self.ackNum = 0
        self.expectedAck = 0
        self.winSize = self.CRP_WINDOW_SIZE
        self.clientWinSize = self.CRP_WINDOW_SIZE
        self.bufferedPackets = {}

        self.sent = 0
        self.newWindow = False

        try:
            print "Init"
            if ipv6:
                self.mainSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            else:
                self.mainSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print "Made Socket"
            self.mainSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except socket.error as err:
            print "Unable to establish a new CRP socket"
            sys.exit()
        print "Done"

    def bind(self, address):
        try:
            self.mainSocket.bind(address)
            self.nextPort = (address[1] + 1) % 65535
        except socket.error:
            print err
            print "Unable to bind to address: %s %s" % address

    def listen(self):
        self.state = CRPState.LISTEN

    def accept(self):
        if self.state != CRPState.LISTEN:
            raise StateError("The socket is not yet listening for connections")

        while (True):
            packet, addr = self.mainSocket.recvfrom(1024)
            
            headerInfo, data = self.__parsePacket(packet)
            
            if headerInfo["CHK"] == 0:
                # Corrupted packet
                continue

            if CRPFlag.DTA_FLAG in headerInfo["FLG"]:
                # Connection was reset but client still sending
                # Reset connection
                print "Resetting connection"
                resetHeader = self.__generateHeader(CRPFlag.RST_FLAG)
                RST = self.__packPacket(resetHeader)
                self.mainSocket.sendto(RST, self.clientAddr)
                self.state = CRPState.LISTEN
                continue

            flags = headerInfo["FLG"]
            
            # If we have received a connection request
            if CRPFlag.CON_FLAG in flags:
                print "Received connection request"
                self.seqNum = randint(0, self.CRP_MAX_SEQ_NUM)
                self.ackNum = (headerInfo["SEQ"] + 1) % self.CRP_MAX_ACK_NUM
                self.state = CRPState.CON_RECEIVED
                self.clientWinSize = headerInfo["WIN"]
                self.clientAddr = addr
                #conn.bind(('', self.nextPort))
                #self.nextPort = (self.nextPort + 1) % 65536

                connFlags = CRPFlag.CON_FLAG | CRPFlag.ACK_FLAG
                conackHeader = self.__generateHeader(connFlags)
                CONACK = self.__packPacket(conackHeader)

                attempts = self.CRP_MAX_ATTEMPTS
                self.mainSocket.settimeout(self.CRP_CON_TIMEOUT)
                while (attempts > 0):
                    try:
                        self.mainSocket.sendto(CONACK, self.clientAddr)

                        response, respAddr = self.mainSocket.recvfrom(1024)
                        if respAddr != self.clientAddr:
                            # Drop packets that aren't part of this connection establishment
                            continue

                        respInfo, data = self.__parsePacket(response)

                        if respInfo["CHK"] == 0:
                            # Corrupted packet
                            continue

                        respFlags = respInfo["FLG"]
                        if CRPFlag.ACK_FLAG not in respFlags and CRPFlag.DTA_FLAG in respFlags:
                            # ACK from client was lost at some point
                            # Reset connection
                            print "Resetting connection"
                            resetHeader = self.__generateHeader(CRPFlag.RST_FLAG)
                            RST = self.__packPacket(resetHeader)
                            self.mainSocket.sendto(RST, self.clientAddr)
                            self.state = CRPState.LISTEN
                            break

                        if CRPFlag.ACK_FLAG in respFlags:
                            self.seqNum = (self.seqNum + 1) % self.CRP_MAX_ACK_NUM
                            if (respInfo["ACK"] == self.seqNum) and (respInfo["SEQ"] == self.ackNum):
                                self.state = CRPState.CONNECTED
                                print "CONNECTED"
                                return self, self.clientAddr

                    except socket.timeout:
                        print "Wait timeout"
                        attempts -= 1

            else:
                # Ignore requests that aren't for a connection
                print "Received other stuff"
                continue
        print "Loop broke"

    """def accept(self):
                    if self.state != CRPState.LISTEN:
                        raise StateError("The socket is not yet listening for connections")
            
                    waiting = True
                    while (waiting):
                        packet, addr = self.mainSocket.recvfrom(1024)
                        
                        headerInfo, data = self.__parsePacket(packet)
                        
                        if headerInfo["CHK"] == 0:
                            # Corrupted packet
                            continue
            
                        flags = headerInfo["FLG"]
                        
                        # If we have received a connection request
                        if CRPFlag.CON_FLAG in flags:
                            print "Received connection request"
                            conn = CRPSocket(self.useIPv6)
                            conn.seqNum = randint(0, self.CRP_MAX_SEQ_NUM)
                            conn.ackNum = (headerInfo["SEQ"] + 1) % self.CRP_MAX_ACK_NUM
                            conn.state = CRPState.CON_RECEIVED
                            conn.clientWinSize = headerInfo["WIN"]
                            conn.clientAddr = addr
                            conn.bind(('', self.nextPort))
                            self.nextPort = (self.nextPort + 1) % 65536
            
                            connFlags = CRPFlag.CON_FLAG | CRPFlag.ACK_FLAG
                            conackHeader = conn.__generateHeader(connFlags)
                            CONACK = conn.__packPacket(conackHeader)
            
                            attempts = self.CRP_MAX_ATTEMPTS
                            conn.mainSocket.settimeout(self.CRP_CON_TIMEOUT)
                            while (attempts > 0):
                                try:
                                    conn.mainSocket.sendto(CONACK, conn.clientAddr)
            
                                    response, respAddr = conn.mainSocket.recvfrom(1024)
                                    if respAddr != conn.clientAddr:
                                        # Drop packets that aren't part of this connection establishment
                                        continue
            
                                    respInfo, data = conn.__parsePacket(response)
            
                                    if respInfo["CHK"] == 0:
                                        # Corrupted packet
                                        continue
            
                                    respFlags = respInfo["FLG"]
                                    if CRPFlag.ACK_FLAG not in respFlags and CRPFlag.DTA_FLAG in respFlags:
                                        # ACK from client was lost at some point
                                        # Reset connection
                                        print "Resetting connection"
                                        resetHeader = conn.__generateHeader(CRPFlag.RST_FLAG)
                                        RST = conn.__packPacket(resetHeader)
                                        conn.mainSocket.sendto(RST, conn.clientAddr)
                                        break
            
                                    if CRPFlag.ACK_FLAG in respFlags:
                                        conn.seqNum = (conn.seqNum + 1) % self.CRP_MAX_ACK_NUM
                                        if (respInfo["ACK"] == conn.seqNum) and (respInfo["SEQ"] == conn.ackNum):
                                            conn.state = CRPState.CONNECTED
                                            print "CONNECTED"
                                            return conn, conn.clientAddr
            
                                except socket.timeout:
                                    print "Wait timeout"
                                    attempts -= 1
            
                        else:
                            # Ignore requests that aren't for a connection
                            print "Received other stuff"
                            continue
                    print "Loop broke"""

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
            self.mainSocket.settimeout(self.CRP_RECV_TIMEOUT)
            try:
                self.mainSocket.sendto(conPacket, address)

                response, respAddr = self.mainSocket.recvfrom(self.CRP_MAX_PACKET_SIZE)
                
                respHeader = self.__parsePacket(response)[0]
                respFlags = respHeader["FLG"]
                if (CRPFlag.CON_FLAG in respFlags) and (CRPFlag.ACK_FLAG in respFlags):
                    self.__incrementSequence(1)
                    if self.seqNum == respHeader["ACK"]:
                        #self.clientAddr = respAddr
                        self.ackNum = (respHeader["SEQ"] + 1) % self.CRP_MAX_ACK_NUM
                        self.state = CRPState.CONNECTED
                        self.clientWinSize = respHeader["WIN"]
                        ackHeader = self.__generateHeader(CRPFlag.ACK_FLAG)
                        ackPacket = self.__packPacket(ackHeader)
                        self.mainSocket.sendto(ackPacket, respAddr)
                        print "CONNECTED"
                        return True

            except socket.timeout:
                attempts -= 1

        print "Failed to connect to the remote server. Please try again."
        return False

    def __incrementSequence(self, amount):
        self.seqNum = (self.seqNum + amount) % self.CRP_MAX_SEQ_NUM


    def close(self):
        # TODO
        if self.state != CRPState.CONNECTED:
            self.mainSocket.close()
            self.state = CRPState.CLOSED


        #self.state = CRPState.END_ACK_WAIT
        closeHeader = self.__generateHeader(CRPFlag.END_FLAG)
        closePacket - self.__packPacket(closeHeader)
        self.state = CRPState.END_ACK_WAIT
        closed = False
        attempts = self.CRP_MAX_ATTEMPTS
        self.seqNum = (self.seqNum + 1) % self.CRP_MAX_SEQ_NUM

        while (not closed):
            self.mainSocket.settimeout(self.CRP_END_TIMEOUT)
            try:
                self.mainSocket.sendto(closePacket, self.clientAddr)

                response, respAddr = self.mainSocket.recvfrom(self.CRP_MAX_PACKET_SIZE)

                respHeader = self.__parsePacket(response)[0]
                respFlags = respHeader["FLG"]
                if (CRPFlag.ACK_FLAG in respFlags) and respHeader["ACK"] == self.seqNum:
                    self.state = CRPState.END_WAIT

                elif (CRPFlag.END_FLAG in respFlags):
                    self.state = CRPState.TERMINATING



            except socket.timeout:
                attempts -= 1
                if attempts == 0:
                    closed = True


        print "Attempting to close"

    def sendData(self, data):
        #self.mainSocket.sendto(data, self.clientAddr)

        if not data:
            # Break on null data
            raise Exception("Data must not be null")
            return

        if self.state != CRPState.CONNECTED:
            # Break if we are not connected
            raise StateError("No connection exists, or the current connection has been closed")
            return

        self.mainSocket.settimeout(.05)

        dataPackets = self.__packetizeData(data)

        unackPackets = []
        currSeqNum = self.seqNum

        for packet in dataPackets:
            header = self.__customHeader(currSeqNum, self.ackNum, self.winSize, CRPFlag.DTA_FLAG)
            packed = self.__packPacket(header, packet)
            unackPackets.append({"Seq":currSeqNum, "Send":True, "Time":0, "Data":packed, "Acks":0})
            currSeqNum = (currSeqNum + 1) % self.CRP_MAX_SEQ_NUM

        sendBase = self.seqNum
        lastUnacked = sendBase
        #print "Unacked Packets: %s" % len(unackPackets)

        while (unackPackets):
            window = unackPackets[0:self.clientWinSize]

            # Send the window of packets
            for curr in window:
                if curr["Send"]:
                    # Handle a window change request on client side
                    # Unpack the current packet and set the correct bit and new window size
                    # Then repack and send
                    if self.newWindow:
                        _, packetData = self.__parsePacket(curr["Data"])
                        newHeader = self.__customHeader(s, self.ackNum, self.winSize, CRPFlag.DTA_FLAG & CRPFlag.WIN_FLAG)
                        newPacket = self.__packPacket(newHeader, packetData)
                        curr["Data"] = newPacket
                        self.newWindow = False
                    curr["Time"] = time.time()
                    curr["Send"] = False
                    #print "Sending sequence number: %s" % curr["Seq"]
                    self.sent += 1
                    try:
                        self.mainSocket.sendto(curr["Data"], self.clientAddr)
                    except socket.error:
                        raise StateError("The connection was forcibly closed by the remote host")
                        return

                currTime = time.time()
                #print currTime - curr["Time"]
                if currTime - curr["Time"] > self.CRP_PACKET_TIMEOUT:
                    print "Packet %s timed out" % curr["Seq"]
                    #print (currTime - curr["Time"])
                    curr["Send"] = True

            try:
                response, addr = self.mainSocket.recvfrom(self.CRP_HEADER_LENGTH)
                try:
                    respInfo, _ = self.__parsePacket(response)
                    if respInfo["CHK"] == 0:
                        continue
                    if CRPFlag.RST_FLAG in respInfo["FLG"]:
                        raise UnableToConnectException("Connection was not properly established. Please attempt to reconnect")
                        return
                    if CRPFlag.ACK_FLAG in respInfo["FLG"]:
                        ackNum = respInfo["ACK"]
                        #if ackNum % 10 == 0:
                        #print "Received Ack: %s" % ackNum
                        lastUnacked = ackNum
                        if lastUnacked < sendBase:
                            temp = 0
                            for w in window:
                                if w["Seq"] == lastUnacked:
                                    break
                                else:
                                    temp += 1
                            newBase = temp
                        else:
                            newBase = lastUnacked-sendBase

                        self.__incrementSequence(newBase)
                        if newBase >= len(unackPackets):
                            # Nothing left to send
                            #print "Nothing left to send here"
                            break
                        unackPackets = unackPackets[newBase:]

                        if newBase < self.clientWinSize:
                            #print self.clientWinSize
                            window[newBase]["Acks"] += 1
                            if window[newBase]["Acks"] > 2:
                                #print "Retransmit: %s" % window[newBase]["Seq"]
                                window[newBase]["Acks"] = 0
                                window[newBase]["Send"] = True
                        sendBase = lastUnacked


                except ChecksumError:
                    # Drop bad ACK
                    continue
            except socket.timeout:
                continue

        print self.sent
        return

    def recvData(self, buff):

        dataBuffer = ''

        receiving = True

        self.mainSocket.settimeout(1)
        timeoutsBeforeReturn = 3

        while (receiving):

            try:
                # Check if buffered packets can be order and returned
                while True:
                    if self.ackNum in self.bufferedPackets:
                        if len(dataBuffer) + self.bufferedPackets[self.ackNum] > buff:
                            return dataBuffer
                        else:
                            dataBuffer += self.bufferedPackets[self.ackNum]
                            del self.bufferedPackets[self.ackNum]
                            self.ackNum = (self.ackNum + 1) % self.CRP_MAX_ACK_NUM
                    else:
                        break


                packet, addr = self.mainSocket.recvfrom(buff)
                headerInfo, payload = self.__parsePacket(packet)

                if CRPFlag.DTA_FLAG in headerInfo["FLG"]:
                    currSeq = headerInfo["SEQ"]
                    if currSeq < self.ackNum or headerInfo["CHK"] == 0:
                        # Already received this packet or corrupted. Ignore it
                        pass
                    elif currSeq > self.ackNum:
                        # Buffer packet and continue
                        #print "Buffering"
                        if currSeq < ((self.ackNum + self.winSize) % self.CRP_MAX_ACK_NUM):
                            self.bufferedPackets[currSeq] = payload
                        else:
                            # Drop any other packet not in window
                            pass
                    else:
                        # Correct next packet. Append the data to our buffer
                        dataBuffer += payload
                        self.ackNum = (self.ackNum + 1) % self.CRP_MAX_ACK_NUM

                    #print "Received sequence number: %s" % currSeq
                    #print "Acking: %s" % self.ackNum
                    respHeader = self.__customHeader(self.seqNum, self.ackNum, self.winSize, CRPFlag.ACK_FLAG)
                    respPacket = self.__packPacket(respHeader)
                    self.mainSocket.sendto(respPacket, self.clientAddr)

                    # Check if we need to return data from the buffer
                    if len(dataBuffer) + self.CRP_MAX_PACKET_SIZE > buff:
                        # Return our buffer if we may exceed buff size
                        return dataBuffer

            except socket.timeout as err:
                # If we stop receiving for a while, break the loop to return any buffered data
                timeoutsBeforeReturn -= 1
                if timeoutsBeforeReturn == 0:
                    receiving = False
            """except ChecksumError as cerr:
                                                    # Drop corrupted packets
                                                    continue"""

        print "Returning buffer"
        return dataBuffer

    def updateWindowSize(self, newWinSize):
        if newWinSize >= 0 and newWinSize < self.CRP_MAX_WINSIZE:
            self.winSize = newWinSize
        else:
            raise Exception("Invalid window size. Must be positive integer < 65536")

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
            segment = data[base:base+self.CRP_MAX_PACKET_SIZE]
            segments.append(segment)
            base += self.CRP_MAX_PACKET_SIZE

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
            headerInfo["CHK"] = 0
        return headerInfo, data

    def __customHeader(self, seq, ack, win, flags):
        try:
            header = pack("<HHHh", seq, ack, win, flags)
            return header
        except:
            return None

    def __generateHeader(self, flags):
        """
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |        Sequence Number        |     Acknowledgment Number     |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                               |                  |A|R|W|D|C|E||
        |         Window Length         |    x0000000000   |C|S|I|T|O|N||
        |                               |                  |K|T|N|A|N|D||
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        |                           Checksum                            |
        +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
        Generates the header without the checksum. The checksum is calculated later
        This is for a generic header where values are default.
        """
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
        packedHeader = pack("<HHHh", seq, ack, win, flags)

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