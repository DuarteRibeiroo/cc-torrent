from tracker.tracker_data_structs import *
from utils.tracker_protocol import *
from utils.file_info import *


# Control info packets are always the same, so it's a constant to avoid repeating its creation
OK_PACKET = b'\x02\x00\x00\x00'
FILE_NOT_FOUND_PACKET = b'\x03\x00\x00\x00'



def handle_register_node(data,address):
    #adds this node to the registered nodes
    nodos_registados_lock.acquire()
    nodos_registados.append((address[0]))
    nodos_registados_lock.release()
    print("Node with address " + str(address) + " registered in database!")
    packets = []
    packets.append(OK_PACKET)
    return packets, True



def handle_add_files(data,address):
    #deserealizes the packet into the add file packet format
    file_packet: Add_File_Packet = Add_File_Packet.deserialize(data)
    
    #adds each file and corresponding packets to the tracker database
    ficheiros_na_rede_lock.acquire()
    for file_hash,content in file_packet.getFiles().items():
        #se esse ficheiro ainda nao estiver registado na base de dados cria um registo
        if file_hash not in ficheiros_na_rede:
            fileinfo = FileInfo(content.name,content.size,5,[])
            ficheiros_na_rede[file_hash] = fileinfo
        fileinfo = ficheiros_na_rede[file_hash]
        #adiciona a informaçao dos chunks que esse node tem
        fileinfo.addNode(address[0], content.chunks)
        print("Node with address " + str(address) + " registered file " + content.name + " in database! ")
    ficheiros_na_rede_lock.release()
    packets = []
    packets.append(OK_PACKET)
    return packets, True

def handle_file_update(data,address):
    update_packet : Update_File_Packet = Update_File_Packet.deserialize(data)
    
    ficheiros_na_rede_lock.acquire()
    fileinfo = ficheiros_na_rede[update_packet.filehash]
    fileinfo.addNode(address[0],update_packet.chunks_added)
    ficheiros_na_rede_lock.release()
    
    if update_packet.need_response == True:
        response_packet = File_Request_Response_Packet(fileinfo)
        response_packet_serialized = response_packet.serialize()
        packet = create_tracker_packet(REQUEST_FILE_RESPONSE,response_packet_serialized)
    else:
        packet = []
        packet.append(OK_PACKET)
    
    return packet, True


def handle_request_file(data,address):
    #the message is deserialized
    request_packet = File_Request_Packet.deserialize(data)
    #the node info and size of that file is searched in the database of the tracker
    file_hash = request_packet.getHash()
    ficheiros_na_rede_lock.acquire()
    if file_hash not in ficheiros_na_rede:
        ficheiros_na_rede_lock.release()
        packets = []
        packets.append(FILE_NOT_FOUND_PACKET)
        return packets, True
    node_info: FileInfo = ficheiros_na_rede[file_hash]
    # A response packet is generated with the gathered info and serialized
    filename = node_info.name
    response_packet = File_Request_Response_Packet(node_info)
    response_packet_serialized = response_packet.serialize()
    ficheiros_na_rede_lock.release()
    
    #The packet that contains that response packet is created, serialized then returned to main
    packet = create_tracker_packet(REQUEST_FILE_RESPONSE,response_packet_serialized)
    
    print("Node with address " + str(address) + " requested file " + filename)
    return packet, True



def handle_delete_node(address):
    #Procura por registos desse node em todos os ficheiros
    ficheiros_na_rede_lock.acquire()
    hashes_to_del = []
    for file_hash in ficheiros_na_rede:
        
        #procura os nodos que possuem esse ficheiro
        fileinfo: FileInfo = ficheiros_na_rede[file_hash]
        no_nodes_with_file = fileinfo.removeNode(address[0])
        
        if no_nodes_with_file:
            hashes_to_del.append(file_hash)
    for hash_to_del in hashes_to_del:
        del ficheiros_na_rede[hash_to_del]
    ficheiros_na_rede_lock.release()
    
    #remove esse nodo da lista de nodos registados
    nodos_registados_lock.acquire()
    nodos_registados.remove(address[0])
    nodos_registados_lock.release()
    print("Node with address " + str(address) + " unregistered! :(")



def handle_list_files(data,address):
    # vai ao dicionário de ficheiros e escreve uma lista
        lista_string = ""
        
        ficheiros_na_rede_lock.acquire()
        for hash in ficheiros_na_rede:
            # para cada ficheiro adiciona à string de lista
            fileinfo: FileInfo = ficheiros_na_rede[hash]
            nome = fileinfo.name
            tamanho = fileinfo.size
            lista_string += "- Name: " + nome + ", Size: " + str(tamanho) + ", Hash: " + hash + "\n"
        ficheiros_na_rede_lock.release()
        print(lista_string)
        
        # cria um pacote com a resposta
        response_packet = List_Files_Packet(lista_string)
        response_packet_serialized = response_packet.serialize()
        
        #The packet that contains that response packet is created, then returned to main
        #TODO: implement size verification
        packet = create_tracker_packet(LIST_FILES,response_packet_serialized)
        
        print(str(address) + "requested a list of all available files")
        return packet, True
    
    

def handle_remove_file(data,address):
    delete_file_packet = Remove_File_Packet.deserialize(data)
    hashes_to_remove = delete_file_packet.hashes()
    
    ficheiros_na_rede_lock.acquire()
    for hash in hashes_to_remove:
        #if a file under that hash does not exist, give an error and remove none
        if hash not in ficheiros_na_rede:
            packets = []
            packets.append(FILE_NOT_FOUND_PACKET)
            return packets, True
    
    for hash in hashes_to_remove:
        fileinfo: FileInfo = ficheiros_na_rede[hash]
        nodeinfo: {} = fileinfo.getnodeinfo()
        for node in nodeinfo:
            #se o nodo a eliminar tiver esse ficheiro, remover essa entrada da base de dados
            if node == address[0]:
                nodeinfo.pop[node]
                break
            # se o node era o unico com esse ficheiro, eliminar o ficheiro da base de dados
            if not ficheiros_na_rede[hash]:
                ficheiros_na_rede.pop(hash)
    ficheiros_na_rede_lock.release()
    packets = []
    packets.append(OK_PACKET)
    return packets, True