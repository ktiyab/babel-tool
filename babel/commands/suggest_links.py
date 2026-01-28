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

from typing import List, Dict
from dataclasses import dataclass

from rapidfuzz import fuzz

from ..commands.base import BaseCommand
from ..core.commit_links import CommitLinkStore
from ..services.git import GitIntegration
from ..presentation.formatters import generate_summary, format_timestamp
from ..presentation.symbols import safe_print
from ..presentation.template import OutputTemplate


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
    commit_date: str = ''  # P12: Temporal attribution
    decision_created_at: str = ''  # P12: Temporal attribution


class SuggestLinksCommand(BaseCommand):
    """
    Command for suggesting decision-to-commit links.

    Helps AI operators and users discover which decisions
    should be linked to which commits.
    """

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
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL SUGGEST-LINKS", "Git Error")
            template.section("STATUS", "Not a git repository.")
            template.footer("Run from within a git repository")
            output = template.render(command="suggest-links", context={"git_error": True})
            print(output)
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
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL SUGGEST-LINKS", "No Commits")
            template.section("STATUS", "No commits found to analyze.")
            template.footer("Ensure repository has commits")
            output = template.render(command="suggest-links", context={"no_commits": True})
            print(output)
            return

        # Filter out already-linked commits
        unlinked_commits = [c for c in commits if c['sha'] not in already_linked]

        if not unlinked_commits:
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL SUGGEST-LINKS", "All Linked")
            template.section("STATUS", f"{symbols.check_pass} All recent commits already have decision links.")
            template.footer("No action needed")
            output = template.render(command="suggest-links", context={"all_linked": True})
            print(output)
            return

        # Get all decisions for matching
        decisions = self._get_linkable_decisions()

        if not decisions:
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL SUGGEST-LINKS", "No Decisions")
            template.section("STATUS", "No decisions found to suggest links for.")
            template.section("ACTION", "Capture decisions with: babel capture \"decision\" --batch")
            template.footer("Capture decisions first, then run suggest-links")
            output = template.render(command="suggest-links", context={"no_decisions": True})
            print(output)
            return

        # Find suggestions
        all_suggestions = []
        for commit in unlinked_commits:
            suggestions = self._find_matches(commit, decisions, min_score if not show_all else 0.1)
            all_suggestions.extend(suggestions)

        if not all_suggestions:
            template = OutputTemplate(symbols=symbols)
            template.header("BABEL SUGGEST-LINKS", "No Matches")
            template.section("ANALYSIS", f"Analyzed {len(unlinked_commits)} unlinked commit(s), no strong matches found.")
            template.section("REASONS", "- Commits are routine (no decision needed)\n- Decisions haven't been captured yet")
            template.section("ACTION", "To link manually: babel link <decision_id> --to-commit <sha>")
            template.footer("No suggestions above threshold")
            output = template.render(command="suggest-links", context={"no_matches": True})
            print(output)
            return

        # Group by commit
        by_commit: Dict[str, List[LinkSuggestion]] = {}
        for s in all_suggestions:
            if s.commit_sha not in by_commit:
                by_commit[s.commit_sha] = []
            by_commit[s.commit_sha].append(s)

        # Build suggestions output with OutputTemplate
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL SUGGEST-LINKS", f"Analyzed {len(unlinked_commits)} Unlinked Commits")
        template.legend({
            "[###]": "high confidence (≥70%)",
            "[## ]": "medium confidence (≥50%)",
            "[#  ]": "low confidence (≥30%)"
        })

        # Build suggestions section
        suggestion_lines = []
        for commit_sha_key, suggestions in by_commit.items():
            # Sort by score descending
            suggestions.sort(key=lambda x: x.score, reverse=True)

            commit_msg = generate_summary(suggestions[0].commit_message)
            # P12: Time always shown for commit
            commit_time = format_timestamp(suggestions[0].commit_date) if suggestions[0].commit_date else ''
            commit_time_str = f" ({commit_time})" if commit_time else ""
            suggestion_lines.append(f"Commit [{commit_sha_key[:8]}]: \"{commit_msg}\"{commit_time_str}")

            for s in suggestions[:3]:  # Top 3 per commit
                score_bar = self._score_bar(s.score)
                decision_alias = self._cli.codec.encode(s.decision_id)
                # P12: Time always shown for decision
                decision_time = format_timestamp(s.decision_created_at) if s.decision_created_at else ''
                decision_time_str = f" ({decision_time})" if decision_time else ""
                suggestion_lines.append(f"  {score_bar} [{decision_alias}] {s.decision_type}: {generate_summary(s.decision_summary)}{decision_time_str}")

                # Show reasons for high-confidence matches
                if s.score >= 0.5 and s.reasons:
                    suggestion_lines.append(f"       Reasons: {', '.join(s.reasons[:2])}")

            suggestion_lines.append("")

        template.section("SUGGESTIONS", "\n".join(suggestion_lines))

        # Strongest match section
        total_suggestions = len(all_suggestions)
        if all_suggestions:
            best = max(all_suggestions, key=lambda x: x.score)
            best_alias = self._cli.codec.encode(best.decision_id)
            template.section("STRONGEST MATCH", f"babel link {best_alias} --to-commit {best.commit_sha[:8]}")

        # Actions section
        template.section("ACTIONS", "To link: babel link <decision_id> --to-commit <commit_sha>")

        template.footer(f"Found {total_suggestions} suggestion(s) across {len(by_commit)} commit(s)")
        output = template.render(command="suggest-links", context={"suggestions": total_suggestions})
        print(output)

    def _get_recent_commits(self, git: GitIntegration, count: int) -> List[Dict]:
        """Get recent commits with their info."""
        commits = []

        # Use git log to get recent commits (P12: include date)
        output = git._run_git([
            "log", f"-{count}", "--format=%H|%aI|%s", "--no-merges"
        ])

        if not output:
            return []

        for line in output.strip().split('\n'):
            if '|' not in line:
                continue
            parts = line.split('|', 2)
            if len(parts) < 3:
                continue
            sha, date, message = parts
            commits.append({
                'sha': sha,
                'date': date,  # P12: Temporal attribution
                'message': message
            })

        return commits

    def _get_specific_commit(self, git: GitIntegration, commit_sha: str) -> List[Dict]:
        """Get a specific commit."""
        commit_info = git.get_commit(commit_sha, include_diff=False)
        if not commit_info:
            return []

        return [{
            'sha': commit_info.hash,
            'date': commit_info.date if hasattr(commit_info, 'date') else '',  # P12: Temporal attribution
            'message': commit_info.message
        }]

    def _get_linkable_decisions(self) -> List[Dict]:
        """Get all decisions that could be linked."""
        decisions = []

        for node_type in ['decision', 'constraint', 'principle', 'proposal']:
            nodes = self.graph.get_nodes_by_type(node_type)
            for node in nodes:
                summary = node.content.get('summary', str(node.content)[:100])
                alias = self._cli.codec.encode(node.id)

                decisions.append({
                    'id': node.event_id or node.id,
                    'short_id': alias,
                    'type': node_type,
                    'summary': summary,
                    'domain': node.content.get('domain', ''),
                    'created_at': node.created_at,  # P12: Temporal attribution
                    'node': node
                })

        return decisions

    def _find_matches(self, commit: Dict, decisions: List[Dict],
                      min_score: float) -> List[LinkSuggestion]:
        """Find matching decisions for a commit."""
        suggestions = []

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
                    reasons=reasons,
                    commit_date=commit.get('date', ''),  # P12: Temporal attribution
                    decision_created_at=decision.get('created_at', '')  # P12: Temporal attribution
                ))

        return suggestions

    def _calculate_match_score(self, commit: Dict, decision: Dict) -> tuple:
        """
        Calculate match score between commit and decision.

        Uses rapidfuzz for 10-100x faster matching than word overlap.
        Returns (score, reasons) tuple.
        """
        score = 0.0
        reasons = []

        commit_msg = commit['message']
        decision_summary = decision['summary']

        # Text similarity using rapidfuzz (main signal)
        # token_set_ratio handles word order differences
        similarity = fuzz.token_set_ratio(commit_msg.lower(), decision_summary.lower()) / 100.0

        if similarity > 0.3:
            # Scale similarity to max 0.6 (same as old word overlap cap)
            text_score = min(similarity * 0.6, 0.6)
            score += text_score
            reasons.append(f"text similarity: {similarity:.0%}")

        # Domain match (if commit mentions domain)
        domain = decision.get('domain', '').lower()
        if domain and domain in commit_msg.lower():
            score += 0.2
            reasons.append(f"domain match: {domain}")

        # Type-specific boosts
        decision_type = decision['type']
        commit_msg_lower = commit_msg.lower()

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


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

COMMAND_NAME = 'suggest-links'


def register_parser(subparsers):
    """Register suggest-links command parser."""
    p = subparsers.add_parser('suggest-links',
                              help='Suggest decision-to-commit links (AI-assisted)')
    p.add_argument('--from-recent', dest='from_recent', type=int, default=5,
                   help='Number of recent commits to analyze (default: 5)')
    p.add_argument('--commit', help='Analyze a specific commit instead of recent')
    p.add_argument('--min-score', dest='min_score', type=float, default=0.3,
                   help='Minimum confidence score (0-1, default: 0.3)')
    p.add_argument('--all', action='store_true',
                   help='Show all suggestions, even low-confidence')
    return p


def handle(cli, args):
    """Handle suggest-links command dispatch."""
    cli._suggest_links_cmd.suggest_links(
        from_recent=args.from_recent,
        commit_sha=args.commit,
        min_score=args.min_score,
        show_all=getattr(args, 'all', False)
    )
