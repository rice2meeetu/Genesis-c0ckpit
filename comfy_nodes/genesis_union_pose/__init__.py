"""Pose selector for the original InstantX/Shakker FLUX.1 Union Pro v1.

That checkpoint uses task index 4 for pose; ComfyUI's generic Union
"openpose" index 0 applies to a different Union family.
"""


class GenesisFluxUnionProPose:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"control_net": ("CONTROL_NET",)}}

    RETURN_TYPES = ("CONTROL_NET",)
    FUNCTION = "select_pose"
    CATEGORY = "GENESIS/pose"

    def select_pose(self, control_net):
        selected = control_net.copy()
        selected.set_extra_arg("control_type", [4])
        return (selected,)


NODE_CLASS_MAPPINGS = {"GenesisFluxUnionProPose": GenesisFluxUnionProPose}
NODE_DISPLAY_NAME_MAPPINGS = {
    "GenesisFluxUnionProPose": "GENESIS FLUX.1 Union Pro v1 Pose (mode 4)"
}
