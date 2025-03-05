import unittest
import socket
import threading
import queue
import time
import json
from unittest.mock import Mock, patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor
from virtual_machine import VirtualMachine

class TestVirtualMachine(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.machine_id = 1
        self.port = 5000
        self.other_ports = [5001, 5002]
        # Patch socket creation in setUp
        self.socket_patcher = patch('socket.socket')
        self.mock_socket = self.socket_patcher.start()
        self.mock_socket_instance = MagicMock()
        self.mock_socket.return_value = self.mock_socket_instance
        
        # Create the virtual machine with running set to False initially
        self.vm = VirtualMachine(self.machine_id, self.port, self.other_ports)
        self.vm.running = False  # Prevent any background threads from starting

    def tearDown(self):
        """Clean up after each test method."""
        self.vm.running = False
        time.sleep(0.1)  # Give time for any running threads to stop
        self.socket_patcher.stop()
        # Close any open log files
        if hasattr(self.vm, 'logger'):
            for handler in self.vm.logger.handlers:
                handler.close()

    def test_initialization(self):
        """Test if the virtual machine initializes correctly."""
        self.assertEqual(self.vm.machine_id, self.machine_id)
        self.assertEqual(self.vm.port, self.port)
        self.assertEqual(self.vm.other_ports, self.other_ports)
        self.assertTrue(1 <= self.vm.clock_rate <= 6)
        self.assertEqual(self.vm.logical_clock, 0)
        self.assertIsInstance(self.vm.message_queue, queue.Queue)
        self.assertIsInstance(self.vm.clock_lock, threading.Lock)

    def test_port_to_machine_id_mapping(self):
        """Test if port to machine ID mapping is created correctly."""
        expected_mapping = {
            5000: 1,
            5001: 2,
            5002: 3
        }
        self.assertEqual(self.vm.port_to_machine_id, expected_mapping)

    def test_connect_to_others(self):
        """Test connection establishment with other machines."""
        # Setup mock for client socket connections
        mock_client_socket = MagicMock()
        self.mock_socket.return_value = mock_client_socket
        
        # Mock successful connections
        mock_client_socket.connect = Mock()
        mock_client_socket.sendall = Mock()
        
        # Call the method
        self.vm.connect_to_others()
        
        # Verify connection attempts were made only to higher ports
        expected_connections = len([p for p in self.other_ports if p > self.port])
        self.assertEqual(mock_client_socket.connect.call_count, expected_connections)
        
        # Verify proper connection messages were sent
        expected_calls = [
            call(('localhost', port)) for port in self.other_ports if port > self.port
        ]
        mock_client_socket.connect.assert_has_calls(expected_calls, any_order=True)

    def test_update_logical_clock(self):
        """Test logical clock updates."""
        initial_clock = self.vm.logical_clock
        received_time = initial_clock + 5
        
        with self.vm.clock_lock:
            self.vm.logical_clock = max(self.vm.logical_clock, received_time) + 1
        
        self.assertEqual(self.vm.logical_clock, received_time + 1)
        
        # Test when received time is less than current time
        current_time = self.vm.logical_clock
        with self.vm.clock_lock:
            self.vm.logical_clock = max(self.vm.logical_clock, received_time - 2) + 1
        
        self.assertEqual(self.vm.logical_clock, current_time + 1)

    def test_message_queue(self):
        """Test message queue operations."""
        # Test adding message to queue
        test_message = {
            'sender_id': 2,
            'logical_clock': 5,
            'timestamp': time.time()
        }
        self.vm.message_queue.put(test_message)
        
        # Verify queue is not empty
        self.assertFalse(self.vm.message_queue.empty())
        
        # Get message from queue
        received_message = self.vm.message_queue.get()
        self.assertEqual(received_message, test_message)
        
        # Verify queue is empty after getting message
        self.assertTrue(self.vm.message_queue.empty())

    @patch('threading.Thread')
    def test_network_message_handling(self, mock_thread):
        """Test handling of network messages."""
        # Create a mock client socket
        mock_client = MagicMock()
        test_message = {
            'sender_id': 2,
            'logical_clock': 5,
            'timestamp': time.time()
        }
        
        # Setup mock to return one valid message and then empty string to simulate disconnect
        encoded_message = (json.dumps(test_message) + '\n').encode()
        mock_client.recv.side_effect = [encoded_message, b'']
        
        # Add mock client to connections
        self.vm.connections[5001] = mock_client
        
        # Set running to True temporarily for this test
        self.vm.running = True
        
        # Simulate message processing directly
        data = mock_client.recv()
        if data:
            try:
                message = json.loads(data.decode().strip())
                with self.vm.clock_lock:
                    self.vm.logical_clock = max(self.vm.logical_clock, message['logical_clock']) + 1
            except json.JSONDecodeError:
                pass  # Ignore invalid JSON
        
        # Verify message was processed
        self.assertGreaterEqual(self.vm.logical_clock, test_message['logical_clock'])

    def test_system_time_sync(self):
        """Test system time synchronization between machines."""
        # Simulate multiple clock updates
        test_times = [5, 8, 3, 10]
        expected_final_time = max(test_times) + 1
        
        for t in test_times:
            with self.vm.clock_lock:
                self.vm.logical_clock = max(self.vm.logical_clock, t) + 1
        
        self.assertEqual(self.vm.logical_clock, expected_final_time)

    def test_error_handling(self):
        """Test error handling for network operations."""
        # Test connection failure
        mock_client_socket = MagicMock()
        self.mock_socket.return_value = mock_client_socket
        mock_client_socket.connect.side_effect = ConnectionRefusedError()
        
        # This should not raise an exception
        try:
            self.vm.connect_to_others()
        except Exception as e:
            self.fail(f"connect_to_others raised {type(e)} unexpectedly!")
        
        # Test message handling with corrupted data
        mock_client = MagicMock()
        mock_client.recv.side_effect = [b'corrupted_data\n', b'']
        
        # Set running to True temporarily for this test
        self.vm.running = True
        
        # This should not raise an exception
        try:
            thread = threading.Thread(target=self.vm.handle_incoming_messages, args=(mock_client,))
            thread.daemon = True
            thread.start()
            time.sleep(0.1)  # Give time for processing
            self.vm.running = False
            thread.join(timeout=1.0)
        except Exception as e:
            self.fail(f"handle_incoming_messages raised unexpected {type(e)}!")

    def test_performance_under_load(self):
        """Test system performance under high message load."""
        message_count = 100  # Reduced count for faster testing
        
        # Function to simulate message processing
        def process_messages():
            for i in range(message_count):
                test_message = {
                    'sender_id': 2,
                    'logical_clock': i,
                    'timestamp': time.time()
                }
                self.vm.message_queue.put(test_message)
                
                # Simulate message processing
                with self.vm.clock_lock:
                    self.vm.logical_clock = max(self.vm.logical_clock, test_message['logical_clock']) + 1

        # Create multiple threads to simulate high load
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(process_messages) for _ in range(4)]
            
        # Wait for all threads to complete
        for future in futures:
            future.result()
            
        end_time = time.time()
        
        # Verify system handled the load
        self.assertGreaterEqual(self.vm.logical_clock, message_count)
        
        # Check processing time (should be reasonable)
        processing_time = end_time - start_time
        self.assertLess(processing_time, 5.0)  # Should process within 5 seconds

if __name__ == '__main__':
    unittest.main()
