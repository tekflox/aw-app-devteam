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


def test_qa_reviews_every_agent_that_delivers_something(spec):
    """A QA wired to only some of the builders is worse than none: the ones
    it isn't adjacent to never learn there is a review step at all."""
    builders = {"coder-sonnet", "coder-opus", "coder-haiku", "coder-codex",
                "ux-coder-sonnet"}
    flow = spec["agent_flows"][0]
    by_id = {n["id"]: n.get("agent_slug") for n in flow["graph"]["nodes"]}
    for qa in ("qa-sonnet", "qa-haiku"):
        adjacent = set()
        for e in flow["graph"]["edges"]:
            if by_id.get(e["source"]) == qa:
                adjacent.add(by_id.get(e["target"]))
            elif by_id.get(e["target"]) == qa:
                adjacent.add(by_id.get(e["source"]))
        assert builders <= adjacent, f"{qa} does not review {builders - adjacent}"


def test_the_ux_coder_sits_where_its_own_skill_says_it_does(spec):
    """aw-agent-ux-coder tells the agent it is 'connected to Source and the
    Product Owner'. If the graph disagrees, the skill is lying to it — and
    the skill is the thing the agent actually reads."""
    flow = spec["agent_flows"][0]
    ux = next(n["id"] for n in flow["graph"]["nodes"]
              if n.get("agent_slug") == "ux-coder-sonnet")
    by_id = {n["id"]: n for n in flow["graph"]["nodes"]}
    adjacent = set()
    for e in flow["graph"]["edges"]:
        if e["source"] == ux:
            adjacent.add(e["target"])
        elif e["target"] == ux:
            adjacent.add(e["source"])
    assert "source" in adjacent
    assert any(by_id[a].get("agent_slug") == "product-owner" for a in adjacent)


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


def test_every_agent_is_reachable_in_the_flow(spec):
    """An agent declared but left off the graph gets no flow context at all —
    it is on the team on paper and disconnected from it at dispatch time."""
    for flow in spec["agent_flows"]:
        wired = {n["agent_slug"] for n in flow["graph"]["nodes"]
                 if n["type"] == "agent"}
        missing = {a["slug"] for a in spec["agents"]} - wired
        assert not missing, f"not wired into {flow['slug']!r}: {sorted(missing)}"


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
    # These three are shipped by aw-app-agents-platform-runners, which this
    # app declares a versioned dependency on precisely so the contracts exist
    # wherever the agents referencing them do.
    from_dependency = {"aw-agent-coder", "aw-agent-qa", "aw-agent-ux-coder"}
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
