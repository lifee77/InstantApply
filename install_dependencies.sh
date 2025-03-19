#!/bin/bash

# First install greenlet with special flags for Python 3.12 compatibility
pip install --no-build-isolation greenlet==3.0.1

# Then install all other requirements
pip install -r requirements.txt

echo "Installation complete!"
echo "Note: If you encounter any issues, try these alternative commands:"
echo "  pip install greenlet==3.0.1 --no-binary :all:"
echo "  pip install SQLAlchemy --no-deps"
