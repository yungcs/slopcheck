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
