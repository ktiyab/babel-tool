"""
CaptureCommand — Intent capture and extraction workflow

Handles conversation capture (P3), extraction, and confirmation flow.
Supports batch mode (HC2) for queuing proposals for later review.
"""

import re
from typing import List, Dict, Optional

from ..commands.base import BaseCommand
from ..services.extractor import Proposal, ExistingArtifact
from ..core.events import (
    capture_conversation, propose_structure, confirm_artifact, EventType,
    add_specification
)
from ..core.scope import EventScope
from ..tracking.ambiguity import detect_uncertainty
from ..presentation.symbols import safe_print


class CaptureCommand(BaseCommand):
    """
    Command for capturing conversations and extracting artifacts.

    Supports:
    - Raw conversation capture with domain attribution (P3)
    - Cross-domain reference detection (P10)
    - Uncertainty flagging (P6)
    - Batch mode for deferred review (HC2)
    - Context-aware extraction to prevent duplicates (P7)
    """

    def _get_existing_artifacts(self) -> List[ExistingArtifact]:
        """
        Gather existing confirmed artifacts for context injection.

        Used to prevent duplicate extraction (P7: Evidence-Weighted Memory).
        Returns summaries only - full content not needed for deduplication.
        """
        existing = []

        # Get confirmed artifacts from events
        for event in self.events.read_all():
            if event.type == EventType.ARTIFACT_CONFIRMED:
                data = event.data
                artifact_type = data.get('artifact_type', 'unknown')

                # Extract summary from content
                content = data.get('content', {})
                if isinstance(content, dict):
                    summary = content.get('summary', '')
                elif isinstance(content, str):
                    summary = content[:100]
                else:
                    summary = str(content)[:100]

                if summary:
                    existing.append(ExistingArtifact(
                        artifact_type=artifact_type,
                        summary=summary,
                        artifact_id=event.id
                    ))

        return existing

    def capture(
        self,
        text: str,
        auto_extract: bool = True,
        share: bool = False,
        domain: str = None,
        uncertain: bool = False,
        uncertainty_reason: str = None,
        batch_mode: bool = False
    ):
        """
        Capture conversation/thought (P3 + P10 compliant).

        Args:
            text: Content to capture
            auto_extract: Run extraction (default True)
            share: Share with team (default False - local only)
            domain: Expertise domain (P3: bounded expertise attribution)
            uncertain: Mark as uncertain/provisional (P10: holding ambiguity)
            uncertainty_reason: Why this is uncertain
            batch_mode: Queue proposals for later review (HC2)
        """
        from ..core.domains import (
            suggest_domain_for_capture, validate_domain, get_domain_description,
            analyze_cross_domain
        )

        symbols = self.symbols

        # P6: Detect uncertainty if not explicitly flagged
        if not uncertain and detect_uncertainty(text):
            # AI would suggest --uncertain here; for CLI we just note it
            pass  # AI layer handles suggestion

        # P10: Analyze for cross-domain references
        cross_domain = analyze_cross_domain(text)

        # Determine scope
        scope = EventScope.SHARED if share else EventScope.LOCAL

        # Auto-suggest domain if not provided (P3: help with domain attribution)
        suggested_domain = None
        if not domain:
            # Use cross-domain analysis primary or fallback to standard suggestion
            suggested_domain = cross_domain.primary_domain or suggest_domain_for_capture(text)

        # Validate explicit domain
        if domain and not validate_domain(domain):
            print(f"Warning: Unknown domain '{domain}'. Using anyway.")

        # Store raw capture with domain and uncertainty
        event = capture_conversation(
            text,
            domain=domain or suggested_domain,
            uncertain=uncertain,
            uncertainty_reason=uncertainty_reason
        )
        self.events.append(event, scope=scope)

        # Index into refs (O(1) lookup later)
        self.refs.index_event(event, self.vocabulary)

        scope_marker = f"{symbols.shared} shared" if share else f"{symbols.local} local"
        domain_note = ""
        if domain:
            domain_note = f" [{domain}]"
        elif suggested_domain:
            domain_note = f" [auto: {suggested_domain}]"

        # P6: Show uncertainty marker
        uncertain_note = ""
        if uncertain:
            uncertain_note = f" {symbols.evidence_only} UNCERTAIN"

        print(f"Captured ({scope_marker}){domain_note}{uncertain_note}.")

        if uncertain and uncertainty_reason:
            print(f"  Uncertainty: {uncertainty_reason}")

        # P10: Show cross-domain references if detected
        if cross_domain.has_cross_domain:
            cross_summary = cross_domain.summary()
            if cross_summary:
                print(f"  {symbols.drift} Cross-domain: {cross_summary}")
            if cross_domain.external_domains:
                print(f"  (Borrowing from: {', '.join(cross_domain.external_domains)})")

        if not share:
            print(f"  Share with: babel share {event.id[:8]}")

        if auto_extract:
            if not self.extractor.is_available:
                env_key = self.config.llm.api_key_env
                print(f"  (Using basic extraction -- set {env_key} for smarter analysis)")
            self.extract_and_confirm(text, event.id, share=share, domain=domain or suggested_domain, batch_mode=batch_mode)

        # Succession hint (centralized)
        from ..output import end_command
        end_command("capture", {})

    def extract_and_confirm(
        self,
        text: str,
        source_id: str,
        share: bool = False,
        domain: str = None,
        batch_mode: bool = False
    ):
        """
        Extract structure and request confirmation.

        Public method - also used by capture_git_commit.

        Args:
            text: Text to extract from
            source_id: ID of source event
            share: Share confirmations with team
            domain: Domain attribution for proposals
            batch_mode: Queue for later review instead of interactive
        """
        # Get existing artifacts for context-aware extraction (prevents duplicates)
        existing_context = self._get_existing_artifacts()
        proposals = self.extractor.extract(text, source_id, existing_context=existing_context)

        if not proposals:
            print("Nothing structured found. That's fine--raw capture is saved.")
            return

        print(f"\nI found {len(proposals)} potential artifact(s):\n")

        # Batch mode: queue proposals for later review (HC2 compliant)
        if batch_mode:
            queued_count = 0
            for i, proposal in enumerate(proposals):
                # Layer 2 (Encoding): Use safe_print for LLM-generated content
                safe_print(f"--- {i+1}. {proposal.artifact_type.upper()} ---")
                safe_print(self.extractor.format_for_confirmation(proposal))

                # Add domain to proposal content (P3)
                if domain:
                    proposal.content['domain'] = domain

                self._queue_proposal(proposal, share=share)
                print("> queued for review\n")
                queued_count += 1

            print(f"Queued {queued_count} proposal(s). Review with: babel review")
            return

        # Interactive mode: ask for confirmation (default)
        for i, proposal in enumerate(proposals):
            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(f"--- {i+1}. {proposal.artifact_type.upper()} ---")
            safe_print(self.extractor.format_for_confirmation(proposal))

            # In trusted user mode, simplified confirmation
            response = input("> ").strip().lower()

            if response in ['y', 'yes', '']:
                # Add domain to proposal content (P3)
                if domain:
                    proposal.content['domain'] = domain
                self._confirm_proposal(proposal, share=share)
                scope_note = " (shared)" if share else ""
                print(f"Confirmed{scope_note}.\n")
            elif response in ['s', 'skip', 'n', 'no']:
                print("Skipped.\n")
            elif response == 'edit':
                # Simple edit: just re-capture with corrections
                print("Enter corrected summary:")
                new_summary = input("> ").strip()
                if new_summary:
                    proposal.content['summary'] = new_summary
                    if domain:
                        proposal.content['domain'] = domain
                    self._confirm_proposal(proposal, share=share)
                    print("Confirmed with edits.\n")
            else:
                print("Skipped.\n")

    def _confirm_proposal(self, proposal: Proposal, share: bool = False):
        """
        Confirm a proposal, creating artifact.

        Confirmations are always shared (team decisions).
        """
        # Confirmations are team decisions - always shared
        scope = EventScope.SHARED

        # Create proposal event (local - it's AI-generated)
        proposal_event = propose_structure(
            proposal.source_id,
            proposal.content,
            proposal.confidence
        )
        self.events.append(proposal_event, scope=EventScope.LOCAL)
        self.graph._project_event(proposal_event)

        # Create confirmation event (shared - human confirmed)
        confirm_event = confirm_artifact(
            proposal_id=proposal_event.id,
            artifact_type=proposal.artifact_type,
            content=proposal.content
        )
        self.events.append(confirm_event, scope=scope)
        self.graph._project_event(confirm_event)

        # Index confirmed artifact into refs
        self.refs.index_event(confirm_event, self.vocabulary)

    def _queue_proposal(self, proposal: Proposal, share: bool = False):
        """
        Queue a proposal for later review (HC2: Human Authority).

        Creates STRUCTURE_PROPOSED event without ARTIFACT_CONFIRMED.
        Human reviews and confirms via `babel review`.
        """
        # Store metadata for later confirmation
        proposal.content['_pending_share'] = share
        proposal.content['type'] = proposal.artifact_type

        # Create proposal event (local - it's AI-generated, pending review)
        proposal_event = propose_structure(
            proposal.source_id,
            proposal.content,
            proposal.confidence
        )
        self.events.append(proposal_event, scope=EventScope.LOCAL)
        # Don't project to graph yet - wait for confirmation

    # =========================================================================
    # Specification Capture (Intent Chain: Need → Spec → Implementation)
    # =========================================================================

    def capture_spec(
        self,
        need_id: str,
        spec_text: str,
        batch_mode: bool = False
    ):
        """
        Capture specification for an existing need (HC1: append-only enrichment).

        Parses structured specification text and creates SPECIFICATION_ADDED event.
        Links spec to need, completing the intent chain: Need → Spec → Implementation.

        Args:
            need_id: ID (or prefix) of the need to enrich
            spec_text: Specification text with OBJECTIVE, ADD, MODIFY, etc.
            batch_mode: Queue for later review (HC2)
        """
        symbols = self.symbols

        # Resolve need_id (support prefix matching)
        resolved_id = self._resolve_need_id(need_id)
        if not resolved_id:
            print(f"Error: No need found matching '{need_id}'")
            print(f"  Use: babel list --filter <keyword> to find needs")
            return

        # Parse the specification text
        spec_data = self._parse_spec_text(spec_text)

        if not spec_data.get('objective'):
            print(f"Warning: No OBJECTIVE found in specification.")
            print(f"  Expected format: OBJECTIVE: <what this achieves>")
            # Use first line as objective fallback
            first_line = spec_text.strip().split('\n')[0]
            spec_data['objective'] = first_line[:200]

        # Create the specification event
        event = add_specification(
            need_id=resolved_id,
            objective=spec_data.get('objective', ''),
            add=spec_data.get('add'),
            modify=spec_data.get('modify'),
            remove=spec_data.get('remove'),
            preserve=spec_data.get('preserve'),
            related_files=spec_data.get('related_files')
        )

        # Store event (shared - specifications are team-visible)
        self.events.append(event, scope=EventScope.SHARED)

        # Index for retrieval
        self.refs.index_event(event, self.vocabulary)

        print(f"Specification added to [{resolved_id[:8]}] ({symbols.shared} shared).")
        print(f"  OBJECTIVE: {spec_data.get('objective', 'N/A')[:80]}...")

        # Show parsed structure
        if spec_data.get('add'):
            print(f"  ADD: {len(spec_data['add'])} item(s)")
        if spec_data.get('modify'):
            print(f"  MODIFY: {len(spec_data['modify'])} item(s)")
        if spec_data.get('remove'):
            print(f"  REMOVE: {len(spec_data['remove'])} item(s)")
        if spec_data.get('preserve'):
            print(f"  PRESERVE: {len(spec_data['preserve'])} item(s)")
        if spec_data.get('related_files'):
            print(f"  RELATED: {len(spec_data['related_files'])} file(s)")

        # Succession hint
        from ..output import end_command
        end_command("capture_spec", {"need_id": resolved_id})

    def _resolve_need_id(self, need_id: str) -> Optional[str]:
        """
        Resolve need_id to full ID (supports prefix matching).

        Searches for artifacts that could be "needs" (conversations, purposes, decisions).
        """
        # Try exact match first
        for event in self.events.read_all():
            if event.id == need_id or event.id.startswith(need_id):
                return event.id

        return None

    def _parse_spec_text(self, text: str) -> Dict[str, any]:
        """
        Parse structured specification text.

        Extracts:
        - OBJECTIVE: Single line describing what this achieves
        - ADD: List of new things to introduce
        - MODIFY: List of existing things to change
        - REMOVE: List of things to delete
        - PRESERVE: List of things that must NOT change
        - RELATED/RELATED_FILES: List of files to consider

        Supports both colon-separated and bullet formats:
          OBJECTIVE: Do something
          ADD:
          - Item 1
          - Item 2
        """
        result = {
            'objective': None,
            'add': [],
            'modify': [],
            'remove': [],
            'preserve': [],
            'related_files': []
        }

        # Normalize line endings
        text = text.replace('\r\n', '\n')

        # Pattern to match section headers
        section_pattern = re.compile(
            r'^(OBJECTIVE|ADD|MODIFY|REMOVE|PRESERVE|RELATED(?:_FILES)?|RELATED FILES)\s*[:\-]?\s*(.*)$',
            re.IGNORECASE | re.MULTILINE
        )

        # Find all section positions
        sections = []
        for match in section_pattern.finditer(text):
            sections.append({
                'name': match.group(1).upper().replace(' ', '_').replace('RELATED_FILES', 'RELATED'),
                'start': match.start(),
                'end': match.end(),
                'inline_content': match.group(2).strip()
            })

        # Extract content for each section
        for i, section in enumerate(sections):
            # Determine section content range
            start = section['end']
            end = sections[i + 1]['start'] if i + 1 < len(sections) else len(text)
            content_block = text[start:end].strip()

            section_name = section['name']
            inline = section['inline_content']

            if section_name == 'OBJECTIVE':
                # Objective is typically single line
                if inline:
                    result['objective'] = inline
                else:
                    # Take first non-empty line
                    for line in content_block.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('-'):
                            result['objective'] = line
                            break
            else:
                # List sections (ADD, MODIFY, REMOVE, PRESERVE, RELATED)
                items = []

                # Add inline content if present
                if inline:
                    items.append(inline)

                # Parse bullet items
                for line in content_block.split('\n'):
                    line = line.strip()
                    # Match bullet items: "- item" or "* item" or "• item"
                    if line.startswith(('-', '*', '•')):
                        item = line[1:].strip()
                        if item:
                            items.append(item)
                    elif line and not line.startswith(('OBJECTIVE', 'ADD', 'MODIFY', 'REMOVE', 'PRESERVE', 'RELATED')):
                        # Non-bullet non-header line in a list section
                        if items or not inline:  # Only add if we're in list mode
                            items.append(line)

                # Map to result keys
                if section_name == 'RELATED':
                    result['related_files'] = items if items else None
                else:
                    key = section_name.lower()
                    result[key] = items if items else None

        return result
