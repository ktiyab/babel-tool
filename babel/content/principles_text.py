"""
Principles text for Babel CLI.

Extracted from cli.py for separation of concerns.
P11: Framework Self-Application — the framework applies to its own discussion.
"""

PRINCIPLES_TEXT = """
Babel Principles -- Framework Self-Application (P11)
====================================================

A framework that cannot govern itself is incomplete.
Use these principles to check your own usage.


CORE PRINCIPLES
---------------

P1: Bootstrap from Need
    Start from real problems, not solutions.
    Every project begins with a stated need.
    -> babel init --need "problem" --purpose "solution"

P2: Emergent Ontology
    Vocabulary emerges, not imposed.
    Define terms as the project discovers them.
    -> babel define, babel challenge, babel refine

P3: Expertise Governance
    Authority derives from domain expertise, not seniority.
    State which domain your claims apply to.
    AI participates as pattern detector, never arbiter.
    -> babel capture "..." --domain architecture

P4: Disagreement as Hypothesis
    Disagreement is information, not noise.
    Challenges require hypotheses and tests.
    -> babel challenge, babel evidence, babel resolve

P5: Dual-Test Truth
    Decisions need both consensus AND evidence.
    Consensus alone risks groupthink.
    Evidence alone risks blind spots.
    -> babel endorse, babel evidence-decision, babel validation

P6: Ambiguity Management
    Hold uncertainty rather than forcing premature closure.
    Acknowledge what you don't know.
    -> babel question, babel capture --uncertain

P7: Evidence-Weighted Memory
    Living artifacts, not exhaustive archives.
    What works is retained; what fails is metabolized.
    -> babel deprecate (de-prioritize, not delete)

P8: Failure Metabolism
    Failures are mandatory learning inputs.
    Silent abandonment loses learning.
    -> Resolution required for revised/deprecated items

P9: Adaptive Cycle Rate
    Pace adapts to coherence and tension.
    High confusion -> slow down, clarify.
    High alignment -> move forward.
    -> babel status (health indicator)

P10: Cross-Domain Learning
    Track where ideas come from.
    Misapplied analogies are diagnostic, not error.
    -> Cross-domain detection in captures

P11: Framework Self-Application
    This framework applies to itself.
    Periodically reflect: Are we following our own rules?
    -> babel principles (this command)


HARD CONSTRAINTS
----------------

HC1: Immutable Events    History is append-only, never edited
HC2: Human Authority     AI proposes, humans decide
HC3: Offline-First       Works without network
HC4: Tool Agnostic       Your choice of AI provider
HC5: Graceful Sync       Team collaboration works


SELF-CHECK QUESTIONS
--------------------

When using Babel, periodically ask:

  [ ] Am I starting from need, or jumping to solutions? (P1)
  [ ] Am I attributing expertise domains? (P3)
  [ ] Am I treating disagreement as information? (P4)
  [ ] Do decisions have both endorsement AND evidence? (P5)
  [ ] Am I acknowledging what I don't know? (P6)
  [ ] Am I capturing lessons from failures? (P8)
  [ ] Is my pace appropriate to current confusion? (P9)
  [ ] Am I noting where borrowed ideas come from? (P10)

If coherence degrades, meta-discussion is legitimate.
Ask: "Are we violating our own principles?"
"""
