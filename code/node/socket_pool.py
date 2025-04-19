from threading import RLock
import socket

MAX_SENDER_THREADS = 15
MAX_REQUESTING_THREADS = 25
MAX_SIMULTANEOUS_DOWNLOADS = 5
MAX_SIMULTANEOUS_REQUESTS_PER_FILE = 5

#Array com elementos par (Bool(se socket está disponivel),Socket)
socket_pool = []
socket_pool_lock = RLock()

#Find an available socket in socket pool
def find_available_socket():
    finding_socket = True
    while finding_socket:
        socket_pool_lock.acquire()
        for i in range(len(socket_pool)):
            socket_free,sender_socket = socket_pool[i]
            if socket_free == True:
                #Assign the socket to the thread and mark socket as being used
                socket_pool[i] = False,sender_socket
                chosen_socket = sender_socket
                empty_socket(chosen_socket,None)
                finding_socket = False
                break
        socket_pool_lock.release()
    return chosen_socket

#Return socket to socket pool
def free_socket(socket):
    socket_pool_lock.acquire()
    for i in range(len(socket_pool)):
        socket_free,sender_socket = socket_pool[i]
        if sender_socket == socket:
            sender_socket.setblocking(True)
            socket_pool[i] = True, sender_socket
            break
    socket_pool_lock.release()
    
#Empties pending bytes in socket
def empty_socket(socket_to_empty: socket,set_timeout):
    socket_to_empty.setblocking(False)
    try:
        while socket_to_empty.recv(1024): pass
    except:
        pass
    socket_to_empty.settimeout(set_timeout)