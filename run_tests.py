#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test runner for the Human Action audiobook generator
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def main():
    """Main entry point for the test runner"""
    parser = argparse.ArgumentParser(
        description='Run tests for the Human Action audiobook generator',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        '-u', '--unit',
        action='store_true',
        help='Run only unit tests'
    )
    
    parser.add_argument(
        '-i', '--integration',
        action='store_true',
        help='Run only integration tests'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    parser.add_argument(
        '-x', '--xml',
        action='store_true',
        help='Generate XML report for CI'
    )
    
    parser.add_argument(
        '--create-missing',
        action='store_true',
        help='Create any missing directories for tests'
    )
    
    args = parser.parse_args()
    
    # Set environment variables for tests
    os.environ['USE_ESPEAK'] = '1'
    os.environ['SKIP_TEXT_OPTIMIZATION'] = '1'
    
    # Create test directories if needed
    if args.create_missing:
        create_test_directories()
    
    # Determine which tests to run
    test_path = 'tests/'
    
    if args.unit:
        test_path = 'tests/unit/'
    elif args.integration:
        test_path = 'tests/integration/'
    
    # Build pytest command
    cmd = ['pytest']
    
    if args.verbose:
        cmd.append('-v')
    
    if args.xml:
        cmd.append('--junitxml=test-results.xml')
    
    cmd.append(test_path)
    cmd.append('--color=yes')
    
    # Run the tests
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    sys.exit(result.returncode)

def create_test_directories():
    """Create any missing test directories"""
    # Create test directories
    base_dir = Path(__file__).parent
    
    directories = [
        base_dir / 'tests',
        base_dir / 'tests/unit',
        base_dir / 'tests/integration',
        base_dir / 'tests/fixtures',
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True)
        
    # Create test fixtures
    fixtures_dir = base_dir / 'tests/fixtures'
    
    # Create sample.md if it doesn't exist
    sample_md = fixtures_dir / 'sample.md'
    if not sample_md.exists():
        with open(sample_md, 'w', encoding='utf-8') as f:
            f.write("""# Test Sample

This is a test sample markdown file.

## Section 1

Lorem ipsum dolor sit amet, consectetur adipiscing elit.

## Section 2

Donec a diam lectus. Sed sit amet ipsum mauris.
""")
    
    print(f"Created test directories: {', '.join(str(d) for d in directories)}")

if __name__ == '__main__':
    main() 