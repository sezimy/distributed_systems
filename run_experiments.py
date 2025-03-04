import subprocess
import time
import re
from datetime import datetime
import statistics
import json
from collections import defaultdict

def run_single_experiment(duration=60, experiment_id=1):
    """Run a single experiment for specified duration"""
    print(f"\nStarting Experiment #{experiment_id} (Duration: {duration}s)")
    
    # Start the system
    process = subprocess.Popen(['python', 'main.py'], 
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    
    # Let it run for specified duration
    time.sleep(duration)
    
    # Terminate the process
    process.terminate()
    process.wait()
    
    print(f"Experiment #{experiment_id} completed")
    return analyze_logs(experiment_id)

def analyze_logs(experiment_id):
    """Analyze logs from all machines for patterns and statistics"""
    results = {
        'experiment_id': experiment_id,
        'machines': {},
        'global_stats': {}
    }
    
    # Analyze each machine's logs
    for machine_id in [1, 2, 3]:
        machine_stats = analyze_machine_log(machine_id)
        results['machines'][machine_id] = machine_stats
    
    # Calculate global statistics
    all_drifts = []
    all_queue_lengths = []
    for machine_stats in results['machines'].values():
        all_drifts.extend(machine_stats['drifts'])
        all_queue_lengths.extend(machine_stats['queue_lengths'])
    
    results['global_stats'] = {
        'max_drift': max(all_drifts) if all_drifts else 0,
        'avg_drift': statistics.mean(all_drifts) if all_drifts else 0,
        'max_queue': max(all_queue_lengths) if all_queue_lengths else 0,
        'avg_queue': statistics.mean(all_queue_lengths) if all_queue_lengths else 0
    }
    
    return results

def analyze_machine_log(machine_id):
    """Analyze log file for a specific machine"""
    stats = {
        'clock_rate': None,
        'drifts': [],
        'queue_lengths': [],
        'messages_received': 0,
        'messages_sent': 0,
        'internal_events': 0,
        'max_logical_clock': 0,
        'drift_by_sender': defaultdict(list)
    }
    
    try:
        with open(f'machine_{machine_id}.log', 'r') as f:
            for line in f:
                # Extract clock rate
                if 'initialized with clock rate' in line:
                    stats['clock_rate'] = int(re.search(r'clock rate: (\d+)', line).group(1))
                
                # Extract queue length
                queue_match = re.search(r'Queue Length: (\d+)', line)
                if queue_match:
                    stats['queue_lengths'].append(int(queue_match.group(1)))
                
                # Extract drift for received messages
                drift_match = re.search(r'Drift: (-?\d+)', line)
                if drift_match:
                    drift = int(drift_match.group(1))
                    stats['drifts'].append(drift)
                    
                    # Extract sender for drift analysis
                    sender_match = re.search(r'from Machine (\d+)', line)
                    if sender_match:
                        sender = int(sender_match.group(1))
                        stats['drift_by_sender'][sender].append(drift)
                
                clock_match = None

                # Count event types and track logical clock for all events
                if 'RECEIVED message' in line:
                    stats['messages_received'] += 1
                    # For received messages, use New Clock
                    clock_match = re.search(r'New Clock: (\d+)', line)
                elif 'SENT message' in line:
                    stats['messages_sent'] += 1
                    # For sent messages, use Logical Clock
                    clock_match = re.search(r'Logical Clock: (\d+)', line)
                elif 'INTERNAL EVENT' in line:
                    stats['internal_events'] += 1
                    # For internal events, use Logical Clock
                    clock_match = re.search(r'Logical Clock: (\d+)', line)
                
            

                # Update maximum logical clock if we found a clock value
                if clock_match:
                    clock_value = int(clock_match.group(1))
                    stats['max_logical_clock'] = max(stats['max_logical_clock'], clock_value)
    
    except FileNotFoundError:
        print(f"Warning: Log file for Machine {machine_id} not found")
    
    # Calculate additional statistics
    if stats['drifts']:
        stats['avg_drift'] = statistics.mean(stats['drifts'])
        stats['max_drift'] = max(stats['drifts'])
        stats['min_drift'] = min(stats['drifts'])
    
    if stats['queue_lengths']:
        stats['avg_queue'] = statistics.mean(stats['queue_lengths'])
        stats['max_queue'] = max(stats['queue_lengths'])
    
    # Calculate drift statistics per sender
    stats['drift_by_sender'] = {
        sender: {
            'avg': statistics.mean(drifts),
            'max': max(drifts),
            'min': min(drifts)
        }
        for sender, drifts in stats['drift_by_sender'].items()
    }
    
    return stats

def print_experiment_results(results):
    """Print detailed analysis of experiment results"""
    print("\n" + "="*50)
    print(f"Experiment #{results['experiment_id']} Analysis")
    print("="*50)
    
    # Global Statistics
    print("\nGlobal Statistics:")
    print(f"Maximum Drift: {results['global_stats']['max_drift']}")
    print(f"Average Drift: {results['global_stats']['avg_drift']:.2f}")
    print(f"Maximum Queue Length: {results['global_stats']['max_queue']}")
    print(f"Average Queue Length: {results['global_stats']['avg_queue']:.2f}")
    
    # Per-Machine Statistics
    for machine_id, stats in results['machines'].items():
        print(f"\nMachine {machine_id} (Clock Rate: {stats['clock_rate']} ticks/sec):")
        print(f"  Messages Sent: {stats['messages_sent']}")
        print(f"  Messages Received: {stats['messages_received']}")
        print(f"  Internal Events: {stats['internal_events']}")
        print(f"  Maximum Logical Clock: {stats['max_logical_clock']}")
        
        if stats['drifts']:
            print(f"  Clock Drift Statistics:")
            print(f"    Average: {stats['avg_drift']:.2f}")
            print(f"    Maximum: {stats['max_drift']}")
            print(f"    Minimum: {stats['min_drift']}")
        
        if stats['drift_by_sender']:
            print(f"  Drift by Sender:")
            for sender, drift_stats in stats['drift_by_sender'].items():
                print(f"    From Machine {sender}:")
                print(f"      Average: {drift_stats['avg']:.2f}")
                print(f"      Maximum: {drift_stats['max']}")
                print(f"      Minimum: {drift_stats['min']}")
        
        if stats['queue_lengths']:
            print(f"  Queue Length Statistics:")
            print(f"    Average: {stats['avg_queue']:.2f}")
            print(f"    Maximum: {stats['max_queue']}")

def run_all_experiments(num_experiments=5, duration=60):
    """Run multiple experiments and analyze trends"""
    all_results = []
    
    for i in range(num_experiments):
        results = run_single_experiment(duration, i+1)
        all_results.append(results)
        print_experiment_results(results)
        
        # Save results to file
        with open(f'experiment_{i+1}_results.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Wait a bit between experiments
        if i < num_experiments - 1:
            print("\nWaiting 5 seconds before next experiment...")
            time.sleep(5)
    
    print("\nAll experiments completed. Results saved to experiment_X_results.json files.")
    return all_results

if __name__ == "__main__":
    run_all_experiments(num_experiments=5, duration=60)
