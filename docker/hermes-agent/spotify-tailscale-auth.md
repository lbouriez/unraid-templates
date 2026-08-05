# Spotify Auth via Tailscale — Setup & Recovery Guide

## Context

Hermes runs in a Docker container with no direct HTTPS exposure.
Tailscale provides a stable HTTPS hostname: `https://<your-machine>.ts.net`
Tailscale terminates TLS and proxies to Hermes's local HTTP servers.

> **Custom image users:** `fix_spotify_auth.py` is pre-bundled at `/opt/fix_spotify_auth.py`
> — no need to create it manually.

---

## Dashboard via Tailscale

The Hermes dashboard binds to `127.0.0.1` (loopback) by default — this bypasses the
auth gate (upstream `dashboard_auth` provider plugins are not yet shipped). Use
`tailscale serve` to expose it securely on your tailnet. Tailscale itself acts as the
auth layer (tailnet membership required).

In the Unraid Docker template, add a **Tailscale Serve** entry:

| Field | Value |
|---|---|
| Tailscale Serve | `https://<your-machine>.ts.net:9119` |
| Tailscale Serve Target | `http://localhost:9119` |

Access the dashboard at `https://<your-machine>.ts.net:9119` from any device on your tailnet.

> WebSocket (Chat/TUI tab) works through Tailscale serve — the dashboard sees the
> connection as loopback, so no auth gate triggers.

---

## Spotify Auth via Tailscale

## One-Time Setup (do this after a fresh container or wipe)

### Step 1 — Patch auth.py

Hermes's Spotify auth code only allows `http://localhost` as redirect URI.
We need to remove those guards so it accepts any HTTPS host + falls back to a local port.

Run from the **Unraid host**:

```bash
docker exec -u 0 hermes python3 /opt/fix_spotify_auth.py
```

Expected output: `PATCHED OK`

If you are using the upstream `nousresearch/hermes-agent` image instead of this custom build,
create the script manually (see **Appendix A** below) then run it.

---

### Step 2 — Configure Tailscale serve (survives restarts)

This makes Tailscale proxy HTTPS traffic on port 443 → local HTTP on port 43827.

#### Option A — Unraid UI (recommended, persists across restarts)

In the Unraid Docker template for the Hermes container, set these fields:

| Field | Value |
|---|---|
| Tailscale Serve | `https://<your-machine>.ts.net` |
| Tailscale Serve Target | `http://localhost:43827` |

Save and restart the container. Tailscale serve will start automatically on every boot. ✅

#### Option B — Manual command (temporary, lost on restart)

Run **inside the Hermes container** (or via `docker exec hermes`):

```bash
tailscale serve --bg http://localhost:43827
```

Verify it's running:

```bash
tailscale serve status
```

You should see something like:
```
https://<your-machine>.ts.net (tailnet only)
|-- / proxy http://localhost:43827
```

> ⚠️ This does NOT survive container restarts — prefer Option A.

---

### Step 3 — Set the redirect URI in .env

```bash
sed -i 's|HERMES_SPOTIFY_REDIRECT_URI=.*|HERMES_SPOTIFY_REDIRECT_URI=https://<your-machine>.ts.net/spotify/callback|' /opt/data/.env
```

Verify:
```bash
grep SPOTIFY_REDIRECT /opt/data/.env
```

Expected:
```
HERMES_SPOTIFY_REDIRECT_URI=https://<your-machine>.ts.net/spotify/callback
```

---

### Step 4 — Allow the redirect URI in Spotify Developer Dashboard

1. Go to https://developer.spotify.com/dashboard
2. Select your Hermes app
3. Edit Settings → Redirect URIs
4. Add: `https://<your-machine>.ts.net/spotify/callback`
5. Save

---

### Step 5 — Authenticate

Inside the container:

```bash
hermes auth spotify
```

Copy the authorization URL, open it in your browser, approve access.
Hermes will catch the callback automatically via Tailscale → port 43827.

---

## After a Container Restart

The **patch** (Step 1) survives restarts (it modifies the source file).
The **.env** (Step 3) survives (it's on the volume).
The **Spotify token** survives (stored in `auth.json` on the volume).

**Tailscale serve** — depends on how you set it up:
- ✅ If you used the **Unraid UI (Option A)** → survives automatically, nothing to do
- ❌ If you used the **manual command (Option B)** → must rerun:

```bash
tailscale serve --bg http://localhost:43827
```

You should NOT need to re-auth Spotify unless tokens expired.

---

## Appendix A — fix_spotify_auth.py (manual fallback)

> **Skip this if using the custom image** — the script is already at `/opt/fix_spotify_auth.py`.

For the upstream `nousresearch/hermes-agent` image, save the contents of
[`fix_spotify_auth.py`](./fix_spotify_auth.py) to `/opt/data/fix_spotify_auth.py`
inside the container, then run it with:

```bash
docker exec -u 0 hermes python3 /opt/data/fix_spotify_auth.py
```

---

## Appendix B — Quick Reference

| What | Command |
|---|---|
| Apply source patch (custom image) | `docker exec -u 0 hermes python3 /opt/fix_spotify_auth.py` |
| Apply source patch (upstream image) | `docker exec -u 0 hermes python3 /opt/data/fix_spotify_auth.py` |
| Start Tailscale proxy | `tailscale serve --bg http://localhost:43827` |
| Check Tailscale proxy | `tailscale serve status` |
| Update redirect URI | `sed -i 's\|HERMES_SPOTIFY_REDIRECT_URI=.*\|HERMES_SPOTIFY_REDIRECT_URI=https://<your-machine>.ts.net/spotify/callback\|' /opt/data/.env` |
| Run auth | `hermes auth spotify` |
| Spotify Dashboard | https://developer.spotify.com/dashboard |