"""The manifest IS this app.

There is no route, no window and no CLI here — everything the app delivers
is a declaration in ``aw-app.json`` that some other component seeds. So the
only thing worth testing is that those declarations are well-formed and
internally consistent, which is exactly what breaks silently otherwise: an
agent naming a skill slug nobody ships seeds fine and then runs with no
contract, and a flow node naming an agent that isn't declared draws a box
wired to nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[1]
MANIFEST = APP_DIR / "aw-app.json"


def _strings(value):
    """Every string leaf in a nested manifest value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings(v)


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def spec(manifest) -> dict:
    return manifest["contributes"]["agents"]


def test_manifest_is_valid_json_with_the_expected_identity(manifest):
    assert manifest["id"] == "devteam"
    assert manifest["manifest_version"] == 1


def test_declares_the_capability_its_contributions_need(manifest):
    # Core rejects contributes.agents without this — a missing capability
    # fails the install rather than silently dropping the contribution.
    assert "agents:contribute" in manifest["permissions"]


def test_ships_the_whole_team_the_app_is_named_for(spec):
    slugs = {a["slug"] for a in spec["agents"]}
    assert {"product-owner", "architect", "ux-coder-sonnet"} <= slugs
    # The Coder and QA families are the point of having variants at all: same
    # contract, different model, chosen by what the task is worth.
    assert {"coder-sonnet", "coder-opus", "coder-haiku", "coder-codex"} <= slugs
    assert {"qa-sonnet", "qa-haiku"} <= slugs


def test_qa_sits_where_its_own_skill_says_it_does(spec):
    """aw-agent-qa tells those agents they are 'connected to Source, the
    Product Owner, and every Coder including the UX Coder'. Same rule as
    the UX Coder below: the app only asserts a position a contract already
    states, and the skill is the thing the agent actually reads — so if the
    graph disagrees, the graph is the bug.

    The adjacency is what makes 'QA reviews, QA never fixes' workable. An
    enabled flow injects it into every member's prompt at dispatch; without
    the edge, a QA that rejects a delivery has nowhere to send it back to
    and the card stalls in review with nobody able to pick it up.

    They are wired as a *group* node, not two agent nodes: one box instead
    of fourteen edges, and a third QA model variant joins by being given
    group_slug 'qas' rather than by somebody redrawing the graph.
    """
    reachable = _neighbours(spec, group_slug="qas")
    assert "source" in reachable
    assert {"product-owner", "coder-sonnet", "coder-opus", "coder-haiku",
            "coder-codex", "ux-coder-sonnet"} <= reachable

    # ...and both QA agents are actually in the group the node names, or it
    # expands to nobody and draws a box connected to nothing.
    members = {a["slug"] for a in spec["agents"] if a["group_slug"] == "qas"}
    assert members == {"qa-sonnet", "qa-haiku"}


def _neighbours(spec, *, agent_slug=None, group_slug=None):
    """Who a node can hand off to, named by agent slug, the way the platform
    itself resolves it (agents-platform core/executor.py::_agents_flow_context).

    Two things that trip up a naive read of the graph and are asserted on
    here because the executor does them: edges are **undirected** for the
    purpose of the adjacency list injected into a prompt, and a **group node
    expands to its members**. A test that only matched `agent_slug` on the
    far end of an edge would call the Coders unreachable the moment they
    were collapsed into one box, which is exactly backwards.
    """
    flow = spec["agent_flows"][0]
    by_id = {n["id"]: n for n in flow["graph"]["nodes"]}
    mine = {nid for nid, n in by_id.items()
            if (agent_slug and n.get("agent_slug") == agent_slug)
            or (group_slug and n.get("group_slug") == group_slug)}
    assert len(mine) == 1, f"expected exactly one node for {agent_slug or group_slug}"

    def expand(node):
        if node["type"] == "agent":
            return {node["agent_slug"]}
        if node["type"] == "group":
            return {a["slug"] for a in spec["agents"]
                    if a["group_slug"] == node["group_slug"]}
        return {node["type"]}  # the source node has no agent behind it

    out = set()
    for e in flow["graph"]["edges"]:
        far = e["target"] if e["source"] in mine else (
            e["source"] if e["target"] in mine else None)
        if far is not None:
            out |= expand(by_id[far])
    return out


def test_every_flow_group_node_names_a_group_this_app_declares(spec):
    """Same join as the agent-node test below, for the other node type.

    A group node whose group_slug matches nothing expands to an empty
    member list — silently, like the agent case: a box wired to the whole
    team that hands off to nobody.
    """
    declared = {g["slug"] for g in spec["groups"]}
    for flow in spec["agent_flows"]:
        for node in flow["graph"]["nodes"]:
            if node["type"] == "group":
                assert node["group_slug"] in declared, node["id"]


def test_the_ux_coder_sits_where_its_own_skill_says_it_does(spec):
    """aw-agent-ux-coder tells the agent it is 'connected to Source and the
    Product Owner'. If the graph disagrees, the skill is lying to it — and
    the skill is the thing the agent actually reads."""
    reachable = _neighbours(spec, agent_slug="ux-coder-sonnet")
    assert "source" in reachable
    assert "product-owner" in reachable
    # ...and NOT the Architect: a prototype that waits on an architecture
    # decision has stopped being a prototype. Skipping that hop is the whole
    # reason this agent is wired separately from the Coders group.
    assert "architect" not in reachable


def test_the_coders_are_one_group_node_sitting_between_design_and_review(spec):
    """The build lane, as a group node for the same reason QA is one: a
    fifth model variant joins the flow by being given group_slug 'coders',
    not by somebody opening the editor and drawing four more edges.

    Its two ends are what the other contracts already state — the Architect
    hands a design down (and the PO reaches it directly, because a coder
    with a genuine product question routes back rather than guessing), and
    the finished work goes to QA.
    """
    members = {a["slug"] for a in spec["agents"] if a["group_slug"] == "coders"}
    assert members == {"coder-sonnet", "coder-opus", "coder-haiku", "coder-codex"}
    # The UX Coder is deliberately NOT here — see the test above; it would
    # inherit the Architect edge this group has and lose the one thing its
    # own contract promises it.
    assert "ux-coder-sonnet" not in members

    reachable = _neighbours(spec, group_slug="coders")
    assert {"architect", "product-owner"} <= reachable
    assert {"qa-sonnet", "qa-haiku"} <= reachable


def test_the_debugger_enters_ahead_of_scoping_and_hands_down_to_the_coders(spec):
    """prompts/debugger.md states this position, and unlike every other role
    here that contract is the prompt itself — no aw-agent-debugger skill
    exists, so the app owns it outright rather than mirroring someone else's.

    Source, not the Product Owner, because "what is actually broken" has to
    be answered before anyone can scope what to do about it. A bug report
    routed through scoping first is being triaged on a symptom.
    """
    reachable = _neighbours(spec, agent_slug="debugger")
    assert "source" in reachable
    assert {"coder-sonnet", "coder-opus", "coder-haiku", "coder-codex"} <= reachable


def test_the_doc_writer_is_wired_to_everything_except_qa(spec):
    """aw-agent-doc-writer states the position AND the exclusion, and the
    exclusion is the load-bearing half: docs-only work completes straight to
    Done, so there is no review hop to route through.

    An edge to QA here would put every docs card into a review lane its own
    contract says it skips — and the contradiction would only show up as
    cards mysteriously stuck one status short of Done.
    """
    reachable = _neighbours(spec, agent_slug="doc-writer")
    assert "source" in reachable
    assert {"coder-sonnet", "coder-opus", "coder-haiku", "coder-codex"} <= reachable
    assert not ({"qa-sonnet", "qa-haiku"} & reachable)


def test_every_group_prompt_carries_the_shared_team_rules(spec):
    """Group instructions are prepended to a member's own system prompt, and
    an agent belongs to exactly one group — so the three rules every Dev Team
    agent shares have to be restated in each group's prompt or they silently
    stop reaching whoever moved out of 'devteam'.

    That is not hypothetical: splitting the QA and Coder lanes out of the
    single original group is exactly the move that would have dropped the
    mandatory knowledge-base search from six of the nine agents.
    """
    for group in spec["groups"]:
        text = (APP_DIR / group["instructions_file"]).read_text()
        assert "search_knowledge_base" in text, group["slug"]
        assert "Report what is true" in text, group["slug"]
        assert "Hand off rather than guess" in text, group["slug"]


def test_every_flow_node_names_an_agent_this_app_declares(spec):
    """The join this app exists to guarantee.

    Agents Platform stores a flow's agent_slug as a plain string — a node
    naming an agent that doesn't exist doesn't error, it draws a box that is
    connected to nothing and injects no context into anybody.
    """
    declared = {a["slug"] for a in spec["agents"]}
    for flow in spec["agent_flows"]:
        for node in flow["graph"]["nodes"]:
            if node["type"] == "agent":
                assert node["agent_slug"] in declared, (
                    f"flow {flow['slug']!r} node {node['id']!r} points at "
                    f"{node['agent_slug']!r}, which this app does not declare"
                )


def test_every_flow_edge_connects_two_real_nodes(spec):
    for flow in spec["agent_flows"]:
        ids = {n["id"] for n in flow["graph"]["nodes"]}
        for edge in flow["graph"]["edges"]:
            assert edge["source"] in ids, edge
            assert edge["target"] in ids, edge


def test_flow_membership_is_exactly_what_the_contracts_document(spec):
    """Membership is an allow-list, not "every agent we ship".

    An enabled flow injects the adjacency list into each member's prompt at
    dispatch, so adding a node is telling that agent something about how the
    team works. This app only asserts a position a contract already states
    (see the UX Coder test below); everything else is left for a human to
    draw in the flow editor, which is also the only way it survives —
    seeding never updates an existing flow.

    Membership is by node, and a node is either one agent or one group. The
    agents wired individually are the ones whose position is their own — the
    PO and the Architect are single roles, the UX Coder skips a hop the
    Coders group does not, the Debugger enters ahead of scoping, and the Doc
    Writer is the one role that bypasses QA entirely.
    """
    wired = {n["agent_slug"] for n in spec["agent_flows"][0]["graph"]["nodes"]
             if n["type"] == "agent"}
    assert wired == {"product-owner", "architect", "ux-coder-sonnet",
                     "debugger", "doc-writer"}
    grouped = {n["group_slug"] for n in spec["agent_flows"][0]["graph"]["nodes"]
               if n["type"] == "group"}
    assert grouped == {"coders", "qas"}

    # Every agent this app ships still reaches the graph, one way or the
    # other — shipping an agent nobody can hand off to is the bug this
    # whole file exists to catch.
    in_a_wired_group = {a["slug"] for a in spec["agents"] if a["group_slug"] in grouped}
    assert wired | in_a_wired_group == {a["slug"] for a in spec["agents"]}


def test_no_declaration_marks_a_card_finished_on_dispatch(spec):
    """kanban_target_status is applied when a run is DISPATCHED, not when it
    finishes (agents-platform core/executor.py::_auto_set_kanban_status —
    'move a Kanban card's Status before its agent's run actually starts').

    So a terminal status here would mark the card finished the moment an
    agent picked it up, before it had done anything. Done is QA's verdict,
    reached at the end through set_qa_status — never a side effect of
    someone starting work. Guarding it as a test because the field reads
    like an on-completion setting and the older hand-built config on the
    legacy platform did set the coders to 'done'.
    """
    terminal = {"done", "ready_to_deploy", "auto_resolved", "archived"}
    for kind in ("agents", "groups"):
        for entry in spec[kind]:
            assert entry.get("kanban_target_status") not in terminal, entry["slug"]


def test_the_flow_has_exactly_one_source_and_it_is_called_source(spec):
    # The flow editor keys its single entry node on the literal id "source";
    # a graph that re-opens without one loses where work enters the team.
    for flow in spec["agent_flows"]:
        sources = [n for n in flow["graph"]["nodes"] if n["type"] == "source"]
        assert len(sources) == 1, flow["slug"]
        assert sources[0]["id"] == "source"


def test_the_flow_is_enabled(spec):
    # Unlike a scheduled task, an Agents Flow that isn't enabled does nothing
    # at all — no context injection, no handoff guidance. A disabled flow is
    # indistinguishable from not shipping one.
    for flow in spec["agent_flows"]:
        assert flow.get("enabled") is True, flow["slug"]


def test_every_flow_node_has_a_position(spec):
    # Positions are editor-only, but omit them and every node stacks at the
    # origin the first time somebody opens the flow.
    for flow in spec["agent_flows"]:
        for node in flow["graph"]["nodes"]:
            assert set(node.get("position", {})) == {"x", "y"}, node["id"]


def test_agents_reference_a_declared_config_and_group(spec):
    configs = {c["slug"] for c in spec["agent_configs"]}
    groups = {g["slug"] for g in spec["groups"]}
    for agent in spec["agents"]:
        assert agent["agent_config_slug"] in configs, agent["slug"]
        assert agent["group_slug"] in groups, agent["slug"]


def test_referenced_files_exist(manifest, spec):
    for skill in manifest["contributes"]["skills"]:
        assert (APP_DIR / skill["path"]).is_file(), skill["path"]
    for agent in spec["agents"]:
        ref = agent.get("system_prompt_file")
        assert ref and (APP_DIR / ref).is_file(), agent["slug"]
    for group in spec["groups"]:
        ref = group.get("instructions_file")
        assert ref and (APP_DIR / ref).is_file(), group["slug"]


def test_skill_slugs_are_either_shipped_here_or_come_from_a_declared_dependency(
    manifest, spec
):
    """A skill_slug that resolves to nothing is the quiet failure mode: the
    agent still runs, just with no contract — which reads as a bad model,
    not a missing file."""
    shipped = {s["id"] for s in manifest["contributes"]["skills"]}
    # These four are shipped by aw-app-agents-platform-runners, which this
    # app declares a versioned dependency on precisely so the contracts exist
    # wherever the agents referencing them do.
    from_dependency = {"aw-agent-coder", "aw-agent-qa", "aw-agent-ux-coder",
                       "aw-agent-doc-writer"}
    depends_on = {d["id"] for d in manifest["dependencies"]["apps"]}
    assert "agents-platform-runners" in depends_on
    for agent in spec["agents"]:
        for slug in agent.get("skill_slugs", []):
            assert slug in shipped or slug in from_dependency, (
                f"{agent['slug']} references skill {slug!r}, which nothing ships"
            )


def test_the_provider_floor_is_new_enough_to_seed_a_flow(manifest):
    """Below 0.55.0 the provider seeds the six agents and silently drops the
    agent_flows entry — the exact half-installed state this floor exists to
    prevent."""
    dep = next(d for d in manifest["dependencies"]["apps"]
               if d["id"] == "agents-platform-runners")
    assert dep["version"] == ">=0.55.0"


def test_no_declaration_ships_a_credential(spec):
    """A manifest goes to a marketplace; a gateway token must not ride along.

    The aw-gateway entry carries a bearer token, so the config declares the
    server BY NAME via mcp_servers and the workspace resolves it at seed
    time, inside the machine that owns the secret.
    """
    for cfg in spec["agent_configs"]:
        assert "mcp_config" not in cfg
        assert cfg["mcp_servers"] == ["aw-gateway"]
    # Scan the string VALUES that actually get POSTed — not the manifest
    # text and not the field names. A leaked credential is always a value,
    # while legitimate field names contain the same words
    # (`auto_compact_threshold_tokens`), and descriptions here discuss
    # tokens on purpose.
    for kind in ("models", "agent_configs", "groups", "agents", "agent_flows"):
        for entry in spec.get(kind, []):
            payload = {k: v for k, v in entry.items() if k != "description"}
            for value in _strings(payload):
                low = value.lower()
                for marker in ("bearer ", "authorization", "ntn_", "sk-"):
                    assert marker not in low, (
                        f"{kind} {entry.get('slug')!r}: {marker} in {value!r}")


def test_the_shipped_skills_do_not_carry_monolith_paths(manifest):
    """These contracts are written for this workspace, not the monolith they
    conceptually descend from — a skill naming awserv or /opt/agentic-workspace
    teaches an agent to call something that isn't here."""
    for skill in manifest["contributes"]["skills"]:
        text = (APP_DIR / skill["path"]).read_text()
        assert "/opt/agentic-workspace" not in text, skill["id"]
        assert "awserv" not in text, skill["id"]
        assert "aw-knowledge-base" not in text, skill["id"]
        assert "ntn_" not in text, skill["id"]
