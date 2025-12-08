#!/usr/bin/env python
"""Simple script to run the Flask app."""
import os
import sys

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)
