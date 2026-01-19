"""
SuggestLinksCommand — AI-assisted decision-to-commit linking suggestions

Analyzes recent commits and suggests matching decisions based on:
- Keyword overlap between commit messages and decision summaries
- File path mentions in decisions
- Domain/context alignment

Designed for AI operators to run after commits or periodically.
Supports --from-recent for efficient incremental checking.

Aligns with:
- P7: Reasoning travels (suggests bridging intent with state)
- P8: Evolution traceable (helps complete the chain)
- HC2: Human authority (suggests, doesn't auto-link)
"""

from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from ..commands.base import BaseCommand
from ..core.commit_links import CommitLinkStore
from ..services.git import GitIntegration
from ..presentation.symbols import safe_print


@dataclass
class LinkSuggestion:
    """A suggested link between a decision and a commit."""
    decision_id: str
    decision_summary: str
    decision_type: str
    commit_sha: str
    commit_message: str
    score: float  # 0-1 confidence score
    reasons: List[str]  # Why this match was suggested


class SuggestLinksCommand(BaseCommand):
    """
    Command for suggesting decision-to-commit links.

    Helps AI operators and users discover which decisions
    should be linked to which commits.
    """

    # Common words to ignore in matching
    STOP_WORDS = {
        'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'could', 'should', 'may', 'might', 'can', 'and', 'or', 'but',
        'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from',
        'as', 'this', 'that', 'it', 'its', 'fix', 'add', 'update',
        'use', 'using', 'used', 'new', 'change', 'changes', 'changed',
        'remove', 'removed', 'file', 'files', 'code', 'function'
    }

    def suggest_links(self, from_recent: int = 5, min_score: float = 0.3,
                      show_all: bool = False, commit_sha: str = None):
        """
        Suggest decision-to-commit links.

        Args:
            from_recent: Number of recent commits to analyze (default: 5)
            min_score: Minimum confidence score to show (default: 0.3)
            show_all: Show all suggestions, even low-confidence
            commit_sha: Specific commit to analyze (overrides from_recent)
        """
        symbols = self.symbols

        # Get git integration
        git = GitIntegration(self.project_dir)

        if not git.is_git_repo:
            print("Not a git repository.")
            return

        # Get commit link store
        commit_links = CommitLinkStore(self.babel_dir)
        already_linked = commit_links.get_linked_commit_shas()

        # Get commits to analyze
        if commit_sha:
            commits = self._get_specific_commit(git, commit_sha)
        else:
            commits = self._get_recent_commits(git, from_recent)

        if not commits:
            print("No commits found to analyze.")
            return

        # Filter out already-linked commits
        unlinked_commits = [c for c in commits if c['sha'] not in already_linked]

        if not unlinked_commits:
            print(f"{symbols.check_pass} All recent commits already have decision links.")
            return

        # Get all decisions for matching
        decisions = self._get_linkable_decisions()

        if not decisions:
            print("No decisions found to suggest links for.")
            print("\nCapture decisions with: babel capture \"decision\" --batch")
            return

        # Find suggestions
        all_suggestions = []
        for commit in unlinked_commits:
            suggestions = self._find_matches(commit, decisions, min_score if not show_all else 0.1)
            all_suggestions.extend(suggestions)

        if not all_suggestions:
            print(f"\nAnalyzed {len(unlinked_commits)} unlinked commit(s), no strong matches found.")
            print("\nThis could mean:")
            print("  - Commits are routine (no decision needed)")
            print("  - Decisions haven't been captured yet")
            print(f"\nTo link manually: babel link <decision_id> --to-commit <sha>")
            return

        # Group by commit
        by_commit: Dict[str, List[LinkSuggestion]] = {}
        for s in all_suggestions:
            if s.commit_sha not in by_commit:
                by_commit[s.commit_sha] = []
            by_commit[s.commit_sha].append(s)

        # Display suggestions
        print(f"\n{symbols.llm_thinking} Link Suggestions")
        print(f"(Analyzed {len(unlinked_commits)} unlinked commits)\n")

        for commit_sha, suggestions in by_commit.items():
            # Sort by score descending
            suggestions.sort(key=lambda x: x.score, reverse=True)

            commit_msg = suggestions[0].commit_message[:50]
            print(f"Commit [{commit_sha[:8]}]: \"{commit_msg}\"")

            for s in suggestions[:3]:  # Top 3 per commit
                score_bar = self._score_bar(s.score)
                safe_print(f"  {score_bar} [{s.decision_id[:8]}] {s.decision_type}: {s.decision_summary[:40]}")

                # Show reasons for high-confidence matches
                if s.score >= 0.5 and s.reasons:
                    print(f"       Reasons: {', '.join(s.reasons[:2])}")

            print()

        # Action hints
        total_suggestions = len(all_suggestions)
        print(f"Found {total_suggestions} suggestion(s) across {len(by_commit)} commit(s).\n")

        if all_suggestions:
            best = max(all_suggestions, key=lambda x: x.score)
            print(f"Strongest match:")
            print(f"  babel link {best.decision_id[:8]} --to-commit {best.commit_sha[:8]}")

        print(f"\nTo link: babel link <decision_id> --to-commit <commit_sha>")

        # Succession hint
        from ..output import end_command
        end_command("suggest-links", {"suggestions": total_suggestions})

    def _get_recent_commits(self, git: GitIntegration, count: int) -> List[Dict]:
        """Get recent commits with their info."""
        commits = []

        # Use git log to get recent commits
        output = git._run_git([
            "log", f"-{count}", "--format=%H|%s", "--no-merges"
        ])

        if not output:
            return []

        for line in output.strip().split('\n'):
            if '|' not in line:
                continue
            sha, message = line.split('|', 1)
            commits.append({
                'sha': sha,
                'message': message,
                'words': self._extract_words(message)
            })

        return commits

    def _get_specific_commit(self, git: GitIntegration, commit_sha: str) -> List[Dict]:
        """Get a specific commit."""
        commit_info = git.get_commit(commit_sha, include_diff=False)
        if not commit_info:
            return []

        return [{
            'sha': commit_info.hash,
            'message': commit_info.message,
            'words': self._extract_words(commit_info.message)
        }]

    def _get_linkable_decisions(self) -> List[Dict]:
        """Get all decisions that could be linked."""
        decisions = []

        for node_type in ['decision', 'constraint', 'principle', 'proposal']:
            nodes = self.graph.get_nodes_by_type(node_type)
            for node in nodes:
                summary = node.content.get('summary', str(node.content)[:100])
                short_id = node.event_id[:8] if node.event_id else node.id.split('_', 1)[-1][:8]

                decisions.append({
                    'id': node.event_id or node.id,
                    'short_id': short_id,
                    'type': node_type,
                    'summary': summary,
                    'words': self._extract_words(summary),
                    'domain': node.content.get('domain', ''),
                    'node': node
                })

        return decisions

    def _extract_words(self, text: str) -> Set[str]:
        """Extract meaningful words from text."""
        words = set(text.lower().split())
        # Remove stop words and short words
        return {w for w in words if w not in self.STOP_WORDS and len(w) > 2}

    def _find_matches(self, commit: Dict, decisions: List[Dict],
                      min_score: float) -> List[LinkSuggestion]:
        """Find matching decisions for a commit."""
        suggestions = []
        commit_words = commit['words']

        for decision in decisions:
            score, reasons = self._calculate_match_score(commit, decision)

            if score >= min_score:
                suggestions.append(LinkSuggestion(
                    decision_id=decision['id'],
                    decision_summary=decision['summary'],
                    decision_type=decision['type'],
                    commit_sha=commit['sha'],
                    commit_message=commit['message'],
                    score=score,
                    reasons=reasons
                ))

        return suggestions

    def _calculate_match_score(self, commit: Dict, decision: Dict) -> tuple:
        """
        Calculate match score between commit and decision.

        Returns (score, reasons) tuple.
        """
        score = 0.0
        reasons = []

        commit_words = commit['words']
        decision_words = decision['words']

        # Word overlap (main signal)
        overlap = commit_words & decision_words
        if overlap:
            # Normalize by smaller set size
            overlap_ratio = len(overlap) / min(len(commit_words), len(decision_words)) if min(len(commit_words), len(decision_words)) > 0 else 0
            word_score = min(overlap_ratio * 0.8, 0.6)  # Cap at 0.6
            score += word_score

            if len(overlap) >= 2:
                reasons.append(f"shared terms: {', '.join(list(overlap)[:3])}")

        # Domain match (if commit mentions domain)
        domain = decision.get('domain', '').lower()
        if domain and domain in commit['message'].lower():
            score += 0.2
            reasons.append(f"domain match: {domain}")

        # Type-specific boosts
        decision_type = decision['type']
        commit_msg_lower = commit['message'].lower()

        # Constraints often relate to "must", "cannot", "require"
        if decision_type == 'constraint':
            if any(word in commit_msg_lower for word in ['enforce', 'require', 'must', 'cannot', 'prevent']):
                score += 0.1
                reasons.append("constraint-related commit")

        # Decisions often relate to "implement", "add", "use"
        if decision_type == 'decision':
            if any(word in commit_msg_lower for word in ['implement', 'use', 'add', 'create', 'build']):
                score += 0.1
                reasons.append("implementation commit")

        return min(score, 1.0), reasons

    def _score_bar(self, score: float) -> str:
        """Visual representation of confidence score."""
        if score >= 0.7:
            return "[###]"  # High confidence
        elif score >= 0.5:
            return "[## ]"  # Medium confidence
        elif score >= 0.3:
            return "[#  ]"  # Low confidence
        else:
            return "[   ]"  # Very low
