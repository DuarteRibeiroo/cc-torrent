import socket
import subprocess
import sys
import threading

from tracker import fs_tracker
from node import fs_node
import utils 



if __name__ == '__main__':  

    arg = sys.argv[1]  # --> -n ou -t

    if(arg == "-t"):        # --> python3.12 fs_main.py -t 
        fs_tracker.main()

    if(arg == "-n"):        # --> python3.12 fs_main.py -n <ip_server>
        ip_server = sys.argv[2]
        fs_node.main(ip_server)
    