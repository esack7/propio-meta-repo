"""Local checkpoints for factory attempts. Tracked delivery state remains authoritative."""

import json
from pathlib import Path
import tempfile

from agents import FactoryError
from delivery import atomic_json


def run_root(d):
    root = d.directory / ".factory-runs"
    if root.resolve() != root:
        raise FactoryError("unsafe factory run directory")
    return root


class Journal:
    def __init__(self, path, state):
        if path.resolve() != path:
            raise FactoryError("unsafe factory journal path")
        self.path = path
        self.state = state

    def save(self, phase, **fields):
        state = dict(self.state, phase=phase, **fields)
        atomic_json(self.path, state)
        self.state = state

    @classmethod
    def create(cls, d, data, packet, preview, mode, phase="start", **checkpoint):
        runs = run_root(d) / preview["slice"]
        if runs.resolve() != runs:
            raise FactoryError("unsafe factory slice directory")
        if list(runs.glob("run-*/journal.json")):
            raise FactoryError("this slice has a factory journal; use resume")
        runs.mkdir(parents=True, exist_ok=True)
        attempt = Path(tempfile.mkdtemp(prefix="run-", dir=runs))
        j = cls(attempt / "journal.json", {})
        state = dict(expected=data, packet=packet, plan=preview, repositories=d.repos,
                     pr_mode=mode, round=1, feedback="", version=1)
        j.save(phase, **dict(state, **checkpoint))
        return j

    @classmethod
    def for_slice(cls, d, sid):
        journals = list((run_root(d) / sid).glob("run-*/journal.json"))
        if not journals:
            return None
        if len(journals) > 1:
            raise FactoryError(f"{sid}: multiple journalled attempts; inspect the run directories")
        j = cls(journals[0], {})
        j.state = json.loads(j.path.read_text())
        if (j.state["version"] != 1 or j.state["plan"]["slice"] != sid
                or j.state["plan"]["spec"] != d.spec):
            raise FactoryError("factory journal does not match the selected slice")
        # Version 1 journals stored only the draft publication permission.
        j.state.setdefault("pr_mode", "draft" if j.state.get("draft") else "local")
        if j.state["pr_mode"] not in {"local", "draft", "ready"}:
            raise FactoryError("unknown PR handoff mode in the saved factory run")
        return j

    @classmethod
    def find(cls, d, sid):
        data = d.load()
        selected = [s for s in data["slices"] if sid is None or s["id"] == sid]
        found = []
        legacy = []
        for s in selected:
            if not sid and s["status"] in {"merged", "verified"}:
                continue
            journal = cls.for_slice(d, s["id"])
            if journal:
                found.append(journal)
            elif s["status"] in {"implementing", "review"} or (
                    s["status"] == "blocked" and s["note"].startswith("interrupted\n")):
                legacy.append(s["id"])
        if len(found) + len(legacy) > 1 and not sid:
            active = [j for j in found if j.state["phase"] not in {"local", "drafted", "ready", "blocked"}]
            if len(active) == 1 and not legacy:
                return active[0]
            raise FactoryError("multiple recoverable slices; select one with --slice")
        return next(iter(found), None)
