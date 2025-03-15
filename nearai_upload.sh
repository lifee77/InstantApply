#!/bin/bash
# Activate the Near AI virtual environment and run commands
source nearai_venv/bin/activate
cd "$(dirname "$0")"
nearai registry upload .
