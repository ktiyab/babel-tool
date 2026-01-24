"""
Skill Export Service — Export Babel skills to platform-specific formats

Following the IDE abstraction pattern from services/ide.py, this service
enables Babel skills to be exported to:
- Claude Code skills (.claude/skills/babel/SKILL.md)
- Cursor skills (.cursor/skills/)
- Codex skills
- Generic fallback (monolithic prompt)

Principles:
- P6 (Token Efficiency): Progressive disclosure via modular skills
- P7 (Reasoning Travels): Portable format across platforms
- HC3 (Offline-First): Filesystem-based, no network required
"""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field

from ..skills import (
    Skill,
    Protocol,
    SkillCategory,
    load_all_skills,
    load_protocols,
    get_always_load_skills,
    get_skills_dir,
)
from ..config import update_env_file


class SkillTarget(Enum):
    """Target platforms for skill export."""
    CLAUDE_CODE = "claude-code"  # .claude/skills/babel/SKILL.md
    CURSOR = "cursor"            # .cursor/skills/babel/
    CODEX = "codex"              # .codex/skills/babel/
    GENERIC = "generic"          # Fallback to monolithic prompt
    ALL = "all"                  # Export to all supported platforms


# Platforms that support Agent Skills standard (excludes GENERIC and ALL)
SKILL_PLATFORMS = [SkillTarget.CLAUDE_CODE, SkillTarget.CURSOR, SkillTarget.CODEX]

# Mapping of targets to their skill directory paths (relative to project root)
SKILL_TARGET_PATHS = {
    SkillTarget.CLAUDE_CODE: Path(".claude") / "skills" / "babel",
    SkillTarget.CURSOR: Path(".cursor") / "skills" / "babel",
    SkillTarget.CODEX: Path(".codex") / "skills" / "babel",
    SkillTarget.GENERIC: Path(".babel") / "skills_reference.md",
}

# Directory markers that indicate platform is in use
PLATFORM_MARKERS = {
    SkillTarget.CLAUDE_CODE: ".claude",
    SkillTarget.CURSOR: ".cursor",
    SkillTarget.CODEX: ".codex",
}


@dataclass
class SkillExportResult:
    """Result of a skill export operation."""
    success: bool
    message: str
    files_created: List[Path]
    target: SkillTarget


@dataclass
class SkillRemoveResult:
    """Result of a skill removal operation."""
    success: bool
    message: str
    files_deleted: int
    target: SkillTarget


@dataclass
class ExportRecord:
    """Record of a single platform export."""
    path: str
    last_export: str
    skills_count: int
    protocols_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "last_export": self.last_export,
            "skills_count": self.skills_count,
            "protocols_count": self.protocols_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExportRecord':
        return cls(
            path=data["path"],
            last_export=data["last_export"],
            skills_count=data.get("skills_count", 0),
            protocols_count=data.get("protocols_count", 0),
        )


@dataclass
class SkillsManifest:
    """Tracks skill exports across platforms for sync and drift detection."""
    source_version: str
    exports: Dict[str, ExportRecord] = field(default_factory=dict)
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_version": self.source_version,
            "exports": {k: v.to_dict() for k, v in self.exports.items()},
            "checksum": self.checksum,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillsManifest':
        exports = {}
        for k, v in data.get("exports", {}).items():
            exports[k] = ExportRecord.from_dict(v)
        return cls(
            source_version=data.get("source_version", ""),
            exports=exports,
            checksum=data.get("checksum", ""),
        )

    def is_outdated(self, platform: str) -> bool:
        """Check if platform export is outdated vs source."""
        if platform not in self.exports:
            return True
        return self.exports[platform].last_export < self.source_version

    def get_outdated_platforms(self) -> List[str]:
        """Get list of platforms needing sync."""
        return [p for p in self.exports if self.is_outdated(p)]

    def get_exported_platforms(self) -> List[str]:
        """Get list of platforms that have been exported."""
        return list(self.exports.keys())


# =============================================================================
# Format Converters
# =============================================================================

def skill_to_claude_code_md(skill: Skill, full_instructions: str = None) -> str:
    """
    Convert a Skill to Claude Code SKILL.md format.

    Claude Code skills use YAML frontmatter + markdown body.
    Reference: https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/skills
    """
    lines = ["---"]

    # YAML frontmatter
    lines.append(f"name: {skill.name}")
    lines.append(f"description: {skill.description}")

    if skill.trigger:
        lines.append(f"trigger: {skill.trigger}")

    if not skill.user_invocable:
        lines.append("user_invocable: false")

    if skill.disable_model_invocation:
        lines.append("disable_model_invocation: true")

    # allowed_tools for Claude Code (restricts tool access when skill active)
    allowed_tools = getattr(skill, 'allowed_tools', [])
    if allowed_tools:
        lines.append(f"allowed_tools: {', '.join(allowed_tools)}")

    lines.append("---")
    lines.append("")

    # Markdown body with instructions
    lines.append(f"# {skill.name.replace('-', ' ').title()}")
    lines.append("")

    if skill.description:
        lines.append(skill.description)
        lines.append("")

    # Command sequence
    if skill.commands:
        lines.append("## Command Sequence")
        lines.append("")
        lines.append("Execute these commands in order:")
        lines.append("")
        lines.append("```bash")
        for cmd in skill.commands:
            lines.append(cmd)
        lines.append("```")
        lines.append("")

    # Context consumed
    if skill.uses_context:
        lines.append("## Context Used")
        lines.append("")
        for ctx in skill.uses_context:
            lines.append(f"- {ctx}")
        lines.append("")

    # What it produces
    if skill.produces:
        lines.append("## Produces")
        lines.append("")
        for prod in skill.produces:
            lines.append(f"- {prod}")
        lines.append("")

    # Related principles
    if skill.principles:
        lines.append("## Principles")
        lines.append("")
        for principle in skill.principles:
            lines.append(f"- {principle}")
        lines.append("")

    # Composability
    if skill.composable_with:
        lines.append("## Composes With")
        lines.append("")
        for other in skill.composable_with:
            lines.append(f"- /{other}")
        lines.append("")

    # Extended examples (multiline content preserved as-is)
    examples = getattr(skill, 'examples', [])
    if examples:
        for example in examples:
            # Multiline examples are complete sections - preserve as-is
            if '\n' in example:
                lines.append(example)
                lines.append("")
            else:
                # Single-line examples use list format
                lines.append(f"- {example}")
        lines.append("")

    # Full instructions if provided (legacy parameter)
    if full_instructions:
        lines.append("## Detailed Instructions")
        lines.append("")
        lines.append(full_instructions)

    return "\n".join(lines)


def protocol_to_md(protocol: Protocol) -> str:
    """
    Convert a Protocol to markdown format with YAML frontmatter.

    Follows Claude Code SKILL.md format for platform compatibility.
    Multiline examples are preserved as-is (they contain their own formatting).
    """
    lines = ["---"]

    # YAML frontmatter
    lines.append(f"name: {protocol.name.lower()}")
    lines.append(f"description: {protocol.description}")

    if not getattr(protocol, 'user_invocable', True):
        lines.append("user_invocable: false")

    lines.append("---")
    lines.append("")

    # Markdown body
    lines.append(f"# {protocol.name}")
    lines.append("")
    lines.append(protocol.description)
    lines.append("")
    lines.append("## Rule")
    lines.append("")
    lines.append(protocol.rule)
    lines.append("")

    if protocol.applies_to:
        lines.append("## Applies To")
        lines.append("")
        for context in protocol.applies_to:
            lines.append(f"- {context}")
        lines.append("")

    if protocol.examples:
        lines.append("## Examples")
        lines.append("")
        for example in protocol.examples:
            # Multiline examples (contain newlines) are sections - preserve as-is
            if '\n' in example:
                lines.append(example)
                lines.append("")
            else:
                # Single-line examples use list format
                lines.append(f"- {example}")
        lines.append("")

    return "\n".join(lines)


def skills_to_monolithic_prompt(
    skills: Dict[SkillCategory, List[Skill]],
    protocols: List[Protocol]
) -> str:
    """
    Convert all skills to a single monolithic prompt.

    This is the fallback for platforms that don't support skills.
    """
    lines = ["# Babel Skills Reference"]
    lines.append("")
    lines.append("This document contains all Babel skills organized by category.")
    lines.append("")

    # Skills by category
    for category in SkillCategory:
        if category == SkillCategory.PROTOCOL:
            continue

        category_skills = skills.get(category, [])
        if not category_skills:
            continue

        lines.append(f"## {category.value.title()} Skills")
        lines.append("")

        for skill in category_skills:
            lines.append(f"### {skill.name}")
            lines.append("")
            lines.append(f"**Trigger:** {skill.trigger}")
            lines.append("")
            lines.append(skill.description)
            lines.append("")

            if skill.commands:
                lines.append("**Commands:**")
                lines.append("```bash")
                for cmd in skill.commands:
                    lines.append(cmd)
                lines.append("```")
                lines.append("")

    # Protocols section
    if protocols:
        lines.append("## Protocols (Cross-Cutting Behaviors)")
        lines.append("")

        for protocol in protocols:
            lines.append(f"### {protocol.name}")
            lines.append("")
            lines.append(protocol.description)
            lines.append("")
            lines.append(f"**Rule:** {protocol.rule}")
            lines.append("")

    return "\n".join(lines)


# =============================================================================
# Export Functions
# =============================================================================

def export_skills_claude_code(
    project_dir: Path,
    force: bool = False
) -> SkillExportResult:
    """
    Export all skills to Claude Code format.

    Creates .claude/skills/babel/ directory with:
    - SKILL.md for each skill
    - protocols.md for protocol reference
    """
    target = SkillTarget.CLAUDE_CODE
    skills_dir = project_dir / SKILL_TARGET_PATHS[target]
    files_created = []

    # Create directory structure
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Load all skills
    all_skills = load_all_skills()
    protocols = load_protocols()

    # Export each skill
    for category, skills in all_skills.items():
        category_dir = skills_dir / category.value
        category_dir.mkdir(parents=True, exist_ok=True)

        for skill in skills:
            skill_file = category_dir / f"{skill.name}.md"

            if skill_file.exists() and not force:
                continue

            content = skill_to_claude_code_md(skill)
            skill_file.write_text(content, encoding='utf-8')
            files_created.append(skill_file)

    # Export protocols
    if protocols:
        protocols_dir = skills_dir / "protocols"
        protocols_dir.mkdir(parents=True, exist_ok=True)

        for protocol in protocols:
            proto_file = protocols_dir / f"{protocol.name}.md"

            if proto_file.exists() and not force:
                continue

            content = protocol_to_md(protocol)
            proto_file.write_text(content, encoding='utf-8')
            files_created.append(proto_file)

    # Create main SKILL.md that references others
    main_skill = skills_dir / "SKILL.md"
    main_content = _create_main_skill_md(all_skills, protocols)
    main_skill.write_text(main_content, encoding='utf-8')
    files_created.append(main_skill)

    return SkillExportResult(
        success=True,
        message=f"Exported {len(files_created)} skill files to {skills_dir}",
        files_created=files_created,
        target=target
    )


def export_skills_cursor(
    project_dir: Path,
    force: bool = False
) -> SkillExportResult:
    """
    Export skills to Cursor format.

    Cursor uses similar skill structure but different paths.
    """
    target = SkillTarget.CURSOR
    skills_dir = project_dir / SKILL_TARGET_PATHS[target]

    # For now, use same format as Claude Code
    # Cursor skills are compatible
    result = export_skills_claude_code(project_dir, force)

    # Copy to Cursor location
    if result.success:
        skills_dir.mkdir(parents=True, exist_ok=True)
        # Cursor uses same format, just different location
        # The skill files are already created, just note the location

    return SkillExportResult(
        success=result.success,
        message=f"Exported skills to {skills_dir}",
        files_created=result.files_created,
        target=target
    )


def export_skills_generic(project_dir: Path) -> SkillExportResult:
    """
    Export skills as monolithic prompt (fallback).

    For platforms that don't support modular skills.
    """
    all_skills = load_all_skills()
    protocols = load_protocols()

    content = skills_to_monolithic_prompt(all_skills, protocols)

    # Write to .babel/skills_reference.md
    output_path = project_dir / ".babel" / "skills_reference.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding='utf-8')

    return SkillExportResult(
        success=True,
        message=f"Exported monolithic skill reference to {output_path}",
        files_created=[output_path],
        target=SkillTarget.GENERIC
    )


def export_skills(
    project_dir: Path,
    target: SkillTarget,
    force: bool = False
) -> SkillExportResult:
    """
    Export skills to the specified target platform.

    Args:
        project_dir: Project root directory
        target: Target platform (or ALL for multi-platform)
        force: Overwrite existing files

    Returns:
        SkillExportResult with details (for ALL, returns combined result)
    """
    if target == SkillTarget.ALL:
        # Export to all platforms
        return export_all_platforms(project_dir, force)
    elif target == SkillTarget.CLAUDE_CODE:
        result = export_skills_claude_code(project_dir, force)
        _update_manifest(project_dir, target, result)
        return result
    elif target == SkillTarget.CURSOR:
        result = export_skills_cursor(project_dir, force)
        _update_manifest(project_dir, target, result)
        return result
    elif target == SkillTarget.CODEX:
        result = export_skills_codex(project_dir, force)
        _update_manifest(project_dir, target, result)
        return result
    else:
        result = export_skills_generic(project_dir)
        _update_manifest(project_dir, target, result)
        return result


def export_skills_codex(
    project_dir: Path,
    force: bool = False
) -> SkillExportResult:
    """
    Export skills to Codex format.

    Codex uses the Agent Skills standard format.
    """
    target = SkillTarget.CODEX
    skills_dir = project_dir / SKILL_TARGET_PATHS[target]
    return _export_agent_skills_format(project_dir, skills_dir, target, force)


def _export_agent_skills_format(
    project_dir: Path,
    skills_dir: Path,
    target: SkillTarget,
    force: bool = False
) -> SkillExportResult:
    """
    Export skills in Agent Skills standard format.

    Used by Claude Code, Cursor, and Codex.
    """
    files_created = []

    # Create directory structure
    skills_dir.mkdir(parents=True, exist_ok=True)

    # Load all skills
    all_skills = load_all_skills()
    protocols = load_protocols()

    # Export each skill
    for category, skills in all_skills.items():
        category_dir = skills_dir / category.value
        category_dir.mkdir(parents=True, exist_ok=True)

        for skill in skills:
            skill_file = category_dir / f"{skill.name}.md"

            if skill_file.exists() and not force:
                continue

            content = skill_to_claude_code_md(skill)
            skill_file.write_text(content, encoding='utf-8')
            files_created.append(skill_file)

    # Export protocols
    if protocols:
        protocols_dir = skills_dir / "protocols"
        protocols_dir.mkdir(parents=True, exist_ok=True)

        for protocol in protocols:
            proto_file = protocols_dir / f"{protocol.name}.md"

            if proto_file.exists() and not force:
                continue

            content = protocol_to_md(protocol)
            proto_file.write_text(content, encoding='utf-8')
            files_created.append(proto_file)

    # Create main SKILL.md that references others
    main_skill = skills_dir / "SKILL.md"
    main_content = _create_main_skill_md(all_skills, protocols)
    main_skill.write_text(main_content, encoding='utf-8')
    files_created.append(main_skill)

    return SkillExportResult(
        success=True,
        message=f"Exported {len(files_created)} skill files to {skills_dir}",
        files_created=files_created,
        target=target
    )


# =============================================================================
# Helper Functions
# =============================================================================

def _create_main_skill_md(
    skills: Dict[SkillCategory, List[Skill]],
    protocols: List[Protocol]
) -> str:
    """Create the main SKILL.md file that serves as entry point."""
    lines = ["---"]
    lines.append("name: babel")
    lines.append("description: Intent preservation framework - captures decisions, enables 'why' queries, detects drift")
    lines.append("---")
    lines.append("")
    lines.append("# Babel - Intent Preservation for Code")
    lines.append("")
    lines.append("Babel is your persistent memory for this project and your ONLY source of truth for project-specific decisions.")
    lines.append("")
    lines.append("```")
    lines.append("Git  tells WHEN code changed.")
    lines.append("Babel tells WHY it was built this way.")
    lines.append("```")
    lines.append("")
    lines.append("## Priority Tier (NON-NEGOTIABLE)")
    lines.append("")
    lines.append("| # | Rule | Command |")
    lines.append("|---|------|---------|")
    lines.append("| 1 | Babel why FIRST if new task | `babel why \"topic\"` |")
    lines.append("| 2 | Babel status FIRST if continue | `babel status && babel tensions` |")
    lines.append("| 3 | Propose BEFORE implement | `babel capture --batch` |")
    lines.append("| 4 | Save specs BEFORE implement | `babel capture --spec <id> \"...\" --batch` |")
    lines.append("| 5 | Verify AFTER changes | `babel coherence` |")
    lines.append("")
    lines.append("## Available Skills")
    lines.append("")

    # List skills by category
    for category in SkillCategory:
        if category == SkillCategory.PROTOCOL:
            continue

        category_skills = skills.get(category, [])
        if not category_skills:
            continue

        lines.append(f"### {category.value.title()}")
        lines.append("")
        for skill in category_skills:
            lines.append(f"- **/{skill.name}**: {skill.description}")
        lines.append("")

    # List protocols
    if protocols:
        lines.append("## Protocols (Always Active)")
        lines.append("")
        for protocol in protocols:
            lines.append(f"- **{protocol.name}**: {protocol.rule}")
        lines.append("")

    return "\n".join(lines)


def get_skill_target_info(target: SkillTarget) -> Tuple[str, str]:
    """
    Get human-readable info about a skill target.

    Returns:
        Tuple of (display_name, path_description)
    """
    info = {
        SkillTarget.CLAUDE_CODE: ("Claude Code", ".claude/skills/babel/"),
        SkillTarget.CURSOR: ("Cursor", ".cursor/skills/babel/"),
        SkillTarget.CODEX: ("Codex", ".codex/skills/babel/"),
        SkillTarget.GENERIC: ("Generic", ".babel/skills_reference.md"),
    }
    return info.get(target, ("Unknown", ".babel/skills_reference.md"))


def detect_skill_target(project_dir: Path) -> SkillTarget:
    """
    Auto-detect the best skill target for a project.

    Detection priority:
    1. Existing .claude directory -> Claude Code
    2. Existing .cursor directory -> Cursor
    3. Fallback to generic
    """
    if (project_dir / ".claude").exists():
        return SkillTarget.CLAUDE_CODE
    elif (project_dir / ".cursor").exists():
        return SkillTarget.CURSOR
    else:
        return SkillTarget.GENERIC


def detect_active_platforms(project_dir: Path) -> List[SkillTarget]:
    """
    Detect all active platforms in a project.

    Returns list of platforms that have their marker directory present.
    """
    active = []
    for target, marker in PLATFORM_MARKERS.items():
        if (project_dir / marker).exists():
            active.append(target)
    return active if active else [SkillTarget.GENERIC]


# =============================================================================
# Manifest Management (Multi-Platform Sync)
# =============================================================================

MANIFEST_FILE = ".babel/skills_manifest.json"


def _get_source_version() -> str:
    """Get current timestamp as source version."""
    return datetime.now(timezone.utc).isoformat()


def _compute_checksum(project_dir: Path) -> str:
    """
    Compute checksum of source skills for drift detection.

    Uses modification times of skill YAML files as a simple hash.
    """
    import hashlib
    skills_dir = get_skills_dir()
    if not skills_dir.exists():
        return ""

    # Collect all YAML files and their mod times
    files_data = []
    for yaml_file in sorted(skills_dir.rglob("*.yaml")):
        stat = yaml_file.stat()
        files_data.append(f"{yaml_file.name}:{stat.st_mtime}")

    combined = "|".join(files_data)
    return hashlib.md5(combined.encode()).hexdigest()[:12]


def load_manifest(project_dir: Path) -> SkillsManifest:
    """Load skills manifest from project directory."""
    manifest_path = project_dir / MANIFEST_FILE
    if not manifest_path.exists():
        return SkillsManifest(source_version="", exports={}, checksum="")

    try:
        data = json.loads(manifest_path.read_text(encoding='utf-8'))
        return SkillsManifest.from_dict(data)
    except (json.JSONDecodeError, KeyError):
        return SkillsManifest(source_version="", exports={}, checksum="")


def save_manifest(project_dir: Path, manifest: SkillsManifest) -> None:
    """Save skills manifest to project directory."""
    manifest_path = project_dir / MANIFEST_FILE
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2),
        encoding='utf-8'
    )


def _update_manifest(
    project_dir: Path,
    target: SkillTarget,
    result: SkillExportResult
) -> None:
    """Update manifest after a successful export."""
    if not result.success:
        return

    manifest = load_manifest(project_dir)

    # Count skills and protocols
    all_skills = load_all_skills()
    protocols = load_protocols()
    total_skills = sum(len(skills) for skills in all_skills.values())

    # Update manifest
    manifest.source_version = _get_source_version()
    manifest.checksum = _compute_checksum(project_dir)
    manifest.exports[target.value] = ExportRecord(
        path=str(SKILL_TARGET_PATHS.get(target, "")),
        last_export=_get_source_version(),
        skills_count=total_skills,
        protocols_count=len(protocols),
    )

    save_manifest(project_dir, manifest)

    # Update .env with skills installation state
    update_env_file(
        project_dir,
        {
            "BABEL_SKILLS_INSTALLED": "true",
            "BABEL_SKILLS_TARGET": target.value,
        },
        section_name="Skills Installation",
        section_comment="set by: babel skill export"
    )


# =============================================================================
# Multi-Platform Export Functions
# =============================================================================

def export_all_platforms(
    project_dir: Path,
    force: bool = False
) -> SkillExportResult:
    """
    Export skills to all detected/active platforms.

    Detects which platforms are in use (by marker directories) and exports
    to each one. Falls back to generic if no platform markers found.
    """
    active_platforms = detect_active_platforms(project_dir)
    all_files = []
    messages = []
    success = True

    for platform in active_platforms:
        if platform == SkillTarget.GENERIC:
            result = export_skills_generic(project_dir)
        elif platform == SkillTarget.CLAUDE_CODE:
            result = export_skills_claude_code(project_dir, force)
        elif platform == SkillTarget.CURSOR:
            result = _export_to_cursor_direct(project_dir, force)
        elif platform == SkillTarget.CODEX:
            result = export_skills_codex(project_dir, force)
        else:
            continue

        if result.success:
            _update_manifest(project_dir, platform, result)
            all_files.extend(result.files_created)
            messages.append(f"✓ {platform.value}: {len(result.files_created)} files")
        else:
            success = False
            messages.append(f"✗ {platform.value}: {result.message}")

    return SkillExportResult(
        success=success,
        message="\n".join(messages),
        files_created=all_files,
        target=SkillTarget.ALL
    )


def _export_to_cursor_direct(
    project_dir: Path,
    force: bool = False
) -> SkillExportResult:
    """
    Export skills directly to Cursor location (not via Claude Code).

    Fixes the bug where export_skills_cursor() would export to Claude location.
    """
    target = SkillTarget.CURSOR
    skills_dir = project_dir / SKILL_TARGET_PATHS[target]
    return _export_agent_skills_format(project_dir, skills_dir, target, force)


def sync_skills(project_dir: Path, force: bool = False) -> SkillExportResult:
    """
    Re-export skills to all previously exported platforms.

    Reads the manifest to find platforms that have been exported before,
    then updates them with current skill definitions.
    """
    manifest = load_manifest(project_dir)

    if not manifest.exports:
        return SkillExportResult(
            success=False,
            message="No previous exports found. Use 'export' first.",
            files_created=[],
            target=SkillTarget.ALL
        )

    all_files = []
    messages = []
    success = True

    for platform_value in manifest.exports:
        try:
            platform = SkillTarget(platform_value)
        except ValueError:
            continue

        # Export to each previously-exported platform
        if platform == SkillTarget.GENERIC:
            result = export_skills_generic(project_dir)
        elif platform == SkillTarget.CLAUDE_CODE:
            result = export_skills_claude_code(project_dir, force)
        elif platform == SkillTarget.CURSOR:
            result = _export_to_cursor_direct(project_dir, force)
        elif platform == SkillTarget.CODEX:
            result = export_skills_codex(project_dir, force)
        else:
            continue

        if result.success:
            _update_manifest(project_dir, platform, result)
            all_files.extend(result.files_created)
            messages.append(f"✓ {platform.value}: synced {len(result.files_created)} files")
        else:
            success = False
            messages.append(f"✗ {platform.value}: {result.message}")

    return SkillExportResult(
        success=success,
        message="\n".join(messages),
        files_created=all_files,
        target=SkillTarget.ALL
    )


@dataclass
class SkillsStatus:
    """Status of skill exports across platforms."""
    source_checksum: str
    platforms: Dict[str, Dict[str, Any]]
    needs_sync: List[str]
    never_exported: List[str]


def get_skills_status(project_dir: Path) -> SkillsStatus:
    """
    Get status of skill exports across all platforms.

    Returns information about:
    - Current source checksum
    - Each exported platform's status
    - Which platforms need sync (source changed since export)
    - Which active platforms have never been exported
    """
    manifest = load_manifest(project_dir)
    current_checksum = _compute_checksum(project_dir)
    active_platforms = detect_active_platforms(project_dir)

    platforms = {}
    needs_sync = []
    never_exported = []

    # Check each active platform
    for platform in active_platforms:
        platform_value = platform.value
        export_record = manifest.exports.get(platform_value)

        if export_record is None:
            never_exported.append(platform_value)
            platforms[platform_value] = {
                "status": "never_exported",
                "path": str(SKILL_TARGET_PATHS.get(platform, "")),
            }
        else:
            # Check if out of sync
            is_outdated = manifest.checksum != current_checksum
            if is_outdated:
                needs_sync.append(platform_value)

            platforms[platform_value] = {
                "status": "outdated" if is_outdated else "current",
                "path": export_record.path,
                "last_export": export_record.last_export,
                "skills_count": export_record.skills_count,
                "protocols_count": export_record.protocols_count,
            }

    return SkillsStatus(
        source_checksum=current_checksum,
        platforms=platforms,
        needs_sync=needs_sync,
        never_exported=never_exported,
    )


def format_skills_status(status: SkillsStatus) -> str:
    """Format skills status for display."""
    lines = ["# Babel Skills Export Status"]
    lines.append("")
    lines.append(f"Source checksum: `{status.source_checksum}`")
    lines.append("")

    if status.never_exported:
        lines.append("## ⚠ Never Exported")
        for p in status.never_exported:
            lines.append(f"- {p}")
        lines.append("")

    if status.needs_sync:
        lines.append("## 🔄 Needs Sync")
        for p in status.needs_sync:
            lines.append(f"- {p}")
        lines.append("")

    lines.append("## Platform Status")
    lines.append("")
    lines.append("| Platform | Status | Skills | Protocols | Last Export |")
    lines.append("|----------|--------|--------|-----------|-------------|")

    for platform, info in status.platforms.items():
        status_icon = {
            "current": "✓",
            "outdated": "🔄",
            "never_exported": "⚠",
        }.get(info["status"], "?")

        skills = info.get("skills_count", "-")
        protocols = info.get("protocols_count", "-")
        last = info.get("last_export", "-")
        if last and last != "-":
            # Truncate ISO timestamp for display
            last = last[:19].replace("T", " ")

        lines.append(f"| {platform} | {status_icon} {info['status']} | {skills} | {protocols} | {last} |")

    lines.append("")
    lines.append("Commands:")
    lines.append("- `babel skill export --target <platform>` - Export to specific platform")
    lines.append("- `babel skill export --all` - Export to all active platforms")
    lines.append("- `babel skill sync` - Re-export to previously exported platforms")
    lines.append("- `babel skill remove --target <platform>` - Remove from specific platform")

    return "\n".join(lines)


# =============================================================================
# Skill Removal Functions
# =============================================================================

def _remove_from_manifest(project_dir: Path, target: SkillTarget) -> None:
    """
    Remove platform entry from manifest after skill removal.

    Args:
        project_dir: Project root directory
        target: Platform to remove from manifest
    """
    manifest = load_manifest(project_dir)
    if target.value in manifest.exports:
        del manifest.exports[target.value]
    save_manifest(project_dir, manifest)


def remove_skills(
    project_dir: Path,
    target: SkillTarget,
    force: bool = False
) -> SkillRemoveResult:
    """
    Remove exported skills from the specified target platform.

    Args:
        project_dir: Project root directory
        target: Target platform to remove from
        force: Skip validation (for --all operations)

    Returns:
        SkillRemoveResult with operation details
    """
    import shutil

    if target == SkillTarget.ALL:
        return remove_all_platforms(project_dir, force)

    # Check if platform was exported
    manifest = load_manifest(project_dir)
    if target.value not in manifest.exports and not force:
        return SkillRemoveResult(
            success=False,
            message=f"Platform '{target.value}' not exported. See: babel skill status",
            files_deleted=0,
            target=target
        )

    # Get the skills directory for this platform
    skills_dir = project_dir / SKILL_TARGET_PATHS.get(target)
    if skills_dir is None:
        return SkillRemoveResult(
            success=False,
            message=f"Unknown platform: {target.value}",
            files_deleted=0,
            target=target
        )

    files_deleted = 0

    # Count files before deletion
    if skills_dir.exists():
        if skills_dir.is_file():
            # Generic is a single file
            files_deleted = 1
            skills_dir.unlink()
        else:
            # Count all files in directory tree
            for f in skills_dir.rglob("*"):
                if f.is_file():
                    files_deleted += 1
            # Remove entire directory tree
            shutil.rmtree(skills_dir)

    # Update manifest
    _remove_from_manifest(project_dir, target)

    # Update .env if no exports remain
    manifest = load_manifest(project_dir)
    if not manifest.exports:
        update_env_file(
            project_dir,
            {
                "BABEL_SKILLS_INSTALLED": "false",
                "BABEL_SKILLS_TARGET": "",
            },
            section_name="Skills Installation",
            section_comment="set by: babel skill remove"
        )

    return SkillRemoveResult(
        success=True,
        message=f"Removed {files_deleted} skill files from {target.value}",
        files_deleted=files_deleted,
        target=target
    )


def remove_all_platforms(
    project_dir: Path,
    force: bool = False
) -> SkillRemoveResult:
    """
    Remove skills from all previously exported platforms.

    Args:
        project_dir: Project root directory
        force: Must be True to proceed (safety check)

    Returns:
        SkillRemoveResult with combined operation details
    """
    if not force:
        return SkillRemoveResult(
            success=False,
            message="Use --force to remove from all platforms",
            files_deleted=0,
            target=SkillTarget.ALL
        )

    manifest = load_manifest(project_dir)
    if not manifest.exports:
        return SkillRemoveResult(
            success=False,
            message="No platforms exported. See: babel skill status",
            files_deleted=0,
            target=SkillTarget.ALL
        )

    total_deleted = 0
    messages = []
    all_success = True

    for platform_value in list(manifest.exports.keys()):
        try:
            platform = SkillTarget(platform_value)
        except ValueError:
            continue

        result = remove_skills(project_dir, platform, force=True)
        if result.success:
            total_deleted += result.files_deleted
            messages.append(f"✓ {platform.value}: {result.files_deleted} files")
        else:
            all_success = False
            messages.append(f"✗ {platform.value}: {result.message}")

    return SkillRemoveResult(
        success=all_success,
        message="\n".join(messages),
        files_deleted=total_deleted,
        target=SkillTarget.ALL
    )
