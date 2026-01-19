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

        Uses LLM to explain WHY, not just WHERE.
        Falls back to listing if no LLM available.
        """
        # Gather relevant artifacts
        artifacts = self._gather_context(query)

        if not artifacts:
            print(f"\nNo matches for \"{query}\".")
            print("Try capturing more context about this topic.")
            return

        # Try LLM synthesis if available
        if self.provider and self.provider.is_available:
            self._synthesized(query, artifacts)
        else:
            self._fallback(query, artifacts)

        # Succession hint (centralized)
        # Check for unlinked artifacts to provide context-aware hint
        from ..output import end_command
        orphans = self.graph.find_orphans()
        end_command("why", {"found_unlinked": len(orphans) > 0})

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
        """
        specs = []
        for event in self.events.read_all():
            if event.type == EventType.SPECIFICATION_ADDED:
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
        short = node.event_id[:8] if node.event_id else node.id.split('_', 1)[-1][:8]

        incoming = self.graph.get_incoming(node.id)
        outgoing = self.graph.get_outgoing(node.id)
        challenges = self.tensions.get_open_challenges_for_parent(node.id)
        validation = self.validation.get_validation(node.id)

        artifact_id = node.event_id or node.id
        specs = self._get_specs_for_artifact(artifact_id)

        # Collect relationship details for context
        relationships = []
        for edge, target in outgoing:
            target_short = target.event_id[:8] if target.event_id else target.id.split('_', 1)[-1][:8]
            relationships.append({
                'relation': edge.relation,
                'target_id': target_short,
                'target_type': target.type,
                'target_summary': target.content.get('summary', '')[:50]
            })
        for edge, source in incoming:
            source_short = source.event_id[:8] if source.event_id else source.id.split('_', 1)[-1][:8]
            relationships.append({
                'relation': f"has_{edge.relation}",  # Reverse direction indicator
                'target_id': source_short,
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

    def _synthesized(self, query: str, artifacts: list):
        """Use LLM to synthesize explanation (with caching)."""
        symbols = self.symbols

        # Check cache first
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

        context = "\n".join(context_parts)

        system_prompt = """You explain project decisions by synthesizing artifacts into clear understanding.

ARTIFACT TYPES (what they mean):
- PURPOSE: The goal/why something exists - use these to explain motivation
- DECISION: A choice made - use these to explain how/what was done
- CONSTRAINT: A limit/rule - use these to explain boundaries
- PRINCIPLE: A guiding rule - use these to explain philosophy

RELATIONSHIPS (what they mean):
- "supports" = enables or implements
- "evolves_from" = supersedes or replaces
- "tensions_with" = conflicts with
- "found via X from [id]" = connected through graph, not direct keyword match

PRIORITIZATION:
1. Start with PURPOSE to explain WHY
2. Use DECISIONs to explain HOW/WHAT
3. Reference CONSTRAINTs for boundaries
4. Cite traversal hits to show connections

CITATION: Always cite sources as [id] when referencing specific artifacts.

OUTPUT: Plain text only, no markdown. Length should match complexity - simple topics need fewer sentences, complex topics may need more."""

        user_prompt = f"""Question: "{query}"

Artifacts found:
{context}

Synthesize these into an explanation. Lead with WHY (from purposes), then HOW (from decisions). Cite [id] for each claim."""

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

            sources_summary = ", ".join(f"{v} {k}{'s' if v > 1 else ''}" for k, v in source_types.items())
            print(f"  Sources: {sources_summary}")
            print(f"  IDs: {' '.join(source_ids[:10])}")  # Show up to 10 IDs for actionability

        except Exception as e:
            print(f"\r{symbols.llm_done} Error\n")
            # Fall back to listing
            self._fallback(query, artifacts)

    def _fallback(self, query: str, artifacts: list):
        """Fallback: list artifacts when no LLM available."""
        symbols = self.symbols
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

                safe_print(f"  [{link.decision_id[:8]}] {decision_type.upper()}")
                safe_print(f"    \"{decision_summary}\"")

                # Show why this decision was made (purpose link)
                incoming = self.graph.get_incoming(decision_node.id)
                for edge, source_node in incoming:
                    if source_node.type == 'purpose':
                        purpose_summary = source_node.content.get('summary', source_node.content.get('purpose', ''))[:50]
                        print(f"    {symbols.arrow} Purpose: \"{purpose_summary}\"")
                        break
            else:
                print(f"  [{link.decision_id[:8]}] (decision not found in graph)")

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
                    short_id = node.event_id[:8] if node.event_id else node.id.split('_', 1)[-1][:8]
                    suggestions.append({
                        'node': node,
                        'short_id': short_id,
                        'summary': node.content.get('summary', ''),
                        'score': overlap
                    })

        suggestions.sort(key=lambda x: x['score'], reverse=True)
        return suggestions
