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
        self.tick_duration = 1.0 / self.clock_rate
        
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
        
        # Initialize connections to other machines
        self.connections: Dict[int, socket.socket] = {}
        
        # Map ports to machine IDs
        self.port_to_machine_id = {}
        for i, p in enumerate([port] + other_ports):
            self.port_to_machine_id[p] = i + 1
        
        # Setup logging
        self.setup_logging()
        
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
        
        for other_port in self.other_ports:
            if other_port > self.port:  # Only connect to higher ports
                try:
                    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_socket.connect(('localhost', other_port))
                    self.connections[other_port] = client_socket
                    print(f"Machine {self.machine_id} connected to Machine {self.port_to_machine_id[other_port]} (port {other_port})")
                except Exception as e:
                    print(f"Failed to connect to port {other_port}: {e}")

    def accept_connections(self):
        """Accept connections from other virtual machines"""
        while self.running:
            try:
                client_socket, addr = self.socket.accept()
                port = addr[1]
                # Find the actual port this connection is from (not the ephemeral port)
                for other_port in self.other_ports:
                    if other_port < self.port:  # Only accept from lower ports
                        self.connections[other_port] = client_socket
                        print(f"Machine {self.machine_id} accepted connection from Machine {self.port_to_machine_id[other_port]} (port {other_port})")
                        break
                threading.Thread(target=self.handle_incoming_messages, args=(client_socket,)).start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")

    def handle_incoming_messages(self, client_socket: socket.socket):
        """Handle incoming messages from other machines"""
        while self.running:
            try:
                data = client_socket.recv(1024)
                if not data:
                    break
                message = json.loads(data.decode())
                self.message_queue.put(message)
            except Exception as e:
                if self.running:
                    print(f"Error receiving message: {e}")
                break

    def update_logical_clock(self, received_time=None):
        """Update the logical clock"""
        with self.clock_lock:
            if received_time is not None:
                self.logical_clock = max(self.logical_clock, received_time) + 1
            else:
                self.logical_clock += 1
            return self.logical_clock

    def send_message(self, target_ports: List[int]):
        """Send message to specified target machines"""
        message = {
            'sender': self.machine_id,
            'clock': self.logical_clock
        }
        
        for port in target_ports:
            if port in self.connections:
                try:
                    self.connections[port].send(json.dumps(message).encode())
                except Exception as e:
                    print(f"Error sending message to port {port}: {e}")

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

    def run(self):
        """Main run loop for the virtual machine"""
        # Start accepting connections in a separate thread
        threading.Thread(target=self.accept_connections).start()
        
        # Connect to other machines
        self.connect_to_others()
        
        # Main processing loop
        while self.running:
            self.process_cycle()
            # Sleep according to clock rate
            time.sleep(self.tick_duration)

    def stop(self):
        """Stop the virtual machine"""
        self.running = False
        self.socket.close()
        for conn in self.connections.values():
            conn.close()
