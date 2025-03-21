import threading
import json
import os
from datetime import datetime
import logging

lock = threading.Lock()

def write_price(file_path, price):
    """Write price data to a JSON file.
    
    Args:
        file_path (str): Path to the JSON file
        price (float): Price value to store
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Create the JSON data with price and timestamp
        data = {
            "price": price,
            "last_updated": datetime.now().isoformat()
        }
        
        # Ensure atomic write by using a temporary file
        temp_file = file_path + ".tmp"
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk
            
        # Rename is atomic on most filesystems
        os.rename(temp_file, file_path)
        return True
    except Exception as e:
        logging.error(f"Error writing price to {file_path}: {e}")
        return False

def read_price(file_path):
    """Read price data from a JSON file.
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        float: Price value or None if not found
    """
    try:
        if not os.path.exists(file_path):
            return None
            
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # Support both new format (with timestamp) and old format (just price)
        if isinstance(data, dict) and "price" in data:
            return data["price"]
        else:
            return data
    except Exception as e:
        logging.error(f"Error reading price from {file_path}: {e}")
        return None
