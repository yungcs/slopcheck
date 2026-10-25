def render_report(tasks, limit):
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


def render_report_again(tasks, limit):
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
