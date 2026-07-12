# Monitoring (Bot 3)

| Layer | Location |
|-------|----------|
| Live dashboard | http://207.246.96.45/dashboard |
| Design manifest | `monitoring/design-manifest.json` |
| Timeline | `monitoring/timeline.jsonl` |
| Full VPS reports | `vps_full_reports/latest/` |

## Pull artifacts

```bash
./scripts/pulse-babysit/pull-vps-artifacts.sh
```

## Deploy

```bash
./scripts/sync-vps-bot3.sh
```
