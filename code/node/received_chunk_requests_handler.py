import socket
from socket import *
from threading import RLock
from concurrent.futures import ThreadPoolExecutor

from node.socket_pool import *
from node.node_data_structs import *
from utils.transfer_protocol import *


def handler_received_requests(incoming_requests_socket:socket):
    try:
        node_name = socket.gethostname()
        with ThreadPoolExecutor(MAX_SENDER_THREADS) as executor:
            while True:
                packet = receive_transfer_packet(incoming_requests_socket)
                #Ignore packets with errors
                if packet == None:
                    print("Received packet with errors")
                    continue
                #Assign the packet to a thread in the thread pool
                executor.submit(handle_received_chunk_request,packet,node_name)
    except KeyboardInterrupt:
        return
                
        
def handle_received_chunk_request(packet,node_name):
    try:
        chosen_socket = find_available_socket()
        #Separate packet components
        address,file_hash,chunk,data = packet
        #Find filename
        filename = own_files_hash_to_name[file_hash]
        file_path = node_name + "/" + filename
        #Aquire file lock
        if file_hash not in file_locks:
            print("File lock doesn't exist!")
            free_socket(chosen_socket)
            return
        lock: RLock() = file_locks[file_hash]
        lock.acquire()
        #Open file
        with open(file_path,"rb") as file:
            #Go to wanted chunk
            file.seek(chunk * CHUNK_SIZE)
            #Read chunk bytes
            chunk_data = file.read(CHUNK_SIZE)
        lock.release()
        #Create packet with data
        file_data_packet = create_transfer_packet(file_hash,chunk,chunk_data)
        #Send packet
        chosen_socket.sendto(file_data_packet,address)
        free_socket(chosen_socket)
    except KeyboardInterrupt:
        return