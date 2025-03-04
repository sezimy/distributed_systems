from virtual_machine import VirtualMachine
import threading
import time
import signal
import sys
import random

def cleanup_ports():
    """Cleanup any processes using our ports"""
    import subprocess
    ports = [5001, 5002, 5003]
    for port in ports:
        try:
            subprocess.run(f"lsof -ti :{port} | xargs kill -9", shell=True)
        except:
            pass

def create_virtual_machines(config='default'):
    """Create virtual machines with different configurations"""
    if config == 'small_variation':
        # Smaller clock rate variation (1-3 instead of 1-6)
        clock_rates = [random.randint(1, 3) for _ in range(3)]
    else:
        # Default: larger variation
        clock_rates = [random.randint(1, 6) for _ in range(3)]
        
    ports = [5001, 5002, 5003]
    machines = []
    
    for i in range(3):
        machine = VirtualMachine(
            machine_id=i+1,
            port=ports[i],
            other_ports=[p for p in ports if p != ports[i]],
            clock_rate=clock_rates[i]
        )
        machines.append(machine)
    
    return machines

def main():
    # Cleanup any existing processes
    cleanup_ports()
    
    print("Initializing virtual machines...")
    config = sys.argv[1] if len(sys.argv) > 1 else 'default'
    machines = create_virtual_machines(config)
    
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
