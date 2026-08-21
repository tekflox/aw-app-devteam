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
| **UX Coder - Sonnet** | Sonnet | `aw-agent-ux-coder` |
| **Debugger** | Sonnet | `aw-agent-debugger` |
| **Code Reviewer - Sonnet** | Sonnet | `aw-agent-code-reviewer` |
| **Doc Writer** | Sonnet | `aw-agent-doc-writer` |
| **QA - Sonnet** | Sonnet | `aw-agent-qa` |
| **QA - Haiku** | Haiku | `aw-agent-qa` |

…wired together by the **Agents Flow: Software Engineering**:

```
        ┌──── UX Coder ─────────────────┐
        │        ↑                      ↓
Source → Product Owner → Architect → [Coders] → [QAs]
   │  │       └──────── (and back) ─────┘  │      ↑
   │  └──────────────────────────────────────────-┘
   ├──→ Debugger ───────────────────────┘  │
   └──→ Doc Writer ◄───────────────────────┘
```

Eight nodes, not eleven: `[Coders]` and `[QAs]` are **group** nodes. The
rest are wired individually because their position is their own — the PO
and the Architect are single roles, the UX Coder skips a hop the Coders
group does not, the Debugger enters ahead of scoping, and the Doc Writer
is the one role that bypasses QA entirely.

That is not a drawing convenience. A group node expands to its members at
dispatch, so a fifth Coder model variant joins the flow by being given
`group_slug: "coders"` — nobody opens the editor, and nobody has to
remember to. It also halves the graph: collapsing the four coder boxes
took the flow from 19 edges to 10 without removing a single handoff.

Three edges there are load-bearing, not decoration:

- **Coders connect straight to the Product Owner.** A coder that hits a
  genuine product question mid-task should route it back rather than pick
  silently, and the flow is what tells it who to route to.
- **UX Coder hangs off Source and the PO, skipping the Architect.** A
  prototype that waits on an architecture decision has stopped being a
  prototype. This is not a preference: `aw-agent-ux-coder` already tells
  that agent it is "a node connected to Source and the Product Owner", so
  `tests/test_manifest.py` asserts the graph agrees with the skill. The
  skill is what the agent actually reads; if the two disagree, the graph
  is the bug.
- **Every builder edges into QAs, and adjacency is two-way.** That is what
  makes "QA reviews, QA never fixes" workable: a QA holding a broken
  delivery has somewhere to send it, so it never has to repair the thing
  it was reviewing just to keep the card moving.

### The two ends nobody had wired

**Debugger** hangs off Source, not the Product Owner. "What is actually
broken" has to be answered before anyone can scope what to do about it —
a bug report routed through scoping first is being triaged on a symptom.
It hands the root cause down to the Coders; it does not write the fix.

Its contract is `aw-agent-debugger`, shipped by
aw-app-agents-platform-runners alongside the other generic role contracts.
It did not exist anywhere before 2026-08-21 — not here, not in the
monolith, where this agent ran on three sentences of inline prompt and
nothing else.

**Doc Writer** hangs off Source and the Coders, and is deliberately **not
connected to QA**. Its own contract says docs-only work completes straight
to Done, so there is no review hop to route through; an edge there would
put every docs card into a lane its contract skips, and the contradiction
would surface only as cards stuck one status short of Done. A test asserts
the absence.

Both agents already existed on this platform as ungoverned rows — created
by hand, declared by no app, so a fresh workspace got neither. They are
declared here now. Seeding is create-if-absent by slug, so adopting them
does not overwrite anything an existing install has tuned.

### Code Reviewer sits beside QA, not inside it

The team had QA and called that review. It isn't. QA judges whether the
delivery matches what was asked — a change can satisfy that and still be
wrong. `code-reviewer-sonnet` judges the code: off-by-one, a changed
return shape with a caller still on the old one, a retry with no ceiling.
Folding either into the other loses whichever question gets asked second.

Its contract forbids `set_qa_status` outright, because a code review that
moves the card to Done has replaced the acceptance check with a style
opinion and nobody would notice.

It is an agent node, not a group, because it runs on one model today. If a
second variant appears it becomes a group, the same way the Coders did.

### Three groups, because an agent only gets one

`devteam` (PO, Architect, UX Coder), `coders` (the four model variants),
`qas` (the two). The split buys two things: a group node per lane in the
graph, and a per-lane `kanban_target_status` — the review lane's is not
the build lane's.

It costs one thing, and it is the trap: **`group_slug` is single-valued**,
so an agent moved into a new group stops seeing the old group's
instructions entirely. The three rules every Dev Team agent shares — search
the knowledge base, report what is true, hand off outside your lane — are
therefore restated in all three prompts, and
`test_every_group_prompt_carries_the_shared_team_rules` fails the build if
one of them drifts. Splitting the lanes without that would have silently
dropped the mandatory knowledge-base search from six of the nine agents.

### The QA lane

They are in the graph on the same terms as the UX Coder — because
`aw-agent-qa` states that position, and `tests/test_manifest.py` asserts
the graph agrees with the skill. The rule this app follows has not
changed: **it only asserts a position a contract already documents.** Until
2026-08-19 no contract documented one, so the app shipped the agents and
left the topology out; the skill now says where QA sits, so the manifest
may say it too.

That gap was not free while it lasted. The agents existed, carried the
right skill, and were unreachable — a card that finished development
stopped dead, because nothing in any prompt told a coder that a QA was
there to hand to.

### Nothing here marks a card finished on dispatch

`kanban_target_status` is applied when a run is **dispatched**, not when it
finishes (agents-platform `core/executor.py::_auto_set_kanban_status`). So
the build lane sets `planned` (PO, Architect) and `running` (Coders, UX
Coder), the QA lane sets `running`, and nothing sets `done`.

Done is QA's verdict, reached at the end through `set_qa_status` — never a
side effect of somebody starting work. The field reads like an
on-completion setting and the older hand-built config on the legacy
platform did set the coders to `done`, so a test guards it.

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
`agent_flows` entry, and it also ships the `aw-agent-coder`, `aw-agent-qa`
and `aw-agent-ux-coder` skills that six of these agents reference by slug.
Install against an older one and you get the agents, no flow, and no
complaint — the half-installed state the version floor exists to prevent.

**UX Coder needs the UX-Proto app** to have somewhere to build. Its skill
is written entirely around that app; without it the agent is told to say
so plainly rather than scatter prototype files somewhere they don't
belong. The other eight agents don't care.

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
