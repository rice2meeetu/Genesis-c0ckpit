import torch

def gpu_status():
    return {
        "torch": torch.__version__,
        "hip": torch.version.hip,
        "gpu": torch.cuda.get_device_name(0)
            if torch.cuda.is_available()
            else "NONE",
        "available": torch.cuda.is_available()
    }


if __name__ == "__main__":
    print(gpu_status())
