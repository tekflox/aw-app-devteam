---
repo: architecture
path: docs/architecture/aw-app-devteam.md
source: generated
edited: false
checksum: sha256:30f7d956148548465d242435604e3e3bbba7b25bf66678feb1934214f8d72fc0
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
### Todo nó do flow nomeia um agente que o próprio app declara
- Given o app declara nove agentes em contributes.agents.agents e um grafo de flow em contributes.agents.agent_flows (repos/aw-app-devteam/aw-app.json:259)
- When o join entre os dois é verificado (repos/aw-app-devteam/tests/test_manifest.py::test_every_flow_node_names_an_agent_this_app_declares:97)
- Then todo nó de tipo agent aponta para um slug presente na lista de declarados — a Agents Platform guarda agent_slug como string solta, então um nó que nomeia agente inexistente não dá erro nenhum: desenha uma caixa ligada a nada, que não injeta contexto em ninguém e não recebe handoff. É exatamente o tipo de junção que só um teste de manifesto pega, porque em runtime o sintoma é um agente quieto, não uma exceção
- intended_status: `not_implemented` · derived health: `not_implemented`
- tests: `repos/aw-app-devteam/tests/test_manifest.py` (passing)

### Os agentes de QA são declarados mas ficam deliberadamente fora do flow
- Given o app entrega qa-sonnet e qa-haiku junto com o resto do time
- When a composição do grafo é conferida (repos/aw-app-devteam/tests/test_manifest.py::test_the_qa_agents_are_deliberately_not_in_the_flow:65 e test_flow_membership_is_exactly_what_the_contracts_document:122)
- Then a adjacência é exatamente {product-owner, architect, coder-sonnet, coder-opus, coder-haiku, coder-codex, ux-coder-sonnet} e nenhum QA aparece nela — entregar um agente e ligá-lo à topologia são duas decisões, e este app só tem alçada sobre a primeira. Um flow habilitado injeta a lista de adjacência no prompt de cada membro, então inventar uma posição que nenhum contrato descreve é ensinar o palpite para todo agente do grafo
- intended_status: `not_implemented` · derived health: `not_implemented`
- tests: `repos/aw-app-devteam/tests/test_manifest.py` (passing)

### Nenhuma declaração que vai pro marketplace carrega credencial
- Given o agent-config vivo usa o aw-gateway, cuja entrada carrega um bearer token, e o manifesto deste app é publicado num marketplace público
- When os valores que de fato são POSTados para a Agents Platform são varridos (repos/aw-app-devteam/tests/test_manifest.py::test_no_declaration_ships_a_credential:211)
- Then nenhum agent_config traz mcp_config, cada um declara o servidor só pelo nome via mcp_servers=["aw-gateway"] (repos/aw-app-devteam/aw-app.json:43) e nenhum valor de string contém "bearer ", "authorization", "ntn_" ou "sk-" — o workspace resolve o token no momento do seed, dentro da máquina que é dona do segredo. A varredura ignora o campo description de propósito: credencial vazada é sempre um valor, e os nomes de campo legítimos falam de token o tempo todo
- intended_status: `not_implemented` · derived health: `not_implemented`
- tests: `repos/aw-app-devteam/tests/test_manifest.py` (passing)

### O piso de versão do provider é o que impede um time semeado sem topologia
- Given quem entrega a superfície contributes.agents é o app agents-platform-runners, e versões abaixo de 0.55.0 não sabem semear agent_flows
- When a dependência declarada é conferida (repos/aw-app-devteam/tests/test_manifest.py::test_the_provider_floor_is_new_enough_to_seed_a_flow:202, contra repos/aw-app-devteam/aw-app.json:418)
- Then o piso é >=0.55.0 — abaixo disso o provider cria os nove agentes e descarta o flow em silêncio, que é o pior resultado possível: o install passa, a tela mostra o time inteiro, e o que não existe é justamente o handoff. A dependência é não-obrigatória de propósito, porque uma declaração que chega antes do provider fica retida e é reexecutada quando ele aparece
- intended_status: `not_implemented` · derived health: `not_implemented`
- tests: `repos/aw-app-devteam/tests/test_manifest.py` (passing)

### Todo skill_slug referenciado por um agente resolve para algo que existe
- Given cada agente do time referencia seu contrato por slug, e três deles (aw-agent-coder, aw-agent-qa, aw-agent-ux-coder) vêm do app de dependência, não deste repo
- When os slugs são resolvidos contra o que este app entrega mais o que a dependência declarada entrega (repos/aw-app-devteam/tests/test_manifest.py::test_skill_slugs_are_either_shipped_here_or_come_from_a_declared_dependency:182)
- Then todo slug cai num dos dois conjuntos, e os arquivos apontados por system_prompt_file e instructions_file existem mesmo em disco (test_referenced_files_exist:171) — um skill_slug que não resolve é a falha silenciosa clássica aqui: o agente sobe e roda normalmente, só que sem contrato nenhum, e o resultado se parece com um modelo ruim em vez de um arquivo faltando
- intended_status: `not_implemented` · derived health: `not_implemented`
- tests: `repos/aw-app-devteam/tests/test_manifest.py` (passing)
