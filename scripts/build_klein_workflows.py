"""Build editable, neutral ComfyUI graphs for local Klein checkpoints."""
from copy import deepcopy
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "genesis/reference/pose_workflows"
T2I = Path("/mnt/AI-Storage/ComfyUI/workflows/Flux.2 Klein 9b Text To Image.json")
EDIT = DEST / "KLEIN9B_REMOTE.json"
MIRACLEIN = "Miraclein NSFW v3.0 FP8 - Klein9B - 12steps,euler,cfg1.1.safetensors"
PORNMASTER = "pornmasterFlux2Klein_v3-fp8.safetensors"
DARKBEAST = "DarkBeast-Klein9b-V2-BFS-FP8-ComfyUI.safetensors"
ENCODER = "qwen_3_8b_fp8mixed.safetensors"


def set_widget(graph, node_id, values):
    node = next(n for n in graph["nodes"] if n["id"] == node_id)
    node["widgets_values"] = values
    names = node.get("widgets_values_named")
    if names:
        for key, value in zip(names, values):
            names[key] = value


def save(graph, name):
    graph["id"] = "genesis-" + name.lower().replace("_", "-")
    (DEST / f"{name}.json").write_text(json.dumps(graph, indent=2) + "\n")


def make_t2i(name, model, steps, cfg, prompt):
    graph = deepcopy(json.loads(T2I.read_text()))
    set_widget(graph, 126, [model, "default"])
    set_widget(graph, 136, [ENCODER, "flux2", "default"])
    sample = next(n for n in graph["nodes"] if n["id"] == 134)
    values = list(sample["widgets_values"])
    values[2:4] = [steps, cfg]
    sample["widgets_values"] = values
    set_widget(graph, 107, [prompt])
    set_widget(graph, 9, ["GENESIS_" + name])
    save(graph, name)

def make_edit(name, model, steps, cfg, prompt):
    graph = deepcopy(json.loads(EDIT.read_text()))
    set_widget(graph, 1, [model, "default"])
    set_widget(graph, 2, [ENCODER, "flux2", "default"])
    set_widget(graph, 4, [prompt])
    set_widget(graph, 6, [cfg])
    set_widget(graph, 7, [steps, 1024, 1024])
    set_widget(graph, 8, [1024, 1024, 1])
    set_widget(graph, 26, ["GENESIS_" + name])
    save(graph, name)
    return graph


def add_link(graph, origin, output_name, target, input_name):
    nodes = {n["id"]: n for n in graph["nodes"]}
    out = next(i for i, port in enumerate(nodes[origin]["outputs"]) if port["name"] == output_name)
    into = next(i for i, port in enumerate(nodes[target]["inputs"]) if port["name"] == input_name)
    graph["last_link_id"] += 1
    link_id = graph["last_link_id"]
    graph["links"].append([link_id, origin, out, target, into, nodes[origin]["outputs"][out]["type"]])
    links = nodes[origin]["outputs"][out].setdefault("links", [])
    if links is None:
        nodes[origin]["outputs"][out]["links"] = [link_id]
    else:
        links.append(link_id)
    nodes[target]["inputs"][into]["link"] = link_id


def disconnect(graph, link_id):
    link = next(link for link in graph["links"] if link[0] == link_id)
    nodes = {n["id"]: n for n in graph["nodes"]}
    graph["links"].remove(link)
    nodes[link[1]]["outputs"][link[2]]["links"].remove(link_id)
    nodes[link[3]]["inputs"][link[4]]["link"] = None

def make_identity():
    graph = make_edit("GENESIS_DARKBEAST_9B_IDENTITY", DARKBEAST, 5, 1.0,
                      "Preserve the subject's facial identity from the second reference image while refining the first image. Keep pose, framing, and clothing consistent.")
    original = {node["id"]: node for node in graph["nodes"]}
    for source_id, new_id, title in [
        (10, 106, "Person A identity image"),
        (12, 107, "Scale identity image"),
        (15, 108, "Encode identity image"),
        (17, 109, "Identity reference · positive"),
        (18, 110, "Identity reference · negative"),
    ]:
        node = deepcopy(original[source_id])
        node["id"] = new_id
        node["title"] = title
        node["pos"][1] += 410
        node["order"] = 40 + new_id - 106
        for port in node.get("inputs", []):
            port["link"] = None
        for port in node.get("outputs", []):
            port["links"] = []
        if new_id == 106:
            node["widgets_values"] = ["GENESIS_IDENTITY.png", "image"]
            if node.get("widgets_values_named"):
                node["widgets_values_named"]["image"] = "GENESIS_IDENTITY.png"
        graph["nodes"].append(node)
    graph["last_node_id"] = 110
    disconnect(graph, 166)
    disconnect(graph, 167)
    for src, out, dst, into in [
        (106, "IMAGE", 107, "image"), (107, "IMAGE", 108, "pixels"),
        (3, "VAE", 108, "vae"), (108, "LATENT", 109, "latent"),
        (108, "LATENT", 110, "latent"),
        (17, "CONDITIONING", 109, "conditioning"),
        (18, "CONDITIONING", 110, "conditioning"),
        (109, "CONDITIONING", 6, "positive"),
        (110, "CONDITIONING", 6, "negative"),
    ]:
        add_link(graph, src, out, dst, into)
    save(graph, "GENESIS_DARKBEAST_9B_IDENTITY")

if __name__ == "__main__":
    make_t2i("GENESIS_MIRACLEIN_9B_T2I", MIRACLEIN, 12, 1.1,
             "A candid photograph of two adult friends standing beside a bicycle in a park, natural light, distinct faces and clothing, coherent hands and limbs.")
    make_t2i("GENESIS_PORNMASTER_9B_T2I", PORNMASTER, 12, 1.0,
             "A detailed natural-language description of two adult people in a sunlit studio, with clear separation of their hair, faces, clothing, posture, and camera perspective.")
    make_edit("GENESIS_MIRACLEIN_9B_EDIT", MIRACLEIN, 12, 1.1,
              "Edit the reference photograph while preserving the person's face, clothing, and natural proportions.")
    make_edit("GENESIS_PORNMASTER_9B_EDIT", PORNMASTER, 12, 1.0,
              "Use the reference photograph and describe the desired changes in complete natural-language sentences while preserving identity.")
    make_identity()
