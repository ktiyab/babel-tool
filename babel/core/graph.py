"""
Graph Store — SQLite projection of events (HC3)

This is a PROJECTION, not source of truth.
Can always be rebuilt from events.
Enables fast traversal and "why?" queries.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .events import Event, EventType, EventStore


@dataclass
class Node:
    id: str
    type: str
    content: Dict[str, Any]
    event_id: str  # Links back to source event


@dataclass 
class Edge:
    source_id: str
    target_id: str
    relation: str
    event_id: str  # Links back to source event


class GraphStore:
    """
    SQLite-based graph projection.
    
    Invariants:
    - Every node/edge traces to source event (INV1, INV2)
    - Projection can be rebuilt from events (HC3)
    - No cycles in dependency relations (INV3)
    """
    
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                event_id TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                event_id TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, relation)
            );
            
            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
        """)
        self.conn.commit()
    
    def add_node(self, node: Node):
        """Add node to graph."""
        import json
        self.conn.execute(
            "INSERT OR REPLACE INTO nodes (id, type, content, event_id) VALUES (?, ?, ?, ?)",
            (node.id, node.type, json.dumps(node.content), node.event_id)
        )
        self.conn.commit()
    
    def add_edge(self, edge: Edge):
        """Add edge to graph."""
        # Check for cycles before adding
        if self._would_create_cycle(edge):
            raise ValueError(f"Edge would create cycle: {edge.source_id} -> {edge.target_id}")
        
        self.conn.execute(
            "INSERT OR REPLACE INTO edges (source_id, target_id, relation, event_id) VALUES (?, ?, ?, ?)",
            (edge.source_id, edge.target_id, edge.relation, edge.event_id)
        )
        self.conn.commit()
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        import json
        row = self.conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()
        
        if row:
            return Node(
                id=row['id'],
                type=row['type'],
                content=json.loads(row['content']),
                event_id=row['event_id']
            )
        return None
    
    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """Get all nodes of a type."""
        import json
        rows = self.conn.execute(
            "SELECT * FROM nodes WHERE type = ?", (node_type,)
        ).fetchall()
        
        return [
            Node(id=r['id'], type=r['type'], content=json.loads(r['content']), event_id=r['event_id'])
            for r in rows
        ]
    
    def get_outgoing(self, node_id: str) -> List[Tuple[Edge, Node]]:
        """Get all nodes this node points to."""
        import json
        rows = self.conn.execute("""
            SELECT e.*, n.id as n_id, n.type as n_type, n.content as n_content, n.event_id as n_event_id
            FROM edges e
            JOIN nodes n ON e.target_id = n.id
            WHERE e.source_id = ?
        """, (node_id,)).fetchall()
        
        return [
            (
                Edge(source_id=r['source_id'], target_id=r['target_id'], relation=r['relation'], event_id=r['event_id']),
                Node(id=r['n_id'], type=r['n_type'], content=json.loads(r['n_content']), event_id=r['n_event_id'])
            )
            for r in rows
        ]
    
    def get_incoming(self, node_id: str) -> List[Tuple[Edge, Node]]:
        """Get all nodes that point to this node."""
        import json
        rows = self.conn.execute("""
            SELECT e.*, n.id as n_id, n.type as n_type, n.content as n_content, n.event_id as n_event_id
            FROM edges e
            JOIN nodes n ON e.source_id = n.id
            WHERE e.target_id = ?
        """, (node_id,)).fetchall()
        
        return [
            (
                Edge(source_id=r['source_id'], target_id=r['target_id'], relation=r['relation'], event_id=r['event_id']),
                Node(id=r['n_id'], type=r['n_type'], content=json.loads(r['n_content']), event_id=r['n_event_id'])
            )
            for r in rows
        ]
    
    def trace_path(self, from_id: str, to_id: str, max_depth: int = 10) -> Optional[List[str]]:
        """Find path between two nodes (for "why?" queries)."""
        visited = set()
        queue = [(from_id, [from_id])]
        
        while queue:
            current, path = queue.pop(0)
            if current == to_id:
                return path
            if current in visited or len(path) > max_depth:
                continue
            visited.add(current)
            
            for edge, node in self.get_outgoing(current):
                if node.id not in visited:
                    queue.append((node.id, path + [node.id]))
        
        return None
    
    def _would_create_cycle(self, new_edge: Edge) -> bool:
        """Check if adding edge would create cycle."""
        # Can we reach source from target? If so, adding this edge creates cycle.
        path = self.trace_path(new_edge.target_id, new_edge.source_id)
        return path is not None
    
    def find_orphans(self) -> List[Node]:
        """Find nodes with no incoming edges (potential orphans)."""
        import json
        rows = self.conn.execute("""
            SELECT n.* FROM nodes n
            LEFT JOIN edges e ON n.id = e.target_id
            WHERE e.target_id IS NULL
            AND n.type != 'purpose'  -- Purpose nodes are allowed to be roots
        """).fetchall()
        
        return [
            Node(id=r['id'], type=r['type'], content=json.loads(r['content']), event_id=r['event_id'])
            for r in rows
        ]
    
    def rebuild_from_events(self, event_store: EventStore):
        """Rebuild entire projection from event stream (HC3 recovery)."""
        # Clear existing
        self.conn.executescript("""
            DELETE FROM edges;
            DELETE FROM nodes;
        """)
        
        # Replay events
        for event in event_store.read_all():
            self._project_event(event)
        
        self.conn.commit()
    
    def _project_event(self, event: Event):
        """Project single event into graph."""
        if event.type == EventType.PURPOSE_DECLARED:
            self.add_node(Node(
                id=f"purpose_{event.id}",
                type="purpose",
                content=event.data,
                event_id=event.id
            ))
        
        elif event.type == EventType.ARTIFACT_CONFIRMED:
            node_id = f"{event.data['artifact_type']}_{event.id}"
            self.add_node(Node(
                id=node_id,
                type=event.data['artifact_type'],
                content=event.data['content'],
                event_id=event.id
            ))
            
            # Link from proposal to confirmed artifact
            # Direction: proposal → artifact (proposal led to this artifact)
            # This enables "what led to this?" queries via get_incoming()
            if event.data.get('proposal_id'):
                proposal_node = self.get_node(f"proposal_{event.data['proposal_id']}")
                if proposal_node:
                    self.add_edge(Edge(
                        source_id=proposal_node.id,
                        target_id=node_id,
                        relation="confirmed_as",
                        event_id=event.id
                    ))
        
        elif event.type == EventType.STRUCTURE_PROPOSED:
            self.add_node(Node(
                id=f"proposal_{event.id}",
                type="proposal",
                content=event.data,
                event_id=event.id
            ))

            # Link to source
            if event.data.get('source_id'):
                self.add_edge(Edge(
                    source_id=f"proposal_{event.id}",
                    target_id=event.data['source_id'],
                    relation="extracted_from",
                    event_id=event.id
                ))

        # =====================================================================
        # Ontology Extension Events (renegotiation-aligned relations)
        # =====================================================================

        elif event.type == EventType.TENSION_DETECTED:
            # tensions_with: bidirectional tension between artifacts
            # Both artifacts preserved (HC1), tension surfaced for negotiation (P4)
            artifact_a = event.data.get('artifact_a_id')
            artifact_b = event.data.get('artifact_b_id')
            if artifact_a and artifact_b:
                # Create tension node to store severity and reason
                tension_id = f"tension_{event.id}"
                self.add_node(Node(
                    id=tension_id,
                    type="tension",
                    content={
                        "severity": event.data.get('severity', 'warning'),
                        "reason": event.data.get('reason', ''),
                        "status": event.data.get('status', 'open')
                    },
                    event_id=event.id
                ))
                # Link both artifacts to the tension
                self.add_edge(Edge(
                    source_id=artifact_a,
                    target_id=tension_id,
                    relation="tensions_with",
                    event_id=event.id
                ))
                self.add_edge(Edge(
                    source_id=artifact_b,
                    target_id=tension_id,
                    relation="tensions_with",
                    event_id=event.id
                ))

        elif event.type == EventType.EVOLUTION_CLASSIFIED:
            # evolves_from: tracks lineage between artifact versions
            # New artifact preferred in queries, old remains for history (HC1)
            artifact_id = event.data.get('artifact_id')
            evolves_from_id = event.data.get('evolves_from_id')
            if artifact_id and evolves_from_id:
                self.add_edge(Edge(
                    source_id=artifact_id,
                    target_id=evolves_from_id,
                    relation="evolves_from",
                    event_id=event.id
                ))

        elif event.type == EventType.NEGOTIATION_REQUIRED:
            # requires_negotiation: artifact touches constrained area
            # Advisory only (HC2), warns but proceeds
            artifact_id = event.data.get('artifact_id')
            constraint_ids = event.data.get('constraint_ids', [])
            for constraint_id in constraint_ids:
                self.add_edge(Edge(
                    source_id=artifact_id,
                    target_id=constraint_id,
                    relation="requires_negotiation",
                    event_id=event.id
                ))

    def stats(self) -> Dict[str, int]:
        """Return graph statistics."""
        nodes = self.conn.execute("SELECT COUNT(*) as c FROM nodes").fetchone()['c']
        edges = self.conn.execute("SELECT COUNT(*) as c FROM edges").fetchone()['c']
        orphans = len(self.find_orphans())
        return {"nodes": nodes, "edges": edges, "orphans": orphans}