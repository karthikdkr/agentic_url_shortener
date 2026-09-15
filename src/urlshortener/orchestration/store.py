from __future__ import annotations

import json
import threading
from pathlib import Path

from .workflow_models import WorkflowRun


class WorkflowStore:
    """Atomic JSON state store suitable for a single prototype process."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

    def _load_all(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        raw = self.path.read_text(encoding="utf8").strip()
        return json.loads(raw) if raw else {}

    def save(self, run: WorkflowRun) -> None:
        with self._lock:
            items = self._load_all()
            items[run.id] = run.model_dump(mode="json")
            temp = self.path.with_suffix(self.path.suffix + ".tmp")
            temp.write_text(json.dumps(items, indent=2, sort_keys=True), encoding="utf8")
            temp.replace(self.path)

    def get(self, run_id: str) -> WorkflowRun | None:
        with self._lock:
            payload = self._load_all().get(run_id)
        return WorkflowRun.model_validate(payload) if payload else None

    def all(self) -> list[WorkflowRun]:
        with self._lock:
            items = self._load_all()
        return [WorkflowRun.model_validate(value) for value in items.values()]
