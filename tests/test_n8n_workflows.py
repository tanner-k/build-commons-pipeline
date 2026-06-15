import json
from pathlib import Path

import pytest

WORKFLOWS_DIR = Path(__file__).parent.parent / "n8n" / "workflows"
WORKFLOW_FILES = ["generate.json", "publish.json", "analytics.json", "enhance.json"]


@pytest.fixture(params=WORKFLOW_FILES)
def workflow(request):
    return json.loads((WORKFLOWS_DIR / request.param).read_text())


def test_workflow_has_required_shape(workflow):
    assert isinstance(workflow["name"], str)
    assert isinstance(workflow["nodes"], list) and len(workflow["nodes"]) >= 2
    assert isinstance(workflow["connections"], dict)


def test_exactly_one_schedule_trigger(workflow):
    triggers = [n for n in workflow["nodes"] if n["type"].endswith("scheduleTrigger")]
    assert len(triggers) == 1


def test_connections_reference_existing_nodes(workflow):
    names = {n["name"] for n in workflow["nodes"]}
    for source, outputs in workflow["connections"].items():
        assert source in names, f"connection source '{source}' is not a node"
        for branch in outputs.get("main", []):
            for target in branch:
                assert target["node"] in names, f"target '{target['node']}' is not a node"


def test_no_embedded_secrets(workflow):
    text = json.dumps(workflow)
    for marker in ("sk-ant", "sk_live", "Bearer ey", "service_role"):
        assert marker not in text


def test_provider_nodes_have_retries():
    wf = json.loads((WORKFLOWS_DIR / "generate.json").read_text())
    provider_nodes = [
        n for n in wf["nodes"]
        if n["type"] == "n8n-nodes-base.httpRequest" and n["name"] != "Trigger render"
    ]
    assert provider_nodes, "expected provider HTTP nodes in generate.json"
    for node in provider_nodes:
        assert node.get("retryOnFail") is True, f"{node['name']} missing retryOnFail"
        assert node.get("maxTries") == 3, f"{node['name']} should have maxTries=3 (2 retries)"


def test_enhance_overlay_node_has_retries():
    wf = json.loads((WORKFLOWS_DIR / "enhance.json").read_text())
    providers = [
        n for n in wf["nodes"]
        if n["type"] == "n8n-nodes-base.httpRequest" and "render" not in n["name"].lower()
    ]
    assert providers, "expected provider HTTP nodes in enhance.json"
    for n in providers:
        assert n.get("retryOnFail") is True, f"{n['name']} missing retryOnFail"
        assert n.get("maxTries") == 3, f"{n['name']} should have maxTries=3"
