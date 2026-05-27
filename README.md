# Unraid-Templates

Personal Unraid Community Applications templates.

## Templates

| Template | Description |
|---|---|
| [Hermes Agent + Whisper](templates/hermes-agent.xml) | [Hermes Agent](https://hermes-agent.nousresearch.com/) extended with [faster-whisper](https://github.com/SYSTRAN/faster-whisper) for local GPU-accelerated STT |

## Adding to Unraid Community Applications

In the Unraid CA plugin, go to **Settings → Community Applications** and add:

```
https://raw.githubusercontent.com/lbouriez/Unraid-Templates/main/templates/ca_profile.xml
```

## Docker images

Custom images live under `docker/` and are built automatically via GitHub Actions on push, published to [GHCR](https://github.com/lbouriez?tab=packages).

| Image | Base | Additions |
|---|---|---|
| `ghcr.io/lbouriez/hermes-agent` | `nousresearch/hermes-agent:latest` | `faster-whisper`, `nvidia-cudnn-cu12`, `nvidia-cublas-cu12` |

## License

MIT
