#!/usr/bin/env python3
"""
YenSense AI - Entry Point
Professional Japan Macro & FX Intelligence
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import main

if __name__ == "__main__":
    main()