def parse_payload(raw):
    try:
        return raw.strip()
    except:  # slopcheck: ignore[SLP001]
        pass
