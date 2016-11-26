import sys
sys.path.insert(0, '../')
from CRP import CRPSocket
import threading
import os
import os.path
import time
import traceback
import logging
try:
    import readline
except ImportError:
    print "Readline is not available on Windows Python 2.7.6 for some reason"

class FTAClient():

    def __init__(self, addr, log, v6):
        self.CRP = CRPSocket(v6)
        self.address = addr
        self.idle = True
        self.connected = False
        self.commandQueue = []
        self.receiving = False
        self.sending = False
        self.active = True

        self.log = logging.getLogger('server')
        self.log.setLevel(log)

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
                else:
                    print "Please wait until the current request has finished"

            elif command == 'post':
                if len(commands) < 2:
                    print 'Must provide a file name'
                    continue

                if not os.path.isfile(commands[1]):
                    print "Invalid file name provided"
                    continue

                if self.idle:
                    threading.Thread(target=self.postRequest, args=(commands[1],)).start()
                else:
                    print "Please wait until the current request has finished"

            elif command == 'connect':
                if not self.connected:
                    print "Attempting connection..."
                    self.connect()
                else:
                    print "Already connected"

            elif command == 'window':
                if len(commands) < 2:
                    print 'Please provide a window value'
                    continue
                try:
                    windowLength = int(commands[1])
                except:
                    print "Please provide a valid window"
                    continue
                if windowLength <= 0 or windowLength > 65535:
                    print 'Invalid window length. Must be in range [1, 65535]'
                    continue
                self.setWindow(windowLength)

            elif command == 'disconnect':
                if self.sending:
                    print "Client will disconnect after it has finished sending"
                while self.sending:
                    pass
                print "Now closing the connection..."
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

    def checkForDisconnect(self):
        while True:
            if self.CRP.state <= 1:
                print "Connection has been closed.\nGoodbye"
                self.CRP.mainSocket.close()
                os._exit(0)
                break

    def handleCommand(self, command):
        if command[0] == 'get':
            self.getRequest(command[1])
        elif command[0] == 'post':
            self.postRequest(command[1])

    def queueCommands(self):
        while self.active:
            if len(self.commandQueue > 0) and self.idle:
                self.handleCommand(self, commandQueue.pop(0))

    def postRequest(self, file):
        postHeader = "POST\n"
        postHeader += "%s\n" % file
        postHeader += "LENGTH:%s" % (os.path.getsize(file))
        self.log.debug("Post Request Header:\n%s" % postHeader)
        
        if self.connected:
            self.log.debug("Sending the POST header to the server")
            post = self.CRP.sendData(postHeader)
            if post:
                while self.active:
                    self.log.debug("Waiting for READY from server")
                    response = self.CRP.recvData(2048)
                    if response:
                        if response[0:5] == "READY":
                            self.log.debug("Received READY")
                            self.postRequestData(file)
                            break
                        else:
                            print response
                            break
        else:
            print "Not connected to the server"

    def getRequest(self, file):
        getHeader = "GET\n"
        getHeader += file
        self.log.debug("Get Request Header:\n%s" % getHeader)

        if self.connected:
            self.log.debug("Sending the GET header to the server")
            if self.CRP.sendData(getHeader):
                while self.active:
                    self.log.debug("Waiting for READY from server")
                    response = self.CRP.recvData(1024)
                    if response:
                        if response[0:5] == "READY":
                            self.log.debug("Received READY")
                            responseLines = response.splitlines()
                            length = int(responseLines[1][7:])
                            self.getRequestData(file, length)
                            break
                        else:
                            print response
                            break
        else:
            print "Not connected to the server"

    def postRequestData(self, filename):
        self.sending = True
        with open(filename, 'rb') as file:
            self.idle = False
            while self.sending:
                data = file.read()
                if data:
                    print "Sending '%s' to the server" % filename
                    result = self.CRP.sendData(data)
                    if result:
                        print "Successfully sent '%s' (%s bytes) to the server" % (filename, os.path.getsize(filename))
                    else:
                        print "Server cancelled and closed the connection before receiving the entire file"
                    self.sending = False
                    break
        self.idle = True


    def getRequestData(self, file, length):
        print "Ready to receive %s" % file
        self.receiving = True
        self.idle = False
        remainingBytes = length
        lastReceivedTime = time.time()
        with open(file, 'wb') as f:
            while self.receiving:
                try:
                    data = self.CRP.recvData(2048)
                    if data:
                        lastReceivedTime = time.time()
                        remainingBytes -= len(data)
                        self.log.debug("Received a data chunk from the server. Remaining bytes to receive: %s" % remainingBytes)
                        f.write(data)
                        if remainingBytes == 0:
                            print "Successfully received '%s' (%s bytes) from the server" % (file, length)
                            self.receiving = False
                            f.close()
                    else:
                        if time.time() - lastReceivedTime > 15:
                            print "Connection timed out. Closing the connection and removing partial files"
                            f.close()
                            os.remove(file)
                            self.CRP.close()
                            os._exit(0)
                            return
                except:
                    #traceback.print_exc()
                    break
            if remainingBytes > 0:
                f.close()
                os.remove(file)
                print "Connection was terminated by the server before receiving the full file."                
        self.idle = True

    def connect(self):
        try:
            if self.CRP.connect(self.address):
                print "Now connected to the remote server"
                self.connected = True
                threading.Thread(target=self.checkForDisconnect).start()
            else:
                print "Failed to connect to the remote server. Please try again."
        except:
            print "Failed to connect to the remote server. Please try again."

    def setWindow(self, winSize):
        print "Setting window size to %s" % winSize
        self.CRP.updateWindowSize(winSize)

if __name__ == "__main__":
    HOST = 'localhost'
    PORT = 5000
    log_level = logging.INFO
    logging.basicConfig(format='%(levelname)s-%(message)s', level=logging.INFO)
    v6 = False

    try:
        HOST = sys.argv[1]
        try:
            PORT = int(sys.argv[2])
            if len(sys.argv) > 3:
                if sys.argv[3] == '-d':
                    print 'Debug enabled'
                    log_level = logging.DEBUG
                elif sys.argv[3] == '-v6':
                    print 'IPv6 mode enabled. Make sure the provided address is the server IPv6 address'
                    v6 = True
                else:
                    print "Invalid flag provided"
                    os._exit(0)
                if len(sys.argv) > 4:
                    if sys.argv[4] == '-d':
                        print 'Debug enabled'
                        log_level = logging.DEBUG
                    elif sys.argv[4] == '-v6':
                        print 'IPv6 mode enabled. Make sure the provided address is the server IPv6 address'
                        v6 = True
                    else:
                        print "Invalid flag provided"
                        os._exit(0)
        except:
            print 'Please provide a valid port number'
            os._exit(0)
        address = (HOST, PORT)
        client = FTAClient(address, log_level, v6)
        client.startClient()

    except KeyboardInterrupt:
        os._exit(0)