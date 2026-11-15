def fix_cut_caption_string(s: str) -> str:
    """Removes broken <a> tags from strings"""
    if s.count("<a") != s.count("</a"):
        return s.rsplit("<a", 1)[0]

    return s
