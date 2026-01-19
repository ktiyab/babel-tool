"""
ReviewCommand — Proposal review and theme synthesis

Handles:
- review: Review pending proposals (interactive or by theme)
- Theme synthesis using LLM clustering
- Theme acceptance recording (P7: Reasoning Travels)

HC2 preserved: Human approves themes (directional decisions),
not individual atoms (micro-management).
"""

from typing import Optional

from .base import BaseCommand
from ..core.events import Event, EventType, confirm_artifact, require_negotiation
from ..core.scope import EventScope
from ..core.graph import Edge
from ..presentation.symbols import get_symbols, TableRenderer, safe_print
from ..core.horizon import _extract_keywords


class ReviewCommand(BaseCommand):
    """Review pending proposals with optional AI synthesis."""

    def review(
        self,
        synthesize: bool = False,
        by_theme: bool = False,
        accept_theme: str = None,
        list_themes: bool = False,
        list_only: bool = False,
        accept_ids: list = None,
        accept_all: bool = False,
        output_format: str = None
    ):
        """
        Review pending proposals.

        Shows all queued proposals and allows batch confirmation.
        Decisions are auto-registered for validation tracking.

        Non-interactive modes (AI-safe):
            --list: Show proposals without prompting
            --accept <id>: Accept specific proposal(s) by ID
            --accept-all: Accept all proposals at once

        Synthesis mode (--synthesize):
            AI clusters proposals into themes with impact assessment.
            Human approves themes (directional), not atoms (micro).
            Preserves HC2 at appropriate abstraction level.
        """
        symbols = get_symbols()
        pending = self._get_pending_proposals()

        if not pending:
            print("No pending proposals to review.")
            print("Queue proposals with: babel capture \"text\" --batch")
            from ..output import end_command
            end_command("review", {})
            return

        # Non-interactive modes (AI-safe)
        if list_only:
            if output_format:
                return self._list_proposals_as_output(pending)
            self._list_proposals(pending, symbols)
            return

        if accept_ids:
            self._accept_by_ids(pending, accept_ids, symbols)
            return

        if accept_all:
            self._accept_all_proposals(pending, symbols)
            return

        # Synthesis modes
        if synthesize or by_theme or accept_theme or list_themes:
            self._review_with_synthesis(
                pending, symbols,
                list_only=list_themes,
                accept_theme=accept_theme,
                interactive=not accept_theme
            )
            return

        # Original interactive review (atom by atom)
        print(f"{len(pending)} proposal(s) to review:\n")

        confirmed = 0
        skipped = 0
        decisions_confirmed = []

        for i, proposal_event in enumerate(pending):
            content = proposal_event.data.get('proposed', {})
            artifact_type = content.get('type', 'unknown')
            summary = content.get('summary', 'No summary')
            rationale = content.get('rationale', '')

            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(f"--- {i+1}/{len(pending)}. {artifact_type.upper()} ---")
            safe_print(f"  \"{summary}\"")
            if rationale:
                safe_print(f"  Why: {rationale[:80]}...")
            print(f"  [ID: {proposal_event.id[:8]}]")
            print()
            print("Confirm? [y]es / [n]o / [a]ll / [q]uit")

            response = input("> ").strip().lower()

            if response in ['y', 'yes', '']:
                result = self._confirm_pending_proposal(proposal_event)
                self._print_confirmation(result, symbols)
                confirmed += 1
                if result['artifact_type'] == 'decision':
                    decisions_confirmed.append(result)
            elif response in ['a', 'all']:
                # Confirm this and all remaining
                result = self._confirm_pending_proposal(proposal_event)
                if result['artifact_type'] == 'decision':
                    decisions_confirmed.append(result)
                confirmed += 1
                for remaining in pending[i+1:]:
                    result = self._confirm_pending_proposal(remaining)
                    if result['artifact_type'] == 'decision':
                        decisions_confirmed.append(result)
                    confirmed += 1
                print(f"\n{symbols.check_pass} Confirmed all {confirmed} proposal(s).")
                self._print_validation_hints(decisions_confirmed, symbols)
                return
            elif response in ['q', 'quit']:
                print(f"\nStopped. Confirmed: {confirmed}, Remaining: {len(pending) - i}")
                self._print_validation_hints(decisions_confirmed, symbols)
                return
            else:
                print("Skipped.\n")
                skipped += 1

        print(f"\nReview complete. Confirmed: {confirmed}, Skipped: {skipped}")
        self._print_validation_hints(decisions_confirmed, symbols)

    # -------------------------------------------------------------------------
    # Synthesis mode
    # -------------------------------------------------------------------------

    def _review_with_synthesis(
        self,
        pending: list,
        symbols,
        list_only: bool = False,
        accept_theme: str = None,
        interactive: bool = True
    ):
        """
        Review proposals using AI synthesis into themes.

        HC2 preserved: Human approves themes (directional decisions),
        not individual atoms (micro-management).
        """
        # Synthesize proposals into themes
        themes = self._synthesize_proposals(pending, symbols)

        if not themes:
            print("Could not synthesize themes. Falling back to individual review.")
            print("(Requires LLM provider to be configured)")
            return

        # Assign letters to themes (A, B, C, D...)
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for i, theme in enumerate(themes):
            letter = letters[i] if i < len(letters) else str(i+1)
            theme['letter'] = letter

        # Display themes using TableRenderer
        print(f"\n{len(pending)} proposal(s) synthesized into {len(themes)} theme(s):\n")
        renderer = TableRenderer(symbols)
        print(renderer.render_themes(themes))
        print()

        if list_only:
            print("Accept with: babel review --accept-theme <name>")
            print("Or by letter: babel review --accept-theme A")
            print("Interactive: babel review --synthesize")
            return

        # Non-interactive: accept specific theme (by name or letter)
        if accept_theme:
            self._accept_specific_theme(themes, accept_theme, symbols)
            return

        # Interactive theme review
        self._interactive_theme_review(themes, pending, symbols)

    def _accept_specific_theme(self, themes: list, accept_theme: str, symbols):
        """Accept a specific theme by name or letter."""
        # Try letter first (A, B, C...)
        if len(accept_theme) == 1 and accept_theme.upper() in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            letter = accept_theme.upper()
            theme = next((t for t in themes if t.get('letter') == letter), None)
        else:
            # Try by name
            theme = next((t for t in themes if t['name'].lower() == accept_theme.lower()), None)

        if not theme:
            print(f"Theme '{accept_theme}' not found.")
            available = ', '.join(f"{t.get('letter', '?')}={t['name']}" for t in themes)
            print(f"Available: {available}")
            return

        decisions_confirmed = []
        for proposal_event in theme['proposals']:
            result = self._confirm_pending_proposal(proposal_event)
            if result['artifact_type'] == 'decision':
                decisions_confirmed.append(result)

        # Record the theme acceptance with recommendation in Babel
        self._record_theme_acceptance(theme, symbols)

        print(f"\n{symbols.check_pass} Accepted theme '{theme['name']}': {len(theme['proposals'])} proposal(s)")
        self._print_validation_hints(decisions_confirmed, symbols)

    def _interactive_theme_review(self, themes: list, pending: list, symbols):
        """Interactive theme-by-theme review."""
        print("Accept theme? [A/B/C...] / [all] / [quit]")
        decisions_confirmed = []
        accepted_letters = set()

        while True:
            response = input("> ").strip()

            if response.lower() in ['q', 'quit']:
                print("Review stopped.")
                self._print_validation_hints(decisions_confirmed, symbols)
                return

            if response.lower() in ['a', 'all'] and len(response) > 1 or response.lower() == 'all':
                for theme in themes:
                    for proposal_event in theme['proposals']:
                        result = self._confirm_pending_proposal(proposal_event)
                        if result['artifact_type'] == 'decision':
                            decisions_confirmed.append(result)
                print(f"\n{symbols.check_pass} Accepted all {len(pending)} proposal(s).")
                self._print_validation_hints(decisions_confirmed, symbols)
                return

            # Accept specific theme by letter (A, B, C...)
            letter = response.upper()
            if len(letter) == 1 and letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                theme = next((t for t in themes if t.get('letter') == letter), None)
                if theme:
                    if letter in accepted_letters:
                        print(f"Theme {letter} already accepted.")
                        continue

                    for proposal_event in theme['proposals']:
                        result = self._confirm_pending_proposal(proposal_event)
                        if result['artifact_type'] == 'decision':
                            decisions_confirmed.append(result)
                    accepted_letters.add(letter)

                    # Record the theme acceptance with recommendation in Babel
                    self._record_theme_acceptance(theme, symbols)

                    print(f"{symbols.check_pass} Accepted {letter}. [{theme['name']}]: {len(theme['proposals'])} proposal(s)")

                    # Check if all done
                    remaining_themes = [t for t in themes if t.get('letter') not in accepted_letters]
                    if not remaining_themes:
                        print("\nAll themes reviewed.")
                        self._print_validation_hints(decisions_confirmed, symbols)
                        return
                    remaining_count = sum(len(t['proposals']) for t in remaining_themes)
                    remaining_letters = ', '.join(t.get('letter', '?') for t in remaining_themes)
                    print(f"\nRemaining: {remaining_letters} ({remaining_count} proposals)")
                    print("Accept? [letter] / [all] / [quit]")
                else:
                    available = ', '.join(t.get('letter', '?') for t in themes)
                    print(f"Invalid letter. Available: {available}")
            else:
                print("Enter letter (A/B/C...), 'all', or 'quit'")

    def _synthesize_proposals(self, pending: list, symbols=None) -> list:
        """
        Use LLM to synthesize proposals into themes with recommendations.

        Returns list of themes, each with:
            - name: short theme name
            - description: impact statement
            - risk: low/medium/high
            - recommendation: Accept/Review/Defer/Caution
            - rationale: why this recommendation
            - proposals: list of proposal events in this theme
        """
        if not self.provider or not self.provider.is_available:
            return None

        if symbols is None:
            symbols = get_symbols()

        # Prepare proposal summaries for LLM
        proposal_texts = []
        for i, p in enumerate(pending):
            content = p.data.get('proposed', {})
            proposal_texts.append(
                f"{i+1}. [{content.get('type', 'unknown')}] {content.get('summary', 'No summary')}"
            )

        system_prompt = """You are a proposal synthesis assistant. Your job is to help humans make INFORMED decisions.

Rules:
- Create 2-5 themes maximum
- IMPACT: What concretely changes in app behavior?
- RISK: Potential for unintended consequences (low/medium/high)
- RECOMMENDATION: What should the human do? (Accept/Review/Defer/Caution)
- RATIONALE: Why this recommendation? Reference project principles if relevant."""

        user_prompt = f"""Analyze these {len(pending)} proposals and cluster them into themes.

PROPOSALS:
{chr(10).join(proposal_texts)}

For each theme provide:
1. IMPACT - what changes in the app
2. RISK - low/medium/high
3. RECOMMENDATION - Accept (safe), Review (needs attention), Defer (not urgent), Caution (potential conflict)
4. RATIONALE - why you recommend this

Format (one theme per line, 6 fields separated by |):
THEME: <name> | <impact> | <risk> | <recommendation> | <rationale> | <proposal numbers>

Example:
THEME: config-centralization | App uses single ConfigManager for all settings | medium | Accept | Reduces scattered config, aligns with maintainability | 1,2,5
THEME: breaking-api-change | Old endpoints removed, clients must update | high | Review | Needs migration plan before accepting | 3,4"""

        try:
            print(f"{symbols.llm_thinking} Synthesizing themes...", end="", flush=True)
            response = self.provider.complete(system_prompt, user_prompt, max_tokens=500)
            print(f"{symbols.llm_done} Done")

            # Parse response into themes
            themes = self._parse_theme_response(response.text, pending)
            return themes if themes else None

        except Exception as e:
            print(f" Error: {e}")
            return None

    def _parse_theme_response(self, response_text: str, pending: list) -> list:
        """Parse LLM response into theme structures."""
        themes = []
        for line in response_text.strip().split('\n'):
            if line.startswith('THEME:'):
                parts = line[6:].strip().split('|')
                if len(parts) >= 6:
                    # Full format: name|impact|risk|recommendation|rationale|numbers
                    name = parts[0].strip()
                    description = parts[1].strip()
                    risk = parts[2].strip().lower()
                    if risk not in ('low', 'medium', 'high'):
                        risk = 'medium'
                    recommendation = parts[3].strip().capitalize()
                    if recommendation not in ('Accept', 'Review', 'Defer', 'Caution'):
                        recommendation = 'Review'
                    rationale = parts[4].strip()

                    try:
                        numbers = [int(n.strip()) for n in parts[5].split(',')]
                        theme_proposals = [pending[n-1] for n in numbers if 1 <= n <= len(pending)]
                    except (ValueError, IndexError):
                        theme_proposals = []

                    if theme_proposals:
                        themes.append({
                            'name': name,
                            'description': description,
                            'risk': risk,
                            'recommendation': recommendation,
                            'rationale': rationale,
                            'proposals': theme_proposals
                        })
                elif len(parts) >= 4:
                    # Fallback: old format without recommendation
                    name = parts[0].strip()
                    description = parts[1].strip()
                    risk = parts[2].strip().lower()
                    if risk not in ('low', 'medium', 'high'):
                        risk = 'medium'

                    try:
                        numbers = [int(n.strip()) for n in parts[3].split(',')]
                        theme_proposals = [pending[n-1] for n in numbers if 1 <= n <= len(pending)]
                    except (ValueError, IndexError):
                        theme_proposals = []

                    if theme_proposals:
                        themes.append({
                            'name': name,
                            'description': description,
                            'risk': risk,
                            'recommendation': 'Review',
                            'rationale': 'No rationale provided',
                            'proposals': theme_proposals
                        })
        return themes

    # -------------------------------------------------------------------------
    # Proposal management
    # -------------------------------------------------------------------------

    def _get_pending_proposals(self):
        """
        Get proposals awaiting review.

        Returns proposals that have STRUCTURE_PROPOSED but no ARTIFACT_CONFIRMED.
        """
        # Get all proposal events
        proposed_events = self.events.read_by_type(EventType.STRUCTURE_PROPOSED)

        # Get all confirmed proposal IDs
        confirmed_events = self.events.read_by_type(EventType.ARTIFACT_CONFIRMED)
        confirmed_ids = {e.data.get('proposal_id') for e in confirmed_events}

        # Filter to pending (not yet confirmed)
        pending = [e for e in proposed_events if e.id not in confirmed_ids]

        return pending

    def _list_proposals(self, pending: list, symbols):
        """
        List proposals without prompting (AI-safe).

        Shows all pending proposals with IDs for use with --accept.
        Dual-Display: [ID] + readable summary for comprehension AND action.
        """
        print(f"{len(pending)} proposal(s) pending:\n")

        for i, proposal_event in enumerate(pending):
            content = proposal_event.data.get('proposed', {})
            artifact_type = content.get('type', 'unknown')
            summary = content.get('summary', 'No summary')
            rationale = content.get('rationale', '')
            short_id = proposal_event.id[:8]

            # Dual-Display: [ID] [TYPE] summary
            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(f"{i+1}. [{short_id}] [{artifact_type.upper()}] {summary}")
            if rationale:
                safe_print(f"   WHY: {rationale[:80]}{'...' if len(rationale) > 80 else ''}")
            print()

        print("Accept with:")
        print("  babel review --accept <id>        # Accept specific proposal")
        print("  babel review --accept-all         # Accept all proposals")
        print("  babel review                      # Interactive review")

        # Succession hint
        from ..output import end_command
        has_decisions = any(p.data.get('proposed', {}).get('type') == 'decision' for p in pending)
        end_command("review", {"has_decisions": has_decisions})

    def _list_proposals_as_output(self, pending: list):
        """Return proposal list as OutputSpec for rendering."""
        from babel.output import OutputSpec

        rows = []
        for i, proposal_event in enumerate(pending):
            content = proposal_event.data.get('proposed', {})
            artifact_type = content.get('type', 'unknown')
            summary = content.get('summary', 'No summary')
            rationale = content.get('rationale', '')

            rows.append({
                "n": i + 1,
                "id": proposal_event.id[:8],
                "type": artifact_type.upper(),
                "summary": summary[:50],
                "rationale": rationale[:40] if rationale else "-"
            })

        # Check if any are decisions (for context-aware hints)
        has_decisions = any(
            p.data.get('proposed', {}).get('type') == 'decision'
            for p in pending
        )

        return OutputSpec(
            data=rows,
            shape="table",
            columns=["#", "ID", "Type", "Summary", "Rationale"],
            column_keys=["n", "id", "type", "summary", "rationale"],
            title=f"{len(pending)} proposal(s) pending",
            empty_message="No pending proposals to review.",
            command="review",
            context={"has_decisions": has_decisions}
        )

    def _accept_by_ids(self, pending: list, accept_ids: list, symbols):
        """
        Accept specific proposals by ID (AI-safe).

        Args:
            pending: List of pending proposal events
            accept_ids: List of proposal IDs (partial match supported)
            symbols: Display symbols
        """
        decisions_confirmed = []
        accepted = 0
        not_found = []

        for accept_id in accept_ids:
            # Find matching proposal (partial ID match)
            matching = [p for p in pending if p.id.startswith(accept_id)]

            if not matching:
                not_found.append(accept_id)
                continue

            if len(matching) > 1:
                print(f"Ambiguous ID '{accept_id}' matches {len(matching)} proposals.")
                print("Use more characters to disambiguate.")
                continue

            proposal_event = matching[0]
            result = self._confirm_pending_proposal(proposal_event)
            accepted += 1

            content = proposal_event.data.get('proposed', {})
            artifact_type = content.get('type', 'unknown')
            summary = content.get('summary', 'No summary')

            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(f"{symbols.check_pass} Accepted [{artifact_type.upper()}] {summary[:50]}...")

            if result['artifact_type'] == 'decision':
                decisions_confirmed.append(result)

        if not_found:
            print(f"\nNot found: {', '.join(not_found)}")
            print("Use 'babel review --list' to see available IDs.")

        if accepted > 0:
            print(f"\nAccepted {accepted} proposal(s).")
            self._print_validation_hints(decisions_confirmed, symbols)

    def _accept_all_proposals(self, pending: list, symbols):
        """
        Accept all pending proposals (AI-safe).

        Args:
            pending: List of pending proposal events
            symbols: Display symbols
        """
        decisions_confirmed = []

        print(f"Accepting {len(pending)} proposal(s):\n")

        for proposal_event in pending:
            result = self._confirm_pending_proposal(proposal_event)

            content = proposal_event.data.get('proposed', {})
            artifact_type = content.get('type', 'unknown')
            summary = content.get('summary', 'No summary')

            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(f"{symbols.check_pass} [{artifact_type.upper()}] {summary[:60]}...")

            if result['artifact_type'] == 'decision':
                decisions_confirmed.append(result)

        print(f"\n{symbols.check_pass} Accepted all {len(pending)} proposal(s).")
        self._print_validation_hints(decisions_confirmed, symbols)

    def _confirm_pending_proposal(self, proposal_event) -> dict:
        """
        Confirm a pending proposal from review.

        Args:
            proposal_event: The STRUCTURE_PROPOSED event to confirm

        Returns:
            Dict with artifact_type, node_id, and summary for display
        """
        content = proposal_event.data.get('proposed', {})
        artifact_type = content.get('type', 'unknown')
        summary = content.get('summary', '')
        content.pop('_pending_share', False)  # Remove share flag

        scope = EventScope.SHARED

        # Project the proposal to graph now
        self.graph._project_event(proposal_event)

        # Create confirmation event
        confirm_event = confirm_artifact(
            proposal_id=proposal_event.id,
            artifact_type=artifact_type,
            content=content
        )
        self.events.append(confirm_event, scope=scope)
        self.graph._project_event(confirm_event)

        # Index confirmed artifact into refs
        self.refs.index_event(confirm_event, self.vocabulary)

        # Auto-register decisions for validation tracking
        node_id = None
        if artifact_type == 'decision':
            # Find the node ID from the graph projection
            nodes = self.graph.get_nodes_by_type('decision')
            for node in nodes:
                if node.content.get('summary') == summary:
                    node_id = node.id
                    self.validation.register_decision(node_id, summary)

                    # Auto-link to active purpose (reduce unlinked artifacts)
                    active_purpose = self._cli._get_active_purpose()
                    if active_purpose:
                        self.graph.add_edge(Edge(
                            source_id=active_purpose.id,
                            target_id=node_id,
                            relation="supports",
                            event_id=confirm_event.id
                        ))
                    break

        # Check for requires_negotiation (artifact touches constrained area)
        # HC2: Warn but proceed - AI surfaces, human decides at their pace
        negotiation_result = self._check_requires_negotiation(
            artifact_id=node_id or f"{artifact_type}_{confirm_event.id}",
            summary=summary,
            artifact_type=artifact_type
        )

        return {
            'artifact_type': artifact_type,
            'node_id': node_id or proposal_event.id[:8],
            'summary': summary,
            'requires_negotiation': negotiation_result
        }

    # -------------------------------------------------------------------------
    # Recording and display
    # -------------------------------------------------------------------------

    def _record_theme_acceptance(self, theme: dict, symbols):
        """
        Record theme acceptance with recommendation in Babel.

        Creates an event capturing:
        - Theme name and letter
        - Recommendation and rationale
        - Number of proposals accepted
        - Impact statement

        This preserves the AI's reasoning for future reference (P7: Reasoning Travels).
        """
        # Build the record
        content = (
            f"THEME ACCEPTED: [{theme.get('letter', '?')}] {theme['name']}\n"
            f"RECOMMENDATION: {theme.get('recommendation', 'Review')}\n"
            f"RATIONALE: {theme.get('rationale', 'No rationale')}\n"
            f"IMPACT: {theme.get('description', 'No impact')}\n"
            f"RISK: {theme.get('risk', 'medium')}\n"
            f"PROPOSALS: {len(theme.get('proposals', []))} accepted"
        )

        # Create event
        event = Event(
            type=EventType.CONVERSATION_CAPTURED,
            data={
                "content": content,
                "source": "review-synthesis",
                "theme_name": theme['name'],
                "theme_letter": theme.get('letter'),
                "recommendation": theme.get('recommendation', 'Review'),
                "rationale": theme.get('rationale'),
                "impact": theme.get('description'),
                "risk": theme.get('risk'),
                "proposal_count": len(theme.get('proposals', []))
            }
        )

        # Store as shared (team can see the decision rationale)
        self.events.append(event, scope=EventScope.SHARED)

        # Layer 2 (Encoding): Use safe_print for LLM-generated content
        safe_print(f"  {symbols.bullet} Recorded: {theme.get('recommendation', 'Review')} - {theme.get('rationale', 'No rationale')[:60]}...")

    def _print_confirmation(self, result: dict, symbols):
        """Print detailed confirmation with validation hints for decisions."""
        node_id = result['node_id']
        summary = result['summary']
        artifact_type = result['artifact_type']

        print(f"\nConfirmed: {artifact_type} [{node_id}]")
        # Layer 2 (Encoding): Use safe_print for LLM-generated content
        safe_print(f"  \"{summary[:50]}{'...' if len(summary) > 50 else ''}\"")

        if artifact_type == 'decision':
            print(f"\n  This decision needs validation:")
            print(f"  {symbols.arrow} babel endorse {node_id} (add team consensus)")
            print(f"  {symbols.arrow} babel evidence-decision {node_id} \"...\" (add evidence)")
            print(f"\n  Validation requires both consensus and evidence.\n")
        else:
            print()

    def _print_validation_hints(self, decisions: list, symbols):
        """Print summary validation hints for confirmed decisions."""
        if not decisions:
            # No decisions, but still show succession hint
            from ..output import end_command
            end_command("review", {})
            return

        print(f"\n{len(decisions)} decision(s) registered for validation:")
        for d in decisions[:3]:
            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(f"  [{d['node_id']}] {d['summary'][:40]}...")
        if len(decisions) > 3:
            print(f"  ... and {len(decisions) - 3} more")
        print(f"\nTo validate: babel endorse <id> and babel evidence-decision <id> \"...\"")
        print(f"Check status: babel validation")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("review", {"has_decisions": True})

    # -------------------------------------------------------------------------
    # Constraint overlap detection (requires_negotiation)
    # -------------------------------------------------------------------------

    def _check_requires_negotiation(
        self,
        artifact_id: str,
        summary: str,
        artifact_type: str
    ) -> dict:
        """
        Check if new artifact touches constrained areas (HC2: warn but proceed).

        Args:
            artifact_id: ID of the confirmed artifact
            summary: Artifact summary text
            artifact_type: Type of artifact

        Returns:
            dict with 'required': bool, 'constraint_ids': list, 'severity': str
        """
        # Get all constraints from graph
        constraints = self.graph.get_nodes_by_type('constraint')
        if not constraints:
            return {'required': False, 'constraint_ids': [], 'severity': None}

        # Extract keywords from the new artifact
        artifact_keywords = set(_extract_keywords(summary))
        if not artifact_keywords:
            return {'required': False, 'constraint_ids': [], 'severity': None}

        # Check for overlap with constraint keywords
        overlapping_constraints = []
        for constraint in constraints:
            constraint_text = constraint.content.get('summary', '')
            constraint_keywords = set(_extract_keywords(constraint_text))

            overlap = artifact_keywords & constraint_keywords
            if overlap and len(overlap) >= 2:  # Meaningful overlap (2+ keywords)
                overlapping_constraints.append({
                    'id': constraint.id,
                    'summary': constraint_text,
                    'overlap': list(overlap)
                })

        if not overlapping_constraints:
            return {'required': False, 'constraint_ids': [], 'severity': None}

        # Determine severity based on overlap characteristics
        severity = self._grade_negotiation_severity(
            artifact_type,
            overlapping_constraints
        )

        # Emit NEGOTIATION_REQUIRED event (advisory only)
        constraint_ids = [c['id'] for c in overlapping_constraints]
        event = require_negotiation(
            artifact_id=artifact_id,
            constraint_ids=constraint_ids,
            severity=severity,
            reason=f"Artifact touches {len(constraint_ids)} constraint(s)",
            author="review_command"
        )
        self.events.append(event)

        # Print warning (HC2: warn but proceed)
        symbols = get_symbols()
        print(f"\n  {symbols.tension} Advisory: This {artifact_type} touches constrained areas")
        for c in overlapping_constraints[:3]:
            short_id = c['id'][:8] if len(c['id']) > 8 else c['id']
            print(f"    [{short_id}] {c['summary'][:50]}...")
            print(f"      Overlap: {', '.join(c['overlap'][:5])}")
        if len(overlapping_constraints) > 3:
            print(f"    ... and {len(overlapping_constraints) - 3} more")
        print(f"\n  Severity: {severity} | Human decides at their pace (HC2)")

        return {
            'required': True,
            'constraint_ids': constraint_ids,
            'severity': severity
        }

    def _grade_negotiation_severity(
        self,
        artifact_type: str,
        overlapping_constraints: list
    ) -> str:
        """
        Grade negotiation severity based on overlap characteristics.

        Returns:
            "critical" | "warning" | "info"
        """
        # Multiple constraint overlaps → critical
        if len(overlapping_constraints) >= 3:
            return "critical"

        # Check for hard constraint indicators in overlapping constraints
        hard_indicators = ['must', 'never', 'cannot', 'always', 'required', 'mandatory']
        for c in overlapping_constraints:
            summary_lower = c['summary'].lower()
            if any(ind in summary_lower for ind in hard_indicators):
                return "warning"

        # Single overlap with soft constraint → info
        return "info"
