from __future__ import annotations

import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REFS = [
    ("DeepSeek V4 official model card", "https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash"),
    ("OpenAI GPT-5.5 official release", "https://openai.com/index/introducing-gpt-5-5/"),
    ("OpenAI GPT-5.5 system card", "https://deploymentsafety.openai.com/gpt-5-5/gpt-5-5.pdf"),
    ("Anthropic Claude Opus 4.7 official release", "https://www.anthropic.com/news/claude-opus-4-7"),
    ("DeepSeek R1 paper", "https://arxiv.org/abs/2501.12948"),
    ("DeepSeek V3 paper", "https://arxiv.org/abs/2412.19437"),
    ("AllMem paper", "https://arxiv.org/abs/2602.13680"),
    ("MemMamba paper", "https://arxiv.org/abs/2510.03279"),
    ("Jamba paper", "https://arxiv.org/abs/2403.19887"),
    ("Mamba paper", "https://arxiv.org/abs/2312.00752"),
    ("Titans paper", "https://arxiv.org/abs/2501.00663"),
]


def add_header(lines: list[str], title: str) -> None:
    lines.extend(
        [
            f"# {title}",
            "",
            "Project X is a research program for a novel LLM-style token predictor.",
            "The plan treats frontier systems as reference signals, not as templates to clone.",
            "Every implementation move must create measurable evidence: run IDs, artifact paths, tests, or source manifests.",
            "Unauthorized access, secret scraping, credential probing, and bypass behavior are out of scope.",
            "",
            "## Public Reference Baseline",
            "",
        ]
    )
    for name, url in REFS:
        lines.append(f"- {name}: {url}")
    lines.extend(["", "## Novel Architecture Seed", ""])
    lines.extend(
        [
            "Working name: Helix Memory Routed Predictor.",
            "Core thesis: next-token prediction should fuse four time scales instead of relying on one monolithic attention stream.",
            "Scale 1 is local causal syntax: short windows, exact autoregressive masking, fast token-to-token composition.",
            "Scale 2 is learned episodic memory: trainable and test-time-updatable slots queried by tokens.",
            "Scale 3 is routed transformation: sparse experts with explicit load, specialization, and failure metrics.",
            "Scale 4 is verifier pressure: training and evaluation loops reward predictions that preserve latent state and causal consistency.",
            "The first runnable scaffold implements the local, memory, and routed streams on CPU for shape, loss, and routing tests.",
            "",
        ]
    )


def phase_lines(phase: int, title: str, count: int) -> list[str]:
    lines = [f"## Phase {phase:02d}: {title}", ""]
    lines.append(f"Goal: turn `{title}` into measurable code, data, and evidence.")
    lines.append("Acceptance: a command runs, writes an artifact, and has a regression check.")
    lines.append("")
    verbs = [
        "Define",
        "Implement",
        "Instrument",
        "Benchmark",
        "Compare",
        "Document",
        "Stress",
        "Ablate",
        "Harden",
        "Promote",
    ]
    objects = [
        "tokenization and corpus ingestion",
        "local attention baselines",
        "memory slot update rules",
        "routing load balance",
        "expert specialization metrics",
        "long-context retrieval probes",
        "state-fidelity tests",
        "causal diagnosis logs",
        "training stability dashboards",
        "artifact manifests",
    ]
    for i in range(1, count + 1):
        verb = verbs[(i + phase) % len(verbs)]
        obj = objects[(i * 3 + phase) % len(objects)]
        lines.append(
            f"{phase:02d}.{i:03d}. {verb} {obj}; record command, input path, output path, metric, and failure mode."
        )
    lines.append("")
    return lines


def build_a_to_z() -> str:
    lines: list[str] = []
    add_header(lines, "A To Z Plan")
    phases = [
        "Repository seed and reproducibility spine",
        "Reference acquisition and provenance",
        "Paper extraction and claim tables",
        "Baseline tokenizer and byte-level corpus path",
        "Transformer control model",
        "Helix local-memory-routed block",
        "Routing and sparse expert experiments",
        "Long-context memory experiments",
        "Reasoning-time verifier pressure",
        "Training pipeline and checkpoint format",
        "Evaluation harness and benchmark ladder",
        "Inference runtime and cache strategy",
        "Hardware scaling and quantization",
        "Safety, containment, and source hygiene",
        "Disruption roadmap and release gates",
    ]
    for index, title in enumerate(phases, start=1):
        lines.extend(phase_lines(index, title, 105))
    lines.extend(
        [
            "## Final Gate",
            "",
            "The architecture graduates only when it beats the local transformer control under the same token, compute, and wall-clock budgets.",
            "The roadmap graduates only when every claimed improvement links to a result file under `artifacts/`.",
            "The reference library graduates only when every imported claim has a URL, fetch date, and local digest.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def build_next() -> str:
    lines: list[str] = [
        "# Do This Next",
        "",
        "Immediate steps to make Project X run on this PC.",
        "Assumed shell: bash in `/mnt/c/Users/nira/Documents/Code/projext-x`.",
        "",
        "## Critical Path",
        "",
    ]
    steps = [
        "Create the Python virtual environment.",
        "Install the package in editable mode with development dependencies.",
        "Run the CPU smoke test.",
        "Run the unit test suite.",
        "Fetch the reference manifest and paper PDFs.",
        "Record the first run ID under `artifacts/`.",
        "Choose the first baseline corpus.",
        "Train the smallest transformer control model.",
        "Train the smallest Helix model with identical data and step count.",
        "Compare loss, speed, memory, and routing balance.",
    ]
    for i in range(1, 101):
        step = steps[(i - 1) % len(steps)]
        lines.append(f"{i:03d}. {step}")
        lines.append(f"     Command evidence must be saved before moving past item {i:03d}.")
        lines.append(f"     If item {i:03d} fails, write the mechanism first, then retry with one changed variable.")
        lines.append("")
    lines.extend(
        [
            "## First Commands",
            "",
            "```bash",
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "pip install -e \".[dev]\"",
            "python -m project_x.smoke",
            "pytest",
            "python scripts/fetch_refs.py",
            "```",
            "",
            "## Decision Thresholds",
            "",
        ]
    )
    for i in range(1, 181):
        lines.append(
            f"T{i:03d}. Keep the novel path only if the measured artifact improves loss, speed, memory, stability, routing health, or long-context retrieval."
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "A_TO_Z_PLAN.md").write_text(build_a_to_z(), encoding="utf-8")
    (DOCS / "DO_THIS_NEXT.md").write_text(build_next(), encoding="utf-8")


if __name__ == "__main__":
    main()
