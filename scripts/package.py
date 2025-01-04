#!/usr/bin/env python3
import os
import tarfile
import fnmatch
from datetime import datetime
from pathlib import Path

def read_gitignore(root_dir):
    """Read .gitignore patterns from the root directory."""
    gitignore_path = os.path.join(root_dir, '.gitignore')
    patterns = []
    
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    patterns.append(line)
    
    # Add some additional sensitive/build files that might not be in .gitignore
    additional_patterns = [
        'credentials.json',
        'accounts.json',
        '.env*',
        '.git/'
    ]
    patterns.extend(additional_patterns)
    
    return patterns

def should_exclude(path, patterns):
    """Check if path matches any of the exclude patterns."""
    path_str = str(Path(path))
    return any(fnmatch.fnmatch(path_str, pattern) for pattern in patterns)

def create_package():
    # Get project root directory (assuming script is in scripts/)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Create dist directory if it doesn't exist
    dist_dir = os.path.join(root_dir, 'dist')
    os.makedirs(dist_dir, exist_ok=True)
    
    # Read gitignore patterns
    exclude_patterns = read_gitignore(root_dir)
    
    # Create timestamp for filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filename = f'pylibre_{timestamp}.tar.gz'
    output_path = os.path.join(dist_dir, output_filename)

    with tarfile.open(output_path, 'w:gz') as tar:
        # Walk through directory
        for dirpath, dirnames, filenames in os.walk(root_dir):
            # Get relative path
            relpath = os.path.relpath(dirpath, root_dir)
            
            # Skip excluded directories
            dirnames[:] = [d for d in dirnames 
                         if not should_exclude(os.path.join(relpath, d), exclude_patterns)]
            
            # Add files that aren't excluded
            for filename in filenames:
                filepath = os.path.join(relpath, filename)
                if not should_exclude(filepath, exclude_patterns):
                    full_path = os.path.join(dirpath, filename)
                    arcname = os.path.join('pylibre', relpath, filename)
                    tar.add(full_path, arcname=arcname)

    print(f'Package created in dist directory: {output_filename}')
    return output_filename

if __name__ == '__main__':
    create_package() 