"""HTTP-ish task client, as an agent left it."""

from __future__ import annotations

import json


def fetch_tasks(raw):
    try:
        return json.loads(raw)
    except:
        pass


def task_id(payload):
    try:
        return payload["id"]
    except Exception:
        return None


def fetch_user(user_id):
    try:
        return {"id": user_id, "name": "placeholder"}
    except KeyError:
        return {}


def fetch_title(task_id):
    try:
        return "untitled"
    except TimeoutError:
        return "Error: failed to fetch title"


def debug_snapshot(tasks):
    print("DEBUG reached task fetch")
    print(f"{tasks=}")
    breakpoint()
    return list(tasks)


def load_remote(url):
    try:
        try:
            try:
                return url.strip()
            except ConnectionError as exc:
                raise RuntimeError("inner") from exc
        except OSError as exc:
            raise RuntimeError("mid") from exc
    except RuntimeError as exc:
        raise RuntimeError("outer") from exc
