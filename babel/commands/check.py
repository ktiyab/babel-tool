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
from ..presentation.template import OutputTemplate


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

        # Collect results for structured output
        passed = []
        issues = []
        warnings = []
        repairs = []

        # Check 1: .babel directory exists
        if not self.babel_dir.exists():
            issues.append(("CRITICAL", ".babel/ directory missing",
                          "Run 'babel init' or 'git checkout .babel/'"))
        else:
            passed.append(".babel/ directory exists")

        # Check 2: Shared events file
        shared_path = self.babel_dir / "shared" / "events.jsonl"
        if not shared_path.exists():
            if (self.babel_dir / "shared").exists():
                warnings.append(("WARNING", "No shared events yet",
                               "This is normal for new projects"))
            else:
                issues.append(("ERROR", ".babel/shared/ missing",
                              "Run 'git checkout .babel/shared/' or 'babel init'"))
        else:
            try:
                shared_events = self.events.read_shared()
                passed.append(f"Shared events: {len(shared_events)} events")
            except Exception as e:
                issues.append(("ERROR", f"Shared events corrupted: {e}",
                              "Restore from git: 'git checkout .babel/shared/events.jsonl'"))

        # Check 3: Local events file (optional)
        local_path = self.babel_dir / "local" / "events.jsonl"
        if local_path.exists():
            try:
                local_events = self.events.read_local()
                passed.append(f"Local events: {len(local_events)} events")
            except Exception as e:
                issues.append(("WARNING", f"Local events corrupted: {e}",
                              "Delete and start fresh: 'rm .babel/local/events.jsonl'"))
        else:
            passed.append("No local events (normal)")

        # Check 4: Graph integrity
        try:
            stats = self.graph.stats()
            passed.append(f"Graph: {stats['nodes']} nodes, {stats['edges']} edges")
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
                active_config, is_local = self.config.llm.get_active_config()
                mode = "local" if is_local else "remote"
                passed.append(f"Config: {active_config.provider} ({active_config.effective_model}) [{mode}]")
        except Exception as e:
            warnings.append(("WARNING", f"Config issue: {e}",
                           "Run 'babel config' to review"))

        # Check 6: Purpose exists (P1)
        purposes = self.graph.get_nodes_by_type('purpose')
        if not purposes:
            warnings.append(("WARNING", "No purpose defined",
                           "Run 'babel init \"purpose\"' to set project purpose"))
        else:
            passed.append(f"Purpose defined: {len(purposes)} purpose(s)")

        # Check 7: Git status
        git = GitIntegration(self.project_dir)
        if git.is_git_repo:
            passed.append("Git repository detected")

            # Check 8: Gitignore protects local data
            gitignore_path = self.babel_dir / ".gitignore"
            if gitignore_path.exists():
                content = gitignore_path.read_text()
                if "local/" in content:
                    passed.append("Local data protected (.gitignore)")
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
                    passed.append("Local data not tracked in git")
            except Exception:
                pass  # Git check failed, not critical
        else:
            warnings.append(("WARNING", "Not a git repository",
                           "Team sync requires git. Run 'git init'"))

        # Handle repairs if requested
        if repair and (issues or warnings):
            # Try to rebuild graph if needed
            for severity, issue, fix in issues + warnings:
                if "Graph" in issue or "rebuild" in fix.lower():
                    try:
                        self._cli._rebuild_graph()
                        repairs.append(f"{symbols.check_pass} Rebuilt graph from events")
                    except Exception as e:
                        repairs.append(f"{symbols.check_fail} Could not rebuild graph: {e}")

            # Fix gitignore if needed
            for severity, issue, fix in issues:
                if ".gitignore" in issue or "Local data" in issue:
                    try:
                        self.events._ensure_gitignore()
                        repairs.append(f"{symbols.check_pass} Fixed .babel/.gitignore (local data now protected)")
                    except Exception as e:
                        repairs.append(f"{symbols.check_fail} Could not fix .gitignore: {e}")

        # Build output with OutputTemplate
        template = OutputTemplate(symbols=symbols)
        template.header("BABEL CHECK", "Project Integrity Verification (P11)")
        template.legend({
            symbols.check_pass: "passed",
            symbols.check_fail: "issue",
            symbols.check_warn: "warning"
        })

        # CHECKS section - passed items
        if passed:
            check_lines = [f"{symbols.check_pass} {item}" for item in passed]
            template.section("CHECKS PASSED", "\n".join(check_lines))

        # ISSUES section
        if issues:
            issue_lines = []
            for severity, issue, fix in issues:
                issue_lines.append(f"{symbols.check_fail} [{severity}] {issue}")
                issue_lines.append(f"    Fix: {fix}")
            template.section(f"ISSUES ({len(issues)})", "\n".join(issue_lines))

        # WARNINGS section
        if warnings:
            warning_lines = []
            for severity, warning, fix in warnings:
                warning_lines.append(f"{symbols.check_warn} [{severity}] {warning}")
                warning_lines.append(f"    Fix: {fix}")
            template.section(f"WARNINGS ({len(warnings)})", "\n".join(warning_lines))

        # REPAIRS section
        if repairs:
            template.section("REPAIRS", "\n".join(repairs))
            if any(symbols.check_pass in r for r in repairs):
                template.section("ACTION", "Run 'babel check' again to verify repairs")

        # Footer with health status
        if not issues and not warnings:
            template.footer(f"{symbols.check_pass} All checks passed. Project is healthy.")
        elif not issues:
            template.footer(f"{symbols.check_pass} No critical issues. Project is functional.")
        elif repair:
            repaired_count = sum(1 for r in repairs if symbols.check_pass in r)
            template.footer(f"Repaired {repaired_count} issue(s). Verify with: babel check")
        else:
            template.footer("Tip: Run 'babel check --repair' to attempt automatic fixes.")

        output = template.render(command="check", context={
            "has_issues": len(issues) > 0,
            "has_warnings": len(warnings) > 0
        })
        print(output)


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
