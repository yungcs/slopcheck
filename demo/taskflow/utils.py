"""Summaries, stubs, and a second copy of the same function."""

from __future__ import annotations


def next_index(index):
    # increment index
    index += 1
    return index


# This function returns the count
def task_count(tasks):
    """Return the number of tasks.

    This helper exists so callers do not have to call len themselves.
    It accepts any sequence and returns an integer.

    Args:
        tasks: The tasks to count.

    Returns:
        The number of tasks.
    """
    return len(tasks)


def _format_legacy_banner(text):
    return "*** " + text + " ***"


def greeting():
    name = "ada"
    if name is not None:
        return name.upper()
    return ""


def export_tasks(tasks, path):
    """Write tasks somewhere eventually."""
    pass


def archive_label(status):
    # status = "archived"
    # owner = "ada"
    return status.replace("-", " ")


def summarize_tasks(tasks, limit):
    rows = []
    index = 0
    for task in tasks:
        title = str(task.get("title", ""))
        owner = str(task.get("owner", ""))
        status = str(task.get("status", "open"))
        if status == "archived":
            continue
        if len(rows) >= limit:
            break
        label = f"{title} ({owner})"
        rows.append(label.strip())
        index += 1
    if not rows:
        return "no tasks"
    header = f"{index} shown"
    return header + "\n" + "\n".join(rows)


def summarize_tasks_v2(tasks, limit):
    rows = []
    index = 0
    for task in tasks:
        title = str(task.get("title", ""))
        owner = str(task.get("owner", ""))
        status = str(task.get("status", "open"))
        if status == "archived":
            continue
        if len(rows) >= limit:
            break
        label = f"{title} ({owner})"
        rows.append(label.strip())
        index += 1
    if not rows:
        return "no tasks"
    header = f"{index} shown"
    return header + "\n" + "\n".join(rows)
