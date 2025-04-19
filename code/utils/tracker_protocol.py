import pickle

from utils.file_info import *
"""
+----------------+------------------+---------------------------------------------------+
|                |                  |                    |                              |
|  tipo mensagem | tamanho mensagem |  faltam fragmentos | mensagem                     |
|    1 byte      |     2  bytes     |   1 byte           |                              |
+----------------+------------------+---------------------------------------------------+
"""

MAX_TRACKER_MSG_SIZE = 65535
TRACKER_HEADER_SIZE = 4
#definir nomes para os numeros de tipo de mensagem
REGISTER_NODE = 0
DELETE_NODE = 1
#Okay has no data field since it's not needed, the Default None is used so we just create a regular Tracker_packet with type OK
OKAY = 2
#file not found has no data field
FILE_NOT_FOUND = 3


ADD_FILES = 10
REMOVE_FILE = 11
REQUEST_FILE = 12
REQUEST_FILE_RESPONSE = 13
LIST_FILES = 14
REMOVE_FILE = 15
UPDATE_FILE = 16

#definining file hash protocol universally
FILE_HASHING_PROTOCOL = "sha1"


#creates a packet with the given parameters (data length is NOT verified, methods that implement it should make sure the data fits in a single packet)
def create_tracker_packet(type:int, data:bytes):
    packets = []
    if data == None:
        type_bytes = type.to_bytes(1,'little')
        size = 0
        size_bytes = size.to_bytes(2,'little')
        #The packet is assembled and returned
        remaining_fragments = 0
        remaining_fragments_bytes = remaining_fragments.to_bytes(1,'little')
        packet = type_bytes + size_bytes + remaining_fragments_bytes
        packets.append(packet)
        return packets
    
    remaining_data_size = len(data)
    while remaining_data_size > MAX_TRACKER_MSG_SIZE - TRACKER_HEADER_SIZE:
        #The type is converted to bytes
        type_bytes = type.to_bytes(1,'little')
        #The size is determined and converted to bytes
        size = (MAX_TRACKER_MSG_SIZE - TRACKER_HEADER_SIZE)
        size_bytes = size.to_bytes(2,'little')
        #The packet is assembled and returned
        remaining_fragments = 1
        remaining_fragments_bytes = remaining_fragments.to_bytes(1,'little')
        packet = type_bytes + size_bytes + remaining_fragments_bytes + data[:(MAX_TRACKER_MSG_SIZE - TRACKER_HEADER_SIZE)]
        data[(MAX_TRACKER_MSG_SIZE - TRACKER_HEADER_SIZE):]
        remaining_data_size -= (MAX_TRACKER_MSG_SIZE - TRACKER_HEADER_SIZE)
        packets.append(packet)
        
    #The type is converted to bytes
    type_bytes = type.to_bytes(1,'little')
    #The size is determined and converted to bytes
    size = remaining_data_size
    size_bytes = size.to_bytes(2,'little')
    #The packet is assembled and returned
    remaining_fragments = 0
    remaining_fragments_bytes = remaining_fragments.to_bytes(1,'little')
    packet = type_bytes + size_bytes + remaining_fragments_bytes + data
    packets.append(packet)
    return packets
    
def send_tracker_packets(conn,packets):
    for i in range(len(packets)):
        packet = packets[i]
        conn.send(packet)
    
#Correctly receives a packet given a connection
def receive_packet_from_socket(conn):
    conn.setblocking(True)
    #Receive message type byte, just one byte so won't partially receive data
    msg_type_bytes = bytearray(1)
    bytes_received = conn.recv_into(msg_type_bytes,1)
    msg_type = int.from_bytes(msg_type_bytes,'little')
    
    #Receive message length
    msg_length_bytes = bytearray(2)
    bytes_received = conn.recv_into(msg_length_bytes,2) #receive message length
    #if the whole message was not received, loop until it is completely received
    while bytes_received < 2:
        #create temp buffer
        msg_length_bytes_temp = bytearray(2 - bytes_received)
        #receive the rest of the message (hopefully)
        bytes_received += conn.recv_into(msg_length_bytes_temp, 2 - bytes_received)
        #print(bytes_received)
        #append the bytes received to the message length variable
        msg_length_bytes += msg_length_bytes_temp
    #translates the message length from bytes to an int
    msg_length = int.from_bytes(msg_length_bytes,'little')
    
    #Receive message type byte, just one byte so won't partially receive data
    remaining_fragments_bytes = bytearray(1)
    bytes_received = conn.recv_into(remaining_fragments_bytes,1)
    #print(bytes_received)
    remaining_fragments = int.from_bytes(remaining_fragments_bytes,'little')
    
    data_buffer = bytearray(msg_length)
    #If there's something besides the header to receive, receive it
    if msg_length > 0:
        bytes_received = conn.recv_into(data_buffer,msg_length)
        #print(bytes_received)
        #if the whole message was not received, keep waiting for data
        while bytes_received < msg_length:
            #Create temp buffer
            temp_buffer = bytearray(msg_length-bytes_received)
            #Receive missing data to temp buffer and update bytes received variable
            bytes_received += conn.recv_into(temp_buffer, msg_length - bytes_received)
            #print(bytes_received)
            #append the bytes received to the message length variable
            data_buffer += temp_buffer
    return msg_type,remaining_fragments, data_buffer
                    
def receive_tracker_packet(conn):
    msg_type,remaining_fragments,data = receive_packet_from_socket(conn)
    while remaining_fragments:
        msg_type_temp,remaining_fragments,data_buffer = receive_packet_from_socket(conn)
        data.extend(data_buffer)
    return msg_type, data


class Register_Node_Packet:
    
    def __init__(self):
        #para já inutil, no futuro dirá o seu hostname
        self.host_name = "" 
    
    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: Register_Node_Packet = pickle.loads(serialized_packet)
        return packet
    
class Unregister_Node_Packet:
    
    def __init__(self):
        #para já inutil, no futuro dirá o seu hostname
        self.host_name = "" 
    
    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: Unregister_Node_Packet = pickle.loads(serialized_packet)
        return packet
    
class Remove_File_Packet:
    
    #creates a packet to remove files according to their hash 
    def __init__(self,file_hashes):
        #array of hashes of the files that got deleted
        self.file_hashes = file_hashes
        
    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: Remove_File_Packet = pickle.loads(serialized_packet)
        return packet
    
class Add_File_PacketContent:
    
    def __init__(self,name:str ,size : int, chunks : []):
        self.name = name
        self.size = size
        self.chunks = chunks
    
#Dizer ao servidor que tem ficheiros novos
class Add_File_Packet:
    
    def __init__(self,fileinfos: {}):
        #Dicionário de chave hash e valor class Add_FilePacketContent, definido acima
        self.files = fileinfos
    
    def getFiles(self):
        return self.files
            
    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: Add_File_Packet = pickle.loads(serialized_packet)
        return packet
    
class Update_File_Packet:
    
    #creates a packet to remove files according to their hash 
    def __init__(self,filehash,chunks_added,need_response):
        #FIle hash and array with chunks added
        self.filehash = filehash
        self.chunks_added = chunks_added
        self.need_response = need_response
        
    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: Update_File_Packet = pickle.loads(serialized_packet)
        return packet

#Pedido de um cliente ao servidor de um ficheiro novo
class File_Request_Packet:
    
    def __init__(self,hash):
        self.hash = hash

    def getHash(self):
        return self.hash

    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: File_Request_Packet = pickle.loads(serialized_packet)
        return packet        


class File_Request_Response_Packet:
    
    def __init__(self,nodeinfo:FileInfo):
        #do tipo class FileInfo
        self.nodeinfo = nodeinfo
        
    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: File_Request_Response_Packet = pickle.loads(serialized_packet)
        return packet   
    

class Request_List_Packet:
    
    def __init__(self):
        #do tipo class FileInfo
        self.host_name = "" 
        
    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: Request_List_Packet = pickle.loads(serialized_packet)
        return packet   


class List_Files_Packet:
    
    def __init__(self, lista_ficheiros):
        # lista de ficheiros convertido em lista
        self.list_files = lista_ficheiros
    
    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: List_Files_Packet = pickle.loads(serialized_packet)
        return packet
    
class Remove_File_Packet:
    
    def __init__(self, filehashes):
        # lista de ficheiros convertido em lista
        self.hashes = filehashes
    
    def serialize(self):
        #Cria uma variável de bytes e serializa-os
        serialized_packet: bytes  = pickle.dumps(self,pickle.HIGHEST_PROTOCOL)
        return serialized_packet
    
    def deserialize(serialized_packet):
        #deserializa o pacote dados os bytes do mesmo
        packet: Remove_File_Packet = pickle.loads(serialized_packet)
        return packet