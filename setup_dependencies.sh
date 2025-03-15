#!/bin/bash

echo "Setting up dependencies for InstantApply..."

# Update pip
echo "Updating pip..."
python -m pip install --upgrade pip

# Install Rust if not already installed
if ! command -v rustc &> /dev/null
then
    echo "Installing Rust toolchain..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
else
    echo "Rust is already installed."
fi

# Verify installations
echo "Checking installed versions:"
pip --version
rustc --version

echo "Setup complete. You may need to restart your terminal for changes to take effect."
echo "After restarting, run 'pip install -r requirements.txt' again."
