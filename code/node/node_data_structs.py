from threading import RLock

# map que contem os ficheiros para cada nodo da rede:
# key : hash do ficheiro
# value : FileInfo
downloading_files_info = {}
downloading_files_info_lock = RLock()

#key:par hash do ficheiro, numero chunk
# value : true -> chunk ja pedido e escrito
        # False -> chunk já pedido mas nao recebido
        #nao existe -> chunk ainda não pedido
downloading_files_downloaded_chunks = {}
downloading_files_downloaded_chunks_lock = RLock()

#key:file hash
#value: file name
own_files_hash_to_name = {}

#key:file hash
#value: Rlock()
file_locks = {}
#Only used to create new locks due to a new file
file_locks_lock = RLock()

print_lock = RLock()


