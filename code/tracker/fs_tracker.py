import socket
import threading

from tracker.tracker_packet_handling import *

# Configurações do servidor
HOST = '0.0.0.0'
PORT = 12345       # Porta para escutar
ADDR = (HOST, PORT)


def handle_packet(message_type: int, data: bytes, address):

    if message_type == REGISTER_NODE:
        return handle_register_node(data,address)
    
    elif message_type == ADD_FILES:
        return handle_add_files(data,address)
    
    elif message_type == REQUEST_FILE:
        return handle_request_file(data,address)
        
    elif message_type == DELETE_NODE:
        packets = []
        packets.append(OK_PACKET)
        return packets, False

    elif message_type == LIST_FILES:
        return handle_list_files(data,address)
    
    elif message_type == REMOVE_FILE:
        return handle_remove_file(data,address)
    
    elif message_type == UPDATE_FILE:
        return handle_file_update(data,address)


def handle_conn(conn, address):

    try:
        print("Connection from: " + str(address))

        while True:
            #Receives packet from Node
            msg_type, data = receive_tracker_packet(conn)
            # Handle the packet depending on its type, returns message in bytes to send to node
            result, connected = handle_packet(msg_type,data, address)
            # Sends the response to the node
            send_tracker_packets(conn,result)
            # Check for a specific condition to terminate the connection
            if not connected:
                break

    except Exception as e:
        print(f"An error occurred while handling the connection from {address}: {e}")
    finally:
        handle_delete_node(address)
        conn.shutdown(socket.SHUT_RDWR)
        conn.close()
        
        

def tracker_program():
    
    # get the hostname
    #host = socket.gethostname()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # get instance
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    # look closely. The bind() function takes tuple as argument
    server_socket.bind(ADDR)  # bind host address and port together

    # configure how many client the server can listen simultaneously
    server_socket.listen()
    
    try:
        while True:
            conn, address = server_socket.accept()  # accept new connection
            thread = threading.Thread(target=handle_conn, args=(conn, address))
            thread.start()
            print(f"Active connections: {threading.active_count()-1}")

    except KeyboardInterrupt:
        server_socket.shutdown(socket.SHUT_RDWR)
        server_socket.close()
        print("Interrupted by the user. Closing the server.")
        

            
#if __name__ == '__main__':
def main():
    print("Tracker starting...")
    print("Listening on " + str(ADDR))
    tracker_program()