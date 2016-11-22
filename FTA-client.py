from CRP import CRPSocket
import sys
import threading

def echoInput():
    while True:
        p = raw_input()
        sys.exit()

threading.Thread(target=echoInput).start()

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
    sys.exit()