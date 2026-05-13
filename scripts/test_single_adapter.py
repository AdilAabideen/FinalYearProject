"""Test Single Adapter script helpers."""

from safetensors.torch import load_file, save_file
from pathlib import Path

src = Path("/Users/adil/Documents/University/MultiAgentResearch/UseCase1ESI/model_artifacts/adapters/esi345/adapter_model.safetensors")
dst = Path("/Users/adil/Documents/University/MultiAgentResearch/UseCase1ESI/model_artifacts/adapters/esi345/adapter_model.safetensors")  # in copied adapter folder

t = load_file(str(src))
drop_keys = ("vision_tower", "vision_model", "multi_modal_projector", "mm_projector")
keep = {k: v for k, v in t.items() if not any(x in k for x in drop_keys)}

print(f"original={len(t)} kept={len(keep)} removed={len(t)-len(keep)}")
save_file(keep, str(dst))