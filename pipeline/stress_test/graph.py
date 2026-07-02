"""ClaimGraph: directed graph of moat claims with dedup, evidence cache, and decay aggregation."""
import hashlib
from dataclasses import dataclass, field


@dataclass
class ClaimNode:
    claim_text: str
    moat_type: str
    depth: int
    status: str = "pending"       # pending | searching | judged
    verdict: str = "inconclusive" # moat_holds | moat_challenged | inconclusive
    decay_score: float = 0.0
    evidence_summary: str = ""
    search_query: str = ""


class ClaimGraph:
    def __init__(self) -> None:
        self.nodes: dict[str, ClaimNode] = {}
        self.edges: dict[str, list[str]] = {}          # parent_id → [child_id, ...]
        self._evidence_cache: dict[str, str] = {}      # sha256(query:depth) → result

    # ── Node management ──────────────────────────────────────────────────────

    def add_claim(
        self,
        text: str,
        moat_type: str,
        depth: int,
        parent_id: str | None = None,
    ) -> str:
        node_id = self._claim_id(text)

        if node_id not in self.nodes:
            self.nodes[node_id] = ClaimNode(
                claim_text=text,
                moat_type=moat_type,
                depth=depth,
            )
            self.edges[node_id] = []

        if parent_id and parent_id in self.edges:
            if node_id not in self.edges[parent_id]:
                self.edges[parent_id].append(node_id)

        return node_id

    # ── Evidence cache ───────────────────────────────────────────────────────

    def get_cached_evidence(self, query: str, depth: int) -> str | None:
        return self._evidence_cache.get(self._evidence_key(query, depth))

    def cache_evidence(self, query: str, depth: int, result: str) -> None:
        self._evidence_cache[self._evidence_key(query, depth)] = result

    # ── Decay aggregation ────────────────────────────────────────────────────

    def aggregate_decay(self, node_id: str) -> float:
        node = self.nodes[node_id]
        children = self.edges.get(node_id, [])
        if not children:
            return node.decay_score
        child_decays = [self.aggregate_decay(c) for c in children]
        return max(node.decay_score, sum(child_decays) / len(child_decays))

    # ── Serialization ────────────────────────────────────────────────────────

    def serialize(self) -> dict:
        return {
            "nodes": {
                nid: {
                    "claim_text": n.claim_text,
                    "moat_type": n.moat_type,
                    "depth": n.depth,
                    "status": n.status,
                    "verdict": n.verdict,
                    "decay_score": n.decay_score,
                    "evidence_summary": n.evidence_summary,
                    "search_query": n.search_query,
                    "children": self.edges.get(nid, []),
                }
                for nid, n in self.nodes.items()
            },
            "edges": self.edges,
        }

    # ── Helpers ──────────────────────────────────────────────────────────────

    @staticmethod
    def _claim_id(text: str) -> str:
        normalized = text.strip().lower()
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    @staticmethod
    def _evidence_key(query: str, depth: int) -> str:
        return hashlib.sha256(f"{query}:{depth}".encode()).hexdigest()[:16]