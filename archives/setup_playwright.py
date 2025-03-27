#!/usr/bin/env python3
import os
import subprocess

def install_playwright_browsers():
    """Install browsers required by Playwright"""
    try:
        print("Installing Playwright browsers...")
        subprocess.run(["playwright", "install", "chromium"], check=True)
        print("Playwright browsers installed successfully!")
    except subprocess.CalledProcessError:
        print("Failed to install Playwright browsers. Make sure Playwright is installed correctly.")
        print("Run: pip install playwright")
        print("Then try running this script again.")
    except FileNotFoundError:
        print("Playwright command not found. Make sure you've installed the package.")
        print("Run: pip install playwright")
        print("Then try running this script again.")

if __name__ == "__main__":
    install_playwright_browsers()
