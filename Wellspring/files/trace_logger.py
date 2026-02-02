"""
Trace Logger - Log development work as prototype thoughts.

Each thread imports this and logs decisions, questions, findings, etc.
Outputs to thread-specific JSONL. Thread 2 will index when ready.
"""

import json
import time
from pathlib import Path
from typing import Optional, List

# Thread-specific output paths
TRACE_PATHS = {
    1: Path("/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/thread-1/traces.jsonl"),
    2: Path("/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/thread-2/traces.jsonl"),
    3: Path("/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/thread-3/traces.jsonl"),
    0: Path("/sessions/upbeat-quirky-turing/mnt/Wellspring Eternal/files/traces.jsonl"),  # coordinator
}

class TraceLogger:
    def __init__(self, thread_id: int, source: Optional[str] = None):
        self.thread_id = thread_id
        self.source = source or f"cowork/thread-{thread_id}"
        self.path = TRACE_PATHS.get(thread_id, TRACE_PATHS[0])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._last_cid: Optional[str] = None

    def _compute_cid(self, content: dict) -> str:
        """Simple CID for traces (not cryptographically signed yet)."""
        import hashlib
        canonical = json.dumps(content, sort_keys=True, separators=(',', ':'))
        digest = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        return f"trace:{digest}"

    def log(
        self,
        category: str,
        title: str,
        body: str = "",
        because: Optional[List[str]] = None,
        chain_previous: bool = False
    ) -> str:
        """
        Log a trace thought.

        Args:
            category: decision, question, finding, artifact, bug, reference
            title: Short description
            body: Details
            because: List of CIDs this thought references
            chain_previous: If True, automatically link to last logged thought

        Returns:
            CID of the logged thought
        """
        if because is None:
            because = []

        if chain_previous and self._last_cid:
            because = [self._last_cid] + because

        thought = {
            "type": "trace",
            "content": {
                "category": category,
                "title": title,
                "body": body,
                "thread": self.thread_id
            },
            "source": self.source,
            "because": because,
            "created_at": int(time.time() * 1000)
        }

        thought["cid"] = self._compute_cid(thought)
        self._last_cid = thought["cid"]

        with open(self.path, 'a') as f:
            f.write(json.dumps(thought) + '\n')

        return thought["cid"]

    # Convenience methods
    def decision(self, title: str, body: str = "", **kwargs) -> str:
        return self.log("decision", title, body, **kwargs)

    def question(self, title: str, body: str = "", **kwargs) -> str:
        return self.log("question", title, body, **kwargs)

    def finding(self, title: str, body: str = "", **kwargs) -> str:
        return self.log("finding", title, body, **kwargs)

    def artifact(self, title: str, body: str = "", **kwargs) -> str:
        return self.log("artifact", title, body, **kwargs)

    def bug(self, title: str, body: str = "", **kwargs) -> str:
        return self.log("bug", title, body, **kwargs)

    def reference(self, title: str, body: str = "", **kwargs) -> str:
        return self.log("reference", title, body, **kwargs)


# Quick access for each thread
def thread1() -> TraceLogger:
    return TraceLogger(1)

def thread2() -> TraceLogger:
    return TraceLogger(2)

def thread3() -> TraceLogger:
    return TraceLogger(3)

def coordinator() -> TraceLogger:
    return TraceLogger(0, source="cowork/coordinator")


if __name__ == "__main__":
    # Demo
    log = coordinator()

    cid1 = log.decision(
        "Using JSONL for trace storage",
        "SQLite graph commits wait for Thread 2. JSONL is append-only, simple, mergeable."
    )
    print(f"Logged decision: {cid1}")

    cid2 = log.finding(
        "Trace format works",
        "Basic logging to JSONL functional.",
        chain_previous=True  # Links to previous thought
    )
    print(f"Logged finding: {cid2}")

    print(f"\nTraces written to: {log.path}")
