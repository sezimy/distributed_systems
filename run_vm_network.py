"""
Script to run a network of virtual machines using multiprocessing.
Each virtual machine runs in its own process, with threads handling connections.
"""

import time
import signal
import sys
from virtual_machine import create_virtual_machine_network

def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully exit the program"""
    print("\nShutting down virtual machine network...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Number of virtual machines to create
    num_machines = 3
    
    print(f"Starting a network of {num_machines} virtual machines...")
    print("Press Ctrl+C to stop the network")
    
    # Create and start the virtual machine network
    processes = create_virtual_machine_network(num_machines=num_machines)
    
    # Keep the main process running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down virtual machine network...")
