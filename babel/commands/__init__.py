"""
Commands — Modular CLI command implementations

Each command module handles a specific domain:
- review: Proposal review and synthesis
- capture: Intent capture and extraction
- query: Why queries and context gathering
- status: Project status and health checks
- tensions: Challenge and resolution workflow
- validation: Decision endorsement and evidence
- questions: Open question management
"""

from .base import BaseCommand

__all__ = ['BaseCommand']
