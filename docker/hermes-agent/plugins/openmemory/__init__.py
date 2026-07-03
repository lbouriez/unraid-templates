"""OpenMemory memory provider — MemoryProvider interface.

Talks directly to the OpenMemory REST API (mem0-aio).
No mem0ai package needed.

Config via environment variables:
  OPENMEMORY_BASE_URL   — OpenMemory API root (default: http://192.168.10.37:8765)
  OPENMEMORY_USER_ID    — User identifier (default: hermes-user)
  OPENMEMORY_APP_NAME   — App name for metadata (default: hermes)

Or via $HERMES_HOME/openmemory.json.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, List, Optional

import httpx

from agent.memory_provider import MemoryProvider

logger = logging.getLogger(__name__)

# Circuit breaker
_BREAKER_THRESHOLD = 5
_BREAKER_COOLDOWN_SECS = 120

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    from hermes_constants import get_hermes_home

    config = {
        "base_url": os.environ.get("OPENMEMORY_BASE_URL", "http://192.168.10.37:8765"),
        "user_id": os.environ.get("OPENMEMORY_USER_ID", "hermes-user"),
        "app_name": os.environ.get("OPENMEMORY_APP_NAME", "hermes"),
    }

    config_path = get_hermes_home() / "openmemory.json"
    if config_path.exists():
        try:
            file_cfg = json.loads(config_path.read_text(encoding="utf-8"))
            config.update({k: v for k, v in file_cfg.items()
                           if v is not None and v != ""})
        except Exception:
            pass

    return config


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

PROFILE_SCHEMA = {
    "name": "openmemory_profile",
    "description": (
        "Retrieve all stored memories about the user — preferences, facts, "
        "project context. Use at conversation start."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}

SEARCH_SCHEMA = {
    "name": "openmemory_search",
    "description": (
        "Search memories by meaning. Returns relevant facts ranked by similarity."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to search for."},
            "top_k": {"type": "integer", "description": "Max results (default: 10, max: 50)."},
        },
        "required": ["query"],
    },
}

ADD_SCHEMA = {
    "name": "openmemory_add",
    "description": (
        "Store a durable fact about the user. Stored verbatim (no LLM extraction). "
        "Use for explicit preferences, corrections, or decisions."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content": {"type": "string", "description": "The fact to store."},
        },
        "required": ["content"],
    },
}

UPDATE_SCHEMA = {
    "name": "openmemory_update",
    "description": "Update a memory's content by ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "string", "description": "The memory ID to update."},
            "content": {"type": "string", "description": "New content for the memory."},
        },
        "required": ["memory_id", "content"],
    },
}

DELETE_SCHEMA = {
    "name": "openmemory_delete",
    "description": "Delete a memory by ID.",
    "parameters": {
        "type": "object",
        "properties": {
            "memory_id": {"type": "string", "description": "The memory ID to delete."},
        },
        "required": ["memory_id"],
    },
}


# ---------------------------------------------------------------------------
# MemoryProvider implementation
# ---------------------------------------------------------------------------

class OpenMemoryProvider(MemoryProvider):
    """OpenMemory memory provider — direct REST API."""

    def __init__(self):
        self._config = None
        self._base_url = ""
        self._user_id = "hermes-user"
        self._app_name = "hermes"
        self._client: Optional[httpx.Client] = None
        self._client_lock = threading.Lock()
        self._prefetch_result = ""
        self._prefetch_lock = threading.Lock()
        self._prefetch_thread = None
        self._sync_thread = None
        # Circuit breaker
        self._consecutive_failures = 0
        self._breaker_open_until = 0.0

    @property
    def name(self) -> str:
        return "openmemory"

    def is_available(self) -> bool:
        cfg = _load_config()
        base = cfg.get("base_url", "")
        return bool(base)

    def get_config_schema(self):
        return [
            {"key": "base_url", "description": "OpenMemory API base URL",
             "default": "http://192.168.10.37:8765", "env_var": "OPENMEMORY_BASE_URL"},
            {"key": "user_id", "description": "User identifier",
             "default": "hermes-user", "env_var": "OPENMEMORY_USER_ID"},
            {"key": "app_name", "description": "App name for metadata",
             "default": "hermes", "env_var": "OPENMEMORY_APP_NAME"},
        ]

    def save_config(self, values, hermes_home):
        from pathlib import Path
        config_path = Path(hermes_home) / "openmemory.json"
        existing = {}
        if config_path.exists():
            try:
                existing = json.loads(config_path.read_text())
            except Exception:
                pass
        existing.update(values)
        config_path.write_text(json.dumps(existing, indent=2))

    def initialize(self, session_id: str, **kwargs) -> None:
        self._config = _load_config()
        self._base_url = self._config.get("base_url", "http://192.168.10.37:8765").rstrip("/")
        self._user_id = kwargs.get("user_id") or self._config.get("user_id", "hermes-user")
        self._app_name = self._config.get("app_name", "hermes")

    def _get_client(self) -> httpx.Client:
        with self._client_lock:
            if self._client is None:
                self._client = httpx.Client(base_url=self._base_url, timeout=30.0)
            return self._client

    def _is_breaker_open(self) -> bool:
        if self._consecutive_failures < _BREAKER_THRESHOLD:
            return False
        if time.monotonic() >= self._breaker_open_until:
            self._consecutive_failures = 0
            return False
        return True

    def _record_success(self):
        self._consecutive_failures = 0

    def _record_failure(self):
        self._consecutive_failures += 1
        if self._consecutive_failures >= _BREAKER_THRESHOLD:
            self._breaker_open_until = time.monotonic() + _BREAKER_COOLDOWN_SECS
            logger.warning(
                "OpenMemory circuit breaker tripped after %d consecutive failures. "
                "Pausing API calls for %ds.",
                self._consecutive_failures, _BREAKER_COOLDOWN_SECS,
            )

    def _api_get(self, path: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """GET request to OpenMemory API with error handling."""
        if self._is_breaker_open():
            return None
        try:
            client = self._get_client()
            r = client.get(path, params=params)
            r.raise_for_status()
            self._record_success()
            return r.json()
        except Exception as e:
            self._record_failure()
            logger.warning("OpenMemory GET %s failed: %s", path, e)
            return None

    def _api_post(self, path: str, data: Dict) -> Optional[Dict]:
        """POST request to OpenMemory API with error handling."""
        if self._is_breaker_open():
            return None
        try:
            client = self._get_client()
            r = client.post(path, json=data)
            r.raise_for_status()
            self._record_success()
            if r.text and r.text.strip():
                return r.json()
            return {"success": True}
        except Exception as e:
            self._record_failure()
            logger.warning("OpenMemory POST %s failed: %s", path, e)
            return None

    def _api_put(self, path: str, data: Dict) -> Optional[Dict]:
        """PUT request to OpenMemory API."""
        if self._is_breaker_open():
            return None
        try:
            client = self._get_client()
            r = client.put(path, json=data)
            r.raise_for_status()
            self._record_success()
            if r.text and r.text.strip():
                return r.json()
            return {"success": True}
        except Exception as e:
            self._record_failure()
            logger.warning("OpenMemory PUT %s failed: %s", path, e)
            return None

    def _api_delete(self, path: str, data: Optional[Dict] = None) -> Optional[Dict]:
        """DELETE request to OpenMemory API."""
        if self._is_breaker_open():
            return None
        try:
            client = self._get_client()
            r = client.request("DELETE", path, json=data)
            r.raise_for_status()
            self._record_success()
            if r.text and r.text.strip():
                return r.json()
            return {"success": True}
        except Exception as e:
            self._record_failure()
            logger.warning("OpenMemory DELETE %s failed: %s", path, e)
            return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def system_prompt_block(self) -> str:
        return (
            "# OpenMemory Memory\n"
            f"Active. User: {self._user_id}.\n"
            "Use openmemory_search to find memories, openmemory_add to store facts, "
            "openmemory_profile for a full overview."
        )

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        if self._prefetch_thread and self._prefetch_thread.is_alive():
            self._prefetch_thread.join(timeout=3.0)
        with self._prefetch_lock:
            result = self._prefetch_result
            self._prefetch_result = ""
        if not result:
            return ""
        return f"## OpenMemory Memory\n{result}"

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        if self._is_breaker_open():
            return

        def _run():
            try:
                results = self._api_post("/api/v1/memories/filter", {
                    "user_id": self._user_id,
                    "search_query": query,
                    "page": 1,
                    "size": 5,
                })
                if results:
                    items = results.get("items", [])
                    if items:
                        lines = [f"- {m.get('content', '')}" for m in items if m.get("content")]
                        with self._prefetch_lock:
                            self._prefetch_result = "\n".join(lines)
            except Exception as e:
                logger.debug("OpenMemory prefetch failed: %s", e)

        self._prefetch_thread = threading.Thread(target=_run, daemon=True, name="openmemory-prefetch")
        self._prefetch_thread.start()

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        """Send the turn to OpenMemory for fact extraction (non-blocking)."""
        if self._is_breaker_open():
            return

        def _sync():
            try:
                text = f"User: {user_content}\nAssistant: {assistant_content}"
                self._api_post("/api/v1/memories/", {
                    "user_id": self._user_id,
                    "text": text,
                    "infer": True,
                    "app": self._app_name,
                    "metadata": {"channel": "hermes", "session_id": session_id},
                })
            except Exception as e:
                logger.warning("OpenMemory sync failed: %s", e)

        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)

        self._sync_thread = threading.Thread(target=_sync, daemon=True, name="openmemory-sync")
        self._sync_thread.start()

    # ------------------------------------------------------------------
    # Tools
    # ------------------------------------------------------------------

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [PROFILE_SCHEMA, SEARCH_SCHEMA, ADD_SCHEMA, UPDATE_SCHEMA, DELETE_SCHEMA]

    def handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str:
        if tool_name == "openmemory_profile":
            return self._handle_profile()
        elif tool_name == "openmemory_search":
            return self._handle_search(args)
        elif tool_name == "openmemory_add":
            return self._handle_add(args)
        elif tool_name == "openmemory_update":
            return self._handle_update(args)
        elif tool_name == "openmemory_delete":
            return self._handle_delete(args)
        return json.dumps({"error": f"Unknown tool: {tool_name}"})

    def _handle_profile(self) -> str:
        result = self._api_get("/api/v1/memories/", params={
            "user_id": self._user_id,
            "page": 1,
            "size": 100,
        })
        if not result:
            return json.dumps({"memories": [], "error": "Could not fetch memories"})
        items = result.get("items", [])
        memories = [{"id": m["id"], "content": m["content"],
                      "created_at": m.get("created_at")} for m in items]
        return json.dumps({"memories": memories, "total": result.get("total", 0)})

    def _handle_search(self, args: dict) -> str:
        query = args.get("query", "")
        top_k = min(args.get("top_k", 10), 50)
        result = self._api_post("/api/v1/memories/filter", {
            "user_id": self._user_id,
            "search_query": query,
            "page": 1,
            "size": top_k,
        })
        if not result:
            return json.dumps({"results": [], "error": "Search failed"})
        items = result.get("items", [])
        results = [{"id": m["id"], "memory": m["content"],
                     "created_at": m.get("created_at")} for m in items]
        return json.dumps({"results": results})

    def _handle_add(self, args: dict) -> str:
        content = args.get("content", "")
        result = self._api_post("/api/v1/memories/", {
            "user_id": self._user_id,
            "text": content,
            "infer": False,
            "app": self._app_name,
        })
        if result:
            return json.dumps({"success": True, "id": result.get("id")})
        return json.dumps({"success": False, "error": "Failed to store memory"})

    def _handle_update(self, args: dict) -> str:
        memory_id = args.get("memory_id", "")
        content = args.get("content", "")
        result = self._api_put(f"/api/v1/memories/{memory_id}", {
            "memory_content": content,
            "user_id": self._user_id,
        })
        if result:
            return json.dumps({"success": True})
        return json.dumps({"success": False, "error": "Failed to update memory"})

    def _handle_delete(self, args: dict) -> str:
        memory_id = args.get("memory_id", "")
        result = self._api_delete("/api/v1/memories/", data={
            "memory_ids": [memory_id],
            "user_id": self._user_id,
        })
        if result:
            return json.dumps({"success": True})
        return json.dumps({"success": False, "error": "Failed to delete memory"})

    def shutdown(self) -> None:
        if self._sync_thread and self._sync_thread.is_alive():
            self._sync_thread.join(timeout=5.0)
        if self._prefetch_thread and self._prefetch_thread.is_alive():
            self._prefetch_thread.join(timeout=3.0)
        with self._client_lock:
            if self._client:
                self._client.close()
                self._client = None

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Mirror built-in memory writes to OpenMemory."""
        text = f"[{action}/{target}] {content}"
        self._api_post("/api/v1/memories/", {
            "user_id": self._user_id,
            "text": text,
            "infer": False,
            "app": self._app_name,
            "metadata": {"source": "builtin-mirror", **(metadata or {})},
        })
