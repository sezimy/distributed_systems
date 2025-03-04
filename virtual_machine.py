import socket
import threading
import queue
import random
import time
import json
import logging
from datetime import datetime
from typing import List, Dict

class VirtualMachine:
    def __init__(self, machine_id: int, port: int, other_ports: List[int]):
        self.machine_id = machine_id
        self.port = port
        self.other_ports = other_ports
        
        # Initialize clock rate (1-6 ticks per second)
        self.clock_rate = random.randint(1, 6)
        self.last_tick_time = time.time()
        self.instruction_counter = 0
        
        # Initialize logical clock
        self.logical_clock = 0
        self.clock_lock = threading.Lock()
        
        # Initialize message queue
        self.message_queue = queue.Queue()
        
        # Initialize socket with proper cleanup
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('localhost', self.port))
        self.socket.listen(5)
        
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
        
    def setup_logging(self):
        """Setup logging configuration for the virtual machine"""
        log_filename = f'machine_{self.machine_id}.log'
        # Create a logger specific to this machine
        self.logger = logging.getLogger(f'machine_{self.machine_id}')
        self.logger.setLevel(logging.INFO)
        
        # Create file handler
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('System Time: %(asctime)s - Event: %(message)s')
        file_handler.setFormatter(formatter)
        
        # Clear any existing handlers and add our file handler
        self.logger.handlers = []
        self.logger.addHandler(file_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False

    def connect_to_others(self):
        """Establish connections with other virtual machines"""
        # Wait a bit to ensure all machines are listening
        time.sleep(1)
        
        # Only initiate connections to machines with higher port numbers
        for other_port in self.other_ports:
            if other_port > self.port:
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect(('localhost', other_port))
                    # Send our identification with a newline separator
                    client_socket.sendall(f"CONNECT {self.port}\n".encode())
                    self.connections[other_port] = client_socket
                    connecting_machine_id = self.port_to_machine_id[other_port]
                    self.logger.info(f"Machine {self.machine_id} established connection with Machine {connecting_machine_id}")
                    print(f"Machine {self.machine_id} established connection with Machine {connecting_machine_id}")
                    # Start message handling thread for this connection
                    threading.Thread(target=self.handle_incoming_messages, args=(client_socket,)).start()
                except Exception as e:
                    print(f"Failed to connect to port {other_port}: {e}")

    def accept_connections(self):
        """Accept connections from other virtual machines"""
        self.socket.listen(5)
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                threading.Thread(target=self.handle_connection, args=(client_socket,)).start()
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
                    threading.Thread(target=self.handle_incoming_messages, args=(client_socket,)).start()
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
            # Update logical clock based on received message
            self.update_logical_clock(message['clock'])
            # Log the receive event
            self.logger.info(
                f"Machine {self.machine_id} RECEIVED message - Queue Length: {self.message_queue.qsize()} - Logical Clock: {self.logical_clock}"
            )
        except queue.Empty:
            # No message in queue, generate random event
            action = random.randint(1, 10)
            if 1 <= action <= 3:
                # Send message cases
                target_ports = []
                if action == 1:
                    target_ports = [self.other_ports[0]]
                elif action == 2:
                    target_ports = [self.other_ports[1]]
                elif action == 3:
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
        threading.Thread(target=self.accept_connections).start()
        
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
