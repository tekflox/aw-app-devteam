---
repo: architecture
path: docs/architecture/aw-app-devteam.md
source: generated
edited: false
checksum: sha256:84ad45030e3e42fc661163331b8c7432264e50548e4df36637d46795b8e67490
---
# Dev Team

- **repo**: aw-app-devteam
- **layer**: app
- **technologies**: python
- **health** (derived): planned

The software-engineering agent team, shipped as one installable unit: the Coder family (Sonnet / Opus / Haiku / GPT5) that writes the code, the Product Owner that decides what is worth building, the Architect that decides how it should be shaped, the skills defining each contract, and the Software Engineering Agents Flow that says how they hand off to one another. Every agent runs on the same config the workspace's existing coder agents use.

## Connections
- `other` → **aw-app-agents-platform-runners** — Provides the contributes
- `other` → **aw-app-kb** — Supplies search_knowledge_base, which all three contracts make a mandatory first step

## MCP tools
_none exposed_

## Requirements
_none documented_
