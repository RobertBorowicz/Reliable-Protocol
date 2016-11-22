from CRP import CRPSocket
import sys
import threading

class Server():

    def __init__(self):
        self.receive = True
        self.crpSock = None

    def handleConnection(self, conn, addr):
        print conn.clientAddr
        with open("DST/dst.gif", 'wb') as f:
            while (self.receive):
                try:
                    data = conn.recvData(4096)
                    if data:
                        f.write(data)
                    elif not data or len(data) == 0:
                        f.close()
                        break
                except:
                    pass

    def echoInput(self):
        while True:
            p = raw_input()
            if "terminate" in p:
                print "Terminating"
                self.crpSock.close()
                sys.exit()

    def startServer(self):
        self.crpSock = CRPSocket(True)
        self.crpSock.bind(('', 5000))
        threading.Thread(target=self.echoInput).start()
        self.crpSock.listen()
        try:
            #while True:
            conn, addr = self.crpSock.accept()
            threading.Thread(target=self.handleConnection, args=(conn, addr)).start()
        except KeyboardInterrupt:
            sys.exit()

server = Server()
server.startServer()