"""
WhyCommand — Query reasoning with LLM synthesis

Handles 'why' queries with:
- Context gathering from graph artifacts
- LLM-synthesized explanations (P1: complexity into clarity)
- Caching for performance
- Fallback listing when no LLM available
- Commit-to-decision queries (P8: Evolution Traceable)
"""

import json
import hashlib
import re
from pathlib import Path
from typing import Optional, List, Set

from ..commands.base import BaseCommand
from ..core.commit_links import CommitLinkStore
from ..core.events import EventType
from ..core.symbols import CodeSymbolStore
from ..presentation.symbols import safe_print


class WhyCommand(BaseCommand):
    """
    Command for answering 'why' queries about project decisions.

    P1: Synthesizes complexity into clarity (not just search results).
    P7: Surfaces graph relationships as readable insight.
    """

    def __init__(self, cli):
        """Initialize with cache setup."""
        super().__init__(cli)
        self._cache_path = self.babel_dir / "why_cache.json"
        self._cache = self._load_cache()

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------

    def _load_cache(self) -> dict:
        """Load why synthesis cache from disk."""
        try:
            if self._cache_path.exists():
                return json.loads(self._cache_path.read_text())
        except Exception:
            pass
        return {}

    def _save_cache(self, query: str, graph_hash: str, result: str):
        """Save why synthesis result to cache."""
        try:
            self._cache[query.lower()] = {
                'graph_hash': graph_hash,
                'result': result
            }
            self._cache_path.write_text(json.dumps(self._cache, indent=2))
        except Exception:
            pass

    def _get_graph_hash(self) -> str:
        """Get hash of current graph state for cache invalidation."""
        stats = self.graph.stats()
        state = f"{stats['nodes']}:{stats['edges']}"
        return hashlib.md5(state.encode()).hexdigest()[:8]

    def _get_cached(self, query: str) -> Optional[str]:
        """Get cached why result if still valid."""
        query_lower = query.lower()
        if query_lower in self._cache:
            cached = self._cache[query_lower]
            if cached.get('graph_hash') == self._get_graph_hash():
                return cached.get('result')
        return None

    # -------------------------------------------------------------------------
    # Main Command
    # -------------------------------------------------------------------------

    def why(self, query: str):
        """
        Answer a 'why' query with LLM-synthesized explanation.

        P1: Synthesizes complexity into clarity (not just search results).
        P7: Surfaces graph relationships as readable insight.
        P8: Surfaces rejections for learning (Failure Metabolism).
        Phase 2: Includes code symbol locations for comprehensive context.

        Uses LLM to explain WHY, not just WHERE.
        Falls back to listing if no LLM available.
        """
        # Gather relevant artifacts (decisions, constraints, principles)
        artifacts = self._gather_context(query)

        # Gather rejection context (P8: Failure Metabolism)
        rejections = self._gather_rejection_context(query)

        # Gather code symbol context (Phase 2: code locations)
        symbols = self._gather_symbol_context(query)

        if not artifacts and not rejections and not symbols:
            print(f"\nNo matches for \"{query}\".")
            print("Try capturing more context about this topic.")
            return

        # Try LLM synthesis if available
        if self.provider and self.provider.is_available:
            self._synthesized(query, artifacts, rejections, symbols)
        else:
            self._fallback(query, artifacts, rejections, symbols)

        # Succession hint (centralized)
        # Check for unlinked artifacts and symbol context for hints
        from ..output import end_command
        orphan_count = self.graph.count_orphans()  # O(1) lookup instead of fetching all
        end_command("why", {
            "found_unlinked": orphan_count > 0,
            "found_symbols": len(symbols) > 0,
            "no_symbols": len(symbols) == 0 and len(artifacts) > 0,  # Has artifacts but no code
        })

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _tokenize(self, text: str) -> Set[str]:
        """
        Tokenize text for keyword matching.

        Handles punctuation, file extensions, compound terms.
        Examples:
            "ontology.py" -> {"ontology", "py"}
            "why-command" -> {"why", "command"}
            "babel_tool" -> {"babel", "tool"}

        Returns:
            Set of lowercase tokens
        """
        # Split on non-alphanumeric characters
        tokens = re.split(r'[^a-zA-Z0-9]+', text.lower())
        # Filter empty strings and single characters (noise)
        return {t for t in tokens if len(t) > 1}

    def _get_specs_for_artifact(self, artifact_id: str) -> List[dict]:
        """
        Get specifications linked to an artifact.

        Returns list of spec data dicts with objective, add, modify, etc.
        Uses read_by_type() for O(1) type lookup instead of iterating all events.
        """
        specs = []
        # Use type-indexed cache instead of read_all() + filter
        for event in self.events.read_by_type(EventType.SPECIFICATION_ADDED):
            need_id = event.data.get('need_id', '')
            # Match if artifact_id matches or is prefix of need_id
            if need_id == artifact_id or need_id.startswith(artifact_id) or artifact_id.startswith(need_id[:8]):
                specs.append({
                    'objective': event.data.get('objective', ''),
                    'add': event.data.get('add', []),
                    'modify': event.data.get('modify', []),
                    'remove': event.data.get('remove', []),
                    'preserve': event.data.get('preserve', []),
                    'related_files': event.data.get('related_files', [])
                })
        return specs

    def _gather_context(self, query: str) -> list:
        """
        Gather relevant artifacts for a why query.

        Uses two strategies:
        1. Keyword matching (direct hits)
        2. Graph traversal (1 hop from top matches)

        This ensures we find both directly matching artifacts AND
        related artifacts that don't match keywords but are connected.
        """
        artifacts = []
        seen_ids = set()  # Avoid duplicates

        # Search graph nodes
        all_nodes = []
        for node_type in ['decision', 'purpose', 'constraint', 'principle', 'tension']:
            all_nodes.extend(self.graph.get_nodes_by_type(node_type))

        # Keyword matching with improved tokenization
        # Handles punctuation: "ontology.py" -> {"ontology", "py"}
        query_tokens = self._tokenize(query)

        for node in all_nodes:
            content_str = str(node.content)
            content_tokens = self._tokenize(content_str)
            overlap = len(query_tokens & content_tokens)
            if overlap > 0:
                artifact_data = self._build_artifact_data(node, overlap, match_type='direct')
                artifacts.append(artifact_data)
                seen_ids.add(node.id)

        # Sort keyword matches by relevance
        artifacts.sort(key=lambda x: (x['score'], x['related_count']), reverse=True)

        # Graph traversal: expand from top keyword matches (1 hop)
        # Take top 5 seeds to avoid explosion
        seeds = artifacts[:5]
        traversed = []

        for seed in seeds:
            node = seed['node']

            # Follow outgoing edges (what does this artifact inform?)
            for edge, target_node in self.graph.get_outgoing(node.id):
                if target_node.id not in seen_ids:
                    # Traversal hits get lower base score (0.5) but include relationship context
                    artifact_data = self._build_artifact_data(
                        target_node,
                        score=0.5,
                        match_type='traversal',
                        via_relation=edge.relation,
                        via_artifact=seed['short_id']
                    )
                    traversed.append(artifact_data)
                    seen_ids.add(target_node.id)

            # Follow incoming edges (what led to this artifact?)
            for edge, source_node in self.graph.get_incoming(node.id):
                if source_node.id not in seen_ids:
                    artifact_data = self._build_artifact_data(
                        source_node,
                        score=0.5,
                        match_type='traversal',
                        via_relation=edge.relation,
                        via_artifact=seed['short_id']
                    )
                    traversed.append(artifact_data)
                    seen_ids.add(source_node.id)

        # Merge: keyword matches first, then traversal hits
        all_artifacts = artifacts + traversed

        # Final sort and limit
        all_artifacts.sort(key=lambda x: (x['score'], x['related_count']), reverse=True)
        return all_artifacts[:10]  # Limit for token efficiency

    def _gather_rejection_context(self, query: str) -> list:
        """
        Gather rejection events matching a query (P8: Failure Metabolism).

        Rejections provide valuable context about what was tried and
        rejected, enabling learning from false starts.

        Returns list of rejection data dicts with original proposal and reason.
        """
        rejections = []
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return rejections

        # Get all rejection events
        rejection_events = self.events.read_by_type(EventType.PROPOSAL_REJECTED)
        if not rejection_events:
            return rejections

        # Get all proposed events to look up original content
        proposed_events = self.events.read_by_type(EventType.STRUCTURE_PROPOSED)
        proposed_by_id = {e.id: e for e in proposed_events}

        for rejection in rejection_events:
            proposal_id = rejection.data.get('proposal_id', '')
            reason = rejection.data.get('reason', 'No reason provided')
            rejection_date = rejection.timestamp[:10] if rejection.timestamp else 'Unknown'

            # Get original proposal
            original = proposed_by_id.get(proposal_id)
            if original:
                content = original.data.get('proposed', {})
                artifact_type = content.get('type', 'unknown')
                summary = content.get('summary', 'No summary')
            else:
                artifact_type = 'unknown'
                summary = 'Original proposal not found'

            # Check if query matches rejection content
            rejection_text = f"{summary} {reason}"
            rejection_tokens = self._tokenize(rejection_text)
            overlap = len(query_tokens & rejection_tokens)

            if overlap > 0:
                rejections.append({
                    'proposal_id': self._cli.codec.encode(proposal_id) if proposal_id else '',
                    'type': artifact_type,
                    'summary': summary,
                    'reason': reason,
                    'date': rejection_date,
                    'score': overlap
                })

        # Sort by relevance
        rejections.sort(key=lambda x: x['score'], reverse=True)
        return rejections[:5]  # Limit for token efficiency

    # -------------------------------------------------------------------------
    # Symbol Context Gathering (Phase 2: Code Symbol Integration)
    # -------------------------------------------------------------------------

    def _get_symbol_store(self) -> CodeSymbolStore:
        """Get or create CodeSymbolStore instance (lazy initialization)."""
        if not hasattr(self, '_symbol_store'):
            self._symbol_store = CodeSymbolStore(
                babel_dir=self.babel_dir,
                events=self.events,
                graph=self.graph,
                project_dir=self.project_dir
            )
        return self._symbol_store

    def _gather_symbol_context(self, query: str) -> list:
        """
        Gather relevant code symbols for a why query.

        Queries the CodeSymbolStore for symbols matching the query keywords.
        Returns code locations to complement decision context.

        Args:
            query: The why query string

        Returns:
            List of symbol data dicts with file_path, line_start, signature, etc.
        """
        symbols_found = []
        query_tokens = self._tokenize(query)

        if not query_tokens:
            return symbols_found

        store = self._get_symbol_store()

        # Query each token as potential symbol name
        seen_qnames = set()  # Avoid duplicates
        for token in query_tokens:
            # Skip very short tokens (likely noise)
            if len(token) < 3:
                continue

            # Query symbol store
            matches = store.query(token)
            for sym in matches:
                if sym.qualified_name in seen_qnames:
                    continue
                seen_qnames.add(sym.qualified_name)

                # Score based on name match quality
                name_lower = sym.name.lower()
                if name_lower == token:
                    score = 2.0  # Exact match
                elif token in name_lower:
                    score = 1.5  # Partial match in name
                else:
                    score = 1.0  # Match in qualified name

                symbols_found.append({
                    'symbol': sym,
                    'name': sym.name,
                    'qualified_name': sym.qualified_name,
                    'symbol_type': sym.symbol_type,
                    'file_path': sym.file_path,
                    'line_start': sym.line_start,
                    'line_end': sym.line_end,
                    'signature': sym.signature,
                    'docstring': sym.docstring,
                    'score': score
                })

        # Also search graph for code_symbol nodes directly
        code_symbol_nodes = self.graph.get_nodes_by_type('code_symbol')
        for node in code_symbol_nodes:
            content = node.content
            node_name = content.get('name', '').lower()
            qname = content.get('qualified_name', '')

            if qname in seen_qnames:
                continue

            # Check for token match
            name_tokens = self._tokenize(node_name)
            qname_tokens = self._tokenize(qname)
            overlap = len(query_tokens & (name_tokens | qname_tokens))

            if overlap > 0:
                seen_qnames.add(qname)
                symbols_found.append({
                    'symbol': None,  # No Symbol object, data from graph
                    'name': content.get('name', ''),
                    'qualified_name': qname,
                    'symbol_type': content.get('symbol_type', ''),
                    'file_path': content.get('file_path', ''),
                    'line_start': content.get('line_start', 0),
                    'line_end': content.get('line_end', 0),
                    'signature': content.get('signature', ''),
                    'docstring': content.get('docstring', ''),
                    'score': overlap * 0.8  # Slightly lower score for graph-only matches
                })

        # Sort by score and limit
        symbols_found.sort(key=lambda x: x['score'], reverse=True)
        return symbols_found[:5]  # Limit for token efficiency

    def _build_artifact_data(
        self,
        node,
        score: float,
        match_type: str = 'direct',
        via_relation: str = None,
        via_artifact: str = None
    ) -> dict:
        """
        Build artifact data dict for context gathering.

        Args:
            node: Graph node
            score: Relevance score
            match_type: 'direct' (keyword match) or 'traversal' (graph expansion)
            via_relation: Edge type if traversal (e.g., 'supports', 'evolves_from')
            via_artifact: Source artifact ID if traversal
        """
        short = self._cli.codec.encode(node.id)

        incoming = self.graph.get_incoming(node.id)
        outgoing = self.graph.get_outgoing(node.id)
        challenges = self.tensions.get_open_challenges_for_parent(node.id)
        validation = self.validation.get_validation(node.id)

        artifact_id = node.event_id or node.id
        specs = self._get_specs_for_artifact(artifact_id)

        # Collect relationship details for context
        relationships = []
        for edge, target in outgoing:
            target_alias = self._cli.codec.encode(target.id)
            relationships.append({
                'relation': edge.relation,
                'target_id': target_alias,
                'target_type': target.type,
                'target_summary': target.content.get('summary', '')[:50]
            })
        for edge, source in incoming:
            source_alias = self._cli.codec.encode(source.id)
            relationships.append({
                'relation': f"has_{edge.relation}",  # Reverse direction indicator
                'target_id': source_alias,
                'target_type': source.type,
                'target_summary': source.content.get('summary', '')[:50]
            })

        return {
            'node': node,
            'short_id': short,
            'type': node.type,
            'summary': node.content.get('summary', str(node.content)[:100]),
            'domain': node.content.get('domain', ''),
            'score': score,
            'related_count': len(incoming) + len(outgoing),
            'challenges': len(challenges),
            'validated': validation.status.value if validation else None,
            'specs': specs,
            # New fields for traceability
            'match_type': match_type,
            'via_relation': via_relation,
            'via_artifact': via_artifact,
            'relationships': relationships[:5]  # Limit to top 5 relationships
        }

    def _synthesized(self, query: str, artifacts: list, rejections: list = None, code_symbols: list = None):
        """Use LLM to synthesize explanation (with caching)."""
        symbols = self.symbols
        rejections = rejections or []
        code_symbols = code_symbols or []

        # Check cache first (only if no rejections or code_symbols - they add context)
        if not rejections and not code_symbols:
            cached = self._get_cached(query)
            if cached:
                print(f"{symbols.llm_done} (cached)\n")
                # Layer 2 (Encoding): Use safe_print for LLM-generated content
                safe_print(f"{query.capitalize()} in this project:\n")
                safe_print(f"  {cached}\n")
                # Show sources with IDs for traceability
                source_types = {}
                source_ids = []
                for a in artifacts:
                    t = a['type']
                    source_types[t] = source_types.get(t, 0) + 1
                    source_ids.append(f"[{a['short_id']}]")
                sources_summary = ", ".join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in source_types.items())
                print(f"  Sources: {sources_summary}")
                print(f"  IDs: {' '.join(source_ids[:10])}")
                return

        print(f"{symbols.llm_thinking} Thinking...", end="", flush=True)

        # Build context for LLM with IDs and relationships for traceability
        context_parts = []
        for a in artifacts:
            # Include ID for citation capability
            short_id = a['short_id']
            part = f"[{short_id}] {a['type'].upper()}: \"{a['summary']}\""

            if a['domain']:
                part += f" [domain: {a['domain']}]"
            if a['challenges'] > 0:
                part += f" (challenged)"
            if a['validated']:
                part += f" ({a['validated']})"

            # Include how this artifact was found (direct match vs traversal)
            if a.get('match_type') == 'traversal' and a.get('via_relation'):
                part += f" (found via {a['via_relation']} from [{a['via_artifact']}])"

            context_parts.append(part)

            # Include key relationships (P7: relationships carry meaning)
            relationships = a.get('relationships', [])
            for rel in relationships[:3]:  # Limit to top 3 relationships
                rel_line = f"  └─ {rel['relation']} → [{rel['target_id']}] {rel['target_type']}: {rel['target_summary']}"
                context_parts.append(rel_line)

            # Include linked specifications (implementation plans)
            for spec in a.get('specs', []):
                spec_parts = []
                if spec.get('objective'):
                    spec_parts.append(f"OBJECTIVE: {spec['objective']}")
                if spec.get('add'):
                    spec_parts.append(f"ADD: {', '.join(spec['add'][:3])}")
                if spec.get('modify'):
                    spec_parts.append(f"MODIFY: {', '.join(spec['modify'][:3])}")
                if spec_parts:
                    context_parts.append(f"  SPEC: {'; '.join(spec_parts)}")

        # Add rejection context (P8: Failure Metabolism)
        rejection_parts = []
        for r in rejections:
            rejection_parts.append(
                f"[{r['proposal_id']}] REJECTED {r['type'].upper()}: \"{r['summary']}\" — REASON: {r['reason']}"
            )

        # Add code symbol context (Phase 2: code locations)
        symbol_parts = []
        for s in code_symbols:
            location = f"{s['file_path']}:{s['line_start']}"
            if s['line_end'] != s['line_start']:
                location += f"-{s['line_end']}"
            type_label = s['symbol_type'].upper()
            part = f"[CODE] {type_label} {s['name']} @ {location}"
            if s['signature']:
                part += f"\n  Signature: {s['signature']}"
            if s['docstring']:
                part += f"\n  Purpose: \"{s['docstring'][:100]}\""
            symbol_parts.append(part)

        context = "\n".join(context_parts)
        rejection_context = "\n".join(rejection_parts) if rejection_parts else ""
        symbol_context = "\n".join(symbol_parts) if symbol_parts else ""

        system_prompt = """You explain project decisions by synthesizing artifacts into clear understanding.

ARTIFACT TYPES (what they mean):
- PURPOSE: The goal/why something exists - use these to explain motivation
- DECISION: A choice made - use these to explain how/what was done
- CONSTRAINT: A limit/rule - use these to explain boundaries
- PRINCIPLE: A guiding rule - use these to explain philosophy
- REJECTED: A proposal that was rejected - explain what was tried and why it failed (P8: learn from failures)
- CODE: A code symbol (class, function, method) - shows WHERE implementation exists

RELATIONSHIPS (what they mean):
- "supports" = enables or implements
- "evolves_from" = supersedes or replaces
- "tensions_with" = conflicts with
- "found via X from [id]" = connected through graph, not direct keyword match

PRIORITIZATION:
1. Start with PURPOSE to explain WHY
2. Use DECISIONs to explain HOW/WHAT
3. Reference CONSTRAINTs for boundaries
4. Mention REJECTIONs if relevant (what was tried and failed)
5. Cite traversal hits to show connections
6. Reference CODE symbols to show where implementation lives (file:line format)

CITATION: Always cite sources as [id] when referencing specific artifacts. For code, mention file:line.

OUTPUT: Plain text only, no markdown. Length should match complexity - simple topics need fewer sentences, complex topics may need more."""

        # Build user prompt with optional rejection and symbol context
        user_prompt_parts = [f'Question: "{query}"', "", "Artifacts found:", context]

        if rejection_context:
            user_prompt_parts.extend(["", "Rejected proposals (P8: learn from what didn't work):", rejection_context])

        if symbol_context:
            user_prompt_parts.extend(["", "Related code locations:", symbol_context])

        user_prompt_parts.extend([
            "",
            "Synthesize these into an explanation. Lead with WHY (from purposes), then HOW (from decisions).",
            "If relevant, mention what was rejected and why. Reference code locations for implementation details.",
            "Cite [id] for each claim."
        ])

        user_prompt = "\n".join(user_prompt_parts)

        try:
            response = self.provider.complete(system_prompt, user_prompt, max_tokens=500)

            # Show completion with token usage
            token_info = response.format_tokens(symbols)
            print(f"\r{symbols.llm_done} Done  {token_info}\n")

            result_text = response.text.strip()

            # Cache the result
            self._save_cache(query, self._get_graph_hash(), result_text)

            # Display synthesized explanation
            # Layer 2 (Encoding): Use safe_print for LLM-generated content
            safe_print(f"{query.capitalize()} in this project:\n")
            safe_print(f"  {result_text}\n")

            # Show sources with IDs for traceability (P7: Reasoning Travels)
            source_types = {}
            source_ids = []
            for a in artifacts:
                t = a['type']
                source_types[t] = source_types.get(t, 0) + 1
                source_ids.append(f"[{a['short_id']}]")

            # Include rejections in source count (P8: Failure Metabolism)
            if rejections:
                source_types['rejection'] = len(rejections)
                for r in rejections:
                    source_ids.append(f"[{r['proposal_id']}]")

            # Include code symbols in source count (Phase 2)
            if code_symbols:
                source_types['code_symbol'] = len(code_symbols)

            sources_summary = ", ".join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in source_types.items())
            print(f"  Sources: {sources_summary}")
            print(f"  IDs: {' '.join(source_ids[:10])}")  # Show up to 10 IDs for actionability

        except Exception as e:
            print(f"\r{symbols.llm_done} Error\n")
            # Fall back to listing
            self._fallback(query, artifacts, rejections, code_symbols)

    def _fallback(self, query: str, artifacts: list, rejections: list = None, code_symbols: list = None):
        """Fallback: list artifacts when no LLM available."""
        symbols = self.symbols
        rejections = rejections or []
        code_symbols = code_symbols or []
        print(f"\n{query.capitalize()}:\n")

        for a in artifacts[:5]:
            node = a['node']
            short_id = a['short_id']
            domain_tag = f" [{a['domain']}]" if a['domain'] else ""

            # Check deprecation status (access via cli)
            dep_info = self._cli._is_deprecated(node.id)
            dep_marker = f" {symbols.deprecated}" if dep_info else ""

            # Show ID for traceability
            safe_print(f"  [{short_id}] {a['type'].capitalize()}: {a['summary'][:50]}{domain_tag}{dep_marker}")

            # Show how artifact was found (if via traversal)
            if a.get('match_type') == 'traversal' and a.get('via_relation'):
                print(f"    (via {a['via_relation']} from [{a['via_artifact']}])")

            # Show key relationships
            for rel in a.get('relationships', [])[:2]:
                print(f"    {symbols.arrow} {rel['relation']} [{rel['target_id']}]")

            if a['challenges'] > 0:
                print(f"    {symbols.tension} {a['challenges']} open challenge(s)")

            # Show linked specifications
            for spec in a.get('specs', []):
                if spec.get('objective'):
                    print(f"    {symbols.arrow} Spec: {spec['objective'][:50]}...")

        # Show rejections (P8: Failure Metabolism)
        if rejections:
            print(f"\nRejected proposals (P8: learn from failures):\n")
            for r in rejections[:3]:
                safe_print(f"  [{r['proposal_id']}] REJECTED {r['type'].upper()}: {r['summary'][:40]}...")
                safe_print(f"    REASON: {r['reason'][:60]}...")

        # Show code symbols (Phase 2: code locations)
        if code_symbols:
            print(f"\nRelated code:\n")
            for s in code_symbols[:5]:
                type_icon = {
                    'class': 'C',
                    'function': 'F',
                    'method': 'M',
                    'module': 'mod'
                }.get(s['symbol_type'], '?')

                location = f"{s['file_path']}:{s['line_start']}"
                if s['line_end'] != s['line_start']:
                    location += f"-{s['line_end']}"

                safe_print(f"  [{type_icon}] {s['name']} @ {location}")
                if s['signature']:
                    safe_print(f"      {s['signature'][:60]}")
                if s['docstring']:
                    safe_print(f"      \"{s['docstring'][:50]}...\"")

        print(f"\n  (Configure LLM for full explanation)")

    # -------------------------------------------------------------------------
    # Commit-based Queries (P8: Evolution Traceable)
    # -------------------------------------------------------------------------

    def why_commit(self, commit_sha: str):
        """
        Answer 'why was this commit made?' by showing linked decisions.

        P8: Traces state (commit) back to intent (decisions).
        Bridges git history with babel reasoning.

        Args:
            commit_sha: Git commit SHA or reference (HEAD, branch, etc.)
        """
        symbols = self.symbols

        # Validate commit exists
        from ..services.git import GitIntegration
        git = GitIntegration()

        if not git.is_git_repo:
            print("Not a git repository.")
            return

        commit_info = git.get_commit(commit_sha, include_diff=False)
        if not commit_info:
            print(f"Commit not found: {commit_sha}")
            return

        full_sha = commit_info.hash
        short_sha = full_sha[:8]

        print(f"\nCommit [{short_sha}]:")
        print(f"  \"{commit_info.message}\"")
        if commit_info.author:
            print(f"  by {commit_info.author}")
        print()

        # Get linked decisions
        commit_links = CommitLinkStore(self.babel_dir)
        links = commit_links.get_decisions_for_commit(full_sha)

        if not links:
            print(f"No decisions linked to this commit.")
            print(f"\nTo link a decision: babel link <decision_id> --to-commit {short_sha}")

            # Try to suggest related decisions based on commit message keywords
            suggestions = self._suggest_decisions_for_commit(commit_info)
            if suggestions:
                print(f"\n{symbols.llm_thinking} Possibly related decisions:")
                for s in suggestions[:3]:
                    safe_print(f"  [{s['short_id']}] {s['summary'][:50]}")
                print(f"\nLink with: babel link <id> --to-commit {short_sha}")
            return

        print(f"Linked decisions ({len(links)}):\n")

        for link in links:
            # Get decision details from graph
            decision_node = self._find_decision_node(link.decision_id)

            if decision_node:
                decision_summary = decision_node.content.get('summary', '')
                decision_type = decision_node.type

                safe_print(f"  {self._cli.format_id(link.decision_id)} {decision_type.upper()}")
                safe_print(f"    \"{decision_summary}\"")

                # Show why this decision was made (purpose link)
                incoming = self.graph.get_incoming(decision_node.id)
                for edge, source_node in incoming:
                    if source_node.type == 'purpose':
                        purpose_summary = source_node.content.get('summary', source_node.content.get('purpose', ''))[:50]
                        print(f"    {symbols.arrow} Purpose: \"{purpose_summary}\"")
                        break
            else:
                print(f"  {self._cli.format_id(link.decision_id)} (decision not found in graph)")

            print(f"    Linked by: {link.linked_by}")
            print()

        # Succession hint
        from ..output import end_command
        end_command("why", {"commit_query": True, "found_links": len(links) > 0})

    def _find_decision_node(self, decision_id: str):
        """Find a decision node by ID (supports prefix matching)."""
        for node_type in ['decision', 'proposal', 'constraint', 'principle']:
            nodes = self.graph.get_nodes_by_type(node_type)
            for node in nodes:
                if node.event_id and node.event_id.startswith(decision_id):
                    return node
                if node.id.endswith(decision_id):
                    return node
        return None

    def _suggest_decisions_for_commit(self, commit_info) -> List[dict]:
        """Suggest possibly related decisions based on commit message keywords."""
        message_words = set(commit_info.message.lower().split())

        # Remove common words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'can', 'and', 'or', 'but',
                     'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
                     'as', 'this', 'that', 'it', 'its', 'fix', 'add', 'update'}
        message_words -= stop_words

        if not message_words:
            return []

        suggestions = []
        for node_type in ['decision', 'constraint', 'principle']:
            nodes = self.graph.get_nodes_by_type(node_type)
            for node in nodes:
                content_str = str(node.content).lower()
                overlap = len(message_words & set(content_str.split()))
                if overlap > 0:
                    alias = self._cli.codec.encode(node.id)
                    suggestions.append({
                        'node': node,
                        'short_id': alias,
                        'summary': node.content.get('summary', ''),
                        'score': overlap
                    })

        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

def register_parser(subparsers):
    """Register why command parser."""
    p = subparsers.add_parser('why', help='Ask why something is the way it is')
    p.add_argument('query', nargs='?', help='What do you want to understand?')
    p.add_argument('--commit', help='Query why a specific commit was made (shows linked decisions)')
    return p


def handle(cli, args):
    """Handle why command dispatch."""
    if args.commit:
        cli._why_cmd.why_commit(args.commit)
    elif args.query:
        cli._why_cmd.why(args.query)
    else:
        print('Usage: babel why "topic"           (query decisions)')
        print('       babel why --commit <sha>    (why was this commit made?)')
