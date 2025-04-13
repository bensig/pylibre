#!/usr/bin/env python
"""
Simple script to test logging to stdout in screen
"""

import sys
import time

def main():
    """Main function."""
    count = 0
    while True:
        count += 1
        sys.stdout.write(f"Test message {count} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        sys.stdout.flush()
        time.sleep(1)

if __name__ == "__main__":
    main()
