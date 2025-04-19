from socket import *
import random
import time
import hashlib
import concurrent.futures 
import os
from math import floor

from node.node_ratings import *
from node.socket_pool import *
from node.node_data_structs import *
from utils.tracker_protocol import *
from utils.transfer_protocol import *

TRANSFER_PORT = 9090
#Number of chunks downloaded until updating the tracker on 
# which chunks the node has and fetch the updated info
FILE_INFO_UPDATE_TRIGGER = 50


def handle_file_download(request_chunk_executor,file_hash,file_size,file_name,tracker_socket,tracker_socket_lock):    
    try:
        own_files_hash_to_name[file_hash] = file_name
        node_name = socket.gethostname()
        file_path = node_name + "/" + file_name
        missing_chunks = file_size
        #Delegates chunk requesting to threads
        active_requests = set()
        print_lock.acquire()
        print("Download of file " + file_name + " started")
        print_lock.release()
        
        file_update_counter = 0
        received_chunks = []
        
        if missing_chunks < MAX_SIMULTANEOUS_REQUESTS_PER_FILE:
            startup = missing_chunks
        else:
            startup = MAX_SIMULTANEOUS_REQUESTS_PER_FILE
        
        for i in range(startup):
            request = request_chunk_executor.submit(handle_chunk_download,file_hash,file_path)
            active_requests.add(request)
        
        while active_requests and missing_chunks:
            finished_requests, _ = concurrent.futures.wait(active_requests,return_when=concurrent.futures.FIRST_COMPLETED)
            for sucess in finished_requests:
                result = sucess.result()
                if result != None :
                    received_chunks.append(result)
                    missing_chunks -= 1
                    file_update_counter += 1
                    if not received_chunks:
                        print("Received chunks error!")
                    if file_update_counter > FILE_INFO_UPDATE_TRIGGER:
                        update_packet = Update_File_Packet(file_hash,received_chunks,True)
                        packet = create_tracker_packet(UPDATE_FILE,update_packet.serialize())
                        tracker_socket_lock.acquire()
                        send_tracker_packets(tracker_socket,packet)
                        time.sleep(0.1) #DO NOT REMOVE, removing this may cause crashes
                        msg_type, data = receive_tracker_packet(tracker_socket)
                        tracker_socket_lock.release()
                        
                        file_info_packet = File_Request_Response_Packet.deserialize(data)
                        file_info : FileInfo = file_info_packet.nodeinfo
                        downloading_files_downloaded_chunks_lock.acquire()
                        for (filehash,chunk),status in downloading_files_downloaded_chunks.items():
                            if filehash == file_hash and status == True:
                                file_info.removechunk(chunk)
                        downloading_files_downloaded_chunks_lock.release()
                        
                        node_ratings_lock.acquire()
                        file_info.sortNodesByRating(node_ratings)
                        node_ratings_lock.release()

                        downloading_files_info_lock.acquire()
                        downloading_files_info[file_hash] = file_info
                        downloading_files_info_lock.release()
                        
                        file_update_counter = 0
                        received_chunks = []
                        
                active_requests.remove(sucess)
            for i in range(len(finished_requests)):
                #Enqueue another chunk request if needed
                if (missing_chunks - len(active_requests)) > 0:
                    request = request_chunk_executor.submit(handle_chunk_download,file_hash,file_path)
                    active_requests.add(request)
                    
        with open(file_path,"rb") as file:
            digest = hashlib.file_digest(file,FILE_HASHING_PROTOCOL)
            obtained_hash = digest.hexdigest()
            
        if obtained_hash != file_hash:
            print("File " + file_name + " is not correct, you might want to download it again!")
            filehashes = []
            filehashes.append(file_hash)
            serialized_remove_file_packet = Remove_File_Packet(filehashes).serialize()
            packet = create_tracker_packet(REMOVE_FILE,serialized_remove_file_packet)
            tracker_socket_lock.acquire()
            send_tracker_packets(tracker_socket,packet)
            msg_type, _ = receive_tracker_packet(tracker_socket)
            tracker_socket_lock.release()
            
            file_locks_lock.acquire()
            del file_locks[file_hash]
            file_locks_lock.release()
        else:
            print("File " + file_name + " downloaded successfully!")
            update_packet = Update_File_Packet(file_hash,[],False)
            packet = create_tracker_packet(UPDATE_FILE,update_packet.serialize())
            tracker_socket_lock.acquire()
            send_tracker_packets(tracker_socket,packet)
            time.sleep(0.1) #DO NOT REMOVE, removing this may cause crashes
            msg_type, _ = receive_tracker_packet(tracker_socket)
            tracker_socket_lock.release()
        
        #Delete info from downloading_files_info
        downloading_files_info_lock.acquire()
        del downloading_files_info[file_hash]
        downloading_files_info_lock.release()
        
        #remove downloaded chunk records from downloading_files_downloaded_chunks
        downloading_files_downloaded_chunks_lock.acquire()
        for i in range(file_size):
            del downloading_files_downloaded_chunks[file_hash,i]
        downloading_files_downloaded_chunks_lock.release()
    except KeyboardInterrupt:
        return
        
def choose_chunk_to_request(file_hash,file_info):
    chunks_by_rarity = file_info.getnodeinfo()
    
    while True:
        #Find a chunk to request based on how rare it is
        chunk_position_chosen = floor(random.expovariate(0.3))
        if chunk_position_chosen >= len(chunks_by_rarity):
            chunk_position_chosen = len(chunks_by_rarity) - 1
        chunk_chosen, nodes_with_chunk = chunks_by_rarity[chunk_position_chosen]
        
        
        #if that chunk hasn't been requested, request it
        downloading_files_downloaded_chunks_lock.acquire()
        if (file_hash,chunk_chosen) not in downloading_files_downloaded_chunks:
            downloading_files_downloaded_chunks_lock.release()
            address_position_chosen = floor(random.expovariate(0.3))
            if address_position_chosen >= len(nodes_with_chunk):
                address_position_chosen = len(nodes_with_chunk) - 1
            address_chosen = nodes_with_chunk[address_position_chosen]
            return chunk_chosen, address_chosen
        downloading_files_downloaded_chunks_lock.release()

        
        
        
def receive_chunk_from_node(chosen_socket,file_hash,chunk,address):
    request_chunk_packet = create_transfer_packet(file_hash,chunk)
    #Send request
    chosen_socket.sendto(request_chunk_packet,(address,TRANSFER_PORT))
    
    #Store start time
    start = time.time()
    #Set timeout
    chosen_socket.settimeout(2 * node_ratings['0'])
    #Receive packet
    packet = receive_transfer_packet(chosen_socket)
    #Store reception end time
    end = time.time()
    
    if packet != None:
        received_address,received_file_hash,received_chunk,received_data = packet
        if(address != received_address[0] or file_hash != received_file_hash or chunk != received_chunk):
            print("Data received is not the one requested, expected chunk " + str(chunk) +" but got chunk " + str(received_chunk))
            #Maybe a late packet from a previous request is still in the buffer, so try to read something else in the socket
            packet = None
        
    #Update rating
    if packet == None:
        update_rating(address,end-start,False)
        received_data = None
    else:
        update_rating(address,end-start,True)
        
    return received_data
    
    
def handle_chunk_download(file_hash,file_path):
    try:
        chosen_socket = find_available_socket()
        downloading_files_info_lock.acquire()
        file_info = downloading_files_info[file_hash]
        #Choose a chunk to request
        chunk, address = choose_chunk_to_request(file_hash,file_info)
        downloading_files_info_lock.release()
        downloading_files_downloaded_chunks_lock.acquire()
        downloading_files_downloaded_chunks[file_hash,chunk] = False
        downloading_files_downloaded_chunks_lock.release()
        
        packet_data = receive_chunk_from_node(chosen_socket,file_hash,chunk,address)
        if packet_data == None:
            #try again if it times out
            packet_data = receive_chunk_from_node(chosen_socket,file_hash,chunk,address)
        free_socket(chosen_socket)
        if packet_data == None:
            print("Packet with chunk " + str(chunk) + " from node " + address + " corrupted or lost in transit twice!")
            #Delete chunk from requested chunks dict
            downloading_files_downloaded_chunks_lock.acquire()
            del downloading_files_downloaded_chunks[file_hash,chunk]
            downloading_files_downloaded_chunks_lock.release()
            return None

        #If chunk already received before, discard it
        downloading_files_downloaded_chunks_lock.acquire()
        if downloading_files_downloaded_chunks[file_hash,chunk] == True:
            downloading_files_downloaded_chunks_lock.release()
            return None
        downloading_files_downloaded_chunks[file_hash,chunk] = True
        downloading_files_downloaded_chunks_lock.release()
        if address in node_ratings:
            print("Received chunk " + str(chunk) + " from address " + str(address))
        #Removes chunk from file info to declutter it and make it easier to find chunks that are actually needed
        downloading_files_info_lock.acquire()
        file_info.removechunk(chunk)
        downloading_files_info_lock.release()
        #If file doesn't exist, create it and corresponding lock
        if file_hash not in file_locks:
            file_locks_lock.acquire()
            if file_hash not in file_locks:
                file_locks[file_hash] = RLock()
                with open(file_path, 'w') as file:
                    pass
                print("Created file " + file_path)
            file_locks_lock.release()
        
        #Write chunk data to the file
        lock = file_locks[file_hash]
        
        lock.acquire()
        with os.fdopen(os.open(file_path, os.O_WRONLY | os.O_CREAT, 0o666), 'r+b') as file:
            file.seek(chunk * CHUNK_SIZE,0)
            file.write(packet_data)
            file.close()
        lock.release()
        return chunk
    #Nof sure if this is needed
    except KeyboardInterrupt:
        return None