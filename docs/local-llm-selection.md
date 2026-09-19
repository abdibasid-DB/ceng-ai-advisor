# Stage 14 - Local LLM Selection

## Detected Environment

| Item | Detected value |
|---|---|
| Operating system | Microsoft Windows NT 10.0.26200.0 |
| Architecture | x64 |
| CPU | 13th Gen Intel(R) Core(TM) i7-1355U |
| Logical processors | 12 |
| RAM | Not available through permitted system queries |
| GPU/VRAM | NVIDIA tooling not detected; GPU/VRAM not confirmed |
| Ollama service | Available at `http://127.0.0.1:11434` |
| Ollama API version | 0.33.2 |
| Ollama CLI | Not detected on PATH in this Codex shell |

Because GPU/VRAM and RAM could not be fully verified, the model choice favors a small local instruction model suitable for CPU fallback and live demo practicality.

## Candidate Models

| Candidate | Ollama tag | Approximate size class | Strengths | Weaknesses | Practicality |
|---|---|---:|---|---|---|
| Qwen2.5 3B | `qwen2.5:3b` | 3.1B parameters | Small, instruction-following oriented, good enough for factual assistant tests, practical on CPU, 32k context metadata reported by Ollama | Lower reasoning depth than larger models | Selected |
| Llama 3.2 3B | `llama3.2:3b` | 3B parameters | Popular local instruction model, practical size | Quality can vary by task; model was not already installed | Good alternative |
| Mistral 7B | `mistral:7b` | 7B parameters | Stronger general quality than small models | Heavier CPU/RAM load, slower for live demo if no GPU | Possible later upgrade |
| Gemma 2B/3B family | e.g. `gemma2:2b` or available Ollama equivalent | Small | Lightweight and fast | Smaller models can be less reliable for strict instructions | Possible fallback |

## Selected Model

Selected model: **`qwen2.5:3b`**

Ollama reported:

- Parameter size: `3.1B`
- Quantization: `Q4_K_M`
- Local model size: `1,929,912,432` bytes, about 1.93 GB
- Context length: `32768`
- Capabilities: `completion`, `tools`

## Selection Rationale

`qwen2.5:3b` was selected because it is small enough to be practical on a student laptop without confirmed GPU acceleration, while still being an instruction-tuned local model capable of direct generation, constrained outputs, and context-following tests.

The larger alternatives may improve answer quality, but they would create unnecessary risk for a live university demo on uncertain hardware.

## Pull Command

Preferred CLI command:

```powershell
ollama pull qwen2.5:3b
```

In this Codex shell, the Ollama CLI was not on PATH, so the model was pulled through the local Ollama API service instead.
