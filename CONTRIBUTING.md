# Contributing to harness-ai-kit

Thank you for your interest in contributing! This document covers the basics.

## Getting Started

```bash
git clone https://github.com/seed-forge/harness-ai-kit.git
cd harness-ai-kit
pip install -e .
harness-ai-kit --version  # verify it works
```

## Developer Certificate of Origin (DCO)

All commits must be signed off (`git commit -s`). By signing off, you certify that you wrote the contribution. See [developercertificate.org](https://developercertificate.org/) for the full text.

## Development Workflow

1. Fork the repo and create a feature branch from `main`
2. Make your changes — keep commits atomic and focused
3. Ensure `python -c "import ai_kit"` works and `harness-ai-kit --help` runs cleanly
4. If you add or modify skills, run the validation: `python -c "import json; [json.loads(open(f'skills/{d}/skill.json').read()) for d in __import__('os').listdir('skills') if __import__('os').path.isfile(f'skills/{d}/skill.json')]"`
5. Submit a PR — CI will run lint, import check, CLI smoke test, and a sensitive-reference scan

## Code Style

- Python >= 3.10 (type hints required)
- Follow existing patterns — the codebase uses a DDD-style layering (domain/application/infrastructure)
- No hardcoded URLs, credentials, or internal hostnames — the CI sensitive-scan will reject them

## Adding a Skill

1. Create a directory under `skills/` with your skill name
2. Include `SKILL.md` (main document), `skill.json` (metadata), and `USAGE.md` (usage guide with a copy-pasteable Chinese prompt section)
3. Follow the `_template/` skill structure if present
4. The CI will validate your `skill.json` on every PR

## Reporting Issues

Use the issue templates. For bugs, include the `harness-ai-kit doctor` output. For feature requests, describe the use case.

## License

By contributing, you agree that your contributions are licensed under Apache-2.0.
