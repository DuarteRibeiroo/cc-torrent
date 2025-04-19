from threading import RLock

#key:address do node
#value: float de rating
node_ratings = {}
node_ratings_lock = RLock()

def update_rating(address,time:float ,sucessful: bool):
    if sucessful:
        #No penalty if sucessfully received
        penalty_factor = 1
    else:
        #If not received, penalize
        penalty_factor = 3
        
    node_ratings_lock.acquire()
    #Create entry equal to std rating if node didn't exist yet
    if address not in node_ratings:
        node_ratings[address] = node_ratings['0']
        
    #Update node and general ratings
    node_ratings[address] = (node_ratings[address] * 0.8) + (time * 0.2 * penalty_factor)
    node_ratings['0'] = (node_ratings['0'] * 0.95) + (time * 0.05 * penalty_factor)
    
    node_ratings_lock.release()

