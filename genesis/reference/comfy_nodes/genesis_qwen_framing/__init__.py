"""Isolated GENESIS Phr00t Qwen Edit reference-framing node.

Adapted from Phr00t/Qwen-Image-Edit-Rapid-AIO
fixed-textencode-node/nodes_qwen.v2.py (Apache-2.0 model repository).
Distinct node ID preserves every upstream ComfyUI Qwen node, including Qwen 2.1.
No external dependencies, network access, persistent state, or core overrides.
"""

import math

import comfy.utils
import node_helpers
from comfy_api.latest import ComfyExtension, io


class GenesisQwenImageEditFraming(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="GenesisQwenImageEditFraming",
            display_name="GENESIS Qwen Edit (reference framing)",
            category="GENESIS/conditioning",
            inputs=[
                io.Clip.Input("clip"),
                io.String.Input("prompt", multiline=True, dynamic_prompts=True),
                io.Vae.Input("vae", optional=True),
                io.Image.Input("image1", optional=True),
                io.Image.Input("image2", optional=True),
                io.Image.Input("image3", optional=True),
                io.Image.Input("image4", optional=True),
                io.Latent.Input("target_latent", optional=True),
            ],
            outputs=[io.Conditioning.Output()],
        )

    @classmethod
    def execute(cls, clip, prompt, vae=None, image1=None, image2=None,
                image3=None, image4=None, target_latent=None):
        references = [image1, image2, image3, image4]
        tokens_images = []
        reference_latents = []
        visual_prompt = ""
        template = (
            "<|im_start|>system\nDescribe the key details of the input images "
            "(objects, subjects, poses, facial features, environment, textures) "
            "and explain how the user instruction should modify or recreate "
            "the picture. Follow the requested edit while preserving the "
            "source subject when appropriate.<|im_end|>\n"
            "<|im_start|>user\n{}<|im_end|>\n<|im_start|>assistant\n"
        )
        for number, image in enumerate(references, 1):
            if image is None:
                continue
            samples = image.movedim(-1, 1)
            scale = math.sqrt((384 * 384) / (samples.shape[3] * samples.shape[2]))
            width = max(8, round(samples.shape[3] * scale))
            height = max(8, round(samples.shape[2] * scale))
            resized_vl = comfy.utils.common_upscale(samples, width, height, "lanczos", "center")
            tokens_images.append(resized_vl.movedim(1, -1))
            if vae is not None:
                if target_latent is not None:
                    target = target_latent.get("samples")
                    if target is None:
                        raise ValueError("GENESIS Qwen framing requires target_latent.samples")
                    target_width = int(target.shape[-1]) * 8
                    target_height = int(target.shape[-2]) * 8
                    if target_width < 64 or target_height < 64:
                        raise ValueError("GENESIS Qwen framing target latent is too small")
                    resized_ref = comfy.utils.common_upscale(
                        samples, target_width, target_height, "lanczos", "center"
                    )
                else:
                    resized_ref = samples
                reference_latents.append(vae.encode(resized_ref.movedim(1, -1)[..., :3]))
            visual_prompt += f"Picture {number}: <|vision_start|><|image_pad|><|vision_end|>"
        tokens = clip.tokenize(visual_prompt + prompt, images=tokens_images, llama_template=template)
        conditioning = clip.encode_from_tokens_scheduled(tokens)
        if reference_latents:
            conditioning = node_helpers.conditioning_set_values(
                conditioning, {"reference_latents": reference_latents}, append=True
            )
        return io.NodeOutput(conditioning)


class GenesisQwenFramingExtension(ComfyExtension):
    async def get_node_list(self):
        return [GenesisQwenImageEditFraming]


async def comfy_entrypoint():
    return GenesisQwenFramingExtension()
