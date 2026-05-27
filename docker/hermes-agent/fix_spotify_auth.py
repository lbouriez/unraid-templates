import sys

path = '/opt/hermes/hermes_cli/auth.py'
with open(path, 'r') as f:
    content = f.read()

# ---------- PATCH 1: full replacement (virgin auth.py) ----------
old1 = '''def _spotify_validate_redirect_uri(redirect_uri: str) -> tuple[str, int, str]:
    parsed = urlparse(redirect_uri)
    if parsed.scheme != "http":
        raise AuthError(
            "Spotify PKCE redirect_uri must use http://localhost or http://127.0.0.1.",
            provider="spotify",
            code="spotify_redirect_invalid",
        )
    host = parsed.hostname or ""
    if host not in {"127.0.0.1", "localhost"}:
        raise AuthError(
            "Spotify PKCE redirect_uri must point to localhost or 127.0.0.1.",
            provider="spotify",
            code="spotify_redirect_invalid",
        )
    if not parsed.port:
        raise AuthError(
            "Spotify PKCE redirect_uri must include an explicit localhost port.",
            provider="spotify",
            code="spotify_redirect_invalid",
        )
    return host, parsed.port, parsed.path or "/"'''

new1 = '''def _spotify_validate_redirect_uri(redirect_uri: str) -> tuple[str, int, str]:
    parsed = urlparse(redirect_uri)
    if parsed.scheme not in {"http", "https"}:
        raise AuthError(
            "Spotify PKCE redirect_uri must use http or https.",
            provider="spotify",
            code="spotify_redirect_invalid",
        )
    host = parsed.hostname or ""
    if not host:
        raise AuthError(
            "Spotify PKCE redirect_uri must include a hostname.",
            provider="spotify",
            code="spotify_redirect_invalid",
        )
    is_local = host in {"127.0.0.1", "localhost"}
    if is_local and not parsed.port:
        raise AuthError(
            "Spotify PKCE redirect_uri must include an explicit port.",
            provider="spotify",
            code="spotify_redirect_invalid",
        )
    bind_host = host if is_local else "0.0.0.0"
    import os as _os
    local_port = parsed.port or int(_os.environ.get("HERMES_SPOTIFY_LOCAL_PORT", "43827"))
    return bind_host, local_port, parsed.path or "/"'''

# ---------- PATCH 2: partial fix (scheme+host already patched, port guard remains) ----------
old2 = '''    if not parsed.port:
        raise AuthError(
            "Spotify PKCE redirect_uri must include an explicit port.",
            provider="spotify",
            code="spotify_redirect_invalid",
        )
    bind_host = host if host in {"127.0.0.1", "localhost"} else "0.0.0.0"
    return bind_host, parsed.port, parsed.path or "/"'''

new2 = '''    is_local = host in {"127.0.0.1", "localhost"}
    if is_local and not parsed.port:
        raise AuthError(
            "Spotify PKCE redirect_uri must include an explicit port.",
            provider="spotify",
            code="spotify_redirect_invalid",
        )
    bind_host = host if is_local else "0.0.0.0"
    import os as _os
    local_port = parsed.port or int(_os.environ.get("HERMES_SPOTIFY_LOCAL_PORT", "43827"))
    return bind_host, local_port, parsed.path or "/"'''

if old1 in content:
    content = content.replace(old1, new1)
    print('Applied PATCH 1 (full replacement)')
elif old2 in content:
    content = content.replace(old2, new2)
    print('Applied PATCH 2 (partial — auth.py was already half-patched)')
elif 'HERMES_SPOTIFY_LOCAL_PORT' in content:
    print('Already fully patched — nothing to do.')
    sys.exit(0)
else:
    print('ERROR: Could not find expected code block. auth.py may have been updated upstream.')
    print('Search for _spotify_validate_redirect_uri and patch manually.')
    sys.exit(1)

with open(path, 'w') as f:
    f.write(content)

print('PATCHED OK')