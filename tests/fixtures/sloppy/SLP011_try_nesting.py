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
