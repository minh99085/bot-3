# VPS full report — mandatory publish workflow (Bot 3)

**Non-negotiable:** The live bot MUST generate a **real, complete** full report on every tick.
Published snapshots go **only** to:

`https://github.com/minh99085/bot-3-clone-of-bot-1-/tree/main/vps_full_reports/latest`

## Engine (VPS)

Pulse engine writes the provenance bundle to `/data` inside `hermes-training`, including
`FULL_REPORT.md`. Missing `FULL_REPORT.md` after deploy = P0.

## Pull + publish

1. Wipe `vps_full_reports/latest/` before every pull.
2. Run `./scripts/pulse-babysit/pull-vps-artifacts.sh` (or `.ps1`).
3. Require `FULL_REPORT.md`; fail if absent.
4. Commit + push only the fresh snapshot to `origin/main`.

## Never

- Publish reports outside `vps_full_reports/latest/`
- Leave stale files in `latest/`
- Fake or inflate performance metrics
