# Support

## Getting Help

| Channel | Best For | Response Time |
|---------|----------|---------------|
| [GitHub Discussions](https://github.com/seed-forge/harness-ai-kit/discussions) | General questions, ideas, show & tell | Community-driven |
| [Bug Reports](https://github.com/seed-forge/harness-ai-kit/issues/new?template=bug_report.md) | Reproducible bugs with error logs | 48h first response |
| [Feature Requests](https://github.com/seed-forge/harness-ai-kit/issues/new?template=feature_request.md) | New features or enhancements | 48h first response |
| [Skill Proposals](https://github.com/seed-forge/harness-ai-kit/issues/new?template=skill_proposal.md) | Suggest new curated skills | Next triage cycle |
| Security | See [SECURITY.md](SECURITY.md) | 48h acknowledgment |

## Before Opening an Issue

1. Run `ai-kit doctor` and attach the output
2. Check [existing issues](https://github.com/seed-forge/harness-ai-kit/issues) for duplicates
3. Read the [Quickstart](docs/quickstart.md) and [Concepts](docs/concepts.md) guides

## FAQ

**Q: Which AI runtimes are supported?**
A: Codex, Claude Code, Cursor, and Kiro. See `ai-kit list runtimes` for details.

**Q: Can I use ai-kit without a private registry?**
A: Yes. `ai-kit add skill <github-url>` installs directly from any GitHub repo.

**Q: How do I install skills globally (not per-project)?**
A: Use `ai-kit add skill <source> --scope global`.

**Q: Is there an offline mode?**
A: Yes. After the first sync, `ai-kit sync --offline` uses the local cache.
