# NVIDIA and accelerated compute

Use NVIDIA skill discovery for NVIDIA-specific hardware/software workflows when available. Do not assume a GPU exists.

Potential acceleration lanes include CUDA, RAPIDS/cuDF, TensorRT, NIM, NeMo, Jetson, Omniverse/OpenUSD, DeepStream, and other catalog-discovered NVIDIA skills.

Route to GPU acceleration only when workload size and runtime support justify it. Keep a CPU/general fallback when practical. Installation of NVIDIA skills or software requires explicit user authorization and compatibility checks.
