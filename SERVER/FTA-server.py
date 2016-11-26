import sys
sys.path.insert(0, '../')
from CRP import CRPSocket
import threading
import os
import os.path
import time
import logging
try:
    import readline
except ImportError:
    print "Readline is not available on Windows Python 2.7.6 for some reason"

class Request:
    GET = 'GET'
    POST = 'POST'
    NONE = 'NONE'

class FTAServer():

    def __init__(self, log):
        self.receive = True
        self.crpSock = None
        self.sending = False
        self.receiving = False
        self.active = True

        self.log = logging.getLogger('server')
        self.log.setLevel(log)

    def handleConnection(self, conn, addr):
        print "Now servicing client: %s %s" % conn.clientAddr[:2]
        lastServiced = time.time()
        waiting = True
        while (waiting):
            try:
                if self.crpSock.state <= 1:
                    break
                if time.time() - lastServiced > 30:
                    print "Connection timed out. Force closing connection..."
                    conn.close()
                    break
                request = conn.recvData(2048)
                if request:
                    self.log.debug("Received request from client:\n%s" % request)
                    requestLines = request.splitlines()
                    response, fileName, fileSize, reqType = self.handleRequest(requestLines)

                    if response[:5] == "READY":
                        conn.sendData(response)
                        if reqType == Request.GET:
                            self.log.debug("Received GET request from client")
                            self.getRequest(conn, fileName)
                        elif reqType == Request.POST:
                            self.log.debug("Received POST request from client")
                            self.postRequest(conn, fileName, fileSize)
                    else:
                        self.log.debug("Received an invalid request")
                        conn.sendData(response)
                        continue
                    lastServiced = time.time()
            except:
                continue

    def getRequest(self, conn, fileName):
        print "Ready to send '%s' to the client" % fileName
        self.sending = True
        with open(fileName, 'rb') as file:
            while self.sending:
                data = file.read()
                if data:
                    self.log.debug("Sending file '%s' to the client" % fileName)
                    result = conn.sendData(data)
                    if result:
                        print "Successfully sent '%s' (%s bytes) to the client" % (fileName, os.path.getsize(fileName))
                    else:
                        print "Client cancelled and closed the connection before receiving the entire file"
                    self.sending = False
                    break


    def postRequest(self, conn, fileName, length):
        self.receiving = True
        remainingBytes = length
        lastReceivedTime = time.time()
        print "Receiving '%s' from the client" % fileName
        with open(fileName, 'wb') as file:
            while self.receiving:
                data = conn.recvData(4096)
                if data:
                    lastReceivedTime = time.time()
                    remainingBytes -= len(data)
                    self.log.debug("Received a data chunk from the client. %s bytes remaining" % remainingBytes)
                    file.write(data)
                    if remainingBytes == 0:
                        self.receiving = False
                        print "Successfully received '%s' (%s bytes) from the client" % (fileName, length)
                        file.close()
                else:
                    if time.time() - lastReceivedTime > 30:
                        print "Connection timed out. Closing connection"
                        file.close()
                        conn.close()
                        return


    def handleRequest(self, requestLines):
        request = requestLines[0]
        if request == Request.GET:
            fileName = requestLines[1].strip()

            response = ""

            if os.path.isfile(fileName):
                response += "READY\n"
                fileSize = os.path.getsize(fileName)
                response += "LENGTH:%s" % fileSize
                return response, fileName, fileSize, Request.GET
            else:
                response += "ERROR\n"
                response += "File does not exist"
                return response, None, -1, Request.GET

        elif request == Request.POST:
            fileName = requestLines[1].strip()

            response = ""

            try:
                fileSize = int(requestLines[2][7:])
                response += "READY"
                return response, fileName, fileSize, Request.POST

            except:
                response += "ERROR\n"
                response += "Invalid file length"
                return response, None, -1, Request.POST

        else:
            return "BADREQUEST\nMust be POST or GET request", None, -1, Request.NONE

        

    def handleInput(self):
        while True:
            inp = raw_input()
            commands = inp.split(' ')
            command = commands[0].lower()
            if command == 'window':
                if len(commands) < 2:
                    print 'Please provide a valid window'
                    continue
                windowLength = int(commands[1])
                if windowLength < 0 or windowLength > 65535:
                    print 'Invalid window length. Must be in range [0, 65535]'
                    continue
                self.setWindow(windowLength)
            elif command == 'terminate':
                """while self.sending:
                    pass"""
                self.active = False
                if self.crpSock.state > 1:
                    print "Closing all active connections..."
                    self.crpSock.close()
                print "Goodbye"
                self.crpSock.mainSocket.close()
                os._exit(0)
            elif command == 'help':
                print '\nwindow W: set the client\'s receive window to W'
                print 'terminate: disconnect from client and exit the application'
            else:
                print "Please enter a valid command. Type 'help' for a list of commands"

    def startServer(self, port):
        self.crpSock = CRPSocket(True)
        try:
            self.crpSock.bind(('', port))
        except:
            os._exit(0)
        threading.Thread(target=self.handleInput).start()
        try:
            while self.active:
                print "Waiting for new connections"
                self.crpSock.listen()
                conn, addr = self.crpSock.accept()
                self.handleConnection(conn, addr)
        except KeyboardInterrupt:
            sys.exit()

    def setWindow(self, winSize):
        print "Setting window size to %s" % winSize
        self.crpSock.updateWindowSize(winSize)

if __name__ == "__main__":
    PORT = 5000
    log_level = logging.INFO
    logging.basicConfig(format='%(levelname)s-%(message)s', level=logging.INFO)

    try:
        try:
            PORT = int(sys.argv[1])
            if len(sys.argv) > 2:
                if sys.argv[2] == '-d':
                    log_level = logging.DEBUG
        except:
            print "Please provide valid port"
            os._exit(0)
        server = FTAServer(log_level)
        server.startServer(PORT)
    except KeyboardInterrupt:
        os._exit(0)