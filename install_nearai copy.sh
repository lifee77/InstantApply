#!/bin/bash

echo "Installing Near AI CLI tools in a dedicated virtual environment..."

# Set up variables
VENV_DIR="nearai_venv"
PROJ_DIR="$(pwd)"

# Create a dedicated virtual environment
echo "Creating virtual environment for Near AI CLI..."
python -m venv $VENV_DIR

# Activate the virtual environment
source $VENV_DIR/bin/activate

# Update pip within the virtual environment
echo "Updating pip..."
pip install --upgrade pip

# Install dependencies with specific versions that work well together
echo "Installing compatible dependencies..."
pip install cryptography==36.0.0
pip install pyOpenSSL==21.0.0
pip install boto3==1.24.0
pip install botocore==1.27.0

# Install Near AI CLI
echo "Installing Near AI CLI..."
pip install nearai

# Verify installation
echo "Checking Near AI CLI version:"
nearai --version

# Create a convenient script to use Near AI with this environment
cat > nearai_upload.sh << 'EOF'
#!/bin/bash
# Activate the Near AI virtual environment and run commands
source nearai_venv/bin/activate
cd "$(dirname "$0")"
nearai registry upload .
EOF

chmod +x nearai_upload.sh

echo "------------------------------------------------------"
echo "Installation complete!"
echo "To upload your package to Near AI registry, run:"
echo "./nearai_upload.sh"
echo "------------------------------------------------------"
