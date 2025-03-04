from virtual_machine import VirtualMachine
import threading
import time
import signal
import sys

def cleanup_ports():
    """Cleanup any processes using our ports"""
    import subprocess
    ports = [5001, 5002, 5003]
    for port in ports:
        try:
            subprocess.run(f"lsof -ti :{port} | xargs kill -9", shell=True)
        except:
            pass

def main():
    # Cleanup any existing processes
    cleanup_ports()
    
    # Define ports for three virtual machines
    ports = [5001, 5002, 5003]
    machines = []
    
    print("Initializing virtual machines...")
    # Create and start virtual machines
    for i in range(3):
        other_ports = [p for p in ports if p != ports[i]]
        vm = VirtualMachine(i + 1, ports[i], other_ports)
        machines.append(vm)
        
    print("\nEstablishing connections between machines...")
    # Start each machine in a separate thread with a small delay
    threads = []
    for machine in machines:
        thread = threading.Thread(target=machine.run)
        thread.start()
        threads.append(thread)
        time.sleep(1)  # Increased delay to ensure proper connection establishment
        
    print("\nAll machines initialized and connected. Starting normal operation...")
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down virtual machines...")
        for machine in machines:
            machine.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
