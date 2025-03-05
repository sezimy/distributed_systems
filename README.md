# Distributed System Simulation

This implementation simulates a distributed system with multiple virtual machines running at different speeds and using logical clocks for event ordering.

## Implementation Details

### Components

1. **Virtual Machine (VM)**
   - Each VM runs at a random speed (1-6 ticks per second)
   - Maintains a logical clock
   - Has a message queue for incoming messages
   - Connects to other VMs via sockets
   - Logs all events to a machine-specific log file
   - Each VM runs in its own process for true parallelism
   - Uses threads within each process for connection and message handling

2. **Event Types**
   - Internal events (random numbers 4-10)
   - Send to one machine (random number 1)
   - Send to another machine (random number 2)
   - Send to both machines (random number 3)

3. **Logging**
   - Each machine logs to its own file (machine_X.log)
   - Logs include: event type, system time, queue length, and logical clock time

## Running the Simulation

1. No external dependencies are required - uses Python standard library only

2. Run the simulation:
   ```bash
   python run_vm_network.py
   ```

3. The simulation will create three virtual machines that communicate with each other, each running in its own process

4. To stop the simulation, press Ctrl+C (the system handles graceful shutdown)

## Testing and Verification

1. Run unit tests:
   ```bash
   python -m unittest tests/test_virtual_machine.py
   ```

2. Verify system behavior by analyzing logs:
   ```bash
   python tests/verify_system.py
   ```

## Log Files

Each machine creates its own log file (machine_1.log, machine_2.log, machine_3.log) containing:
- Timestamp
- Event type (internal, send, receive)
- Message queue length (for receive events)
- Logical clock value

## Implementation Notes

- Uses TCP sockets for reliable communication
- Implements Lamport's logical clocks
- Each machine runs in its own process (multiprocessing)
- Uses threads within each process for connection and message handling
- Graceful shutdown handling with signal processing
- Random clock rates simulate different processing speeds
- Robust error handling for network issues
