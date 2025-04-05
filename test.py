import torch
print(f"CUDA is available: {torch.cuda.is_available()}")
print(f"CUDA devices: {torch.cuda.device_count()}")