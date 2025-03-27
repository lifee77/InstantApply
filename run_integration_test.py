#!/usr/bin/env python
"""
Helper script to run the integration test with the current Python environment.
This avoids hardcoding paths to Python interpreters.
"""
import os
import sys
import asyncio
from unittest.mock import patch

# Make sure we can import from the project
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_test_for_url(url=None):
    """Run the integration test for a specific URL or use the default"""
    from archive.test_integration_real import integration_test, TEST_URL
    
    async def run():
        if url:
            print(f"Running integration test for URL: {url}")
            # Patch the TEST_URL value with our URL
            with patch('archive.integration.test_integration_real.TEST_URL', url):
                await integration_test()
        else:
            print(f"Running integration test with default URL: {TEST_URL}")
            await integration_test()
    
    asyncio.run(run())

if __name__ == "__main__":
    # If a URL is provided as a command-line argument, use it
    if len(sys.argv) > 1:
        url = sys.argv[1]
        run_test_for_url(url)
    else:
        run_test_for_url()
    
    print("Integration test completed.")
