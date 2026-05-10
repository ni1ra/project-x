from __future__ import annotations

import json
import pathlib
import urllib.request


ROOT = pathlib.Path(__file__).resolve().parents[1]
REF = ROOT / "ref"


SOURCES = [
    {
        "id": "deepseek-v4-hf",
        "title": "DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence",
        "url": "https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash",
        "kind": "model-card",
        "notes": "Official DeepSeek Hugging Face card for V4 Flash and V4 Pro claims.",
    },
    {
        "id": "openai-gpt-5-5",
        "title": "Introducing GPT-5.5",
        "url": "https://openai.com/index/introducing-gpt-5-5/",
        "kind": "release-note",
        "notes": "Official OpenAI release page; useful for public capability targets, not architecture internals.",
    },
    {
        "id": "openai-gpt-5-5-system-card",
        "title": "GPT-5.5 System Card",
        "url": "https://deploymentsafety.openai.com/gpt-5-5/gpt-5-5.pdf",
        "pdf": "https://deploymentsafety.openai.com/gpt-5-5/gpt-5-5.pdf",
        "kind": "system-card",
    },
    {
        "id": "anthropic-claude-opus-4-7",
        "title": "Introducing Claude Opus 4.7",
        "url": "https://www.anthropic.com/news/claude-opus-4-7",
        "kind": "release-note",
        "notes": "Official Anthropic release page; useful for public capability targets, not architecture internals.",
    },
    {
        "id": "deepseek-r1",
        "title": "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning",
        "url": "https://arxiv.org/abs/2501.12948",
        "pdf": "https://arxiv.org/pdf/2501.12948",
        "kind": "paper",
    },
    {
        "id": "deepseek-v3",
        "title": "DeepSeek-V3 Technical Report",
        "url": "https://arxiv.org/abs/2412.19437",
        "pdf": "https://arxiv.org/pdf/2412.19437",
        "kind": "paper",
    },
    {
        "id": "allmem",
        "title": "AllMem: A Memory-centric Recipe for Efficient Long-context Modeling",
        "url": "https://arxiv.org/abs/2602.13680",
        "pdf": "https://arxiv.org/pdf/2602.13680",
        "kind": "paper",
    },
    {
        "id": "memmamba",
        "title": "MemMamba: Rethinking Memory Patterns in State Space Model",
        "url": "https://arxiv.org/abs/2510.03279",
        "pdf": "https://arxiv.org/pdf/2510.03279",
        "kind": "paper",
    },
    {
        "id": "jamba",
        "title": "Jamba: A Hybrid Transformer-Mamba Language Model",
        "url": "https://arxiv.org/abs/2403.19887",
        "pdf": "https://arxiv.org/pdf/2403.19887",
        "kind": "paper",
    },
    {
        "id": "mamba",
        "title": "Mamba: Linear-Time Sequence Modeling with Selective State Spaces",
        "url": "https://arxiv.org/abs/2312.00752",
        "pdf": "https://arxiv.org/pdf/2312.00752",
        "kind": "paper",
    },
    {
        "id": "titans",
        "title": "Titans: Learning to Memorize at Test Time",
        "url": "https://arxiv.org/abs/2501.00663",
        "pdf": "https://arxiv.org/pdf/2501.00663",
        "kind": "paper",
    },
]


def fetch(url: str, dest: pathlib.Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "project-x-ref-fetch/0.1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        dest.write_bytes(response.read())


def main() -> None:
    REF.mkdir(exist_ok=True)
    (REF / "papers").mkdir(exist_ok=True)
    (REF / "pages").mkdir(exist_ok=True)
    (REF / "sources.json").write_text(json.dumps(SOURCES, indent=2) + "\n", encoding="utf-8")

    manifest = [
        "# Source Manifest",
        "",
        "Public reference sources for Project X. These are references, not design authority.",
        "",
    ]
    for source in SOURCES:
        manifest.append(f"- `{source['id']}`: {source['title']} - {source['url']}")
    (REF / "SOURCE_MANIFEST.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")

    for source in SOURCES:
        if source.get("pdf"):
            fetch(source["pdf"], REF / "papers" / f"{source['id']}.pdf")


if __name__ == "__main__":
    main()
