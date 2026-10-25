def load_user(raw):
    try:
        return raw["id"]
    except Exception:
        return None
