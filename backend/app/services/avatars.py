from urllib.parse import quote_plus

_COLORS = ["6366f1", "8b5cf6", "0ea5e9", "10b981", "f59e0b", "ec4899", "14b8a6", "f43f5e"]


def avatar_for(name: str) -> str:
    """Placeholder profile picture from the free ui-avatars.com service (initials on a coloured tile)."""
    color = _COLORS[sum(ord(c) for c in name) % len(_COLORS)]
    return f"https://ui-avatars.com/api/?name={quote_plus(name)}&background={color}&color=fff&size=160&bold=true"
