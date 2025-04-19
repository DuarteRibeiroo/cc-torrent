import pickle
import socket
import hashlib

#Using ethernet packet size as a reference size
MAX_PACKET_SIZE = 64000
#Header:
    #16 bytes - chunk hash
    #2 bytes - message length
    #40 bytes - file hash length
    #2 bytes - file chunk number
PROTOCOL_HEADER_SIZE = 60

CHUNK_HASH_FUNC = 'md5'
CHUNK_HASH_SIZE = 16

CHUNK_SIZE = MAX_PACKET_SIZE - PROTOCOL_HEADER_SIZE

#Receives an incoming UDP packet, returns None if the hash doesn't match up with the contents
def receive_transfer_packet(socket: socket):
    
    try:
        bytes_buffer = bytearray(MAX_PACKET_SIZE)
        bytes_received, address = socket.recvfrom_into(bytes_buffer, MAX_PACKET_SIZE)
        
    except TimeoutError:
        return None
    
    chunk_hash = bytearray(CHUNK_HASH_SIZE)
    chunk_hash = bytes_buffer[:16]
    bytes_buffer = bytes_buffer[16:]
    
    msg_length_bytes = bytes_buffer[:2]
    bytes_buffer = bytes_buffer[2:]
    msg_length = int.from_bytes(msg_length_bytes,'little')

    file_hash_bytes = bytes_buffer[:40]
    bytes_buffer = bytes_buffer[40:]
    file_hash = file_hash_bytes.decode()
    
    chunk_bytes = bytes_buffer[:2]
    bytes_buffer = bytes_buffer[2:]
    chunk = int.from_bytes(chunk_bytes,'little')
    
    data = bytes_buffer[:msg_length]
    
    h = hashlib.new(CHUNK_HASH_FUNC)
    h.update(msg_length_bytes + file_hash_bytes + chunk_bytes + data)
    obtained_chunk_hash = h.digest()
    
    if obtained_chunk_hash != chunk_hash:
        print("Received wrong packet!")
        return None
    
    return address, file_hash,chunk, data
    
    

#creates a packet with the given parameters (data length is NOT verified, methods that implement it should make sure the data fits in a single packet)
def create_transfer_packet(file_hash :str,chunk : int, data:bytes = None):
    #The size is determined and converted to bytes
    if data == None:  
        size = 0
    else:
        size = len(data)
    size_bytes = size.to_bytes(2,'little')
    file_hash_bytes = file_hash.encode()
    chunk_bytes = chunk.to_bytes(2,'little')
    if data:
        packet = size_bytes + file_hash_bytes + chunk_bytes + data
    else: 
        packet = size_bytes + file_hash_bytes + chunk_bytes
    #Determine chunk hash
    h = hashlib.new(CHUNK_HASH_FUNC)
    h.update(packet)
    chunk_hash_bytes = h.digest()
    
    #The packet is assembled and returned
    return chunk_hash_bytes + packet

    