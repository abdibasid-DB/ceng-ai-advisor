"""Run Stage 14 live local Ollama tests.

This script tests direct local model inference only. It does not connect the
retriever to the model, build a RAG prompt, or generate final advisor answers.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.llm_service import LocalLLMService


OUTPUT_PATH = PROJECT_ROOT / "docs" / "local-llm-test-results.json"

TEST_PROMPTS = [
    {
        "id": "ready_exact",
        "kind": "instruction_following",
        "prompt": "Respond with exactly the word READY.",
    },
    {
        "id": "computer_engineering_short",
        "kind": "direct_inference",
        "prompt": "Explain what Computer Engineering is in three short sentences.",
    },
    {
        "id": "hardware_software",
        "kind": "direct_inference",
        "prompt": "Explain the difference between software and hardware in simple English.",
    },
    {
        "id": "insufficient_exact",
        "kind": "instruction_following",
        "prompt": "You must answer with exactly: INSUFFICIENT_INFORMATION",
    },
    {
        "id": "three_bullets",
        "kind": "format_following",
        "prompt": "Return exactly three bullet points explaining what an operating system does.",
    },
    {
        "id": "context_answer",
        "kind": "context_following",
        "prompt": "CONTEXT:\nThe fictional CENG laboratory closes at 17:45 on Wednesday.\n\nQUESTION:\nWhat time does the fictional CENG laboratory close on Wednesday?",
    },
    {
        "id": "context_insufficient",
        "kind": "context_following",
        "prompt": "CONTEXT:\nThe document only discusses laboratory opening hours.\n\nQUESTION:\nWhat salary does a Computer Engineer earn?\n\nInstruction:\nIf the context does not contain the answer, respond with INSUFFICIENT_INFORMATION.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def run_tests() -> dict:
    service = LocalLLMService()
    version = service.version()
    models = service.list_models()
    results = []

    for item in TEST_PROMPTS:
        response = service.generate(item["prompt"])
        results.append(
            {
                "id": item["id"],
                "kind": item["kind"],
                "prompt": item["prompt"],
                "response": response.text.strip(),
                "model": response.model,
                "wall_time_seconds": round(response.wall_time_seconds, 3),
                "total_duration_seconds": response.total_duration_seconds,
                "load_duration_seconds": response.load_duration_seconds,
                "prompt_eval_count": response.prompt_eval_count,
                "eval_count": response.eval_count,
                "eval_duration_seconds": response.eval_duration_seconds,
                "response_character_count": len(response.text.strip()),
                "response_word_count": len(response.text.strip().split()),
            }
        )

    output = {
        "stage": "Stage 14 - Local Open-Source LLM Setup and Testing",
        "generated_at": utc_now(),
        "ollama_version": version.get("version"),
        "available_models": models,
        "results": results,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return output


def main() -> None:
    print(json.dumps(run_tests(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
