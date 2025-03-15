#!/usr/bin/env python

"""
Simple script to locate NEAR AI installation path
"""

import sys
import os

def find_package_location(package_name):
    """Find the location of an installed Python package"""
    try:
        # Try to import the package to see if it's installed
        __import__(package_name)
        
        # Get the package from sys.modules
        package = sys.modules[package_name]
        
        # Print the package location
        if hasattr(package, '__file__'):
            package_path = os.path.dirname(os.path.abspath(package.__file__))
            print(f"\n{package_name} is installed at:\n{package_path}")
            return package_path
        else:
            print(f"\nCould not determine the location of {package_name}")
            return None
    except ImportError:
        print(f"\n{package_name} is not installed in the current environment")
        return None

if __name__ == "__main__":
    print("Finding NEAR AI installation location...\n")
    
    find_package_location('nearai')
    
    print("\nTo navigate to this directory in your terminal, copy and paste the path.")
