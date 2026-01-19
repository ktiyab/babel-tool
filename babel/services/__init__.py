"""
Services — External integration layer for Babel CLI

Contains integrations with external systems:
- Extractor: LLM-based structure extraction
- Providers: LLM backend providers
- Git: Git repository integration
- Scanner: Code analysis
- IDE: IDE integration
"""

from .extractor import Extractor, Proposal, QueuedExtraction, ExistingArtifact
from .providers import get_provider, get_provider_status
from .git import GitIntegration
from .scanner import Scanner, ScanResult, ScanFinding, ScanContext, format_scan_result
from .ide import IDEType, detect_ide, get_prompt_path, install_prompt

__all__ = [
    # Extractor
    "Extractor", "Proposal", "QueuedExtraction", "ExistingArtifact",
    # Providers
    "get_provider", "get_provider_status",
    # Git
    "GitIntegration",
    # Scanner
    "Scanner", "ScanResult", "ScanFinding", "ScanContext", "format_scan_result",
    # IDE
    "IDEType", "detect_ide", "get_prompt_path", "install_prompt",
]
