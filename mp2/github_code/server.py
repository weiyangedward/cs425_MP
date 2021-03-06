"""

    def main():
        1. parse args
        2. init a lock for both of Replica and Server
        3. init Server obj
        4. launch Server thread to talk to client
        5. listen to manager command

    class Server(derived from multiprocessing.Process):

        def __init__(serverID, arg_consistency, variableStored, lock):
            get server Address and Port info from configreader
            set consistency model (eventual consistency modified from channel, linearizability modified from totalOrderChannel)
            set TCP connect

        def run():
            launch a replicaThread
            while True:
                keep accepting client
                launch a server thread for a client

        def serverThread():

        def replicaThread():
            set UDP connect
            while true:
                receiving message
                self.server.consistency.recv(data, address)


"""

import multiprocessing
from threading import Thread
import sys
import threading
import socket
import argparse
import configreader
from variableStored import VariableStored
from eventualConsistency import EventualConsistency
from linearizabilityConsistency import LinearizabilityConsistency


class Server(multiprocessing.Process):
    """
        a server gets request from all clients and sends data back
    """
    def __init__(self, serverID, arg_consistency, W, R):
        super(Server, self).__init__()
        # get address and port info
        self.process_info, self.addr_dict = configreader.get_processes_info()
        self.address = self.process_info[serverID]
        self.ip, self.port = self.address[0], self.address[1]

        self.arg_consistency = arg_consistency
        self.lock = multiprocessing.Lock()
        self.serverID = serverID
        self.W = W
        self.R = R

        """    
            init TCP connect to clients 
        """
        for res in socket.getaddrinfo(self.ip, self.port, socket.AF_UNSPEC, socket.SOCK_STREAM, 0, socket.AI_PASSIVE):
            af, socktype, proto, canonname, sa = res
            try:
                print("building a socket")
                self.socket = socket.socket(af, socktype, proto) # build a socket
            except socket.error as msg:
                self.socket = None
                continue
            try:
                print("binding to a socket")
                self.socket.bind(sa) # build to a socket
                print("listening")
                self.socket.listen(1) # listen
            except socket.error as msg:
                self.socket.close()
                self.socket = None
                continue
            break
        if self.socket is None:
            print('could not open socket')

        """
            init consistency model
        """
        if (self.arg_consistency == "eventual"):
            if (self.serverID == 1):
                self.consistency = EventualConsistency(self, self.serverID, self.process_info, self.addr_dict, self.W, self.R, self.lock, True)
            else:
                self.consistency = EventualConsistency(self, self.serverID, self.process_info, self.addr_dict, self.W, self.R, self.lock)
        elif (self.arg_consistency == "linearizability"):
            if (self.serverID == 1):
                self.consistency = LinearizabilityConsistency(self, self.serverID, self.process_info, self.addr_dict, self.lock, True)
            else:
                self.consistency = LinearizabilityConsistency(self, self.serverID, self.process_info, self.addr_dict, self.lock)
        else:
            print("consistency model not known")
    

    def recvClient(self, data, conn):
        print("server recvClient...")
        self.consistency.recvClient(data, conn)

    def recvReplica(self, data):
        print("server recvReplica...")
        self.consistency.recvReplica(data)

    """
        init a thread for server replica
        init a new thread for every client
    """
    def run(self):
        try:
            # init replica thread
            t_replica = Thread(target = self.replicaThread, args=())
            t_replica.start()

            while(1):
                conn, addr = self.socket.accept() # accept
                print('Connected by', addr) # addr = (host, port)
                # init a server thread for a client
                t_serverThread = Thread(target = self.serverThread, args=(conn, ))
                t_serverThread.start()
        except:
            print("CTRL C occured")
        finally:
            print("exit server thread")
            self.socket.close()
            t_replica.terminate()

    # replicaThread function
    def replicaThread(self):
        process_info, addr_dict = self.process_info, self.addr_dict
        address = self.address
        ip, port = self.ip, self.port

        socketUDP = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        socketUDP.bind(address)
        try:
            while True:
                data, address = socketUDP.recvfrom(4096)
                self.recvReplica(data)
        except:
            print("CTRL C occured")
        finally:
            print("exit replica thread")
            socketUDP.close()

    # serverThread function
    def serverThread(self, conn):
        # try:
        while True:
            data, address = conn.recvfrom(4096)
            if not data: break
            print("receive client message ", data, address)
            self.recvClient(data, conn)
        # except:
        #     print("disconnected from client")
        # finally:
        print("Lost connection from client")
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="replica server")
    parser.add_argument("id", help="process id (1-10), default=1", type=int, default=1)
    parser.add_argument("consistency", help="consistency model (eventual || linearizability), default=eventual", type=str, default='eventual')
    parser.add_argument("W", help="number of w_ack indicates finished, default=1", type=int, default='1')
    parser.add_argument("R", help="number of r_ack indicates finished, default=1", type=int, default='1')
    args = parser.parse_args()
    # lock = multiprocessing.Lock()

    # start server thread
    t_server = Server(args.id, args.consistency, args.W, args.R)
    t_server.daemon = True
    t_server.start()

    # replica talks to other replicas
    try:
        while True and t_server.is_alive():
            cmd = raw_input()
            if cmd:
                cmd_args = cmd.split()
                if cmd_args[0] == "exit": break
    except KeyboardInterrupt:
        print("CTRL C occured")
    finally:
        print("exit server process")
        t_server.terminate()

if __name__ == '__main__':
    main()
