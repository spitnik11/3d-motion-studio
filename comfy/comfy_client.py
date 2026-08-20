"""Minimal ComfyUI HTTP client (stdlib only) + openpose-ControlNet SDXL workflow.

Reuses the production ComfyUI on :8188 read-only for jobs. No custom nodes required —
only core CheckpointLoaderSimple / CLIPTextEncode / ControlNetLoader / KSampler /
VAEDecode / LoadImage / SaveImage.
"""

from __future__ import annotations

import json
import time
import urllib.request
import uuid
from pathlib import Path

from comfy.style_profile import StyleProfile


class ComfyClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8188"):
        self.base = base_url.rstrip("/")
        self.client_id = str(uuid.uuid4())

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base}{path}", data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"})
        return json.load(urllib.request.urlopen(req, timeout=30))

    def _get(self, path: str) -> dict:
        return json.load(urllib.request.urlopen(f"{self.base}{path}", timeout=30))

    def upload_image(self, path: str, subfolder: str = "3dms") -> str:
        """Upload via multipart; returns the name ComfyUI stores it under."""
        import mimetypes
        boundary = "----3dms" + uuid.uuid4().hex
        data = Path(path).read_bytes()
        name = Path(path).name
        mime = mimetypes.guess_type(name)[0] or "image/png"
        body = b"".join([
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="image"; filename="{name}"\r\n'.encode(),
            f"Content-Type: {mime}\r\n\r\n".encode(), data, b"\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="subfolder"\r\n\r\n',
            subfolder.encode(), b"\r\n",
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="overwrite"\r\n\r\n', b"true\r\n",
            f"--{boundary}--\r\n".encode(),
        ])
        req = urllib.request.Request(
            f"{self.base}/upload/image", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
        r = json.load(urllib.request.urlopen(req, timeout=30))
        return r["subfolder"] + "/" + r["name"] if r.get("subfolder") else r["name"]

    def queue(self, workflow: dict) -> str:
        return self._post("/prompt", {"prompt": workflow, "client_id": self.client_id})["prompt_id"]

    def wait(self, prompt_id: str, timeout: int = 600) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            hist = self._get(f"/history/{prompt_id}")
            if prompt_id in hist:
                return hist[prompt_id]
            time.sleep(1.5)
        raise TimeoutError(f"Comfy job {prompt_id} did not finish in {timeout}s")

    def download_outputs(self, history: dict, out_dir: str) -> list[str]:
        out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
        saved = []
        import urllib.parse
        for node in history.get("outputs", {}).values():
            for img in node.get("images", []):
                q = urllib.parse.urlencode({
                    "filename": img["filename"],
                    "subfolder": img.get("subfolder", ""),
                    "type": img.get("type", "output"),
                })
                data = urllib.request.urlopen(f"{self.base}/view?{q}", timeout=30).read()
                p = out / img["filename"]
                p.write_bytes(data)
                saved.append(str(p))
        return saved


def build_workflow(sp: StyleProfile, openpose_name: str, seed: int = 42) -> dict:
    """Core-node openpose-ControlNet SDXL graph as a ComfyUI API-format prompt."""
    return {
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": sp.checkpoint}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": sp.positive, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": sp.negative, "clip": ["4", 1]}},
        "10": {"class_type": "LoadImage", "inputs": {"image": openpose_name}},
        "11": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": sp.controlnet}},
        "12": {"class_type": "ControlNetApply", "inputs": {
            "conditioning": ["6", 0], "control_net": ["11", 0],
            "image": ["10", 0], "strength": sp.controlnet_strength}},
        "5": {"class_type": "EmptyLatentImage",
              "inputs": {"width": sp.width, "height": sp.height, "batch_size": 1}},
        "3": {"class_type": "KSampler", "inputs": {
            "seed": seed, "steps": sp.steps, "cfg": sp.cfg,
            "sampler_name": sp.sampler, "scheduler": sp.scheduler, "denoise": 1.0,
            "model": ["4", 0], "positive": ["12", 0], "negative": ["7", 0], "latent_image": ["5", 0]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "3dms_frame", "images": ["8", 0]}},
    }
