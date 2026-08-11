# Usage Scenarios — How to actually use these skills day-to-day

Installing a skill is only step one. The real question is: **when you sit down to do
real work, how do these skills get pulled into the loop?** This page answers that.

There are two distinct usage models, one for **skills** and one for **loops**.

> **No lock-in:** every skill is a plain Markdown+JSON folder. You can have your agent fetch it, `npx`-style pull it, or copy it by hand — ai-kit is not required to *use* a skill. What ai-kit adds is the **asset manifest** (`ai-kit.yml` + `ai-kit.lock`) plus reproducible `sync`, which is what makes the team flow in the [README](../README.md#team-collaboration--commit-the-manifest-not-the-assets) work.

---

## Model A: Skills + an SDD framework (recommended)

Skills are knowledge and methodology packaged for an AI agent. On their own they sit in
`.agents/skills/` waiting to be invoked. They deliver the most value when driven by a
**Spec-Driven Development (SDD) framework** that:

1. Takes your natural-language task,
2. Decomposes it into requirements / design / tasks,
3. Matches each sub-task against the installed skills,
4. Pulls the right skill in at the right step.

That decomposition-and-match step is what turns a pile of skills into a working system.

### Recommended pairing: Trellis

We use **[Trellis](https://github.com/)** (an SDD framework) as the primary driver. Trellis
reads the task, breaks it down, and routes each piece to a matching skill — exactly the
behavior these skills are designed for. Other SDD frameworks work too (Kiro spec workflow,
GitHub Spec-Kit); the model is the same.

```
You: "重构这个模块的数据访问层，消除 god-class"
        │
        ▼
   SDD framework (Trellis)
        │  decompose → match skills
        ▼
   ┌─────────────────────────────────────────────┐
   │ requirements.md   → devlab-spec-driven-dev   │
   │ design.md         → devlab-tech-debt-ops     │
   │ tasks.md (DB)     → public-mysql-expert-base │
   │ verify            → devlab-eval-driven-agent │
   └─────────────────────────────────────────────┘
```

### Concrete flows

**Flow 1 — Feature/refactor with spec discipline**
```bash
ai-kit add skill devlab-spec-driven-dev
ai-kit add skill devlab-tech-debt-ops
ai-kit sync
```
Then in your SDD framework: *"按 spec 驱动方式做这个重构：先出 requirements/design/tasks，我确认后再执行。"*
The framework loads `devlab-spec-driven-dev` for the workflow discipline and
`devlab-tech-debt-ops` for the refactor method.

**Flow 2 — Production incident**
```bash
ai-kit add skill diag-mysql-deadlock
ai-kit add skill public-mysql-expert-base
ai-kit sync
```
Ask your agent: *"MySQL 又死锁了，帮我诊断。"* — `diag-mysql-deadlock` walks the
lock-chain analysis, backed by the `public-mysql-expert-base` knowledge.

**Flow 3 — Building an AI application**
```bash
ai-kit add skill devlab-ai-agent-engineering
ai-kit add skill devlab-eval-driven-agent
ai-kit sync
```
The SDD framework uses `devlab-ai-agent-engineering` to shape the architecture and
`devlab-eval-driven-agent` to install the quality gates.

### Why an SDD framework instead of "just chatting"?

| Without SDD | With SDD + skills |
|-------------|-------------------|
| Skill sits unused unless you remember it | Framework matches the skill to the task automatically |
| Ad-hoc, drifts mid-task | Requirements/design/tasks as the source of truth |
| Hard to resume across sessions | Spec files carry progress forward |
| No verification gate | Eval/regression gate before "done" |

---

## Model B: Loops + a runtime

A **loop** is an autonomous, multi-turn workflow (diagnose → fix → verify → repeat until
converged or escalate). Unlike skills, a loop is **bound to a specific agent runtime**
because it drives that runtime's execution engine.

Supported runtime bindings:

| Runtime | Notes |
|---------|-------|
| **Codex** | `codex exec` non-interactive loop driver |
| **Claude Code** | Claude Code session as the loop executor |
| **Qoder** | Qoder runtime loop |
| **OpenClaw** | OpenClaw runtime loop |

```
loop = { driver: <runtime>, steps: [diagnose, fix, verify], stop: converged|escalate }
```

A loop picks its runtime, then repeatedly invokes skills within that runtime until the
stop condition is met. Example: a CI-auto-fix loop running on Codex will, on each failed
pipeline, invoke the relevant `diag-*` skill, generate a fix, run verification, and iterate.

> **Loops ship in v0.2.** The loop framework and the first curated loops (ci-auto-fix,
> eval-regression, incident diagnose-fix) are on the [roadmap](ROADMAP.md). Today, the
> skills above already work standalone inside any runtime; loops add the autonomous
> repeat-until-converged layer on top.

---

## Quick decision guide

| You want to… | Use |
|--------------|-----|
| Give your AI domain expertise (DB, Git, NL2SQL) | a `public-*-expert-base` skill |
| Troubleshoot a specific production failure | a `diag-*` skill |
| Run a disciplined feature/refactor workflow | `devlab-spec-driven-dev` + an SDD framework |
| Draft a patent / copyright / SOP document | a `patent-*` / `work-sc-*` / `document-*` skill |
| Automate a repeat-until-converged workflow | a **loop** (v0.2) bound to your runtime |

## See also

- [Skill Catalog](../CATALOG.md) — full categorized index
- [Quickstart](quickstart.md) — install your first skill
- [Concepts](concepts.md) — asset model, lockfile, runtime adapters
- [Examples](../examples/README.md) — copy-pasteable real-world flows
