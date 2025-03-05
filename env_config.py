"""
Environment variable configuration for the distributed system simulation.
Provides access to configuration values through environment variables with sensible defaults.
"""

import os
import logging

# Network configuration
def get_num_machines():
    """Get the number of virtual machines to create."""
    return int(os.environ.get('VM_NUM_MACHINES', '3'))

def get_base_port():
    """Get the base port number for virtual machines."""
    return int(os.environ.get('VM_BASE_PORT', '5000'))

def get_host():
    """Get the host for virtual machine connections."""
    return os.environ.get('VM_HOST', 'localhost')

# VM configuration
def get_min_clock_rate():
    """Get the minimum clock rate."""
    return int(os.environ.get('VM_MIN_CLOCK_RATE', '1'))

def get_max_clock_rate():
    """Get the maximum clock rate."""
    return int(os.environ.get('VM_MAX_CLOCK_RATE', '6'))

def get_clock_rate_range():
    """Get the range for random clock rates."""
    return (get_min_clock_rate(), get_max_clock_rate())

def get_max_retries():
    """Get the maximum number of connection retries."""
    return int(os.environ.get('VM_MAX_RETRIES', '5'))

def get_retry_delay():
    """Get the delay between connection retries."""
    return float(os.environ.get('VM_RETRY_DELAY', '1.0'))

def get_startup_base_delay():
    """Get the base startup delay."""
    return float(os.environ.get('VM_STARTUP_BASE_DELAY', '1.0'))

def get_startup_per_machine_factor():
    """Get the per-machine factor for startup delay."""
    return float(os.environ.get('VM_STARTUP_PER_MACHINE_FACTOR', '0.5'))

# Event configuration
def get_internal_event_range():
    """Get the range for internal events."""
    min_val = int(os.environ.get('VM_INTERNAL_EVENT_MIN', '4'))
    max_val = int(os.environ.get('VM_INTERNAL_EVENT_MAX', '10'))
    return [min_val, max_val]

def get_send_to_one_value():
    """Get the value for send-to-one events."""
    return int(os.environ.get('VM_SEND_TO_ONE_VALUE', '1'))

def get_send_to_other_value():
    """Get the value for send-to-other events."""
    return int(os.environ.get('VM_SEND_TO_OTHER_VALUE', '2'))

def get_send_to_both_value():
    """Get the value for send-to-both events."""
    return int(os.environ.get('VM_SEND_TO_BOTH_VALUE', '3'))

def get_event_ranges():
    """Get all event ranges as a dictionary."""
    return {
        'internal': get_internal_event_range(),
        'send_to_one': get_send_to_one_value(),
        'send_to_other': get_send_to_other_value(),
        'send_to_both': get_send_to_both_value()
    }

# Logging configuration
def get_log_directory():
    """Get the log directory."""
    return os.environ.get('VM_LOG_DIRECTORY', 'logs')

def get_log_level():
    """Get the log level."""
    level_str = os.environ.get('VM_LOG_LEVEL', 'INFO')
    return getattr(logging, level_str, logging.INFO)

def get_log_format():
    """Get the log format."""
    return os.environ.get('VM_LOG_FORMAT', 
                         'System Time: %(asctime)s - Event: %(message)s')

# Helper function to print all environment variables and their current values
def print_all_env_vars():
    """Print all environment variables used by the system and their current values."""
    env_vars = {
        'VM_NUM_MACHINES': get_num_machines(),
        'VM_BASE_PORT': get_base_port(),
        'VM_HOST': get_host(),
        'VM_MIN_CLOCK_RATE': get_min_clock_rate(),
        'VM_MAX_CLOCK_RATE': get_max_clock_rate(),
        'VM_MAX_RETRIES': get_max_retries(),
        'VM_RETRY_DELAY': get_retry_delay(),
        'VM_STARTUP_BASE_DELAY': get_startup_base_delay(),
        'VM_STARTUP_PER_MACHINE_FACTOR': get_startup_per_machine_factor(),
        'VM_INTERNAL_EVENT_MIN': get_internal_event_range()[0],
        'VM_INTERNAL_EVENT_MAX': get_internal_event_range()[1],
        'VM_SEND_TO_ONE_VALUE': get_send_to_one_value(),
        'VM_SEND_TO_OTHER_VALUE': get_send_to_other_value(),
        'VM_SEND_TO_BOTH_VALUE': get_send_to_both_value(),
        'VM_LOG_DIRECTORY': get_log_directory(),
        'VM_LOG_LEVEL': os.environ.get('VM_LOG_LEVEL', 'INFO'),
        'VM_LOG_FORMAT': get_log_format()
    }
    
    print("Current Environment Variable Configuration:")
    print("===========================================")
    for var, value in env_vars.items():
        print(f"{var}: {value}")
    print("===========================================")
