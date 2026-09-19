# Stage 14 - Local LLM Test Report

## Scope

This stage validates the local generative model side only. It does not connect retrieval results to the LLM, build the final RAG prompt, generate knowledge-base-grounded advisor answers, implement chatbot API endpoints, or add frontend chatbot features.

## Environment

| Item | Detected value |
|---|---|
| Operating system | Microsoft Windows NT 10.0.26200.0 |
| Architecture | x64 |
| CPU | 13th Gen Intel(R) Core(TM) i7-1355U |
| Logical processors | 12 |
| RAM | Not available through permitted system queries |
| GPU/VRAM | Not confirmed; `nvidia-smi` not available |
| Ollama API version | 0.33.2 |
| Ollama CLI | Not detected on PATH |
| Ollama service | Available at `http://127.0.0.1:11434` |

Some Windows hardware queries were blocked by access restrictions, so unavailable values are documented rather than guessed.

## Selected Model

| Field | Value |
|---|---|
| Selected model | `qwen2.5:3b` |
| Parameter size | 3.1B |
| Quantization | Q4_K_M |
| Local size | 1,929,912,432 bytes, about 1.93 GB |
| Context length reported by Ollama | 32768 |
| Capabilities | completion, tools |

The model was downloaded locally through the Ollama service and is listed by `/api/tags`.

## Configuration

Configuration is stored in `backend/app/core/llm_config.py`.

| Setting | Value |
|---|---|
| Ollama base URL | `http://127.0.0.1:11434` |
| Model | `qwen2.5:3b` |
| Timeout | 120 seconds |
| Temperature | 0.2 |
| Context setting | 4096 |
| Max predicted tokens | 256 |

The local LLM service is implemented in `backend/app/services/llm_service.py`.

## Live Test Results

Results were saved to `docs/local-llm-test-results.json`.

| Test | Result | Wall time |
|---|---|---:|
| Respond exactly `READY` | Passed | 4.145s |
| Explain Computer Engineering in three short sentences | Passed | 5.045s |
| Explain software vs hardware | Passed, but verbose | 19.503s |
| Respond exactly `INSUFFICIENT_INFORMATION` | Passed | 0.762s |
| Return exactly three bullet points | Passed | 5.494s |
| Answer using artificial context | Passed | 2.438s |
| Refuse unsupported context question with `INSUFFICIENT_INFORMATION` | Passed | 1.411s |

First-response latency includes model load time. Ollama reported load duration of about 3.397 seconds for the first request. Subsequent short instruction/context tests were practical for a live demo.

## Instruction Following

The model followed exact-output tests:

- `READY`
- `INSUFFICIENT_INFORMATION`

It also returned exactly three bullet points for the operating-system format test.

## Context Following

The model correctly answered:

`The fictional CENG laboratory closes at 17:45 on Wednesday.`

It also correctly returned:

`INSUFFICIENT_INFORMATION`

when the supplied context did not contain salary information.

## Practical Live-Demo Assessment

`qwen2.5:3b` is practical enough for the next RAG integration stage on this machine:

- local Ollama service is available
- model is installed locally
- no API key is required
- no commercial cloud LLM API is used
- short factual/instruction tests are responsive enough
- longer generations can take 5-20 seconds, so later prompts should be concise

## Limitations

- RAM and GPU/VRAM could not be fully detected.
- Ollama CLI was not available on PATH in the Codex shell, although the Ollama service worked.
- This test does not evaluate knowledge-base grounding.
- This test does not connect the retriever to the model.
- This test does not implement final RAG answer generation.

## Commands

Pull the model with the Ollama CLI:

```powershell
ollama pull qwen2.5:3b
```

Verify the Ollama service:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:11434/api/version
```

Run the Stage 14 live local LLM test:

```powershell
python scripts\test_local_llm.py
```

Run unit tests:

```powershell
python -m unittest tests.test_llm_service
```

## Readiness Decision

**A. LOCAL LLM READY FOR RAG INTEGRATION**
