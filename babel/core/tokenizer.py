"""
Universal Tokenizer — Language-agnostic name tokenization

Extracts semantic tokens from ANY naming convention:
- camelCase: getUserProfile → [get, user, profile]
- snake_case: user_profile → [user, profile]
- kebab-case: user-profile → [user, profile]
- PascalCase: UserProfile → [user, profile]
- SCREAMING_CASE: USER_PROFILE → [user, profile]

Key insight: Naming conventions are FORMATTING, not CONTENT.
The semantic meaning is in the tokens, not the separators.

Design decisions:
- [EL-TT] Universal tokenization - single tokenizer for all naming conventions
- [ZK-AS] Agnostic-Adaptable-Scalable design
- [CV-RY] Naming conventions are encoding schemes for the same semantic content
"""

import re
from typing import List, Set


def tokenize_name(name: str) -> List[str]:
    """
    Universal name tokenizer - works for ANY language.

    Extracts semantic tokens from any naming convention by:
    1. Removing common prefixes (#, ., get_, set_, is_, has_, on_)
    2. Splitting on case boundaries (camelCase, PascalCase)
    3. Splitting on separators (_, -, ., space)
    4. Handling acronyms (HTMLParser → html, parser)
    5. Normalizing to lowercase
    6. Filtering noise (tokens < 2 chars)

    Args:
        name: Any identifier name (function, class, variable, CSS selector, etc.)

    Returns:
        List of lowercase semantic tokens

    Examples:
        >>> tokenize_name("getUserProfile")
        ['get', 'user', 'profile']
        >>> tokenize_name("user_profile_card")
        ['user', 'profile', 'card']
        >>> tokenize_name("UserProfileCard")
        ['user', 'profile', 'card']
        >>> tokenize_name("user-profile-card")
        ['user', 'profile', 'card']
        >>> tokenize_name("HTMLParser")
        ['html', 'parser']
        >>> tokenize_name("#main-navigation")
        ['main', 'navigation']
        >>> tokenize_name("__init__")
        ['init']

    Note:
        Consecutive acronyms like "XMLHTTPRequest" become ['xmlhttp', 'request']
        because splitting XMLHTTP into XML+HTTP requires dictionary knowledge.
        The token_match_score function handles this via substring matching.
    """
    if not name:
        return []

    # Step 1: Remove common prefixes that don't carry semantic meaning
    # CSS: #, .
    # Common method prefixes: get_, set_, is_, has_, on_
    # Python dunder: __
    cleaned = re.sub(r'^[#.]+', '', name)  # CSS prefixes
    cleaned = re.sub(r'^(get_|set_|is_|has_|on_)', '', cleaned)  # Method prefixes
    cleaned = re.sub(r'^_+', '', cleaned)  # Leading underscores
    cleaned = re.sub(r'_+$', '', cleaned)  # Trailing underscores

    # Step 2: Handle acronyms - insert boundary before transition from uppercase sequence to lowercase
    # HTMLParser → HTML_Parser → html, parser
    # XMLHTTPRequest → XML_HTTP_Request → xml, http, request
    cleaned = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', cleaned)

    # Step 3: Split camelCase and PascalCase - insert boundary between lower→upper
    # getUserProfile → get_User_Profile
    # UserProfile → User_Profile
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1_\2', cleaned)

    # Step 4: Split on any non-alphanumeric characters (separators)
    # Handles: _, -, ., space, and any other separators
    tokens = re.split(r'[^a-zA-Z0-9]+', cleaned)

    # Step 5: Normalize to lowercase and filter
    tokens = [t.lower() for t in tokens if t]

    # Step 6: Filter noise - tokens shorter than 2 chars
    tokens = [t for t in tokens if len(t) >= 2]

    return tokens


def tokenize_text(text: str) -> Set[str]:
    """
    Tokenize free-form text (queries, descriptions).

    Similar to tokenize_name but returns a set and handles
    multiple words/identifiers in the text.

    Args:
        text: Free-form text that may contain multiple identifiers

    Returns:
        Set of lowercase semantic tokens

    Examples:
        >>> tokenize_text("Find the UserProfile class")
        {'find', 'the', 'user', 'profile', 'class'}
        >>> tokenize_text("user_profile authentication")
        {'user', 'profile', 'authentication'}
    """
    if not text:
        return set()

    # Split text into potential identifiers/words
    # Preserve identifier boundaries while splitting on whitespace
    parts = re.split(r'\s+', text)

    all_tokens = set()
    for part in parts:
        tokens = tokenize_name(part)
        all_tokens.update(tokens)

    return all_tokens


def tokens_overlap(tokens1: Set[str], tokens2: Set[str]) -> int:
    """
    Count overlapping tokens between two token sets.

    Args:
        tokens1: First set of tokens
        tokens2: Second set of tokens

    Returns:
        Number of tokens in common
    """
    return len(tokens1 & tokens2)


def token_match_score(query_tokens: Set[str], name: str) -> float:
    """
    Calculate match score between query tokens and a name.

    Score components:
    - Exact token matches: 1.0 per token
    - Partial matches (token is substring): 0.5 per token

    Args:
        query_tokens: Tokens from the query
        name: Name to match against

    Returns:
        Match score (higher = better match)
    """
    name_tokens = set(tokenize_name(name))

    score = 0.0
    for qt in query_tokens:
        if qt in name_tokens:
            score += 1.0  # Exact token match
        else:
            # Check for partial match (token is substring of name token)
            for nt in name_tokens:
                if qt in nt or nt in qt:
                    score += 0.5
                    break

    return score
