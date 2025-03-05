"""
Script to run a network of virtual machines using multiprocessing.
Each virtual machine runs in its own process, with threads handling connections.
"""

import time
import signal
import sys
import argparse
import os
from virtual_machine import create_virtual_machine_network
from env_config import get_num_machines, print_all_env_vars

def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully exit the program"""
    print("\nShutting down virtual machine network...")
    sys.exit(0)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Run a network of virtual machines')
    parser.add_argument('--num-machines', type=int, help='Number of virtual machines to create (overrides VM_NUM_MACHINES env var)')
    parser.add_argument('--base-port', type=int, help='Base port number for VMs (overrides VM_BASE_PORT env var)')
    parser.add_argument('--show-config', action='store_true', help='Show current configuration from environment variables')
    return parser.parse_args()

def set_env_var(name, value):
    """Set an environment variable if value is not None"""
    if value is not None:
        os.environ[name] = str(value)

if __name__ == "__main__":
    # Parse command line arguments
    args = parse_arguments()
    
    # Set environment variables from command line arguments
    set_env_var('VM_NUM_MACHINES', args.num_machines)
    set_env_var('VM_BASE_PORT', args.base_port)
    
    # Show configuration if requested
    if args.show_config:
        print_all_env_vars()
        sys.exit(0)
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Number of virtual machines to create
    num_machines = get_num_machines()
    
    print(f"Starting a network of {num_machines} virtual machines...")
    print("Press Ctrl+C to stop the network")
    
    # Create and start the virtual machine network
    processes = create_virtual_machine_network()
    
    # Keep the main process running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down virtual machine network...")
