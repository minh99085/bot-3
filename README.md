# Bot-3 (clone of Bot-1)

**Bot 3 Directional** — standalone BTC/ETH pulse paper bot (Hermes trading engine).

| | Bot 3 |
|---|-------|
| **Strategy** | Directional paper (tier engine + loop architecture) |
| **VPS** | `207.246.96.45` (`/opt/Bot-3`) |
| **Dashboard** | http://207.246.96.45/dashboard |
| **TradingView** | http://207.246.96.45/webhooks/tradingview |
| **Deploy** | `.\scripts\sync-vps-bot3.ps1` |

## Quick start (VPS deploy)

1. Paste your TradingView secret into `hermes-agent-main/plugins/hermes-trading-engine/tradingview.secret` (one line).
2. From the repo root on your laptop:

```powershell
cd C:\hermes-agent\bot-3-clone-of-bot-1-
git pull origin main
.\scripts\sync-vps-bot3.ps1
```

The deploy script applies env (`Bot 3 Directional` dashboard label, TV context/tier gates ON, port 80), validates secrets, rebuilds Docker, and starts the loop.

**Note:** Port 80 can host only one bot. If Bot-1 is still running on this VPS, stop it first (`docker compose down` in `/opt/Bot-1/...`) or use a different `VpsHost` in `sync-vps-bot3.ps1`.

## Local training (Docker Desktop)

```powershell
.\scripts\run-bot3-local-training.ps1
```

Dashboard: http://localhost:8810/dashboard (label: `Bot 3 - Local Training`, TV gates OFF for focused local runs).

**TradingView (local):** copy `tradingview.secret.example` → `tradingview.secret`, paste secret, restart. Expose with `ngrok http 8810` → `https://<ngrok>/webhooks/tradingview`.

Profile: `scripts/bot-profile.json`