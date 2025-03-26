#!/usr/bin/env python3
import os
import sys

def check_gemini_api():
    """
    Check if the Gemini API key exists in the .env file
    If it doesn't exist, provide instructions
    """
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    
    # Check if .env file exists
    if not os.path.exists(env_path):
        create_env_file(env_path)
        print_instructions()
        return False
        
    # Check if GEMINI_API_KEY is in .env
    with open(env_path, 'r') as f:
        env_content = f.read()
        
    if 'GEMINI_API_KEY=' not in env_content:
        print_instructions()
        return False
    
    print("✅ Gemini API key found in .env file.")
    return True

def create_env_file(env_path):
    """Create a new .env file if it doesn't exist"""
    try:
        with open(env_path, 'a'):
            pass
        print(f"Created .env file at: {env_path}")
    except Exception as e:
        print(f"Error creating .env file: {str(e)}")
        sys.exit(1)

def print_instructions():
    """Print instructions for setting up the Gemini API key"""
    print("\n⚠️ GEMINI API KEY NOT FOUND")
    print("---------------------------")
    print("To use Google Gemini for application filling, please:")
    
    print("\n1. Get an API key from Google AI Studio:")
    print("   https://makersuite.google.com/app/apikey")
    
    print("\n2. Add your API key to the .env file:")
    print('   echo "GEMINI_API_KEY=your_api_key_here" >> .env')
    
    print("\nAfter adding the API key, restart the application.")
    print("---------------------------\n")

if __name__ == "__main__":
    check_gemini_api()
