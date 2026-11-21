"""Noninteractive agent adapters. Each invocation starts a new session."""

import json
import os
from pathlib import Path, PurePosixPath
import signal
import subprocess
import sys

from delivery import HELD_LOCKS


class FactoryError(ValueError):
    pass


class AgentUnavailable(FactoryError):
    """A transient process failure; the saved stage can be retried."""


def process(argv, cwd, prompt, log, timeout, stdout=None, env=None):
    """Keep full diagnostics on disk. Cancel the entire process group on timeout."""
    with log.open("wb") as output:
        child = subprocess.Popen(
            [sys.executable, "-I", Path(__file__).with_name("worker.py"), str(timeout), *argv],
            cwd=cwd, stdin=subprocess.PIPE, stdout=stdout or output, env=env,
            stderr=output, start_new_session=True, pass_fds=tuple(HELD_LOCKS),
        )
        try:
            child.communicate(prompt.encode(), timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait()
            if isinstance(exc, KeyboardInterrupt):
                raise
            raise AgentUnavailable(f"{argv[0]} timed out after {timeout}s (see {log})") from exc
        return child.returncode


def tail(path, limit=4000):
    with path.open("rb") as f:
        f.seek(max(0, path.stat().st_size - limit))
        return f.read().decode(errors="replace").strip()


def role_config(value):
    if isinstance(value, str):
        value = {"agent": value}
    if not isinstance(value, dict) or value.keys() - {"agent", "model"}:
        raise FactoryError("role must name an agent and optionally a model")
    if value.get("agent") not in ("claude", "codex"):
        raise FactoryError("select claude or codex for each role")
    if "model" in value and not (isinstance(value["model"], str) and value["model"].strip()):
        raise FactoryError("model must be a nonempty string")
    return value


def invoke(role, config, cwd, prompt, directory, timeout):
    outcomes = ["built", "blocked"] if role == "builder" else ["approve", "changes", "blocked"]
    schema = {"type": "object", "additionalProperties": False,
              "properties": {"outcome": {"type": "string", "enum": outcomes},
                             "summary": {"type": "string"}},
              "required": ["outcome", "summary"]}
    if role == "builder":
        schema["properties"]["intended_files"] = {
            "type": "array", "items": {"type": "string"},
            "description": "Exact repository-relative files intentionally kept as source changes, including generated snapshots."}
        schema["required"].append("intended_files")
    agent = config["agent"]
    log = directory / (role + ".log")
    model = ["--model", config["model"]] if "model" in config else []
    response = directory / (role + "-response.json")
    if agent == "codex":
        schema_path = directory / (role + "-schema.json")
        schema_path.write_text(json.dumps(schema))
        mode = "workspace-write" if role == "builder" else "read-only"
        argv = ["codex", "exec", "--ephemeral", "--ignore-user-config", "--sandbox", mode,
                "-c", 'approval_policy="never"', "--output-schema", str(schema_path),
                "-o", str(response), *model, "-"]
        rc = process(argv, cwd, prompt, log, timeout)
    else:
        allowed = "Read,Glob,Grep,StructuredOutput"
        if role == "builder":
            allowed += ",Edit,Write"
        argv = ["claude", "-p", "--restricted", "--strict-mcp-config", "--no-session-persistence",
                "--permission-mode", "dontAsk", "--tools", allowed, "--allowedTools", allowed,
                "--output-format", "json", "--json-schema", json.dumps(schema), *model]
        # Claude emits its result on stdout. Keep diagnostics out of its JSON.
        with response.open("wb") as stdout:
            rc = process(argv, cwd, prompt, log, timeout, stdout=stdout)
    if rc:
        diagnostic = tail(log, 1000)
        if agent == "claude" and response.stat().st_size:
            try:
                error = json.loads(response.read_text())
                diagnostic = str(error.get("result") or diagnostic)[:1000]
            except (AttributeError, ValueError):
                diagnostic = diagnostic or tail(response, 1000)
        raise AgentUnavailable(f"{agent} {role} exited {rc}: {diagnostic}")
    try:
        result = json.loads(response.read_text())
        if agent == "claude":
            if result.get("is_error") or result.get("subtype") != "success":
                raise FactoryError(f"Claude {role} failed: {str(result.get('result', result.get('subtype')))[:1000]}")
            result = result["structured_output"]
        if (set(result) != set(schema["required"]) or result["outcome"] not in outcomes
                or not isinstance(result["summary"], str) or not result["summary"].strip()):
            raise ValueError("invalid outcome or summary")
        if role == "builder":
            paths = result["intended_files"]
            if not isinstance(paths, list) or not all(
                isinstance(p, str) and p and "\0" not in p and "\\" not in p
                and not PurePosixPath(p).is_absolute() and PurePosixPath(p).as_posix() == p
                and p != "." and ".." not in PurePosixPath(p).parts
                and PurePosixPath(p).parts[0] != ".git" for p in paths
            ):
                raise ValueError("intended_files must contain exact repository-relative file paths")
    except FactoryError:
        raise
    except (OSError, AttributeError, TypeError, KeyError, ValueError) as exc:
        raise FactoryError(f"{agent} {role} returned an invalid structured response: {exc}") from exc
    return result
