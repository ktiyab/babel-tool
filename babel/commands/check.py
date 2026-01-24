"""
CheckCommand — Project integrity verification and repair

Handles project health checking (P11 compliance):
- Events file validation
- Graph integrity
- Configuration validity
- Git protection verification
"""

import subprocess

from ..commands.base import BaseCommand
from ..services.git import GitIntegration


class CheckCommand(BaseCommand):
    """
    Command for project integrity verification.

    P11: Framework Self-Application — the framework must govern itself.
    Verifies that Babel's own data structures are healthy.
    """

    def check(self, repair: bool = False):
        """
        Verify project integrity and suggest recovery (P11 compliance).

        Checks:
        - Events file exists and is valid
        - Graph can be rebuilt from events
        - Required directories exist
        - Configuration is valid

        Args:
            repair: Attempt automatic repair of issues
        """
        symbols = self.symbols

        print("\nBabel Integrity Check")
        print("=" * 40)

        issues = []
        warnings = []

        # Check 1: .babel directory exists
        if not self.babel_dir.exists():
            issues.append(("CRITICAL", ".babel/ directory missing",
                          "Run 'babel init' or 'git checkout .babel/'"))
        else:
            print(f"{symbols.check_pass} .babel/ directory exists")

        # Check 2: Shared events file
        shared_path = self.babel_dir / "shared" / "events.jsonl"
        if not shared_path.exists():
            if (self.babel_dir / "shared").exists():
                warnings.append(("WARNING", "No shared events yet",
                               "This is normal for new projects"))
                print(f"{symbols.local} No shared events (normal for new projects)")
            else:
                issues.append(("ERROR", ".babel/shared/ missing",
                              "Run 'git checkout .babel/shared/' or 'babel init'"))
        else:
            try:
                shared_events = self.events.read_shared()
                print(f"{symbols.check_pass} Shared events: {len(shared_events)} events")
            except Exception as e:
                issues.append(("ERROR", f"Shared events corrupted: {e}",
                              "Restore from git: 'git checkout .babel/shared/events.jsonl'"))

        # Check 3: Local events file (optional)
        local_path = self.babel_dir / "local" / "events.jsonl"
        if local_path.exists():
            try:
                local_events = self.events.read_local()
                print(f"{symbols.check_pass} Local events: {len(local_events)} events")
            except Exception as e:
                issues.append(("WARNING", f"Local events corrupted: {e}",
                              "Delete and start fresh: 'rm .babel/local/events.jsonl'"))
        else:
            print(f"{symbols.local} No local events (normal)")

        # Check 4: Graph integrity
        try:
            stats = self.graph.stats()
            print(f"{symbols.check_pass} Graph: {stats['nodes']} nodes, {stats['edges']} edges")
        except Exception as e:
            warnings.append(("WARNING", f"Graph issue: {e}",
                           "Run 'babel sync' to rebuild"))

        # Check 5: Config validity
        try:
            error = self.config.llm.validate()
            if error:
                warnings.append(("WARNING", f"Config: {error}",
                               "Run 'babel config' to review"))
            else:
                print(f"{symbols.check_pass} Config: {self.config.llm.provider} ({self.config.llm.effective_model})")
        except Exception as e:
            warnings.append(("WARNING", f"Config issue: {e}",
                           "Run 'babel config' to review"))

        # Check 6: Purpose exists (P1)
        purposes = self.graph.get_nodes_by_type('purpose')
        if not purposes:
            warnings.append(("WARNING", "No purpose defined",
                           "Run 'babel init \"purpose\"' to set project purpose"))
        else:
            print(f"{symbols.check_pass} Purpose defined: {len(purposes)} purpose(s)")

        # Check 7: Git status
        git = GitIntegration(self.project_dir)
        if git.is_git_repo:
            print(f"{symbols.check_pass} Git repository detected")

            # Check 8: Gitignore protects local data
            gitignore_path = self.babel_dir / ".gitignore"
            if gitignore_path.exists():
                content = gitignore_path.read_text()
                if "local/" in content:
                    print(f"{symbols.check_pass} Local data protected (.gitignore)")
                else:
                    issues.append(("ERROR", "Local data NOT protected in .gitignore",
                                 "Add 'local/' to .babel/.gitignore or run with --repair"))
            else:
                issues.append(("ERROR", ".babel/.gitignore missing",
                             "Local data may be committed! Run with --repair"))

            # Check 9: Verify local/ is not tracked
            try:
                result = subprocess.run(
                    ["git", "ls-files", ".babel/local/"],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    issues.append(("CRITICAL", "Local events ARE tracked in git!",
                                 "Run: git rm --cached .babel/local/ && git commit"))
                else:
                    print(f"{symbols.check_pass} Local data not tracked in git")
            except Exception:
                pass  # Git check failed, not critical
        else:
            warnings.append(("WARNING", "Not a git repository",
                           "Team sync requires git. Run 'git init'"))

        # Summary
        print("\n" + "-" * 40)

        if issues:
            print(f"\n{symbols.check_fail} {len(issues)} issue(s) found:\n")
            for severity, issue, fix in issues:
                print(f"  [{severity}] {issue}")
                print(f"    Fix: {fix}\n")

        if warnings:
            print(f"\n{symbols.check_warn} {len(warnings)} warning(s):\n")
            for severity, warning, fix in warnings:
                print(f"  [{severity}] {warning}")
                print(f"    Fix: {fix}\n")

        if not issues and not warnings:
            print(f"\n{symbols.check_pass} All checks passed. Project is healthy.")
        elif not issues:
            print(f"\n{symbols.check_pass} No critical issues. Project is functional.")

        # Repair suggestions
        if repair and (issues or warnings):
            print("\nAttempting repairs...")
            repaired = 0

            # Try to rebuild graph if needed
            for severity, issue, fix in issues + warnings:
                if "Graph" in issue or "rebuild" in fix.lower():
                    try:
                        self._cli._rebuild_graph()
                        print(f"  {symbols.check_pass} Rebuilt graph from events")
                        repaired += 1
                    except Exception as e:
                        print(f"  {symbols.check_fail} Could not rebuild graph: {e}")

            # Fix gitignore if needed
            for severity, issue, fix in issues:
                if ".gitignore" in issue or "Local data" in issue:
                    try:
                        self.events._ensure_gitignore()
                        print(f"  {symbols.check_pass} Fixed .babel/.gitignore (local data now protected)")
                        repaired += 1
                    except Exception as e:
                        print(f"  {symbols.check_fail} Could not fix .gitignore: {e}")

            if repaired > 0:
                print(f"\nRepaired {repaired} issue(s). Run 'babel check' again to verify.")
            else:
                print("\nNo automatic repairs available. See manual fixes above.")
        elif issues or warnings:
            print("\nTip: Run 'babel check --repair' to attempt automatic fixes.")

        # Succession hint (centralized)
        from ..output import end_command
        end_command("check", {"has_issues": len(issues) > 0, "has_warnings": len(warnings) > 0})


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

def register_parser(subparsers):
    """Register check command parser."""
    p = subparsers.add_parser('check', help='Verify project integrity and suggest recovery')
    p.add_argument('--repair', action='store_true',
                   help='Attempt automatic repair of issues')
    return p


def handle(cli, args):
    """Handle check command dispatch."""
    cli._check_cmd.check(repair=args.repair)
