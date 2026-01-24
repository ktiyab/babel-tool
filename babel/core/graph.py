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

import orjson

from .events import Event, EventType, EventStore


@dataclass
class Node:
    id: str
    type: str
    content: Dict[str, Any]
    event_id: str  # Links back to source event
    created_at: str = ""  # ISO timestamp from source event


@dataclass
class Edge:
    source_id: str
    target_id: str
    relation: str
    event_id: str  # Links back to source event
    created_at: str = ""  # ISO timestamp from source event


class GraphStore:
    """
    SQLite-based graph projection.

    Invariants:
    - Every node/edge traces to source event (INV1, INV2)
    - Projection can be rebuilt from events (HC3)
    - No cycles in dependency relations (INV3)

    Performance optimizations (aligned with orjson/rapidfuzz/xxhash strategy):
    - WAL mode for concurrent reads during writes
    - Reduced synchronous for projection (rebuildable from events)
    - Increased cache and mmap for memory-mapped I/O
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path), cached_statements=256)
        self.conn.row_factory = sqlite3.Row
        self._configure_pragmas()
        self._init_schema()
        self._init_stats_table()

    def _configure_pragmas(self):
        """
        Configure SQLite for performance (safe for projection that can be rebuilt).

        These settings prioritize speed over durability because:
        - Graph is a PROJECTION, not source of truth (HC3)
        - Can always be rebuilt from events via rebuild_from_events()
        - Events are the durable layer (JSONL files)
        """
        self.conn.executescript("""
            -- WAL mode: 2-10x faster writes, concurrent reads during writes
            PRAGMA journal_mode=WAL;

            -- NORMAL sync: 2x faster (FULL not needed for rebuildable projection)
            PRAGMA synchronous=NORMAL;

            -- 64MB cache (negative = KB): reduces disk reads
            PRAGMA cache_size=-65536;

            -- 256MB mmap: memory-mapped I/O for faster access
            PRAGMA mmap_size=268435456;

            -- Store temp tables in memory
            PRAGMA temp_store=MEMORY;

            -- Optimize query planner on first open (per SQLite docs)
            PRAGMA optimize=0x10002;
        """)
    
    def _init_schema(self):
        # Create tables (new databases get created_at, existing ones don't yet)
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                event_id TEXT NOT NULL,
                created_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation TEXT NOT NULL,
                event_id TEXT NOT NULL,
                created_at TEXT DEFAULT '',
                PRIMARY KEY (source_id, target_id, relation)
            );

            CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(type);
            CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
            CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);
        """)

        # Migration: add created_at column if missing (existing databases)
        # Must happen BEFORE creating index on created_at
        try:
            self.conn.execute("ALTER TABLE nodes ADD COLUMN created_at TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            self.conn.execute("ALTER TABLE edges ADD COLUMN created_at TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create index on created_at (after migration ensures column exists)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_created ON nodes(created_at)")
        self.conn.commit()

    def _init_stats_table(self):
        """
        Initialize stats table with triggers for O(1) orphan count.

        Per SQLite best practices: maintain materialized counts via triggers
        instead of expensive COUNT queries on large tables.
        """
        self.conn.executescript("""
            -- Stats table for O(1) lookups
            CREATE TABLE IF NOT EXISTS stats (
                key TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0
            );

            -- Trigger: new node is orphan until linked (exclude purpose/proposal - they're chain starts)
            CREATE TRIGGER IF NOT EXISTS trg_node_insert_v2 AFTER INSERT ON nodes
            WHEN NEW.type NOT IN ('purpose', 'proposal')
            BEGIN
                UPDATE stats SET value = value + 1 WHERE key = 'orphan_count';
            END;

            -- Trigger: edge created reduces orphan count (if target exists and was orphan)
            CREATE TRIGGER IF NOT EXISTS trg_edge_insert_v2 AFTER INSERT ON edges
            BEGIN
                UPDATE stats SET value = value - 1
                WHERE key = 'orphan_count'
                AND (SELECT COUNT(*) FROM edges WHERE target_id = NEW.target_id) = 1
                AND EXISTS (SELECT 1 FROM nodes WHERE id = NEW.target_id AND type NOT IN ('purpose', 'proposal'));
            END;

            -- Trigger: edge deleted may increase orphan count
            CREATE TRIGGER IF NOT EXISTS trg_edge_delete_v2 AFTER DELETE ON edges
            BEGIN
                UPDATE stats SET value = value + 1
                WHERE key = 'orphan_count'
                AND NOT EXISTS (SELECT 1 FROM edges WHERE target_id = OLD.target_id)
                AND EXISTS (SELECT 1 FROM nodes WHERE id = OLD.target_id AND type NOT IN ('purpose', 'proposal'));
            END;

            -- Trigger: node deleted decreases orphan count if it was orphan
            CREATE TRIGGER IF NOT EXISTS trg_node_delete_v2 AFTER DELETE ON nodes
            WHEN OLD.type NOT IN ('purpose', 'proposal')
            BEGIN
                UPDATE stats SET value = value - 1
                WHERE key = 'orphan_count'
                AND NOT EXISTS (SELECT 1 FROM edges WHERE target_id = OLD.id);
            END;

            -- Drop old triggers (migration from v1)
            DROP TRIGGER IF EXISTS trg_node_insert;
            DROP TRIGGER IF EXISTS trg_edge_insert;
            DROP TRIGGER IF EXISTS trg_edge_delete;
            DROP TRIGGER IF EXISTS trg_node_delete;
        """)

        # Recalculate orphan_count (always, to handle migration from v1 triggers)
        # Proposals and purposes are excluded - they're intentional chain starts
        count = self.conn.execute("""
            SELECT COUNT(*) FROM nodes n
            WHERE n.type NOT IN ('purpose', 'proposal')
            AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.target_id = n.id)
        """).fetchone()[0]
        self.conn.execute(
            "INSERT OR REPLACE INTO stats (key, value) VALUES ('orphan_count', ?)",
            (count,)
        )

        self.conn.commit()

    def add_node(self, node: Node, auto_commit: bool = True):
        """
        Add node to graph.

        Args:
            node: Node to add
            auto_commit: If True, commit immediately (default for backward compat).
                         Set False for batch operations, then call commit() manually.
        """
        self.conn.execute(
            "INSERT OR REPLACE INTO nodes (id, type, content, event_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (node.id, node.type, orjson.dumps(node.content).decode(), node.event_id, node.created_at)
        )
        if auto_commit:
            self.conn.commit()

    def add_edge(self, edge: Edge, auto_commit: bool = True):
        """
        Add edge to graph.

        Args:
            edge: Edge to add
            auto_commit: If True, commit immediately (default for backward compat).
                         Set False for batch operations, then call commit() manually.
        """
        # Check for cycles before adding
        if self._would_create_cycle(edge):
            raise ValueError(f"Edge would create cycle: {edge.source_id} -> {edge.target_id}")

        self.conn.execute(
            "INSERT OR REPLACE INTO edges (source_id, target_id, relation, event_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (edge.source_id, edge.target_id, edge.relation, edge.event_id, edge.created_at)
        )
        if auto_commit:
            self.conn.commit()
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        row = self.conn.execute(
            "SELECT * FROM nodes WHERE id = ?", (node_id,)
        ).fetchone()

        if row:
            return Node(
                id=row['id'],
                type=row['type'],
                content=orjson.loads(row['content']),
                event_id=row['event_id'],
                created_at=row['created_at'] or ""
            )
        return None

    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """Get all nodes of a type."""
        rows = self.conn.execute(
            "SELECT * FROM nodes WHERE type = ?", (node_type,)
        ).fetchall()

        return [
            Node(id=r['id'], type=r['type'], content=orjson.loads(r['content']),
                 event_id=r['event_id'], created_at=r['created_at'] or "")
            for r in rows
        ]

    def get_nodes_by_type_recent(self, node_type: str, limit: int = 10) -> List[Node]:
        """Get most recent nodes of a type, ordered by created_at descending."""
        rows = self.conn.execute(
            "SELECT * FROM nodes WHERE type = ? ORDER BY created_at DESC LIMIT ?",
            (node_type, limit)
        ).fetchall()

        return [
            Node(id=r['id'], type=r['type'], content=orjson.loads(r['content']),
                 event_id=r['event_id'], created_at=r['created_at'] or "")
            for r in rows
        ]
    
    def get_outgoing(self, node_id: str) -> List[Tuple[Edge, Node]]:
        """Get all nodes this node points to."""
        rows = self.conn.execute("""
            SELECT e.*, n.id as n_id, n.type as n_type, n.content as n_content,
                   n.event_id as n_event_id, n.created_at as n_created_at
            FROM edges e
            JOIN nodes n ON e.target_id = n.id
            WHERE e.source_id = ?
        """, (node_id,)).fetchall()

        return [
            (
                Edge(source_id=r['source_id'], target_id=r['target_id'], relation=r['relation'],
                     event_id=r['event_id'], created_at=r['created_at'] or ""),
                Node(id=r['n_id'], type=r['n_type'], content=orjson.loads(r['n_content']),
                     event_id=r['n_event_id'], created_at=r['n_created_at'] or "")
            )
            for r in rows
        ]

    def get_incoming(self, node_id: str) -> List[Tuple[Edge, Node]]:
        """Get all nodes that point to this node."""
        rows = self.conn.execute("""
            SELECT e.*, n.id as n_id, n.type as n_type, n.content as n_content,
                   n.event_id as n_event_id, n.created_at as n_created_at
            FROM edges e
            JOIN nodes n ON e.source_id = n.id
            WHERE e.target_id = ?
        """, (node_id,)).fetchall()

        return [
            (
                Edge(source_id=r['source_id'], target_id=r['target_id'], relation=r['relation'],
                     event_id=r['event_id'], created_at=r['created_at'] or ""),
                Node(id=r['n_id'], type=r['n_type'], content=orjson.loads(r['n_content']),
                     event_id=r['n_event_id'], created_at=r['n_created_at'] or "")
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
    
    def find_orphans(self, limit: int = 0) -> List[Node]:
        """
        Find nodes with no incoming edges (potential orphans).

        Uses NOT EXISTS pattern for better query plan (per SQLite docs).

        Args:
            limit: Max orphans to return (0 = all). Use limit for display,
                   use count_orphans() for counts.
        """
        query = """
            SELECT n.* FROM nodes n
            WHERE n.type NOT IN ('purpose', 'proposal')
            AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.target_id = n.id)
        """
        if limit > 0:
            query += f" LIMIT {limit}"

        rows = self.conn.execute(query).fetchall()

        return [
            Node(id=r['id'], type=r['type'], content=orjson.loads(r['content']),
                 event_id=r['event_id'], created_at=r['created_at'] or "")
            for r in rows
        ]

    def count_orphans(self) -> int:
        """
        Get orphan count in O(1) from stats table.

        Maintained by triggers, no expensive COUNT query needed.
        """
        row = self.conn.execute(
            "SELECT value FROM stats WHERE key = 'orphan_count'"
        ).fetchone()
        return row[0] if row else 0

    def delete_nodes_by_type_pattern(
        self,
        node_type: str,
        pattern: str,
        exclude_pattern: str = None
    ) -> int:
        """
        Delete nodes of a specific type matching a content pattern.

        Used for clearing code_symbol nodes by file path pattern.
        Code symbols are cache (not intent), so deletion is safe.

        Args:
            node_type: Node type to delete (e.g., 'code_symbol')
            pattern: SQL LIKE pattern to match in content (e.g., '%.venv%')
            exclude_pattern: Optional pattern to exclude from deletion

        Returns:
            Number of nodes deleted
        """
        if exclude_pattern:
            cursor = self.conn.execute(
                """
                DELETE FROM nodes
                WHERE type = ? AND content LIKE ? AND content NOT LIKE ?
                """,
                (node_type, pattern, exclude_pattern)
            )
        else:
            cursor = self.conn.execute(
                "DELETE FROM nodes WHERE type = ? AND content LIKE ?",
                (node_type, pattern)
            )
        deleted = cursor.rowcount
        self.conn.commit()
        return deleted

    def rebuild_from_events(self, event_store: EventStore):
        """
        Rebuild entire projection from event stream (HC3 recovery).

        Uses batch commit pattern: all operations in single transaction,
        reducing thousands of fsyncs to one. Safe because projection is
        rebuildable — if interrupted, just rebuild again.
        """
        # Clear existing (including stats)
        self.conn.executescript("""
            DELETE FROM edges;
            DELETE FROM nodes;
            DELETE FROM stats;
        """)

        # Replay events with deferred commits (batch pattern)
        for event in event_store.read_all():
            self._project_event(event, auto_commit=False)

        # Single commit for entire rebuild (10-100x faster)
        self.conn.commit()

        # Recompute orphan count after rebuild (triggers don't fire in batch mode)
        count = self.conn.execute("""
            SELECT COUNT(*) FROM nodes n
            WHERE n.type != 'purpose'
            AND NOT EXISTS (SELECT 1 FROM edges e WHERE e.target_id = n.id)
        """).fetchone()[0]
        self.conn.execute(
            "INSERT OR REPLACE INTO stats (key, value) VALUES ('orphan_count', ?)",
            (count,)
        )
        self.conn.commit()

    def _project_event(self, event: Event, auto_commit: bool = True):
        """
        Project single event into graph.

        Args:
            event: Event to project
            auto_commit: If True, commit after each node/edge (default).
                         Set False for batch operations (e.g., rebuild).
        """
        if event.type == EventType.PURPOSE_DECLARED:
            self.add_node(Node(
                id=f"purpose_{event.id}",
                type="purpose",
                content=event.data,
                event_id=event.id,
                created_at=event.timestamp
            ), auto_commit=auto_commit)

        elif event.type == EventType.ARTIFACT_CONFIRMED:
            node_id = f"{event.data['artifact_type']}_{event.id}"
            self.add_node(Node(
                id=node_id,
                type=event.data['artifact_type'],
                content=event.data['content'],
                event_id=event.id,
                created_at=event.timestamp
            ), auto_commit=auto_commit)

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
                        event_id=event.id,
                        created_at=event.timestamp
                    ), auto_commit=auto_commit)

        elif event.type == EventType.STRUCTURE_PROPOSED:
            self.add_node(Node(
                id=f"proposal_{event.id}",
                type="proposal",
                content=event.data,
                event_id=event.id,
                created_at=event.timestamp
            ), auto_commit=auto_commit)

            # Link to source
            if event.data.get('source_id'):
                self.add_edge(Edge(
                    source_id=f"proposal_{event.id}",
                    target_id=event.data['source_id'],
                    relation="extracted_from",
                    event_id=event.id,
                    created_at=event.timestamp
                ), auto_commit=auto_commit)

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
                    event_id=event.id,
                    created_at=event.timestamp
                ), auto_commit=auto_commit)
                # Link both artifacts to the tension
                self.add_edge(Edge(
                    source_id=artifact_a,
                    target_id=tension_id,
                    relation="tensions_with",
                    event_id=event.id,
                    created_at=event.timestamp
                ), auto_commit=auto_commit)
                self.add_edge(Edge(
                    source_id=artifact_b,
                    target_id=tension_id,
                    relation="tensions_with",
                    event_id=event.id,
                    created_at=event.timestamp
                ), auto_commit=auto_commit)

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
                    event_id=event.id,
                    created_at=event.timestamp
                ), auto_commit=auto_commit)

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
                    event_id=event.id,
                    created_at=event.timestamp
                ), auto_commit=auto_commit)

        elif event.type == EventType.SYMBOL_INDEXED:
            # code_symbol: processor-backed symbol for strategic loading
            # Enables LLMs to query locations without loading full files
            symbol_id = f"code_symbol_{event.id}"
            self.add_node(Node(
                id=symbol_id,
                type="code_symbol",
                content={
                    "symbol_type": event.data.get("symbol_type"),
                    "name": event.data.get("name"),
                    "qualified_name": event.data.get("qualified_name"),
                    "file_path": event.data.get("file_path"),
                    "line_start": event.data.get("line_start"),
                    "line_end": event.data.get("line_end"),
                    "signature": event.data.get("signature"),
                    "docstring": event.data.get("docstring"),
                    "visibility": event.data.get("visibility", "public"),
                    "git_hash": event.data.get("git_hash")
                },
                event_id=event.id,
                created_at=event.timestamp
            ), auto_commit=auto_commit)

            # Create contains edge for nested symbols (method in class)
            parent_symbol = event.data.get("parent_symbol")
            if parent_symbol:
                # Parent contains this symbol
                self.add_edge(Edge(
                    source_id=parent_symbol,
                    target_id=symbol_id,
                    relation="contains",
                    event_id=event.id,
                    created_at=event.timestamp
                ), auto_commit=auto_commit)

    def stats(self) -> Dict[str, int]:
        """Return graph statistics (O(1) for orphan count via stats table)."""
        nodes = self.conn.execute("SELECT COUNT(*) as c FROM nodes").fetchone()['c']
        edges = self.conn.execute("SELECT COUNT(*) as c FROM edges").fetchone()['c']
        orphans = self.count_orphans()  # O(1) from stats table
        return {"nodes": nodes, "edges": edges, "orphans": orphans}

    def close(self):
        """
        Close database connection with optimization.

        Per SQLite docs: run PRAGMA optimize before closing long-lived connections
        to update query planner statistics.
        """
        self.conn.execute("PRAGMA optimize")
        self.conn.close()

    def commit(self):
        """Commit pending changes."""
        self.conn.commit()