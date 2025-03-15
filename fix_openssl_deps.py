#!/usr/bin/env python

"""
Fix OpenSSL dependency issues for NEAR AI tools
This script resolves common incompatibilities between PyOpenSSL and the system OpenSSL
"""

import os
import sys
import subprocess
import importlib.util
import pkg_resources

def print_header(msg):
    """Print a formatted header message"""
    print("\n" + "=" * 80)
    print(f" {msg}")
    print("=" * 80)

def run_command(cmd, verbose=True):
    """Run a shell command and return the output"""
    if verbose:
        print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if verbose and result.stdout:
            print(result.stdout)
        if result.returncode != 0 and verbose:
            print(f"Warning: Command returned non-zero exit code: {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
        return result
    except Exception as e:
        if verbose:
            print(f"Error executing command: {e}")
        return None

def is_anaconda():
    """Check if running in an Anaconda environment"""
    return "anaconda" in sys.prefix.lower() or "conda" in sys.prefix.lower()

def check_dependencies():
    """Check for OpenSSL and related package versions"""
    print_header("Checking OpenSSL Dependencies")
    
    # Check if using Anaconda
    if is_anaconda():
        print("✓ Detected Anaconda environment")
        print(f"  Python location: {sys.executable}")
        print(f"  Environment: {sys.prefix}")
    else:
        print(f"✓ Using Python from: {sys.executable}")
    
    # Check installed packages
    packages = {
        'pyopenssl': None,
        'cryptography': None,
        'urllib3': None,
        'boto3': None,
        'nearai': None
    }
    
    for package in packages:
        try:
            version = pkg_resources.get_distribution(package).version
            packages[package] = version
            print(f"✓ {package}: {version}")
        except pkg_resources.DistributionNotFound:
            print(f"✗ {package}: Not installed")
    
    # Check for OpenSSL import issue
    print("\nTesting for X509_V_FLAG_NOTIFY_POLICY issue...")
    try:
        import OpenSSL.crypto
        if hasattr(OpenSSL.crypto._lib, 'X509_V_FLAG_NOTIFY_POLICY'):
            print("✓ OpenSSL compatibility check: OK")
            return True, packages
        else:
            print("✗ OpenSSL compatibility issue detected: X509_V_FLAG_NOTIFY_POLICY missing")
            return False, packages
    except ImportError:
        print("✗ Cannot import OpenSSL.crypto")
        return False, packages
    except Exception as e:
        print(f"✗ Error checking OpenSSL: {str(e)}")
        return False, packages

def fix_dependencies(auto_fix=False):
    """Provide guidance or automatically fix OpenSSL dependency issues"""
    compatible, packages = check_dependencies()
    
    if compatible:
        print_header("No OpenSSL compatibility issues detected")
        print("You should be able to use NEAR AI tools without problems.")
        return True
    
    print_header("OpenSSL Compatibility Fix Required")
    
    # Determine if we're in a virtual environment
    in_venv = sys.prefix != sys.base_prefix
    
    if is_anaconda():
        print("\nAnaconda-specific solution:")
        print("  1. Create a new conda environment:")
        print("     conda create -n nearai_env python=3.9")
        print("  2. Activate the environment:")
        print("     conda activate nearai_env")
        print("  3. Install specific versions of the packages:")
        print("     pip install 'pyopenssl>=22.0.0,<23.0.0' 'cryptography>=38.0.0,<39.0.0' boto3 nearai")
    elif in_venv:
        print(f"\nVirtual environment detected: {sys.prefix}")
        print("  1. Reinstall compatible versions:")
        print("     pip uninstall -y pyopenssl cryptography")
        print("     pip install 'pyopenssl>=22.0.0,<23.0.0' 'cryptography>=38.0.0,<39.0.0'")
        print("     pip install boto3 nearai")
    else:
        print("\nRecommended solution:")
        print("  1. Create a new virtual environment:")
        print("     python -m venv nearai_env")
        print("  2. Activate the environment:")
        print("     source nearai_env/bin/activate  # On Unix/Mac")
        print("     nearai_env\\Scripts\\activate  # On Windows")
        print("  3. Install compatible versions:")
        print("     pip install 'pyopenssl>=22.0.0,<23.0.0' 'cryptography>=38.0.0,<39.0.0' boto3 nearai")
    
    # Auto-fix option
    if auto_fix:
        if not in_venv:
            print("\nWARNING: Auto-fix is only available inside virtual environments.")
            print("Please create and activate a virtual environment first.")
            return False
        
        print_header("Attempting automatic fix")
        
        # Uninstall problematic packages
        print("\nUninstalling incompatible packages...")
        run_command([sys.executable, "-m", "pip", "uninstall", "-y", "pyopenssl", "cryptography"])
        
        # Install compatible versions
        print("\nInstalling compatible versions...")
        run_command([sys.executable, "-m", "pip", "install", "pyopenssl==22.0.0", "cryptography==38.0.0"])
        
        if packages.get('boto3') is None:
            run_command([sys.executable, "-m", "pip", "install", "boto3"])
        
        if packages.get('nearai') is None:
            run_command([sys.executable, "-m", "pip", "install", "nearai"])
        
        # Verify fix worked
        print("\nVerifying fix...")
        compatible, _ = check_dependencies()
        if compatible:
            print_header("SUCCESS! OpenSSL compatibility issues fixed")
            return True
        else:
            print_header("FIX FAILED - Please try manual steps")
            return False
    
    return False

if __name__ == "__main__":
    print("OpenSSL Dependency Fixer for NEAR AI\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        fix_dependencies(auto_fix=True)
    else:
        fix_dependencies(auto_fix=False)
        print("\nTo automatically apply fixes (in a virtual environment), run:")
        print(f"  python {os.path.basename(__file__)} --fix")
