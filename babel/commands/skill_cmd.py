"""
Skill Command — Export Babel skills to platform-specific formats

Following modular command pattern, delegates to services/skills.py.

Commands:
    babel skill                     Show skill status
    babel skill export [--target X] Export skills to platform
    babel skill export --all        Export to all active platforms
    babel skill sync                Re-export to previously exported platforms
    babel skill list                List available skills
"""

from pathlib import Path
from typing import List, Optional

from ..services.skills import (
    SkillTarget,
    export_skills,
    sync_skills,
    remove_skills,
    get_skills_status,
    format_skills_status,
    detect_active_platforms,
    SKILL_TARGET_PATHS,
)
from ..skills import (
    load_all_skills,
    load_protocols,
    SkillCategory,
)


class SkillCommand:
    """Handler for babel skill command."""

    def __init__(self, cli):
        self.cli = cli
        self.project_dir = cli.project_dir

    def status(self):
        """Show skill export status across platforms."""
        status = get_skills_status(self.project_dir)
        output = format_skills_status(status)
        print(output)

    def export(self, target: str = None, force: bool = False):
        """
        Export skills to specified target or auto-detect.

        Args:
            target: Platform target (claude-code, cursor, codex, generic, all)
            force: Overwrite existing files
        """
        # Parse target
        if target == "all":
            skill_target = SkillTarget.ALL
        elif target:
            try:
                skill_target = SkillTarget(target)
            except ValueError:
                print(f"Unknown target: {target}")
                print(f"Valid targets: {', '.join(t.value for t in SkillTarget)}")
                return
        else:
            # Auto-detect
            active = detect_active_platforms(self.project_dir)
            if len(active) == 1:
                skill_target = active[0]
                print(f"Auto-detected platform: {skill_target.value}")
            else:
                print(f"Multiple platforms detected: {', '.join(t.value for t in active)}")
                print("Use --target to specify, or --all to export to all.")
                return

        # Export
        result = export_skills(self.project_dir, skill_target, force=force)

        if result.success:
            print(f"\n✓ {result.message}")
            if result.files_created:
                print(f"\nFiles created: {len(result.files_created)}")
                for f in result.files_created[:5]:  # Show first 5
                    print(f"  - {f.relative_to(self.project_dir)}")
                if len(result.files_created) > 5:
                    print(f"  ... and {len(result.files_created) - 5} more")
        else:
            print(f"\n✗ Export failed: {result.message}")

    def sync(self, force: bool = False):
        """Re-export skills to all previously exported platforms."""
        result = sync_skills(self.project_dir, force=force)

        if result.success:
            print(f"\n✓ Sync complete:\n{result.message}")
        else:
            print(f"\n✗ {result.message}")

    def remove(self, target: str = None, force: bool = False):
        """
        Remove exported skills from specified platform(s).

        Args:
            target: Platform target (claude-code, cursor, codex, generic, all)
            force: Required for --all to prevent accidental mass removal
        """
        # Parse target
        if target == "all":
            skill_target = SkillTarget.ALL
        elif target:
            try:
                skill_target = SkillTarget(target)
            except ValueError:
                print(f"Unknown target: {target}")
                print(f"Valid targets: {', '.join(t.value for t in SkillTarget if t != SkillTarget.ALL)}")
                return
        else:
            # Auto-detect from manifest
            from ..services.skills import load_manifest
            manifest = load_manifest(self.project_dir)
            exported = list(manifest.exports.keys())

            if len(exported) == 0:
                print("No platforms exported. See: babel skill status")
                return
            elif len(exported) == 1:
                skill_target = SkillTarget(exported[0])
                print(f"Auto-detected platform: {skill_target.value}")
            else:
                print(f"Multiple platforms exported: {', '.join(exported)}")
                print("Use --target to specify, or --all --force to remove all.")
                return

        # Remove
        result = remove_skills(self.project_dir, skill_target, force=force)

        if result.success:
            print(f"\n✓ {result.message}")
        else:
            print(f"\n✗ {result.message}")

    def list_skills(self, category: str = None):
        """List available skills."""
        all_skills = load_all_skills()
        protocols = load_protocols()

        if category:
            try:
                cat = SkillCategory(category)
                skills = all_skills.get(cat, [])
                if not skills:
                    print(f"No skills in category: {category}")
                    return
                print(f"\n# {category.title()} Skills\n")
                for skill in skills:
                    print(f"/{skill.name}")
                    print(f"  {skill.description}")
                    print(f"  Trigger: {skill.trigger}")
                    print()
            except ValueError:
                print(f"Unknown category: {category}")
                print(f"Valid categories: {', '.join(c.value for c in SkillCategory if c != SkillCategory.PROTOCOL)}")
                return
        else:
            # Show all categories
            print("\n# Babel Skills\n")

            total_skills = 0
            for cat in SkillCategory:
                if cat == SkillCategory.PROTOCOL:
                    continue
                skills = all_skills.get(cat, [])
                if skills:
                    print(f"## {cat.value.title()} ({len(skills)} skills)")
                    for skill in skills:
                        print(f"  /{skill.name}: {skill.description[:50]}...")
                    print()
                    total_skills += len(skills)

            print(f"## Protocols ({len(protocols)})")
            for proto in protocols:
                print(f"  {proto.name}: {proto.rule[:50]}...")
            print()

            print(f"\nTotal: {total_skills} skills, {len(protocols)} protocols")
            print("\nUse 'babel skill list <category>' for details.")

    def help(self):
        """Show skill command help."""
        print("""
Babel Skill — Export skills to platform-specific formats

Commands:
    babel skill                     Show skill export status
    babel skill export              Export skills (auto-detect platform)
    babel skill export --target X   Export to specific platform
    babel skill export --all        Export to all active platforms
    babel skill sync                Re-export to previously exported platforms
    babel skill remove              Remove skills (auto-detect platform)
    babel skill remove --target X   Remove from specific platform
    babel skill remove --all --force  Remove from all platforms
    babel skill list                List available skills
    babel skill list <category>     List skills in category

Targets:
    claude-code    .claude/skills/babel/
    cursor         .cursor/skills/babel/
    codex          .codex/skills/babel/
    generic        .babel/skills_reference.md (monolithic fallback)
    all            All platforms (export: detected, remove: exported)

Examples:
    babel skill export --target claude-code
    babel skill export --all --force
    babel skill sync
    babel skill remove --target claude-code
    babel skill remove --all --force
    babel skill list lifecycle
""")


# =============================================================================
# Command Registration (Self-Registration Pattern)
# =============================================================================

COMMAND_NAME = 'skill'


def register_parser(subparsers):
    """Register skill command parser with subcommands."""
    skill_parser = subparsers.add_parser('skill', help='Export skills to AI coding platforms')
    skill_sub = skill_parser.add_subparsers(dest='skill_command')

    # skill export
    export_parser = skill_sub.add_parser('export', help='Export skills to platform')
    export_parser.add_argument('--target', '-t',
                               choices=['claude-code', 'cursor', 'codex', 'generic', 'all'],
                               help='Target platform (default: auto-detect)')
    export_parser.add_argument('--force', '-f', action='store_true',
                               help='Overwrite existing files')
    export_parser.add_argument('--all', action='store_true',
                               help='Export to all active platforms')

    # skill sync
    sync_parser = skill_sub.add_parser('sync', help='Re-export to previously exported platforms')
    sync_parser.add_argument('--force', '-f', action='store_true',
                             help='Overwrite existing files')

    # skill remove
    remove_parser = skill_sub.add_parser('remove', help='Remove exported skills from platform')
    remove_parser.add_argument('--target', '-t',
                               choices=['claude-code', 'cursor', 'codex', 'generic', 'all'],
                               help='Target platform (default: auto-detect)')
    remove_parser.add_argument('--force', '-f', action='store_true',
                               help='Required for --all to prevent accidental removal')
    remove_parser.add_argument('--all', action='store_true',
                               help='Remove from all exported platforms (requires --force)')

    # skill list
    list_parser = skill_sub.add_parser('list', help='List available skills')
    list_parser.add_argument('category', nargs='?',
                             help='Category to list (lifecycle, knowledge, validation, maintenance, preference, analyze)')

    # skill status
    skill_sub.add_parser('status', help='Show skill export status')

    return skill_parser


def handle(cli, args):
    """Handle skill command dispatch."""
    if args.skill_command == 'export':
        target = getattr(args, 'target', None)
        if getattr(args, 'all', False):
            target = 'all'
        cli._skill_cmd.export(target=target, force=getattr(args, 'force', False))
    elif args.skill_command == 'sync':
        cli._skill_cmd.sync(force=getattr(args, 'force', False))
    elif args.skill_command == 'remove':
        target = getattr(args, 'target', None)
        if getattr(args, 'all', False):
            target = 'all'
        cli._skill_cmd.remove(target=target, force=getattr(args, 'force', False))
    elif args.skill_command == 'list':
        cli._skill_cmd.list_skills(category=getattr(args, 'category', None))
    elif args.skill_command == 'status':
        cli._skill_cmd.status()
    else:
        # No subcommand - show status by default
        cli._skill_cmd.status()
