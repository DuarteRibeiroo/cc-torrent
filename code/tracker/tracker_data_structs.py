import threading

# map que contem os ficheiros para cada nodo da rede:
# key : hash do ficheiro
# value : class fileinfo que tem:
            #nome do ficheiro
            #filesize
            #array with pair:
                #chunk number - int
                #array of addresses that have that chunk
ficheiros_na_rede = {}
ficheiros_na_rede_lock = threading.RLock()

#array com nodos registados
nodos_registados = []
nodos_registados_lock = threading.RLock()