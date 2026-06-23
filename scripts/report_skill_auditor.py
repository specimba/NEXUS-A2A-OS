#!/usr/bin/env python
"""
Utility script to generate and print the Skill Auditor ingestion markdown report.
"""

import sys
import os

# Add the project root to the path so that imports work from any cwd
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from nexus_os.governor.skill_auditor import generate_skill_audit_report

if __name__ == "__main__":
    print(generate_skill_audit_report())