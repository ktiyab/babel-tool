"""
Tests for Capture → Retrieve Loop — Coherence Evidence for P1

These tests validate Success Criterion 1:
"Reasoning travels with artifacts. 'Why?' always has an answer."
"""


from babel.core.events import EventStore, capture_conversation, declare_purpose, confirm_artifact, propose_structure
from babel.core.graph import GraphStore, Node, Edge
from babel.services.extractor import Extractor


class TestCaptureFlow:
    """P-FRICTION: Low friction capture, system proposes structure."""
    
    def test_raw_capture_always_works(self, tmp_path):
        """Raw conversation capture requires no structure."""
        events = EventStore(tmp_path / "events.jsonl")
        
        # Just capture raw text—no extraction required
        event = capture_conversation(
            "We had a long discussion about architecture. "
            "Decided to go with microservices but keep the core monolithic for now."
        )
        events.append(event)
        
        # Should persist regardless of extraction
        retrieved = events.read_all()
        assert len(retrieved) == 1
        assert "microservices" in retrieved[0].data['content']
    
    def test_extraction_proposes_structure(self, tmp_path):
        """Extractor proposes artifacts from natural language."""
        extractor = Extractor()  # Mock mode
        
        proposals = extractor.extract(
            "We decided to use Python because it's fastest for prototyping.",
            source_id="conv_123"
        )
        
        # Should detect decision
        assert len(proposals) > 0
        assert any(p.artifact_type == "decision" for p in proposals)
    
    def test_confirmation_creates_linked_artifacts(self, tmp_path):
        """Confirmed proposals become linked artifacts."""
        events = EventStore(tmp_path / "events.jsonl")
        graph = GraphStore(tmp_path / "graph.db")
        
        # Capture conversation
        conv = capture_conversation("We decided to use SQLite for the MVP")
        events.append(conv)
        
        # Propose structure
        proposal = propose_structure(
            source_id=conv.id,
            proposed={"summary": "Use SQLite", "type": "decision"},
            confidence=0.9
        )
        events.append(proposal)
        graph._project_event(proposal)
        
        # Confirm
        confirmation = confirm_artifact(
            proposal_id=proposal.id,
            artifact_type="decision",
            content={"summary": "Use SQLite for MVP database"}
        )
        events.append(confirmation)
        graph._project_event(confirmation)
        
        # Should have linked artifacts
        decisions = graph.get_nodes_by_type("decision")
        assert len(decisions) == 1
        
        # Should trace back to proposal
        incoming = graph.get_incoming(decisions[0].id)
        assert len(incoming) > 0


class TestWhyQueries:
    """P1: Answering 'why?' with provenance."""
    
    def test_decision_traces_to_purpose(self, tmp_path):
        """Decisions can trace back to purpose they serve."""
        graph = GraphStore(tmp_path / "graph.db")
        
        # Setup: Purpose → Decision chain
        graph.add_node(Node(
            id="purpose_1",
            type="purpose", 
            content={"summary": "Build tool that preserves intent"},
            event_id="e1"
        ))
        
        graph.add_node(Node(
            id="decision_1",
            type="decision",
            content={"summary": "Use event sourcing architecture"},
            event_id="e2"
        ))
        
        graph.add_edge(Edge(
            source_id="decision_1",
            target_id="purpose_1",
            relation="serves",
            event_id="e3"
        ))
        
        # Query: Why event sourcing?
        path = graph.trace_path("decision_1", "purpose_1")
        
        assert path is not None
        assert "purpose_1" in path
        
        # Can get the actual content
        purpose = graph.get_node("purpose_1")
        assert "preserves intent" in purpose.content['summary']
    
    def test_constraint_traces_to_decision(self, tmp_path):
        """Constraints can trace to decisions they bound."""
        graph = GraphStore(tmp_path / "graph.db")
        
        graph.add_node(Node(
            id="decision_1",
            type="decision",
            content={"summary": "Use SQLite"},
            event_id="e1"
        ))
        
        graph.add_node(Node(
            id="constraint_1",
            type="constraint",
            content={"summary": "MVP must work offline"},
            event_id="e2"
        ))
        
        graph.add_edge(Edge(
            source_id="decision_1",
            target_id="constraint_1",
            relation="satisfies",
            event_id="e3"
        ))
        
        # Why SQLite? Because of offline constraint.
        incoming = graph.get_incoming("constraint_1")
        
        assert len(incoming) == 1
        assert incoming[0][1].content['summary'] == "Use SQLite"


class TestEvolutionTracking:
    """P2: Evolution is traceable."""
    
    def test_event_history_preserved(self, tmp_path):
        """All changes are recorded in event stream."""
        events = EventStore(tmp_path / "events.jsonl")
        
        # Initial purpose
        events.append(declare_purpose("Build MVP in 2 weeks"))
        
        # Capture discussion about scope
        events.append(capture_conversation("Actually, 2 weeks is too tight. Let's say 4 weeks."))
        
        # New purpose
        events.append(declare_purpose("Build MVP in 4 weeks"))
        
        # History shows evolution
        purposes = events.read_by_type(events.read_all()[0].type)
        
        # Actually let's check all events
        all_events = events.read_all()
        assert len(all_events) == 3
        
        # Can see the change happened
        purpose_events = [e for e in all_events if e.type.value == 'purpose_declared']
        assert len(purpose_events) == 2
        assert "2 weeks" in purpose_events[0].data['purpose']
        assert "4 weeks" in purpose_events[1].data['purpose']


class TestNewPartyOnboarding:
    """Success Criterion 1: New party understands within one session."""
    
    def test_project_state_queryable(self, tmp_path):
        """New party can query current project state."""
        events = EventStore(tmp_path / "events.jsonl")
        graph = GraphStore(tmp_path / "graph.db")
        
        # Setup project history
        p = declare_purpose("Build intent preservation tool")
        events.append(p)
        graph._project_event(p)
        
        # A new party arrives. What can they learn?
        
        # 1. What's the purpose?
        purposes = graph.get_nodes_by_type("purpose")
        assert len(purposes) > 0
        assert "intent preservation" in purposes[0].content['purpose']
        
        # 2. How many events happened?
        event_count = events.count()
        assert event_count > 0
        
        # 3. Graph stats
        stats = graph.stats()
        assert stats['nodes'] > 0