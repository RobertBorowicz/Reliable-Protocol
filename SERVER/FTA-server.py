import sys
sys.path.insert(0, '../')
from CRP import CRPSocket
import threading
import os.path
import time

class Request:
    GET = 'GET'
    POST = 'POST'
    NONE = 'NONE'

class FTAServer():

    def __init__(self):
        self.receive = True
        self.crpSock = None
        self.sending = False
        self.receiving = False
        self.active = True

    def handleConnection(self, conn, addr):
        print "Now servicing %s %s" % conn.clientAddr
        lastServiced = time.time()
        waiting = True
        while (waiting):
            try:
                if time.time() - lastServiced > 30:
                    print "Connection timed out. Closing connection..."
                    conn.close()
                    break
                request = conn.recvData(2048)
                if request:
                    requestLines = request.splitlines()
                    response, fileName, fileSize, reqType = self.handleRequest(requestLines)
                    print response

                    if response[:5] == "READY":
                        conn.sendData(response)
                        print "All good"
                        if reqType == Request.GET:
                            self.getRequest(conn, fileName)
                        elif reqType == Request.POST:
                            print 'Posting'
                            self.postRequest(conn, fileName, fileSize)
                    else:
                        conn.sendData(response)
                        continue
                    lastServiced = time.time()
            except:
                continue

    def getRequest(self, conn, fileName):
        print "Ready to service get request"
        self.sending = True
        with open(fileName, 'rb') as file:
            while self.sending:
                data = file.read()
                if data:
                    print "Sending data"
                    result = conn.sendData(data)
                    if result:
                        print "Successfully sent %s bytes to client" % os.path.getsize(fileName)
                    else:
                        print "Client cancelled and closed the connection before receiving the entire file"
                    self.sending = False
                    break


    def postRequest(self, conn, fileName, length):
        self.receiving = True
        remainingBytes = length
        lastReceivedTime = time.time()
        buff = ''
        print 'Receiving data'
        with open(fileName, 'wb') as file:
            while self.receiving:
                data = conn.recvData(4096)
                if data:
                    lastReceivedTime = time.time()
                    remainingBytes -= len(data)
                    buff += data
                    #file.write(data)
                    if remainingBytes < 10000:
                        print remainingBytes
                    if remainingBytes == 0:
                        self.receiving = False
                        file.write(buff)
                        file.close()
                else:
                    if time.time() - lastReceivedTime > 30:
                        print "Connection timed out. Closing connection"
                        file.close()
                        conn.close()
                        return


    def handleRequest(self, requestLines):
        print "Handling request"
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
                print "Invalid file length"
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
                self.crpSock.close()
                sys.exit(0)
            else:
                print "Please enter a valid command. ('window x' or 'terminate')"

    def startServer(self, port):
        self.crpSock = CRPSocket()
        self.crpSock.bind(('', port))
        threading.Thread(target=self.handleInput).start()
        try:
            #while True:
            while self.active:
                print "Waiting for connections"
                self.crpSock.listen()
                conn, addr = self.crpSock.accept()
                self.handleConnection(conn, addr)
        except KeyboardInterrupt:
            sys.exit()

    def setWindow(self, winSize):
        self.crpSock.updateWindowSize(winSize)

if __name__ == "__main__":
    PORT = 5000
    #log_level = logging.INFO
    #logging.basicConfig(format='%(levelname)s-%(message)s', level=logging.INFO)

    try:
        try:
            PORT = int(sys.argv[1])
        except:
            print "Please provide valid port"
            sys.exit(0)
        server = FTAServer()
        server.startServer(PORT)
    except KeyboardInterrupt:
        sys.exit(0)