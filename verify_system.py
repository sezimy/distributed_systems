import re
from collections import defaultdict
import time
from datetime import datetime

def parse_timestamp(timestamp_str):
    """Parse timestamp from log entry"""
    return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')

def verify_clock_rates():
    """Verify that each machine respects its clock rate"""
    for machine_id in [1, 2, 3]:
        print(f"\nChecking clock rate for Machine {machine_id}...")
        events_per_second = defaultdict(int)
        clock_rate = None
        
        try:
            with open(f'machine_{machine_id}.log', 'r') as f:
                for line in f:
                    if 'initialized with clock rate' in line:
                        clock_rate = int(re.search(r'clock rate: (\d+)', line).group(1))
                        print(f"Machine {machine_id} clock rate: {clock_rate} ticks/second")
                        continue
                    
                    # Parse timestamp for events
                    match = re.search(r'System Time: ([\d-]+ [\d:,]+)', line)
                    if match and ('SENT message' in line or 'RECEIVED message' in line or 'INTERNAL EVENT' in line):
                        timestamp = parse_timestamp(match.group(1))
                        second_key = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                        events_per_second[second_key] += 1
            
            if clock_rate is None:
                print(f"WARNING: Could not find clock rate for Machine {machine_id}")
                continue
                
            # Check if any second exceeds the clock rate
            violations = 0
            for second, count in events_per_second.items():
                if count > clock_rate:
                    print(f"WARNING: At {second}, machine {machine_id} processed {count} events (exceeds rate of {clock_rate})")
                    violations += 1
            
            if violations == 0:
                print(f"✓ Machine {machine_id} respects its clock rate")
            else:
                print(f"✗ Machine {machine_id} has {violations} clock rate violations")
                
        except FileNotFoundError:
            print(f"WARNING: Log file for Machine {machine_id} not found")

def verify_logical_clocks():
    """Verify logical clock properties"""
    for machine_id in [1, 2, 3]:
        print(f"\nChecking logical clocks for Machine {machine_id}...")
        current_clock = 0
        violations = 0
        
        try:
            with open(f'machine_{machine_id}.log', 'r') as f:
                for line in f:
                    # Extract logical clock value
                    clock_match = re.search(r'Logical Clock: (\d+)', line)
                    if clock_match:
                        clock_value = int(clock_match.group(1))
                        
                        # Check if clock always increases
                        if clock_value < current_clock:
                            print(f"WARNING: Logical clock decreased from {current_clock} to {clock_value}")
                            violations += 1
                        current_clock = clock_value
            
            if violations == 0:
                print(f"✓ Machine {machine_id} maintains monotonically increasing logical clock")
            else:
                print(f"✗ Machine {machine_id} has {violations} logical clock violations")
        except FileNotFoundError:
            print(f"WARNING: Log file for Machine {machine_id} not found")

def verify_connections():
    """Verify that all machines are properly connected"""
    expected_connections = {
        1: {2, 3},  # Machine 1 should connect to 2 and 3
        2: {3},     # Machine 2 should connect to 3
        3: set()    # Machine 3 doesn't initiate connections
    }
    
    print("\nChecking connection establishment...")
    for machine_id in [1, 2, 3]:
        established = set()
        accepted = set()
        
        try:
            with open(f'machine_{machine_id}.log', 'r') as f:
                for line in f:
                    if 'established connection with Machine' in line:
                        other_machine = int(re.search(r'with Machine (\d+)', line).group(1))
                        established.add(other_machine)
                    elif 'accepted connection from Machine' in line:
                        other_machine = int(re.search(r'from Machine (\d+)', line).group(1))
                        accepted.add(other_machine)
            
            # Verify established connections
            if established == expected_connections[machine_id]:
                print(f"✓ Machine {machine_id} established correct connections: {established}")
            else:
                print(f"✗ Machine {machine_id} has wrong connections. Expected {expected_connections[machine_id]}, got {established}")
            
            # Verify accepted connections
            expected_accepted = {i for i in range(1, machine_id)}
            if accepted == expected_accepted:
                print(f"✓ Machine {machine_id} accepted correct connections: {accepted}")
            else:
                print(f"✗ Machine {machine_id} has wrong accepted connections. Expected {expected_accepted}, got {accepted}")
        except FileNotFoundError:
            print(f"WARNING: Log file for Machine {machine_id} not found")

def verify_message_passing():
    """Verify message passing between machines"""
    print("\nChecking message passing...")
    for machine_id in [1, 2, 3]:
        sent_count = 0
        received_count = 0
        
        try:
            with open(f'machine_{machine_id}.log', 'r') as f:
                for line in f:
                    if 'SENT message' in line:
                        sent_count += 1
                    elif 'RECEIVED message' in line:
                        received_count += 1
            
            print(f"Machine {machine_id}:")
            print(f"  - Sent messages: {sent_count}")
            print(f"  - Received messages: {received_count}")
            if sent_count > 0 and received_count > 0:
                print(f"✓ Machine {machine_id} is actively participating in message passing")
            else:
                print(f"✗ Machine {machine_id} might not be properly sending/receiving messages")
        except FileNotFoundError:
            print(f"WARNING: Log file for Machine {machine_id} not found")

def main():
    print("Starting system verification...\n")
    print("=" * 50)
    verify_clock_rates()
    print("\n" + "=" * 50)
    verify_logical_clocks()
    print("\n" + "=" * 50)
    verify_connections()
    print("\n" + "=" * 50)
    verify_message_passing()

if __name__ == "__main__":
    main()
