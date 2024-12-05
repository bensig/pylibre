import threading
import json

lock = threading.Lock()

def write_price(file_path, price):
    """Write the latest price to a file."""
    with lock:
        with open(file_path, "w") as f:
            json.dump({"price": price}, f)

def read_price(file_path):
    """Read the latest price from a file."""
    with lock:
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                return data.get("price")
        except (FileNotFoundError, json.JSONDecodeError):
            return None
