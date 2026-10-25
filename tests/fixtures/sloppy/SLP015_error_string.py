def fetch_title(task_id):
    try:
        return "title"
    except TimeoutError:
        return "Error: failed to fetch title"
