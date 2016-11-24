import sys
sys.path.insert(0, '../')
from CRP import CRPSocket
import threading
import os
import os.path
import time
import traceback


class FTAClient():

    def __init__(self, addr):
        self.CRP = CRPSocket()
        self.address = addr
        self.idle = True
        self.connected = False
        self.commandQueue = []
        self.receiving = False
        self.sending = False
        self.active = True

    def startClient(self):
        print "Client is ready to receive commands\nFor a list of commands, type 'help'"
        self.idle = True
        threading.Thread(target=self.handleInput).start()

    def handleInput(self):
        while True:
            inp = raw_input()
            commands = inp.split(' ')
            command = commands[0].lower()
            if command == 'get':
                if len(commands) < 2:
                    print 'Must provide a file name'
                    continue

                if self.idle:
                    threading.Thread(target=self.getRequest, args=(commands[1],)).start()

            elif command == 'post':
                if len(commands) < 2:
                    print 'Must provide a file name'
                    continue

                if not os.path.isfile(commands[1]):
                    print "Invalid file name provided"
                    continue

                if self.idle:
                    threading.Thread(target=self.post, args=(commands[1],)).start()

            elif command == 'connect':
                print "Attempting connection"
                self.connect()

            elif command == 'window':
                if len(commands) < 2:
                    print 'Please provide a valid window'
                    continue
                windowLength = int(commands[1])
                if windowLength <= 0 or windowLength > 65535:
                    print 'Invalid window length. Must be in range [1, 65535]'
                    continue
                self.setWindow(windowLength)

            elif command == 'disconnect':
                if self.sending:
                    print "Client will disconnect after it has finished sending"
                while self.sending:
                    pass
                self.CRP.close()
                self.active = False
                sys.exit(0)
                break
            elif command == 'help':
                print '\nconnect: connect to the remote server'
                print 'get X: request a file, X, from the server'
                print 'post X: send a file, X, to the server'
                print 'window W: set the client\'s receive window to W'
                print 'disconnect: disconnect from the server and exit the application'
            else:
                print "Please enter a valid command. Type 'help' for a list of commands"

    def handleCommand(self, command):
        if command[0] == 'get':
            self.getRequest(command[1])
        elif command[0] == 'post':
            self.postRequest(command[1])

    def queueCommands(self):
        while self.active:
            if len(self.commandQueue > 0) and self.idle:
                self.handleCommand(self, commandQueue.pop(0))

    def post(self, file):
        print 'Servicing post request'
        postHeader = "POST\n"
        postHeader += "%s\n" % file
        postHeader += "LENGTH:%s" % (os.path.getsize(file))
        print postHeader
        
        if self.connected:
            print postHeader
            print self.CRP.sendData(postHeader)
            while self.active:
                response = self.CRP.recvData(2048)
                if response:
                    print response
                    if response[0:5] == "READY":
                        self.postRequestData(file)
                        break
                    else:
                        print response
                        break

    def getRequest(self, file):
        getHeader = "GET\n"
        getHeader += file

        if self.connected:
            print getHeader
            print self.CRP.sendData(getHeader)
            while self.active:
                response = self.CRP.recvData(1024)
                if response:
                    print response
                    if response[0:5] == "READY":
                        responseLines = response.splitlines()
                        length = int(responseLines[1][7:])
                        self.getRequestData(file, length)
                        break
                    else:
                        print response
                        break

    def postRequestData(self, filename):
        print "Ready to service post request"
        self.sending = True
        with open(filename, 'rb') as file:
            while self.sending:
                data = file.read()
                if data:
                    print "Sending data"
                    result = self.CRP.sendData(data)
                    if result:
                        print "Successfully sent %s bytes to client" % os.path.getsize(filename)
                    else:
                        print "Server cancelled and closed the connection before receiving the entire file"
                    self.sending = False
                    break


    def getRequestData(self, file, length):
        print "Ready to receive data"
        self.receiving = True
        remainingBytes = length
        lastReceivedTime = time.time()
        with open(file, 'wb') as f:
            while self.receiving:
                try:
                    data = self.CRP.recvData(2048)
                    print len(data)
                    if data:
                        lastReceivedTime = time.time()
                        remainingBytes -= len(data)
                        f.write(data)
                        if remainingBytes == 0:
                            self.receiving = False
                            f.close()
                    else:
                        if time.time() - lastReceivedTime > 15:
                            print "Connection timed out"
                            f.close()
                            os.remove(file)
                            self.CRP.close()
                            return
                except:
                    traceback.print_exc()
                    break
            if remainingBytes > 0:
                print "Connection was terminated before receiving the full file"
                f.close()
                os.remove(file)


    def postRequest(self, file):
        pass

    def connect(self):
        try:
            if self.CRP.connect(self.address):
                self.connected = True
        except:
            print "Unable to connect"

    def initiateClose(self):
        while True:
            if self.idle:
                self.CRP.close()
                print 'Connection has been closed.\nGoodbye'
                return

    def setWindow(self, winSize):
        self.CRP.updateWindowSize(winSize)

"""threading.Thread(target=echoInput).start()

crpSock = CRPSocket()
try:
    #crpSock.connect(('172.17.0.2', 5000))
    if(crpSock.connect(('172.17.0.2', 5000))):
        with open("SRC/src.gif", "rb") as f:
            while True:
                data = f.read()
                if data:
                    crpSock.sendData(data)
                else:
                    break
    else:
        print "exit"
        sys.exit()
except KeyboardInterrupt:
    sys.exit()"""


if __name__ == "__main__":
    HOST = 'localhost'
    PORT = 5000
    #log_level = logging.INFO
    #logging.basicConfig(format='%(levelname)s-%(message)s', level=logging.INFO)

    try:
        HOST = sys.argv[1]
        try:
            PORT = int(sys.argv[2])
        except:
            print 'Please provide a valid port number'
            sys.exit(0)
        address = (HOST, PORT)
        client = FTAClient(address)
        client.startClient()

    except KeyboardInterrupt:
        sys.exit(0)