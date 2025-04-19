import hashlib
from math import ceil
from pathlib import Path
from os import path

from utils.tracker_protocol import *
from utils.file_info import *
from node.node_data_structs import *
from node.file_download_handler import *
from node.node_ratings import *


#Espera uma mensagem de OK do servidor e fecha a conexão
def receive_control_msg(tracker_socket):
    
    msg_type, _ = receive_tracker_packet(tracker_socket)
    
    #checks if the server responded with OK (get error messages in the future if needed)
    if(msg_type == OKAY): 
        print('Received OK from server')  # show in terminal
    else:
        print("Unknown issue happened!")

# Asks the tracker to be registered in it
def node_register(tracker_socket,tracker_socket_lock):
        
    #Create register packet to send
    register_packet = Register_Node_Packet()
    #Create tracker packet that contains the register info, then serializes it
    packet = create_tracker_packet(REGISTER_NODE,register_packet.serialize())
    tracker_socket_lock.acquire()
    #Sends the serialzied packet to the server and gets OK
    send_tracker_packets(tracker_socket,packet)
    receive_control_msg(tracker_socket)
    tracker_socket_lock.release()
    
    
    
def unregister_node(tracker_socket,tracker_socket_lock):
    
    unregister_packet = Unregister_Node_Packet()
    packet = create_tracker_packet(DELETE_NODE,unregister_packet.serialize())
    tracker_socket_lock.acquire()
    send_tracker_packets(tracker_socket,packet)
    receive_control_msg(tracker_socket)
    tracker_socket_lock.release()
    
    
    
def node_add_files(filenames: [], tracker_socket,tracker_socket_lock):
    host_name = socket.gethostname()
    #remove the ADD command from the string array
    filenames.pop(0)
    
    fileinfos = {}
    
    #array de pares filname,hash
    filehashes = []
    
    #Percorre todos os ficheiros que quer adicionar, cria os seua metadados e coloca-os no fileinfos
    for filename in filenames:
            #descobre a hash do ficheiro com algoritmo sha256
            if path.exists(host_name + '/' + filename) == False:
                print(filename + " doesn't exist!")
                continue
            with open(host_name + '/' + filename,'rb') as f:
                digest = hashlib.file_digest(f,FILE_HASHING_PROTOCOL)
            hash = digest.hexdigest()
            f.close()
            
            #Descobre o tamanho do ficheiro (no futuro altear o tamanho do ficheiro em bytes por numero de chunks)
            file = Path('./' + host_name + '/' + filename)
            size_bytes: int = file.stat().st_size
            size_chunks:int = ceil(size_bytes / CHUNK_SIZE)
            #Cria conteudo para colocar no fileinfos
            #para já apenas funciona para ficheiros completos, logo o array está sempre vazio
            content: Add_File_PacketContent = Add_File_PacketContent(filename,size_chunks,[]) 

            fileinfos[hash] = content
            
            filehashes.append((filename,hash))
            
            #Create lock for that file
            file_locks_lock.acquire()
            file_locks[hash] = RLock()
            file_locks_lock.release()
            
            
            own_files_hash_to_name[hash] = filename
                
    #Created the packet with file info
    add_file_packet = Add_File_Packet(fileinfos)
    packet = create_tracker_packet(ADD_FILES,add_file_packet.serialize())
    tracker_socket_lock.acquire()
    #Sends the serialized packet to the server
    send_tracker_packets(tracker_socket,packet)
    receive_control_msg(tracker_socket)
    tracker_socket_lock.release()
    
    for (name,hash) in filehashes:
        print("File " + name + " has been added under the hash " + hash)


    
def node_remove_files(filenames: [],tracker_socket,tracker_socket_lock):
    #remove the "remove" part of the command
    filenames.pop(0)
    filehashes = []
    
    for filename in filenames:
        #calculate file hashes for those filenames
        with open(filename,'rb') as f:
            digest = hashlib.file_digest(f,FILE_HASHING_PROTOCOL)
        hash = digest.hexdigest()
        f.close
        filehashes.append(hash)
        
    #message is created with the filehashes and sent to tracker
    serialized_remove_file_packet = Remove_File_Packet(filehashes).serialize()
    packet = create_tracker_packet(REMOVE_FILE,serialized_remove_file_packet)
    tracker_socket_lock.acquire()
    send_tracker_packets(tracker_socket,packet)
    receive_control_msg(tracker_socket)
    tracker_socket_lock.release()


# View the list of files in the network
def node_list_files(tracker_socket,tracker_socket_lock):
    
    #Create tracker packet that contains the register info, then serializes it
    packet = create_tracker_packet(LIST_FILES,None)
    tracker_socket_lock.acquire()
    send_tracker_packets(tracker_socket,packet)
    
    # Receives response from tracker
    msg_type, data  = receive_tracker_packet(tracker_socket)
    tracker_socket_lock.release()
    print("packet received!")
    if msg_type != LIST_FILES:
        print("Server responded differently than expected!")
        return
    
    file_info_packet = List_Files_Packet.deserialize(data)
    print(file_info_packet.list_files)
            
        
#Asks the tracker what nodes have this particular file
def node_download(file_hash, tracker_socket, download_manager_executor, request_chunk_executor,tracker_socket_lock):
    file_request_packet = File_Request_Packet(file_hash).serialize()
    packet = create_tracker_packet(REQUEST_FILE,file_request_packet)
    tracker_socket_lock.acquire()
    send_tracker_packets(tracker_socket,packet)
    time.sleep(0.1) #DO NOT REMOVE, removing this may cause crashes
    msg_type, data = receive_tracker_packet(tracker_socket)
    tracker_socket_lock.release()
    
    #checks if the server responded with OK (get error messages in the future if needed)
    if(msg_type == FILE_NOT_FOUND):
        print("File not found in the tracker's database")
        return None
    if(msg_type != REQUEST_FILE_RESPONSE):
        print("Something went wrong, server didn't reply correctly!")
        return None
    
    #deserializa a informação recebida 
    file_info_packet = File_Request_Response_Packet.deserialize(data)
    file_info : FileInfo = file_info_packet.nodeinfo
    node_ratings_lock.acquire()
    file_info.sortNodesByRating(node_ratings)
    node_ratings_lock.release()
    #Adds the info to the downloading info
    downloading_files_info_lock.acquire()
    downloading_files_info[file_hash] = file_info
    downloading_files_info_lock.release()
    
    print("Received node information for file " + file_hash + ":")
    print("File Name: " + file_info.name)
    print("File size: " + str(file_info.size))
    
    #Assign a thread to handle the download of the file
    download_manager_executor.submit(handle_file_download,request_chunk_executor,file_hash,file_info.size,file_info.name,tracker_socket,tracker_socket_lock)
    
    
    
    