"""Pytest configuration for spo2-desaturation-index tests."""
import os
import sys
from pathlib import Path

# Set a deterministic test key for audit trail (only for testing)
os.environ.setdefault("AUDIT_SECRET_KEY", "test-key-not-for-production-only-unit-tests")

# Ensure project root is on sys.path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
