"""
Tests for Graph Store — Coherence Evidence for HC3, INV1-4

These tests validate:
- HC3: Single source of truth (projection from events)
- INV1: Every artifact traces to event
- INV2: Every structure links to conversation
- INV3: No circular dependencies
"""

import pytest
import tempfile
from pathlib import Path

from babel.core.events import EventStore, capture_conversation, declare_purpose
from babel.core.graph import GraphStore, Node, Edge


class TestSingleSourceOfTruth:
    """HC3: All projections derive from events."""
    
    def test_graph_rebuilt_from_events(self, tmp_path):
        """Graph can be completely rebuilt from event stream."""
        events = EventStore(tmp_path / "events.jsonl")
        graph = GraphStore(tmp_path / "graph.db")
        
        # Create events
        p1 = declare_purpose("First purpose")
        p2 = declare_purpose("Second purpose")
        events.append(p1)
        events.append(p2)
        
        # Project manually
        graph._project_event(p1)
        graph._project_event(p2)
        
        initial_stats = graph.stats()
        
        # Rebuild from scratch
        graph.rebuild_from_events(events)
        
        rebuilt_stats = graph.stats()
        
        assert initial_stats['nodes'] == rebuilt_stats['nodes']
    
    def test_nodes_link_to_source_events(self, tmp_path):
        """Every node traces to originating event (INV1)."""
        events = EventStore(tmp_path / "events.jsonl")
        graph = GraphStore(tmp_path / "graph.db")
        
        event = declare_purpose("Test purpose")
        events.append(event)
        graph._project_event(event)
        
        nodes = graph.get_nodes_by_type('purpose')
        
        assert len(nodes) == 1
        assert nodes[0].event_id == event.id


class TestCycleDetection:
    """INV3: No circular dependencies in artifact relationships."""
    
    def test_direct_cycle_prevented(self, tmp_path):
        """Direct A->B->A cycle is prevented."""
        graph = GraphStore(tmp_path / "graph.db")
        
        graph.add_node(Node(id="a", type="decision", content={}, event_id="e1"))
        graph.add_node(Node(id="b", type="decision", content={}, event_id="e2"))
        
        graph.add_edge(Edge(source_id="a", target_id="b", relation="depends", event_id="e3"))
        
        with pytest.raises(ValueError, match="cycle"):
            graph.add_edge(Edge(source_id="b", target_id="a", relation="depends", event_id="e4"))
    
    def test_indirect_cycle_prevented(self, tmp_path):
        """Indirect A->B->C->A cycle is prevented."""
        graph = GraphStore(tmp_path / "graph.db")
        
        for id in ["a", "b", "c"]:
            graph.add_node(Node(id=id, type="decision", content={}, event_id=f"e_{id}"))
        
        graph.add_edge(Edge(source_id="a", target_id="b", relation="depends", event_id="e1"))
        graph.add_edge(Edge(source_id="b", target_id="c", relation="depends", event_id="e2"))
        
        with pytest.raises(ValueError, match="cycle"):
            graph.add_edge(Edge(source_id="c", target_id="a", relation="depends", event_id="e3"))
    
    def test_parallel_edges_allowed(self, tmp_path):
        """Multiple edges between same nodes (different relations) allowed."""
        graph = GraphStore(tmp_path / "graph.db")
        
        graph.add_node(Node(id="a", type="decision", content={}, event_id="e1"))
        graph.add_node(Node(id="b", type="decision", content={}, event_id="e2"))
        
        graph.add_edge(Edge(source_id="a", target_id="b", relation="depends", event_id="e3"))
        graph.add_edge(Edge(source_id="a", target_id="b", relation="informs", event_id="e4"))
        
        outgoing = graph.get_outgoing("a")
        assert len(outgoing) == 2


class TestTraceability:
    """P1: Reasoning travels with artifacts."""
    
    def test_path_finding(self, tmp_path):
        """Can trace path between connected nodes."""
        graph = GraphStore(tmp_path / "graph.db")
        
        # Create chain: purpose -> decision -> constraint
        graph.add_node(Node(id="purpose_1", type="purpose", content={"name": "Build tool"}, event_id="e1"))
        graph.add_node(Node(id="decision_1", type="decision", content={"name": "Use Python"}, event_id="e2"))
        graph.add_node(Node(id="constraint_1", type="constraint", content={"name": "MVP scope"}, event_id="e3"))
        
        graph.add_edge(Edge(source_id="decision_1", target_id="purpose_1", relation="serves", event_id="e4"))
        graph.add_edge(Edge(source_id="constraint_1", target_id="decision_1", relation="constrains", event_id="e5"))
        
        # Can trace from constraint to purpose
        path = graph.trace_path("constraint_1", "purpose_1")
        
        assert path is not None
        assert path == ["constraint_1", "decision_1", "purpose_1"]
    
    def test_no_path_returns_none(self, tmp_path):
        """Unconnected nodes return no path."""
        graph = GraphStore(tmp_path / "graph.db")
        
        graph.add_node(Node(id="a", type="decision", content={}, event_id="e1"))
        graph.add_node(Node(id="b", type="decision", content={}, event_id="e2"))
        
        # No edge between them
        path = graph.trace_path("a", "b")
        
        assert path is None


class TestOrphanDetection:
    """Quality metric: detect unlinked artifacts."""
    
    def test_orphans_detected(self, tmp_path):
        """Nodes without incoming edges flagged as orphans."""
        graph = GraphStore(tmp_path / "graph.db")
        
        # Purpose is allowed to be root (not orphan)
        graph.add_node(Node(id="purpose_1", type="purpose", content={}, event_id="e1"))
        
        # Decision without link IS orphan
        graph.add_node(Node(id="decision_1", type="decision", content={}, event_id="e2"))
        
        orphans = graph.find_orphans()
        
        assert len(orphans) == 1
        assert orphans[0].id == "decision_1"
    
    def test_linked_nodes_not_orphans(self, tmp_path):
        """Properly linked nodes are not orphans."""
        graph = GraphStore(tmp_path / "graph.db")
        
        graph.add_node(Node(id="purpose_1", type="purpose", content={}, event_id="e1"))
        graph.add_node(Node(id="decision_1", type="decision", content={}, event_id="e2"))
        
        # Link decision to purpose
        graph.add_edge(Edge(source_id="purpose_1", target_id="decision_1", relation="enabled", event_id="e3"))
        
        orphans = graph.find_orphans()
        
        assert len(orphans) == 0