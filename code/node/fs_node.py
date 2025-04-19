import socket
import sys
import readline
import threading
from concurrent.futures import ThreadPoolExecutor

from node.socket_pool import *
from node.node_packet_handling import *
from node.file_download_handler import *
from node.node_ratings import *
from node.received_chunk_requests_handler import *


# Configurações do cliente
#IP do servidor, será preenchido no inicio do programa
SERVER_IP = ""
TRACKER_PORT = 12345            # Porta do servidor


if __name__ == '__main__':
    
    # buscar o IP Address do PC 
    #ip_host = socket.gethostbyname(socket.gethostname())
    #print(f"Host IP: {ip_host}")
    
    #Init std_rating
    node_ratings_lock.acquire()
    node_ratings['0'] = 0.1
    node_ratings_lock.release()
    
    
    #Create socket pool for packet transmission and reception
    for i in range(MAX_SENDER_THREADS + MAX_REQUESTING_THREADS):
        socket_in_pool = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) # create UDP socket
        socket_in_pool.bind(('',0))
        socket_pool.append((True,socket_in_pool)) #Add it to the pool

    receive_requests_socket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) # create UDP socket to receive requests
    receive_requests_socket.bind(('',TRANSFER_PORT)) #bind it to port 9090
    #Create a thread that will handle incoming chunk requests
    chunk_requests_handler_thread = threading.Thread(target=handler_received_requests,args=(receive_requests_socket,))
    chunk_requests_handler_thread.start()
    
    
    SERVER_IP = sys.argv[1]  # --> IP do servidor onde o tracker está a correr

    tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # instantiate TCP socket
    tracker_socket.connect((SERVER_IP, TRACKER_PORT))  # connect to the server
    tracker_socket_lock = RLock()
    empty_socket(tracker_socket,None)

    node_register(tracker_socket,tracker_socket_lock)  #Register node in tracker

    message = input(" -> ")  # take input
    
    try:
        #Create thread pools
        with (
            #Pool that manages file downloads
            ThreadPoolExecutor(MAX_SIMULTANEOUS_DOWNLOADS) as download_manager_executor, 
            #Pool that mananges individual chunk transfer
            ThreadPoolExecutor(MAX_REQUESTING_THREADS) as request_chunk_executor, 
        ):
            while message != "exit":
                comandos = message.strip().split(' ')

                if comandos[0] == "add":
                    node_add_files(comandos,tracker_socket,tracker_socket_lock)
                elif comandos[0] == "get":
                    ficheiro = comandos[1]
                    node_download(ficheiro, tracker_socket, download_manager_executor,request_chunk_executor,tracker_socket_lock)
                elif comandos[0] == "list":
                    node_list_files(tracker_socket,tracker_socket_lock)
                elif comandos[0] == "remove":
                    node_remove_files(comandos,tracker_socket,tracker_socket_lock)

                message = input(" -> ")  # take input again

    except KeyboardInterrupt:
        print("Interrupted by the user. Closing connection.")
    
    finally:
        unregister_node(tracker_socket,tracker_socket_lock)
        #avisa o tracker do fim da conexão
        tracker_socket.shutdown(socket.SHUT_RDWR)
        tracker_socket.close()
        
        receive_requests_socket.close()
        
        #Close sockets in pool
        for bool,socket_in_pool in socket_pool:
            socket_in_pool.close()

        