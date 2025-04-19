def sort_chunks_by_rarity(chunkinfo):
    return len(chunkinfo[1])

def sort_nodes_by_rating(address):
    return 

class FileInfo:
    
    def __init__(self,name,size,sort_trigger,nodeinfo):
        #actual name of the file
        self.name = name
        #size of the file
        self.size = size
        #array with pair:
            #chunk number - int
            #array of addresses that have that chunk
        self.nodeinfo:[] = nodeinfo
        #If empty, create the array
        if not nodeinfo:
            for i in range(self.size):
                self.nodeinfo.append((i,[]))
        self.edits_since_sort = 0
        self.sort_trigger = sort_trigger
        
    #adds a node to the dictionary that says which nodes have this file
    def addNode(self,node,chunks:[]):
        for chunk_number,addresses in self.nodeinfo:
            if (not chunks or chunk_number in chunks) and node not in addresses:
                addresses.append(node)
        self.edits_since_sort += 1
        #Re-Sort array by rarity if it has been updated enough times
        if self.edits_since_sort > self.sort_trigger:
            self.nodeinfo.sort(key=sort_chunks_by_rarity)
            self.edits_since_sort = 0
            
    def removeNode(self,node):
        no_nodes_with_file = True
        node_has_chunks_of_file = False
        for chunk_number,addresses in self.nodeinfo:
            if node in addresses:
                node_has_chunks_of_file = True
                addresses.pop(addresses.index(node))
                if len(addresses) != 0:
                    no_nodes_with_file = False
        self.edits_since_sort += 1
        #Re-sort array by rarity if it has been updated enough times
        if self.edits_since_sort > self.sort_trigger:
                self.nodeinfo.sort(key=sort_chunks_by_rarity)
                self.edits_since_sort = 0
        if node_has_chunks_of_file:
            return no_nodes_with_file
        else:
            return False
                
    def removechunk(self,chunk_number):
        for chunk, addressses in self.nodeinfo:
            if chunk == chunk_number:
                self.nodeinfo.remove((chunk_number,addressses))
    
                
    def sortNodesByRating(self,node_ratings):
        for chunk_number,addresses in self.nodeinfo:
            addresses.sort(key = lambda node_address: node_ratings[node_address] if node_address in node_ratings else node_ratings['0'])
            
    def getnodeinfo(self):
        return self.nodeinfo