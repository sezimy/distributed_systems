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

## Environment Variable Configuration

The system is configured using environment variables, making it easy to adjust parameters without modifying code.

You can print their current values using the following command:
```bash
python run_vm_network.py --show-config
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VM_NUM_MACHINES` | Number of virtual machines to create | 3 |
| `VM_BASE_PORT` | Starting port number (each VM uses base_port + id) | 5000 |
| `VM_HOST` | Host address for socket connections | localhost |
| `VM_MIN_CLOCK_RATE` | Minimum clock rate (ticks per second) | 1 |
| `VM_MAX_CLOCK_RATE` | Maximum clock rate (ticks per second) | 6 |
| `VM_MAX_RETRIES` | Maximum connection retry attempts | 5 |
| `VM_RETRY_DELAY` | Initial delay between retry attempts (seconds) | 1.0 |
| `VM_STARTUP_BASE_DELAY` | Base delay for VM startup (seconds) | 1.0 |
| `VM_STARTUP_PER_MACHINE_FACTOR` | Additional delay factor per machine ID | 0.5 |
| `VM_INTERNAL_EVENT_MIN` | Minimum value for internal event range | 4 |
| `VM_INTERNAL_EVENT_MAX` | Maximum value for internal event range | 10 |
| `VM_SEND_TO_ONE_VALUE` | Event value for sending to first machine | 1 |
| `VM_SEND_TO_OTHER_VALUE` | Event value for sending to second machine | 2 |
| `VM_SEND_TO_BOTH_VALUE` | Event value for sending to all machines | 3 |
| `VM_LOG_DIRECTORY` | Directory for log files | logs |
| `VM_LOG_LEVEL` | Logging level (INFO, DEBUG, etc.) | INFO |
| `VM_LOG_FORMAT` | Format string for log messages | System Time: %(asctime)s - Event: %(message)s |
