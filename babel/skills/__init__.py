"""
Babel Skills — Modular, composable command sequences for LLM operators

Skills are atomic units of Babel expertise that can be:
- Loaded independently (progressive disclosure, P6)
- Composed together (/orient + /recall)
- Exported to platform-specific formats (Claude Code, Cursor, Codex)
- Tested independently

Skill Categories:
- lifecycle: Session & task management (orient, continue, start-new)
- knowledge: Knowledge capture & retrieval (recall, remember, spec, uncertain)
- validation: Human governance (validate, strengthen, challenge, revise)
- maintenance: System health (maintain, discover, git-babel)
- preference: User preferences (preference, init-memo)
- analyze: Expert advisory (health-check, architecture-review, security-audit, etc.)

Protocols (cross-cutting behaviors, not skills):
- verbatim, batch, dual-display, output-format, code-mod, ai-safe
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, Any
import yaml


class SkillCategory(Enum):
    """Skill categories mapped to user workflows."""
    LIFECYCLE = "lifecycle"
    KNOWLEDGE = "knowledge"
    VALIDATION = "validation"
    MAINTENANCE = "maintenance"
    PREFERENCE = "preference"
    ANALYZE = "analyze"
    PROTOCOL = "protocols"  # Cross-cutting behaviors


@dataclass
class Skill:
    """
    A Babel skill definition.

    Skills are modular command sequences with clear triggers and purposes.
    Following principle [8f5a7d89]: Skills map to user workflows, not implementation.
    """
    name: str
    category: SkillCategory
    description: str
    trigger: str  # When to invoke this skill
    commands: List[str]  # Command sequence
    principles: List[str] = field(default_factory=list)  # Related Babel principles
    uses_context: List[str] = field(default_factory=list)  # What context this skill consumes
    produces: List[str] = field(default_factory=list)  # What this skill produces
    composable_with: List[str] = field(default_factory=list)  # Skills this composes with

    # For progressive disclosure
    always_load: bool = False  # Load at session start
    load_on_demand: bool = True  # Load when triggered

    # Platform export hints
    disable_model_invocation: bool = False  # Only user can invoke (e.g., /deploy)
    user_invocable: bool = True  # Appears in slash command menu
    allowed_tools: List[str] = field(default_factory=list)  # Tools allowed when skill active

    # Extended content for rich skill documentation
    examples: List[str] = field(default_factory=list)  # Detailed usage examples (multiline)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization."""
        result = {
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "trigger": self.trigger,
            "commands": self.commands,
            "principles": self.principles,
            "uses_context": self.uses_context,
            "produces": self.produces,
            "composable_with": self.composable_with,
            "always_load": self.always_load,
            "load_on_demand": self.load_on_demand,
            "disable_model_invocation": self.disable_model_invocation,
            "user_invocable": self.user_invocable,
        }
        if self.allowed_tools:
            result["allowed_tools"] = self.allowed_tools
        if self.examples:
            result["examples"] = self.examples
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Skill':
        """Create Skill from dictionary (e.g., parsed YAML)."""
        return cls(
            name=data["name"],
            category=SkillCategory(data.get("category", "lifecycle")),
            description=data.get("description", ""),
            trigger=data.get("trigger", ""),
            commands=data.get("commands", []),
            principles=data.get("principles", []),
            uses_context=data.get("uses_context", []),
            produces=data.get("produces", []),
            composable_with=data.get("composable_with", []),
            always_load=data.get("always_load", False),
            load_on_demand=data.get("load_on_demand", True),
            disable_model_invocation=data.get("disable_model_invocation", False),
            user_invocable=data.get("user_invocable", True),
            allowed_tools=data.get("allowed_tools", []),
            examples=data.get("examples", []),
        )

    def to_yaml(self) -> str:
        """Serialize to YAML format."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'Skill':
        """Parse from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)


@dataclass
class Protocol:
    """
    A cross-cutting behavior that applies across all skills.

    Protocols don't have triggers - they're always active.
    They modify HOW skills behave, not WHAT they do.
    Following decision [753fa97e]: Protocols are cross-cutting, not skills.
    """
    name: str
    description: str
    rule: str  # The core rule/behavior
    applies_to: List[str] = field(default_factory=list)  # Which skills/contexts
    examples: List[str] = field(default_factory=list)  # Usage examples

    # Platform export hints (for parity with Skill)
    user_invocable: bool = True  # Whether users can invoke directly

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "description": self.description,
            "rule": self.rule,
            "applies_to": self.applies_to,
            "examples": self.examples,
        }
        if not self.user_invocable:
            result["user_invocable"] = False
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Protocol':
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            rule=data.get("rule", ""),
            applies_to=data.get("applies_to", []),
            examples=data.get("examples", []),
            user_invocable=data.get("user_invocable", True),
        )


# =============================================================================
# Skill Loading
# =============================================================================

def get_skills_dir() -> Path:
    """Get the skills directory path."""
    return Path(__file__).parent


def list_skill_categories() -> List[SkillCategory]:
    """List all skill categories."""
    return [c for c in SkillCategory if c != SkillCategory.PROTOCOL]


def list_skills_in_category(category: SkillCategory) -> List[Path]:
    """List all skill files in a category."""
    skills_dir = get_skills_dir() / category.value
    if not skills_dir.exists():
        return []
    return list(skills_dir.glob("*.yaml")) + list(skills_dir.glob("*.md"))


def load_skill(skill_path: Path) -> Optional[Skill]:
    """
    Load a skill from a YAML or Markdown file.

    Markdown files use YAML frontmatter (between --- markers).
    """
    if not skill_path.exists():
        return None

    content = skill_path.read_text(encoding='utf-8')

    # Handle Markdown with YAML frontmatter
    if skill_path.suffix == '.md':
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                yaml_content = parts[1]
                data = yaml.safe_load(yaml_content)
                # Store markdown body as description if not set
                if not data.get('description'):
                    data['description'] = parts[2].strip()
                return Skill.from_dict(data)
        return None

    # Handle pure YAML
    data = yaml.safe_load(content)
    return Skill.from_dict(data)


def load_all_skills() -> Dict[SkillCategory, List[Skill]]:
    """Load all skills organized by category."""
    result: Dict[SkillCategory, List[Skill]] = {}

    for category in list_skill_categories():
        skills = []
        for skill_path in list_skills_in_category(category):
            skill = load_skill(skill_path)
            if skill:
                skills.append(skill)
        result[category] = skills

    return result


def load_protocols() -> List[Protocol]:
    """Load all protocol definitions."""
    protocols_dir = get_skills_dir() / "protocols"
    if not protocols_dir.exists():
        return []

    protocols = []
    for proto_path in protocols_dir.glob("*.yaml"):
        content = proto_path.read_text(encoding='utf-8')
        data = yaml.safe_load(content)
        protocols.append(Protocol.from_dict(data))

    return protocols


def get_skill_by_name(name: str) -> Optional[Skill]:
    """Find a skill by name across all categories."""
    for category in list_skill_categories():
        for skill_path in list_skills_in_category(category):
            skill = load_skill(skill_path)
            if skill and skill.name == name:
                return skill
    return None


def get_always_load_skills() -> List[Skill]:
    """Get skills that should always be loaded at session start."""
    result = []
    for category, skills in load_all_skills().items():
        for skill in skills:
            if skill.always_load:
                result.append(skill)
    return result


# =============================================================================
# Skill Composition
# =============================================================================

def compose_skills(skill_names: List[str]) -> List[Skill]:
    """
    Compose multiple skills into a sequence.

    Following principle [cd32a0a0]: Skills should be composable.
    """
    skills = []
    for name in skill_names:
        skill = get_skill_by_name(name)
        if skill:
            skills.append(skill)
    return skills


def get_skill_commands(skill_names: List[str]) -> List[str]:
    """Get the combined command sequence for multiple skills."""
    commands = []
    for skill in compose_skills(skill_names):
        commands.extend(skill.commands)
    return commands
