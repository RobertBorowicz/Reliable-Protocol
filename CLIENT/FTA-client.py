import sys
sys.path.insert(0, '../')
from CRP import CRPSocket
import threading
import os
import os.path
import time


class FTAClient():

    def __init__(self, addr):
        self.CRP = CRPSocket()
        self.address = addr
        self.idle = True
        self.connected = False
        self.commandQueue = []
        self.receiving = False
        self.sending = False

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
                    self.getRequest(commands[1])

            elif command == 'post':
                # TODO
                pass
            elif command == 'connect':
                print "Attempting connection"
                self.connect()
            elif command == 'window':
                if len(commands) < 2:
                    print 'Please provide a valid window'
                    continue
                windowLength = int(commands[1])
                if windowLength < 0 or windowLength > 65535:
                    print 'Invalid window length. Must be in range [0, 65535]'
                    continue
                self.setWindow(windowLength)
            elif command == 'terminate':
                while self.sending:
                    pass
                self.CRP.close()
                sys.exit(0)
            else:
                print "Please enter a valid command. ('window x' or 'terminate')"

    def handleCommand(self, command):
        if command[0] == 'get':
            self.getRequest(command[1])
        elif command[0] == 'post':
            self.postRequest(command[1])

    def queueCommands(self):
        while True:
            if len(self.commandQueue > 0) and self.idle:
                self.handleCommand(self, commandQueue.pop(0))

    def getRequest(self, file):
        getHeader = "GET\n"
        getHeader += file

        if self.connected:
            print getHeader
            self.CRP.sendData(getHeader)
            while True:
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


    def getRequestData(self, file, length):
        print "Ready to receive data"
        self.receiving = True
        remainingBytes = length
        lastReceivedTime = time.time()
        with open(file, 'wb') as f:
            while self.receiving:
                try:
                    data = self.CRP.recvData(2048)
                    if data:
                        lastReceivedTime = time.time()
                        remainingBytes -= len(data)
                        #print remainingBytes
                        f.write(data)
                        if remainingBytes == 0:
                            self.receiving = False
                            f.close()
                    else:
                        if time.time() - lastReceivedTime > 30:
                            print "Connection timed out. Closing connection"
                            f.close()
                            os.remove(file)
                            self.CRP.close()
                            return
                except:
                    continue


    def postRequest(self, file):
        pass

    def connect(self):
        print self.address
        self.CRP.connect(self.address)
        self.connected = True

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