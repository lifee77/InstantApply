#!/usr/bin/env python

"""
Simple OpenSSL compatibility fix script for NEAR AI tools
This avoids dependencies that may cause issues in Anaconda environments
"""

import os
import sys
import subprocess

def print_header(msg):
    """Print a formatted header message"""
    print("\n" + "=" * 80)
    print(f" {msg}")
    print("=" * 80)

def run_pip_command(args):
    """Run a pip command and return the output"""
    cmd = [sys.executable, "-m", "pip"] + args
    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.returncode != 0 and result.stderr:
            print(f"Error: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"Error executing command: {e}")
        return False

def is_anaconda():
    """Check if running in an Anaconda environment"""
    return "anaconda" in sys.prefix.lower() or "conda" in sys.prefix.lower()

def check_openssl():
    """Check for OpenSSL issue without using pkg_resources"""
    print_header("Checking OpenSSL Compatibility")
    
    print(f"Python interpreter: {sys.executable}")
    print(f"Python version: {sys.version}")
    print(f"Environment: {sys.prefix}")
    
    if is_anaconda():
        print("✓ Detected Anaconda environment")
    
    # Try importing OpenSSL directly
    try:
        import OpenSSL
        print(f"✓ OpenSSL module imported")
        
        # Check for the problematic attribute
        try:
            from OpenSSL import crypto
            if hasattr(crypto._lib, 'X509_V_FLAG_NOTIFY_POLICY'):
                print("✓ OpenSSL compatibility check: OK")
                return True
            else:
                print("✗ OpenSSL compatibility issue detected: X509_V_FLAG_NOTIFY_POLICY missing")
                return False
        except AttributeError:
            print("✗ OpenSSL crypto module has attribute error")
            return False
    except ImportError:
        print("✗ Unable to import OpenSSL module")
        return False
    except Exception as e:
        print(f"✗ Error checking OpenSSL: {str(e)}")
        return False

def fix_openssl_issue():
    """Fix the OpenSSL compatibility issue"""
    print_header("OpenSSL Compatibility Fix")
    
    # Check if user is in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    
    if is_anaconda():
        print("\nAnaconda environment detected.")
        print("\nFor Anaconda environments, the recommended solution is:")
        print("1. Create a new clean conda environment:")
        print("   conda create -n nearai python=3.9")
        print("2. Activate the environment:")
        print("   conda activate nearai")
        print("3. Install the required packages:")
        print("   pip install pyopenssl==22.0.0 cryptography==38.0.0 boto3 nearai")
        
        choice = input("\nWould you like to attempt a fix in the current environment? (y/N): ")
        if choice.lower() != 'y':
            return False
    
    if not in_venv:
        print("\nWARNING: You are not in a virtual environment.")
        print("It's recommended to create a dedicated virtual environment for NEAR AI.")
        print("\n1. Create a new virtual environment:")
        print("   python -m venv nearai_env")
        print("2. Activate the environment:")
        print("   source nearai_env/bin/activate  # On Unix/Mac")
        print("   nearai_env\\Scripts\\activate  # On Windows")
        print("3. Run this script again in the new environment")
        
        choice = input("\nDo you want to proceed anyway? (y/N): ")
        if choice.lower() != 'y':
            return False
    
    print("\nStep 1: Uninstalling problematic packages...")
    run_pip_command(["uninstall", "-y", "pyopenssl", "cryptography"])
    
    print("\nStep 2: Installing compatible versions...")
    success1 = run_pip_command(["install", "pyopenssl==22.0.0"])
    success2 = run_pip_command(["install", "cryptography==38.0.0"])
    
    # Check if boto3 and nearai are installed
    try:
        import boto3
    except ImportError:
        print("\nInstalling boto3...")
        run_pip_command(["install", "boto3"])
    
    try:
        import nearai
    except ImportError:
        print("\nInstalling nearai...")
        run_pip_command(["install", "nearai"])
    
    if success1 and success2:
        print("\nVerifying the fix...")
        if check_openssl():
            print_header("SUCCESS! The OpenSSL issue has been fixed.")
            print("You should now be able to use NEAR AI tools.")
            return True
        else:
            print_header("Fix verification failed.")
            print("You may need to try the manual steps for your environment.")
            return False
    else:
        print_header("Installation failed.")
        print("Please try the manual installation commands for your environment.")
        return False

def main():
    print("Simple OpenSSL Fix Tool for NEAR AI\n")
    
    # Check if fix is needed
    if check_openssl():
        print_header("Good news! Your OpenSSL setup appears to be compatible.")
        print("You should be able to use NEAR AI tools without problems.")
        return
    
    # Ask user if they want to fix the issue
    print("\nAn OpenSSL compatibility issue was detected.")
    choice = input("Would you like to fix this issue now? (y/N): ")
    
    if choice.lower() == 'y':
        fix_openssl_issue()
    else:
        print("\nFix skipped. You can run this script again later if needed.")

if __name__ == "__main__":
    main()
