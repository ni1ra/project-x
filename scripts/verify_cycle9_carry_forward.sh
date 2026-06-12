#!/usr/bin/env bash
set -euo pipefail

BIN="build/organic_v0"
TIMEOUT="${TIMEOUT:-180s}"
ARTIFACT="run/artifacts/organic-v0/cycle9_carry_forward_verification.json"
ROOT="$(mktemp -d /tmp/cycle9_carry_forward.XXXXXX)"
OUT="$ROOT/out"
STATE="$ROOT/state"
EVENTS="$ROOT/events"
TRANSCRIPTS="$ROOT/transcripts"
LEGACY="$ROOT/legacy_inputs"
mkdir -p "$OUT" "$STATE" "$EVENTS" "$TRANSCRIPTS" "$LEGACY"

make -s "$BIN"

if [[ ! -f /tmp/cycle2.pxstate || ! -f /tmp/organic_v0_cycle5_fixture.jsonl ]]; then
  echo "missing historical legacy rail inputs: /tmp/cycle2.pxstate and /tmp/organic_v0_cycle5_fixture.jsonl" >&2
  exit 2
fi
cp /tmp/cycle2.pxstate "$LEGACY/cycle2.pxstate"
cp /tmp/organic_v0_cycle5_fixture.jsonl "$LEGACY/organic_v0_cycle5_fixture.jsonl"

run_cmd() {
  local name="$1"
  shift
  printf '[cycle9-carry-forward] %s\n' "$name" >&2
  timeout "$TIMEOUT" "$@"
}

run_cmd cycle6_regression "$BIN" --phase eval \
  --out "$OUT/eval_cycle6_relations_all_on.json" \
  --save-state "$STATE/v2c6.pxstate" \
  --event-log "$EVENTS/v2c6-eval-all-on.jsonl"

run_cmd legacy_cycle2_cycle5 "$BIN" --phase eval \
  --data "$LEGACY/organic_v0_cycle5_fixture.jsonl" \
  --load-state "$LEGACY/cycle2.pxstate" \
  --out "$OUT/eval_cycle6_legacy_cycle2_cycle5_fixture.json"

run_cmd clean_chat "$BIN" --phase eval \
  --data benchmarks/v2_ladder/organic_live_chat_v0.jsonl \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c7-chat-manifesto.pxstate \
  --out "$OUT/eval_live_chat_v0_manifesto_from_v2c7_chat.json"

for seed in 7001 7002; do
  run_cmd "cycle7b_seed_${seed}" "$BIN" --phase interactive-hidden-rule \
    --scenario-seed "$seed" \
    --action-budget 64 \
    --feedback-strength 2.0 \
    --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
    --save-state "$STATE/cycle7b-ihr-seed${seed}.pxstate" \
    --event-log "$EVENTS/cycle7b-ihr-seed${seed}.jsonl" \
    --out "$OUT/interactive_hidden_rule_cycle7b_seed${seed}.json"
done

for seed in 7101 7102; do
  run_cmd "cycle7c_seed_${seed}" "$BIN" --phase interactive-symbolic-rule \
    --scenario-seed "$seed" \
    --action-budget 64 \
    --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
    --save-state "$STATE/cycle7c-symbolic-seed${seed}.pxstate" \
    --event-log "$EVENTS/cycle7c-symbolic-seed${seed}.jsonl" \
    --out "$OUT/interactive_symbolic_rule_cycle7c_seed${seed}.json"
  run_cmd "cycle7c_probe_${seed}" "$BIN" --phase interactive-symbolic-probe \
    --scenario-seed "$seed" \
    --load-state "$STATE/cycle7c-symbolic-seed${seed}.pxstate" \
    --event-log "$EVENTS/cycle7c-symbolic-probe-seed${seed}.jsonl" \
    --out "$OUT/interactive_symbolic_rule_cycle7c_probe_seed${seed}.json"
done

for seed in 7201 7202; do
  run_cmd "cycle7d_seed_${seed}" "$BIN" --phase interactive-grid-rule \
    --scenario-seed "$seed" \
    --action-budget 64 \
    --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
    --save-state "$STATE/cycle7d-grid-seed${seed}.pxstate" \
    --event-log "$EVENTS/cycle7d-grid-seed${seed}.jsonl" \
    --out "$OUT/interactive_grid_rule_cycle7d_seed${seed}.json"
  run_cmd "cycle7d_probe_${seed}" "$BIN" --phase interactive-grid-probe \
    --scenario-seed "$seed" \
    --load-state "$STATE/cycle7d-grid-seed${seed}.pxstate" \
    --event-log "$EVENTS/cycle7d-grid-probe-seed${seed}.jsonl" \
    --out "$OUT/interactive_grid_rule_cycle7d_probe_seed${seed}.json"
done

run_cmd cycle7e_text_all_on "$BIN" --phase text-experience \
  --experience-db experience/organic-v0/text_experience_seed_v0.jsonl \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state "$STATE/cycle7e-text-experience.pxstate" \
  --event-log "$EVENTS/cycle7e-text-experience.jsonl" \
  --out "$OUT/text_experience_cycle7e.json" \
  --transcript-out "$TRANSCRIPTS/text_experience_cycle7e_transcript.md"

run_cmd cycle7e_text_from_disk "$BIN" --phase text-experience-probe \
  --experience-db experience/organic-v0/text_experience_seed_v0.jsonl \
  --load-state "$STATE/cycle7e-text-experience.pxstate" \
  --event-log "$EVENTS/cycle7e-text-experience-from-disk.jsonl" \
  --out "$OUT/text_experience_cycle7e_from_disk_probe.json"

run_cmd cycle7e_text_ablation "$BIN" --phase text-experience \
  --experience-db experience/organic-v0/text_experience_seed_v0.jsonl \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state "$STATE/cycle7e-text-experience-ablate.pxstate" \
  --event-log "$EVENTS/cycle7e-text-experience-ablate.jsonl" \
  --out "$OUT/text_experience_cycle7e_ablate_learning.json" \
  --transcript-out "$TRANSCRIPTS/text_experience_cycle7e_ablate_transcript.md" \
  --ablate-text-experience-learning

run_cmd cycle7f_replay_all_on "$BIN" --phase text-experience-replay \
  --experience-db experience/organic-v0/text_experience_seed_v0.jsonl \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state "$STATE/cycle7f-text-replay.pxstate" \
  --event-log "$EVENTS/cycle7f-text-replay.jsonl" \
  --out "$OUT/text_experience_replay_cycle7f.json" \
  --transcript-out "$TRANSCRIPTS/text_experience_replay_cycle7f_transcript.md"

run_cmd cycle7f_replay_from_disk "$BIN" --phase text-experience-probe \
  --experience-db experience/organic-v0/text_experience_seed_v0.jsonl \
  --load-state "$STATE/cycle7f-text-replay.pxstate" \
  --event-log "$EVENTS/cycle7f-text-replay-from-disk.jsonl" \
  --out "$OUT/text_experience_replay_cycle7f_from_disk_probe.json"

run_cmd cycle7f_replay_disabled "$BIN" --phase text-experience-replay \
  --experience-db experience/organic-v0/text_experience_seed_v0.jsonl \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state "$STATE/cycle7f-text-replay-disabled.pxstate" \
  --event-log "$EVENTS/cycle7f-text-replay-disabled.jsonl" \
  --out "$OUT/text_experience_replay_cycle7f_replay_disabled.json" \
  --transcript-out "$TRANSCRIPTS/text_experience_replay_cycle7f_replay_disabled_transcript.md" \
  --ablate-text-experience-replay

run_cmd cycle7f_audit_ablation "$BIN" --phase text-experience-replay \
  --experience-db experience/organic-v0/text_experience_seed_v0.jsonl \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state "$STATE/cycle7f-text-replay-audit-ablate.pxstate" \
  --event-log "$EVENTS/cycle7f-text-replay-audit-ablate.jsonl" \
  --out "$OUT/text_experience_replay_cycle7f_audit_ablation.json" \
  --transcript-out "$TRANSCRIPTS/text_experience_replay_cycle7f_audit_ablation_transcript.md" \
  --ablate-text-replay-audit

run_cmd cycle7g_raw_spans_all_on "$BIN" --phase text-experience \
  --experience-db experience/organic-v0/text_experience_raw_spans_v0.jsonl \
  --derive-raw-text-spans \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state "$STATE/cycle7g-raw-spans.pxstate" \
  --event-log "$EVENTS/cycle7g-raw-spans.jsonl" \
  --out "$OUT/text_experience_raw_spans_cycle7g.json" \
  --transcript-out "$TRANSCRIPTS/text_experience_raw_spans_cycle7g_transcript.md"

run_cmd cycle7g_raw_spans_from_disk "$BIN" --phase text-experience-probe \
  --experience-db experience/organic-v0/text_experience_raw_spans_v0.jsonl \
  --derive-raw-text-spans \
  --load-state "$STATE/cycle7g-raw-spans.pxstate" \
  --event-log "$EVENTS/cycle7g-raw-spans-from-disk.jsonl" \
  --out "$OUT/text_experience_raw_spans_cycle7g_from_disk_probe.json"

run_cmd cycle7g_raw_spans_ablation "$BIN" --phase text-experience \
  --experience-db experience/organic-v0/text_experience_raw_spans_v0.jsonl \
  --derive-raw-text-spans \
  --ablate-raw-text-spans \
  --load-state run/state/organic-v0/snapshots/raphael-local-0001/v2c6.pxstate \
  --save-state "$STATE/cycle7g-raw-spans-ablate.pxstate" \
  --event-log "$EVENTS/cycle7g-raw-spans-ablate.jsonl" \
  --out "$OUT/text_experience_raw_spans_cycle7g_ablation.json" \
  --transcript-out "$TRANSCRIPTS/text_experience_raw_spans_cycle7g_ablation_transcript.md"

ROOT="$ROOT" OUT="$OUT" ARTIFACT="$ARTIFACT" python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ["ROOT"])
out = Path(os.environ["OUT"])
artifact = Path(os.environ["ARTIFACT"])

def load(name):
    return json.loads((out / name).read_text())

def overall_eval(doc):
    return doc["summary_metrics"]["overall"]

def score_overall(doc, key="scorecard"):
    return doc[key]["overall"]

def metric(doc, *keys):
    cur = doc
    for key in keys:
        cur = cur[key]
    return cur

def raw_for_event(doc, event_id):
    for row in doc["results"]:
        if row.get("event_id") == event_id:
            return row.get("raw_generated_output")
    raise KeyError(event_id)

def expect(name, actual, expected):
    passed = actual == expected
    return {"name": name, "passed": passed, "actual": actual, "expected": expected}

checks = []
rails = {}

cycle6 = load("eval_cycle6_relations_all_on.json")
rails["cycle6_regression"] = {
    "artifact": str(out / "eval_cycle6_relations_all_on.json"),
    "overall": overall_eval(cycle6),
    "model_state_hash": cycle6["model_state_hash"],
}
checks.append(expect("cycle6_count", overall_eval(cycle6)["count"], 30))
checks.append(expect("cycle6_exact_rate", overall_eval(cycle6)["exact_rate"], 1.0))
checks.append(expect("cycle6_hash", cycle6["model_state_hash"], "29958f0880e662dc"))

legacy = load("eval_cycle6_legacy_cycle2_cycle5_fixture.json")
rails["legacy_cycle2_cycle5"] = {
    "artifact": str(out / "eval_cycle6_legacy_cycle2_cycle5_fixture.json"),
    "overall": overall_eval(legacy),
    "model_state_hash": legacy["model_state_hash"],
    "evt_mem_test_001_raw": raw_for_event(legacy, "evt_mem_test_001"),
}
checks.append(expect("legacy_count", overall_eval(legacy)["count"], 25))
checks.append(expect("legacy_exact_rate", overall_eval(legacy)["exact_rate"], 0.36))
checks.append(expect("legacy_hash", legacy["model_state_hash"], "3536309de837d3e2"))
checks.append(expect("legacy_raw_evt_mem_test_001", raw_for_event(legacy, "evt_mem_test_001"), "milaquart arch6"))

chat = load("eval_live_chat_v0_manifesto_from_v2c7_chat.json")
rails["clean_chat"] = {
    "artifact": str(out / "eval_live_chat_v0_manifesto_from_v2c7_chat.json"),
    "overall": overall_eval(chat),
    "model_state_hash": chat["model_state_hash"],
}
checks.append(expect("clean_chat_count", overall_eval(chat)["count"], 5))
checks.append(expect("clean_chat_exact_rate", overall_eval(chat)["exact_rate"], 0.2))
checks.append(expect("clean_chat_hash", chat["model_state_hash"], "888b7664126b7f5f"))

expected_7b_hashes = {7001: "879b7e4f6295fc12", 7002: "030516a10354131a"}
rails["cycle7b_numeric_interactive"] = {}
for seed, expected_hash in expected_7b_hashes.items():
    doc = load(f"interactive_hidden_rule_cycle7b_seed{seed}.json")
    ov = score_overall(doc)
    rails["cycle7b_numeric_interactive"][str(seed)] = {
        "artifact": str(out / f"interactive_hidden_rule_cycle7b_seed{seed}.json"),
        "scorecard": ov,
        "model_state_hash": doc["model_state_hash"],
    }
    checks.append(expect(f"cycle7b_{seed}_held_out_count", ov["held_out_count"], 7))
    checks.append(expect(f"cycle7b_{seed}_held_out_exact", ov["held_out_exact"], 7))
    checks.append(expect(f"cycle7b_{seed}_hash", doc["model_state_hash"], expected_hash))

expected_7c_hashes = {7101: "0bb1b59f651f32eb", 7102: "5bc8e066bf1ba522"}
rails["cycle7c_symbolic_interactive"] = {}
for seed, expected_hash in expected_7c_hashes.items():
    doc = load(f"interactive_symbolic_rule_cycle7c_seed{seed}.json")
    probe = load(f"interactive_symbolic_rule_cycle7c_probe_seed{seed}.json")
    ov = score_overall(doc)
    post = score_overall(doc, "post_episode_probe_scorecard")
    pov = score_overall(probe)
    rails["cycle7c_symbolic_interactive"][str(seed)] = {
        "artifact": str(out / f"interactive_symbolic_rule_cycle7c_seed{seed}.json"),
        "probe_artifact": str(out / f"interactive_symbolic_rule_cycle7c_probe_seed{seed}.json"),
        "scorecard": ov,
        "post_episode_probe": post,
        "from_disk_probe": pov,
        "model_state_hash": doc["model_state_hash"],
        "probe_model_state_hash": probe["model_state_hash"],
    }
    checks.append(expect(f"cycle7c_{seed}_held_out_exact", ov["held_out_exact"], 8))
    checks.append(expect(f"cycle7c_{seed}_post_probe_exact", post["exact"], 8))
    checks.append(expect(f"cycle7c_{seed}_from_disk_probe_exact", pov["exact"], 8))
    checks.append(expect(f"cycle7c_{seed}_hash", doc["model_state_hash"], expected_hash))
    checks.append(expect(f"cycle7c_{seed}_probe_hash_match", probe["model_state_hash"], doc["model_state_hash"]))

expected_7d_hashes = {7201: "93032ff81f0bc258", 7202: "ba359ad133fe4d3a"}
rails["cycle7d_grid_interactive"] = {}
for seed, expected_hash in expected_7d_hashes.items():
    doc = load(f"interactive_grid_rule_cycle7d_seed{seed}.json")
    probe = load(f"interactive_grid_rule_cycle7d_probe_seed{seed}.json")
    ov = score_overall(doc)
    post = score_overall(doc, "post_episode_probe_scorecard")
    pov = score_overall(probe)
    rails["cycle7d_grid_interactive"][str(seed)] = {
        "artifact": str(out / f"interactive_grid_rule_cycle7d_seed{seed}.json"),
        "probe_artifact": str(out / f"interactive_grid_rule_cycle7d_probe_seed{seed}.json"),
        "scorecard": ov,
        "post_episode_probe": post,
        "from_disk_probe": pov,
        "model_state_hash": doc["model_state_hash"],
        "probe_model_state_hash": probe["model_state_hash"],
    }
    checks.append(expect(f"cycle7d_{seed}_held_out_exact", ov["held_out_exact"], 8))
    checks.append(expect(f"cycle7d_{seed}_post_probe_exact", post["exact"], 8))
    checks.append(expect(f"cycle7d_{seed}_from_disk_probe_exact", pov["exact"], 8))
    checks.append(expect(f"cycle7d_{seed}_hash", doc["model_state_hash"], expected_hash))
    checks.append(expect(f"cycle7d_{seed}_probe_hash_match", probe["model_state_hash"], doc["model_state_hash"]))

text7e = load("text_experience_cycle7e.json")
text7e_disk = load("text_experience_cycle7e_from_disk_probe.json")
text7e_ablate = load("text_experience_cycle7e_ablate_learning.json")
rails["cycle7e_text"] = {
    "all_on": {"artifact": str(out / "text_experience_cycle7e.json"), "summary_metrics": text7e["summary_metrics"], "model_state_hash": text7e["model_state_hash"]},
    "from_disk": {"artifact": str(out / "text_experience_cycle7e_from_disk_probe.json"), "summary_metrics": text7e_disk["summary_metrics"], "model_state_hash": text7e_disk["model_state_hash"]},
    "learning_disabled_ablation": {"artifact": str(out / "text_experience_cycle7e_ablate_learning.json"), "summary_metrics": text7e_ablate["summary_metrics"], "model_state_hash": text7e_ablate["model_state_hash"], "state_growth": text7e_ablate["state_growth"]},
}
checks.append(expect("cycle7e_all_on_probe_exact", metric(text7e, "summary_metrics", "probe", "exact"), 4))
checks.append(expect("cycle7e_from_disk_probe_exact", metric(text7e_disk, "summary_metrics", "probe", "exact"), 4))
checks.append(expect("cycle7e_all_on_hash", text7e["model_state_hash"], "be0fc781039a2038"))
checks.append(expect("cycle7e_hash_match", text7e_disk["model_state_hash"], text7e["model_state_hash"]))
checks.append(expect("cycle7e_ablation_probe_exact", metric(text7e_ablate, "summary_metrics", "probe", "exact"), 0))
checks.append(expect("cycle7e_ablation_hash", text7e_ablate["model_state_hash"], "29958f0880e662dc"))

text7f = load("text_experience_replay_cycle7f.json")
text7f_disk = load("text_experience_replay_cycle7f_from_disk_probe.json")
text7f_disabled = load("text_experience_replay_cycle7f_replay_disabled.json")
text7f_audit = load("text_experience_replay_cycle7f_audit_ablation.json")
rails["cycle7f_replay"] = {
    "all_on": {"artifact": str(out / "text_experience_replay_cycle7f.json"), "summary_metrics": text7f["summary_metrics"], "model_state_hash": text7f["model_state_hash"]},
    "from_disk": {"artifact": str(out / "text_experience_replay_cycle7f_from_disk_probe.json"), "summary_metrics": text7f_disk["summary_metrics"], "model_state_hash": text7f_disk["model_state_hash"]},
    "replay_disabled": {"artifact": str(out / "text_experience_replay_cycle7f_replay_disabled.json"), "summary_metrics": text7f_disabled["summary_metrics"], "model_state_hash": text7f_disabled["model_state_hash"], "replay_state_growth": text7f_disabled["replay_state_growth"]},
    "audit_ablation": {"artifact": str(out / "text_experience_replay_cycle7f_audit_ablation.json"), "summary_metrics": text7f_audit["summary_metrics"], "model_state_hash": text7f_audit["model_state_hash"]},
}
checks.append(expect("cycle7f_all_on_post_replay_probe_exact", metric(text7f, "summary_metrics", "post_replay_probe", "exact"), 4))
checks.append(expect("cycle7f_from_disk_probe_exact", metric(text7f_disk, "summary_metrics", "probe", "exact"), 4))
checks.append(expect("cycle7f_all_on_hash", text7f["model_state_hash"], "89fc3a01a35451e9"))
checks.append(expect("cycle7f_hash_match", text7f_disk["model_state_hash"], text7f["model_state_hash"]))
checks.append(expect("cycle7f_replay_disabled_hash", text7f_disabled["model_state_hash"], "be0fc781039a2038"))
checks.append(expect("cycle7f_replay_disabled_growth_zero", all(v == 0 for v in text7f_disabled["replay_state_growth"].values()), True))
checks.append(expect("cycle7f_audit_ablation_probe_exact", metric(text7f_audit, "summary_metrics", "post_replay_probe", "exact"), 1))
checks.append(expect("cycle7f_audit_ablation_hash", text7f_audit["model_state_hash"], "f6dfaabe5eda3d11"))

text7g = load("text_experience_raw_spans_cycle7g.json")
text7g_disk = load("text_experience_raw_spans_cycle7g_from_disk_probe.json")
text7g_ablate = load("text_experience_raw_spans_cycle7g_ablation.json")
rails["cycle7g_raw_spans"] = {
    "all_on": {"artifact": str(out / "text_experience_raw_spans_cycle7g.json"), "summary_metrics": text7g["summary_metrics"], "model_state_hash": text7g["model_state_hash"]},
    "from_disk": {"artifact": str(out / "text_experience_raw_spans_cycle7g_from_disk_probe.json"), "summary_metrics": text7g_disk["summary_metrics"], "model_state_hash": text7g_disk["model_state_hash"]},
    "raw_span_ablation": {"artifact": str(out / "text_experience_raw_spans_cycle7g_ablation.json"), "summary_metrics": text7g_ablate["summary_metrics"], "model_state_hash": text7g_ablate["model_state_hash"]},
}
checks.append(expect("cycle7g_all_on_probe_exact", metric(text7g, "summary_metrics", "probe", "exact"), 4))
checks.append(expect("cycle7g_from_disk_probe_exact", metric(text7g_disk, "summary_metrics", "probe", "exact"), 4))
checks.append(expect("cycle7g_all_on_hash", text7g["model_state_hash"], "16c29f604e814f58"))
checks.append(expect("cycle7g_hash_match", text7g_disk["model_state_hash"], text7g["model_state_hash"]))
checks.append(expect("cycle7g_ablation_probe_exact", metric(text7g_ablate, "summary_metrics", "probe", "exact"), 0))
checks.append(expect("cycle7g_ablation_hash", text7g_ablate["model_state_hash"], "0229fbe5c96d5c3e"))

legacy_inputs = {}
for source in (root / "legacy_inputs").iterdir():
    legacy_inputs[str(source)] = hashlib.sha256(source.read_bytes()).hexdigest()

failed = [check for check in checks if not check["passed"]]
result = {
    "schema": "project_x.cycle9_carry_forward_verification.v1",
    "run_id": "cycle9-carry-forward-" + root.name.rsplit(".", 1)[-1],
    "date": "2026-05-15",
    "run_root": str(root),
    "timeout_per_command": os.environ.get("TIMEOUT", "180s"),
    "legacy_input_copies_sha256": legacy_inputs,
    "all_required_checks_passed": not failed,
    "checks": checks,
    "failed_checks": failed,
    "rails": rails,
    "negative_space": {
        "not_alignment": True,
        "not_sandbox_escape_resistance": True,
        "not_wrapper_sandbox": True,
        "not_supply_chain_safety": True,
        "not_tool_use_safety": True,
        "not_event_log_external_length_anchor": True,
    },
    "honest_interpretation": "Fresh post-Cycle-9 carry-forward rerun over the listed substrate rails. This verifies bit-exact hashes and expected held-out/probe/ablation scores for those rails only. In-process policy enforcement; wrapper-level sandbox is a future cycle. This does not solve alignment, AGI safety, sandbox escape resistance, or broader tool-use safety. It also does not prove A0 predictor usefulness or one-hour policy-scale endurance."
}
artifact.parent.mkdir(parents=True, exist_ok=True)
artifact.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
if failed:
    print(json.dumps({"artifact": str(artifact), "failed_checks": failed}, indent=2))
    raise SystemExit(1)
print(json.dumps({"artifact": str(artifact), "all_required_checks_passed": True, "run_root": str(root)}, indent=2))
PY
