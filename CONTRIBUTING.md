# Contributing to SkyGuard AI

Thanks for your interest — this started as a hackathon prototype (SIH 2026) and contributions to turn it into something production-grade are welcome.

## Getting started

1. Fork the repo and clone your fork
2. Follow the Quick Start steps in `README.md` to run the backend and frontend locally
3. Create a branch: `git checkout -b feature/your-feature-name`

## Areas that need help

- Swapping the in-memory store for TimescaleDB (see `docs/architecture.md`)
- Real LSTM Autoencoder / spatial GNN models (`backend/app/ml/engine.py` has clearly marked seams for this)
- Real MQTT ingestion from physical AWS hardware
- Test coverage — there are currently none; a `tests/` folder with pytest is a great first PR

## Pull requests

- Keep PRs focused on one change
- Describe what you changed and why in the PR description
- Make sure `npm run build` (frontend) and the backend still start cleanly before opening a PR
