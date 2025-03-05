import socket
import threading
import multiprocessing as mp
import queue
import random
import time
import json
import logging
import os
from datetime import datetime
from typing import List, Dict

# Import the environment variable configuration
from env_config import (
    get_num_machines, get_base_port, get_host,
    get_clock_rate_range, get_max_retries, get_retry_delay,
    get_startup_base_delay, get_startup_per_machine_factor, get_event_ranges, 
    get_log_directory, get_log_level, get_log_format
)

class VirtualMachine:
    def __init__(self, machine_id: int, port: int, other_ports: List[int]):
        self.machine_id = machine_id
        self.port = port
        self.other_ports = other_ports
        self.host = get_host()
        
        # Initialize clock rate based on configured range
        min_rate, max_rate = get_clock_rate_range()
        self.clock_rate = random.randint(min_rate, max_rate)
        self.last_tick_time = time.time()
        self.instruction_counter = 0
        
        # Initialize logical clock
        self.logical_clock = 0
        self.clock_lock = threading.Lock()
        
        # Initialize message queue
        self.message_queue = queue.Queue()
        
        # Initialize socket with proper cleanup and reuse options
        self._initialize_socket()
        
        # Initialize connections
        self.connections: Dict[int, socket.socket] = {}
        
        # Create port to machine ID mapping for all machines including self
        self.port_to_machine_id = {}
        all_ports = [self.port] + self.other_ports
        all_ports.sort()  # Sort ports to ensure consistent machine IDs
        for i, p in enumerate(all_ports):
            self.port_to_machine_id[p] = i + 1
        
        # Setup logging
        self.setup_logging()
        
        # Log initialization
        print(f"Machine {self.machine_id} initialized with clock rate: {self.clock_rate} ticks/second")
        self.logger.info(f"Machine {self.machine_id} initialized with clock rate: {self.clock_rate} ticks/second")
        
        # Flags for control
        self.running = True
    
    def _initialize_socket(self, max_retries=None, retry_delay=None):
        """Initialize socket with proper cleanup and reuse options, with retry mechanism"""
        max_retries = max_retries or get_max_retries()
        retry_delay = retry_delay or get_retry_delay()
        
        for attempt in range(max_retries):
            try:
                # Create a new socket
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                
                # Set socket options for address reuse
                self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if hasattr(socket, 'SO_REUSEPORT'):  # Not available on all platforms
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                
                # Set a timeout for operations to avoid hanging
                self.socket.settimeout(10)
                
                # Try to bind to the port
                self.socket.bind((self.host, self.port))
                self.socket.listen(5)
                
                # Reset timeout to blocking mode for normal operation
                self.socket.settimeout(None)
                
                # If we get here, binding was successful
                return
            except OSError as e:
                if e.errno == 48:  # Address already in use
                    if attempt < max_retries - 1:
                        print(f"Port {self.port} is in use, waiting {retry_delay}s before retry {attempt+1}/{max_retries}...")
                        time.sleep(retry_delay)
                        
                        # Try to kill any process using this port (Unix only)
                        if os.name == 'posix':
                            try:
                                os.system(f"lsof -ti :{self.port} | xargs kill -9")
                                time.sleep(retry_delay)  # Wait for the process to be killed
                            except:
                                pass
                    else:
                        raise RuntimeError(f"Failed to bind to port {self.port} after {max_retries} attempts: {e}")
                else:
                    # For other socket errors, raise immediately
                    raise
        
    def setup_logging(self):
        """Setup logging configuration for the virtual machine"""
        log_dir = get_log_directory()
        os.makedirs(log_dir, exist_ok=True)
        log_filename = os.path.join(log_dir, f'machine_{self.machine_id}.log')
        
        # Create a logger specific to this machine
        self.logger = logging.getLogger(f'machine_{self.machine_id}')
        self.logger.setLevel(get_log_level())
        
        # Create file handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(get_log_level())
        
        # Create formatter
        formatter = logging.Formatter(get_log_format())
        file_handler.setFormatter(formatter)
        
        # Clear any existing handlers and add our file handler
        self.logger.handlers = []
        self.logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False

    def connect_to_others(self):
        """Establish connections with other virtual machines"""
        # Wait longer to ensure all machines are listening
        # Higher machine IDs wait less time since they start later
        base_delay = get_startup_base_delay()
        per_machine_factor = get_startup_per_machine_factor()
        
        startup_delay = base_delay + (per_machine_factor * self.machine_id)
        print(f"Machine {self.machine_id} waiting {startup_delay:.1f}s before connecting to others...")
        time.sleep(startup_delay)
        
        # Connect to machines with higher port numbers
        for other_port in self.other_ports:
            if other_port > self.port:
                # Try to connect with retries
                max_retries = get_max_retries()
                retry_delay = get_retry_delay()
                connected = False
                
                for attempt in range(max_retries):
                    try:
                        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_socket.settimeout(5)  # Set a timeout for the connection attempt
                        client_socket.connect((self.host, other_port))
                        # Send our identification with a newline separator
                        client_socket.sendall(f"CONNECT {self.port}\n".encode())
                        client_socket.settimeout(None)  # Reset to blocking mode
                        
                        self.connections[other_port] = client_socket
                        other_id = self.port_to_machine_id[other_port]
                        self.logger.info(f"Machine {self.machine_id} connected to Machine {other_id}")
                        print(f"Machine {self.machine_id} connected to Machine {other_id}")
                        connected = True
                        break
                    except Exception as e:
                        if attempt < max_retries - 1:
                            print(f"Connection attempt {attempt+1} to port {other_port} failed: {e}. Retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            # Increase retry delay for exponential backoff
                            retry_delay *= 2
                        else:
                            self.logger.error(f"Failed to connect to port {other_port} after {max_retries} attempts: {e}")
                
                if not connected:
                    print(f"Machine {self.machine_id} failed to connect to port {other_port}")

    def accept_connections(self):
        """Accept connections from other virtual machines"""
        self.socket.listen(5)
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                threading.Thread(target=self.handle_connection, args=(client_socket,), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")

    def handle_connection(self, client_socket: socket.socket):
        """Handle initial connection and setup"""
        try:
            # Receive the connection message
            data = client_socket.recv(1024).decode()
            if data.startswith('CONNECT '):
                connecting_port = int(data.split()[1])
                if connecting_port < self.port:  # Only accept connections from lower port numbers
                    connecting_machine_id = self.port_to_machine_id[connecting_port]
                    self.connections[connecting_port] = client_socket
                    self.logger.info(f"Machine {self.machine_id} accepted connection from Machine {connecting_machine_id}")
                    print(f"Machine {self.machine_id} accepted connection from Machine {connecting_machine_id}")
                    # Start message handling thread
                    threading.Thread(target=self.handle_incoming_messages, args=(client_socket,), daemon=True).start()
        except Exception as e:
            print(f"Error handling connection: {e}")

    def handle_incoming_messages(self, client_socket: socket.socket):
        """Handle incoming messages from other machines"""
        buffer = ""
        while self.running:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    message_str, buffer = buffer.split('\n', 1)
                    if not message_str.startswith('CONNECT'):  # Ignore connection messages
                        try:
                            message = json.loads(message_str)
                            self.message_queue.put(message)
                        except json.JSONDecodeError:
                            pass  # Ignore invalid JSON
            except Exception as e:
                if self.running:
                    print(f"Error receiving message: {e}")
                break

    def send_message(self, target_ports: List[int]):
        """Send message to specified target machines"""
        message = {
            'sender': self.machine_id,
            'clock': self.logical_clock
        }
        message_bytes = json.dumps(message).encode() + b'\n'  # Add newline as message separator
        
        for port in target_ports:
            if port in self.connections:
                try:
                    self.connections[port].sendall(message_bytes)
                except Exception as e:
                    print(f"Error sending message to port {port}: {e}")
                    # Remove broken connection
                    self.connections.pop(port, None)

    def update_logical_clock(self, received_time=None):
        """Update the logical clock"""
        with self.clock_lock:
            if received_time is not None:
                self.logical_clock = max(self.logical_clock, received_time) + 1
            else:
                self.logical_clock += 1
            return self.logical_clock

    def process_cycle(self):
        """Process one clock cycle"""
        # Check if there's a message in the queue
        try:
            message = self.message_queue.get_nowait()
            # Get local clock before update for jump calculation
            local_clock = self.logical_clock
            # Update logical clock based on received message
            self.update_logical_clock(message['clock'])
             # Calculate clock drift
            drift = self.logical_clock - local_clock - 1
            # Log the receive event with clock jump details
            self.logger.info(
                f"Machine {self.machine_id} RECEIVED message from Machine {message['sender']}| Queue Length: {self.message_queue.qsize()} | "
                f"Local Clock: {local_clock}, Sender Clock: {message['clock']}, New Clock: {self.logical_clock} "
                f"(Drift: {drift})"
            )
        except queue.Empty:
            # No message in queue, generate random event
            event_ranges = get_event_ranges()
            internal_range = event_ranges.get('internal', [4, 10])
            send_to_one = event_ranges.get('send_to_one')
            send_to_other = event_ranges.get('send_to_other')
            send_to_both = event_ranges.get('send_to_both')
            
            action = random.randint(1, 10)
            
            if action == send_to_one and len(self.other_ports) > 0:
                # Send to first machine
                target_ports = [sorted(self.other_ports)[0]]
                self.update_logical_clock()
                self.send_message(target_ports)
                target_machines = [self.port_to_machine_id[port] for port in target_ports]
                self.logger.info(
                    f"Machine {self.machine_id} SENT message to machines {target_machines} - Logical Clock: {self.logical_clock}"
                )
            elif action == send_to_other and len(self.other_ports) > 1:
                # Send to second machine
                target_ports = [sorted(self.other_ports)[1]]
                self.update_logical_clock()
                self.send_message(target_ports)
                target_machines = [self.port_to_machine_id[port] for port in target_ports]
                self.logger.info(
                    f"Machine {self.machine_id} SENT message to machines {target_machines} - Logical Clock: {self.logical_clock}"
                )
            elif action == send_to_both and len(self.other_ports) > 0:
                # Send to all machines
                target_ports = self.other_ports
                self.update_logical_clock()
                self.send_message(target_ports)
                target_machines = [self.port_to_machine_id[port] for port in target_ports]
                self.logger.info(
                    f"Machine {self.machine_id} SENT message to machines {target_machines} - Logical Clock: {self.logical_clock}"
                )
            else:
                # Internal event
                self.update_logical_clock()
                self.logger.info(
                    f"Machine {self.machine_id} INTERNAL EVENT - Logical Clock: {self.logical_clock}"
                )

    def can_execute_instruction(self):
        """Check if we can execute another instruction based on our clock rate"""
        current_time = time.time()
        elapsed_time = current_time - self.last_tick_time
        
        # If a second has passed, reset the counter
        if elapsed_time >= 1.0:
            self.instruction_counter = 0
            self.last_tick_time = current_time
        
        # Check if we can execute another instruction
        if self.instruction_counter < self.clock_rate:
            self.instruction_counter += 1
            return True
        return False

    def run(self):
        """Main run loop for the virtual machine"""
        # Start accepting connections in a separate thread
        threading.Thread(target=self.accept_connections, daemon=True).start()
        
        # Connect to other machines
        self.connect_to_others()
        
        # Main processing loop
        while self.running:
            if self.can_execute_instruction():
                self.process_cycle()
            else:
                # If we've hit our instruction limit for this second, sleep briefly
                time.sleep(0.1)

    def stop(self):
        """Stop the virtual machine"""
        self.running = False
        # Close all connections
        for socket in self.connections.values():
            try:
                socket.close()
            except:
                pass
        self.connections.clear()
        # Close listening socket
        try:
            self.socket.close()
        except:
            pass
        
        self.logger.info("Virtual machine stopped")

# Function to run a virtual machine in a separate process
def run_vm_process(machine_id, port, other_ports):
    try:
        # Calculate a startup delay based on machine ID
        # Lower IDs will start listening sooner, higher IDs will wait longer before connecting
        base_delay = get_startup_base_delay()
        startup_delay = base_delay * machine_id
        time.sleep(startup_delay)
        
        vm = VirtualMachine(machine_id, port, other_ports)
        print(f"Starting VM {machine_id} on port {port}")
        vm.run()
    except KeyboardInterrupt:
        print(f"VM {machine_id} received keyboard interrupt, shutting down")
    except Exception as e:
        print(f"Error starting VM {machine_id} on port {port}: {e}")

# Function to create and start multiple virtual machines as separate processes
def create_virtual_machine_network(num_machines=None, base_port=None):
    # Use environment variable values if not specified
    num_machines = num_machines or get_num_machines()
    base_port = base_port or get_base_port()
    
    processes = []
    ports = [base_port + i for i in range(num_machines)]
    
    # Start processes in reverse order (highest machine_id first)
    for i in reversed(range(num_machines)):
        machine_id = i + 1
        port = ports[i]
        other_ports = [p for p in ports if p != port]
        
        process = mp.Process(
            target=run_vm_process,
            args=(machine_id, port, other_ports)
        )
        process.start()
        processes.append(process)
    
    return processes
