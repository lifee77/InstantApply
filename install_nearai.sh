#!/bin/bash

echo "Installing Near AI CLI tools..."

# Make sure pip is updated
pip install --upgrade pip

# Install Near AI CLI
pip install nearai

# Verify installation
nearai --version

echo "Near AI CLI tools installed. You can now upload your package with:"
echo "nearai registry upload ."
