# backend/run_tests.py

import sys
import subprocess
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

def run_tests():
    """Run pytest with proper configuration"""
    result = subprocess.run(
        [
            'pytest',
            'tests/',
            '-v',
            '--tb=short',
            '--cov=app',
            '--cov-report=html',
            '--cov-report=term'
        ],
        cwd=backend_dir
    )
    
    return result.returncode

if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)