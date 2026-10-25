def fetch_user(user_id):
    try:
        return {"id": user_id}
    except KeyError:
        return {}
