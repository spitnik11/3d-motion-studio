"""StyleProfile — Phase 18.

Binds a rendered PoseBundle frame to a ComfyUI style (checkpoint family + prompts +
sampler). Architecture adapters differ only in checkpoint + prompt tokens; they all
drive the same openpose-ControlNet SDXL graph. Use only locally discovered models.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StyleProfile:
    architecture: str                 # illustrious | pony | anima | zimage | krea
    checkpoint: str                   # a checkpoint present in ComfyUI
    controlnet: str = "controlnet-openpose-sdxl-1.0.safetensors"
    positive: str = "masterpiece, best quality, 1girl"
    negative: str = "lowres, bad anatomy, bad hands, worst quality"
    steps: int = 20
    cfg: float = 6.0
    sampler: str = "euler"
    scheduler: str = "normal"
    controlnet_strength: float = 0.9
    width: int = 768
    height: int = 768
    extra: dict = field(default_factory=dict)


# Reasonable defaults per architecture; checkpoint chosen from discovered models.
def illustrious(checkpoint: str, **kw) -> StyleProfile:
    return StyleProfile(
        architecture="illustrious", checkpoint=checkpoint,
        positive=kw.pop("positive", "masterpiece, best quality, absurdres, 1girl, anime"),
        negative=kw.pop("negative", "lowres, bad anatomy, bad hands, extra digits, worst quality"),
        **kw,
    )
