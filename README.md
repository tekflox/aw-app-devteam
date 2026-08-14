# aw-app-devteam — the software-engineering agent team

Installs the agents that take a request from "somebody wants this" to
"this is merged", plus the thing that makes them a team rather than a list:

| Agent | Model | Contract |
|---|---|---|
| **Product Owner** | Opus | `aw-agent-product-owner` (shipped here) |
| **Architect** | Opus | `aw-agent-architect` (shipped here) |
| **Coder - Sonnet** | Sonnet | `aw-agent-coder` |
| **Coder - Opus** | Opus | `aw-agent-coder` |
| **Coder - Haiku** | Haiku | `aw-agent-coder` |
| **Coder - GPT5** | Codex / GPT-5 | `aw-agent-coder` |

…wired together by the **Agents Flow: Software Engineering**:

```
Source → Product Owner → Architect → Coder - Sonnet
                      ↘             ↘ Coder - Opus
                        (and back)  ↘ Coder - Haiku
                                    ↘ Coder - GPT5
```

Every Coder is also connected directly to the Product Owner. That edge is
not decoration: a coder that hits a genuine product question mid-task
should route it back rather than pick silently, and the flow is what tells
it who to route to.

## Why an app instead of clicking six times

A team of agents used to be a dozen unrelated things somebody created by
hand across two UIs — an agent row per member, a config bundle, a group,
a skill file each, then a flow graph drawn node by node to connect them.
Nothing linked them and nothing checked them, and every failure was silent:
an agent pointing at a skill slug that doesn't exist runs with no contract
(which reads as a bad model, not a missing file), and a team with no flow
is a set of agents that never hand off.

Here it's one manifest, and `tests/test_manifest.py` asserts the joins —
every flow node names a declared agent, every declared agent is wired into
the flow, every prompt and skill file referenced actually exists.

## Model choice is the only difference between the Coders

All four share one contract (`aw-agent-coder`) and one system prompt. Pick
by what the task is worth, not by what it's about:

- **Haiku** — the answer is already decided. Rename across 30 files, lint
  sweep, dependency bump.
- **Sonnet** — the default. Reach for it unless you have a reason not to.
- **Opus** — getting it wrong is expensive. Cross-subsystem changes, a bug
  that survived two fix attempts, a refactor with no tests to catch you.
- **GPT5** — a genuinely independent second opinion (different vendor, not
  the same model retried), and the fallback when Anthropic is degraded.

## Requirements

`aw-app-agents-platform-runners` **>= 0.55.0**. That floor is doing real
work: 0.55.0 is the first version whose provisioner can seed an
`agent_flows` entry, and it also ships the `aw-agent-coder` skill the four
Coders reference by slug. Install against an older one and you get six
agents, no flow, and no complaint — the half-installed state the version
floor exists to prevent.

`aw-app-kb` is optional but the team is materially worse without it: all
three contracts make `search_knowledge_base` a mandatory first step, and
the KB is what stops the Architect re-deciding something already decided.

## Seeded, not owned

Create-if-absent, matched by slug, **never updated and never removed on
uninstall** (see aw-workspace's `src/apps/agents.py`). Re-installing will
not overwrite a system prompt, a model choice or a flow graph you have
since tuned in the UI — which also means shipping a corrected prompt here
does not reach an existing install. Edit it in the UI, or ship a new slug.

## Tests

```bash
python3 -m pytest tests -q
```

The manifest *is* this app — no routes, no window, no CLI — so the tests
are entirely about whether the declarations are internally consistent.
