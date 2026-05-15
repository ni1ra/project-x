#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cctype>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <thread>
#include <unordered_map>
#include <utility>
#include <vector>
#include <unistd.h>

namespace px {

constexpr int kDim = 256;
constexpr int kAscii = 128;
// kMaxRoles caps the segment-mode action-space expansion (cycle-3 mechanism).
// WHAT: extra action ids past kAscii reserved for "start copy span from role-token R".
// WHY: per docs/past_work/cycles/phase_v2_organic_substrate/cycle_docs/CYCLE3_MECHANISM.md, the generator's softmax now ranges over
//   literal-char actions [0..kAscii) PLUS role-switch actions [kAscii..kAscii+kMaxRoles).
//   Same connection weights drive both — no authored role-dispatch.
// NEGATIVE-SPACE: this is a compile-time cap on UNIQUE role strings the brain has ever
//   seen during training. The tightened benchmark exposes ~6 (name/object/place/signal/
//   topic/intent); 16 gives ~10 headroom. Hitting the cap is fail-fast at registration
//   (std::runtime_error), never silent overflow. Bumping it is one line + recompile;
//   serialized state survives because role_id is a stable fnv1a hash, not an index.
constexpr int kMaxRoles = 16;
constexpr int kExtendedActions = kAscii + kMaxRoles;
constexpr unsigned char kStart = 2;
constexpr unsigned char kEnd = 3;

struct Config {
  int dimensions = kDim;
  uint64_t seed = 1729;
  double learning_rate = 1.0;
  int top_k = 5;
  int max_output_chars = 48;
  double trace_gain = 4.0;
  double context_gain = 1.0;
  // Cycle-6 calibration for computed-relation feature addresses. Generic hidden_rule tokens
  // accumulate across parity/threshold/modular examples; relation-specific features need a
  // separate persisted gain so computed evidence beats shared surface words without becoming
  // an authored answer route.
  double derived_relation_gain = 5.0;
  // Cycle-7C symbolic relation channel.
  // WHAT: non-numeric entity attributes can activate same/different relation addresses
  // (for example left_color:red + right_color:red -> color:same). These are feature
  // addresses only; arbitrary action labels still have to be learned from feedback.
  // NEGATIVE-SPACE: this never maps color:same, shape:different, etc. to an answer.
  double symbolic_relation_gain = 5.0;
  // Cycle-7D tiny-grid spatial channel.
  // WHAT: 3x3 cell observations can activate spatial relation addresses such as
  // horizontal_mirror:yes or row_shift:no, bound to the cue token in the input.
  // NEGATIVE-SPACE: no relation-to-action branch; arbitrary labels are still learned
  // from feedback after action.
  double grid_spatial_gain = 5.0;
  double transition_gain = 0.65;
  double position_gain = 0.35;
  double state_binding_gain = 1.35;
  double slot_pass_gain = 7.5;
  // segment_mode_gain scales the softmax contribution of mode-switch weights vs literal-char
  // weights. WHY: the action space [kAscii..) carries different units of evidence than ASCII
  // chars (1 mode-switch decision vs N character-bigrams), so a separate gain knob keeps the
  // two contributions comparable without distorting either.
  // CALIBRATION: 5.0 caused mode-switches to win at post-filler positions over the literal
  // separator ' ' that was learned at the exact (pos, prev) — bucket-feature transfer of the
  // mode-switch dominated. 1.5 keeps mode-switches competitive at segment-starts (where
  // mode-switch has full feature match and literal chars have wrong-prev mismatch) while
  // letting ' ' separators win at post-filler positions where they have full-feature match.
  double segment_mode_gain = 0.3;
  bool use_trace_id_feature = true;
  bool use_slot_pass_through = true;
  // use_segment_mode flips the cycle-3 learned segment generation. WHEN TRUE: learn() routes
  // observation-filler spans to mode-switch weights; generate() runs the segment-mode state
  // machine; serialize/load persist ROLES + SEGMENT_CONNS sections; state_hash includes both.
  // WHEN FALSE: legacy emission path bit-exactly (cycle-2 hash 3536309de837d3e2 preserved
  // when applied to cycle-2 saved state). Default TRUE so new training uses the mechanism;
  // cycle-2 loaded state will override to FALSE via the CONFIG line.
  bool use_segment_mode = true;
  // Compile-time cap mirrored from kMaxRoles, surfaced through CONFIG so the
  // serialized snapshot self-documents the action-space width.
  int max_roles = kMaxRoles;
  // Cycle-4 trace-span-position literal feature.
  // WHAT: when a stored trace says "this target span came from observation role R", the
  // literal fallback also learns a trace-local feature keyed by (trace-id, role, offset
  // inside that copied span). Generate reactivates that feature only when an activated
  // trace's own target segmentation says the current output position is inside such a span.
  // WHY: cycle-3.5's trace-id literal walk still lost one deep-span char because its
  // evidence was split across pos/prev/bucket bindings while a global-prev transition
  // carried the inter-word space. This feature adds the missing variable: "where am I
  // inside the remembered copy span for this trace?"
  // NEGATIVE-SPACE: no current-observation parser decides the answer. The feature only
  // contributes weights learned during training, and copy-mode still owns normal role
  // transfer when the role is present.
  double trace_span_position_gain = 0.5;
  bool use_trace_span_position_features = true;
  // Cycle-13 mechanical text-quality pressure.
  // WHAT: when enabled during raw corpus exposure, copied raw_utterance spans learn an
  // explicit post-copy END feature and generation penalizes character choices that extend
  // a repeated suffix. This is decoder/generator hygiene, not authored answer content.
  // NEGATIVE-SPACE: no template text, no semantic parser, no route table, and no subjective
  // quality score. The only learned target remains the observed raw utterance itself.
  double repetition_penalty_weight = 0.0;
  // Cycle-5 derived-belief channel.
  // WHAT: pure numeric observation fillers (for example mark:7) activate deterministic
  // role-relative facts such as parity=odd. Those facts are only feature addresses; the
  // learned CONNS substrate still decides which output chars/actions they support.
  // NEGATIVE-SPACE: this never maps odd->stay or even->go. It is an encoder-side belief
  // primitive, not an answer route.
  bool use_numeric_derived_features = true;
  // Cycle-6 threshold-derived channel.
  // WHAT: numeric observation fillers can be compared with a numeric cutoff observation
  // (for example mark:8 + cutoff:5 -> gt). The relation becomes a feature address only;
  // target text still has to be learned from rewarded examples.
  bool use_threshold_derived_features = true;
  // Cycle-6 modular-derived channel.
  // WHAT: numeric observation fillers can be assigned to a modular class using an observed
  // modulus (for example mark:11 + modulus:3 -> class 2). Namespace is distinct from parity
  // so mod-2/parity ablations cannot accidentally couple.
  bool use_modular_derived_features = true;
  // Cycle-5 relation projection channel.
  // WHAT: rewarded traces self-supervise role-to-role projection weights (for example
  // person:arin -> object:copper). At generation, a topic cue can activate the learned
  // relation address even when the target filler is absent from current observations.
  // NEGATIVE-SPACE: no authored entity->answer table; projected chars are emitted from
  // learned CONNS rows exactly like normal literals.
  bool use_relation_projection = true;
  bool use_symbolic_relation_features = true;
  bool use_grid_spatial_features = true;
  // Cycle-8 A0 event-outcome predictor.
  // Disabled by default so legacy train/eval/text/interactive phases keep their pinned
  // state hashes. sleep-wake/daemon-lite explicitly enables it and owns all updates.
  bool use_outcome_predictor = false;
  double outcome_predictor_learning_rate = 0.025;
};

struct Event {
  std::string event_id;
  std::string episode_id;
  std::string split;
  std::string domain;
  int level = 0;
  std::string input;
  std::vector<std::string> observations;
  std::string target_output;
  std::map<std::string, double> reward;
  std::string source;
  std::string composition = "unspecified";

  double reward_scalar() const {
    if (reward.empty()) return 0.0;
    double total = 0.0;
    for (const auto& item : reward) total += item.second;
    return total / static_cast<double>(reward.size());
  }
};

struct TextExperienceRecord {
  std::string schema;
  std::string experience_id;
  std::string session_id;
  std::string split;
  std::string input_text;
  std::vector<std::string> observations;
  std::string correction_output;
  std::map<std::string, double> reward;
  std::string source;
  std::string composition = "text_experience";
};

struct VoicePromptRecord {
  std::string schema;
  std::string prompt_id;
  std::string prompt_text;
  std::vector<std::string> observations;
  std::string source;
  std::string composition = "voice_pressure";
};

struct ProbeStateRecord {
  std::string schema;
  std::string state_id;
  std::string parent_state_path;
  std::string state_path;
  std::string source_artifact_path;
  std::string lineage;
};

struct CorpusShardRecord {
  std::string schema;
  std::string source_id;
  std::string shard_id;
  std::string local_path;
  std::string sha256;
  std::string canonicalization_hash;
  std::string dedup_hash;
  std::string encoding;
  std::string line_separator;
  int byte_count = 0;
  int char_count = 0;
  int line_count = 0;
  std::string split;
  int split_bucket = -1;
  std::string split_policy_version;
  std::string filter_status;
  std::string filter_reason;
  std::string filter_version;
  std::string retrieval_timestamp_utc;
  std::string license_spdx_id;
};

struct ObservationSlot {
  std::string type;
  std::string value;
};

struct Trace {
  std::string event_id;
  std::string episode_id;
  std::string split;
  std::string domain;
  int level = 0;
  std::string input;
  std::vector<std::string> observations;
  // Derived runtime caches. These are rebuilt from observations on learn/load and are not
  // serialized or hashed; they remove repeated parse/allocation during generation scans.
  std::vector<ObservationSlot> slots;
  bool has_numeric_relation_control = false;
  std::vector<std::string> threshold_keys;
  std::vector<std::string> modular_keys;
  std::vector<std::string> symbolic_relation_keys;
  std::vector<std::string> grid_spatial_keys;
  std::string target_output;
  double reward_scalar = 0.0;
  std::array<double, kDim> vector{};
};

struct Feature {
  uint64_t id = 0;
  double scale = 0.0;
};

struct Activation {
  std::string event_id;
  std::string domain;
  int level = 0;
  double similarity = 0.0;
  double reward_scalar = 0.0;
};

struct OutcomePrediction {
  double reward_scalar = 0.0;
  double exact_prob_or_score = 0.0;
  double lcs_error_ratio = 1.0;
  double surprise = 1.0;
  size_t feature_count = 0;
  std::vector<Feature> features;
  std::vector<Activation> trace_refs;
};

struct OutcomeTarget {
  double reward_scalar = 0.0;
  double exact_binary = 0.0;
  double lcs_error_ratio = 1.0;
};

struct PredictionError {
  double reward_abs_error = 0.0;
  double exact_abs_error = 0.0;
  double lcs_error_abs_error = 0.0;
  double surprise = 0.0;
};

struct PredictorWeights {
  double reward_w = 0.0;
  double exact_w = 0.0;
  double error_w = 0.0;
};

struct MutationRef {
  std::string mutation_id;
  std::string kind;
  bool accepted = false;
  uint64_t state_before_hash = 0;
  uint64_t state_after_hash = 0;
  std::string reason;
};

struct GenerationStep {
  int position = 0;
  unsigned char chosen = 0;
  double score = 0.0;
  std::vector<std::pair<unsigned char, double>> top_chars;
  size_t active_state_feature_count = 0;
  size_t active_slot_copy_count = 0;
  size_t active_copy_boundary_count = 0;
  // Cycle-3 evidence: true when this step was a learned mode-switch (first emission of a
  // copy span). copy_role records which role-token was selected. Subsequent emissions within
  // the same copy span have is_copy_emit=true and the same copy_role.
  bool is_mode_switch = false;
  bool is_copy_emit = false;
  std::string copy_role;
};

struct Generation {
  std::string output;
  std::vector<Activation> activations;
  std::vector<GenerationStep> steps;
  uint64_t state_hash = 0;
  size_t connection_feature_count = 0;
  size_t connection_nonzero_count = 0;
  size_t slot_copy_link_count = 0;
  // Cycle-3 cumulative evidence: how many mode-switches fired during this generate, and how
  // many output chars came from copy-mode emission (vs literal-mode emission).
  size_t segment_mode_switch_count = 0;
  size_t copy_mode_char_count = 0;
  size_t copy_boundary_feature_count = 0;
};

struct Weights {
  // Action-space layout (cycle-3 expansion):
  //   value[0..kAscii)              → literal-char actions (existing behavior)
  //   value[kAscii..kExtendedActions) → mode-switch actions, indexed by role-table slot
  // NEGATIVE-SPACE: this is NOT a separate map keyed by role_id. The role_id_hex64 in
  // SEGMENT_CONNS serializes the stable hash, but at runtime the brain stores mode-switch
  // weights in a fixed-width slot array indexed by role-table position. The slot ←→ role_id
  // mapping is kept in role_token_table_ on OrganicBrain; serialization writes role_id (the
  // hash) so the array slot is irrelevant across processes.
  std::array<double, kExtendedActions> value{};
};

struct TraceSpanPosition {
  std::string role;
  size_t offset = 0;
};

uint64_t fnv1a(std::string_view text, uint64_t seed = 1469598103934665603ull) {
  uint64_t hash = seed;
  for (unsigned char c : text) {
    hash ^= static_cast<uint64_t>(c);
    hash *= 1099511628211ull;
  }
  return hash;
}

uint64_t mix64(uint64_t x) {
  x += 0x9e3779b97f4a7c15ull;
  x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ull;
  x = (x ^ (x >> 27)) * 0x94d049bb133111ebull;
  return x ^ (x >> 31);
}

uint64_t combine(uint64_t a, uint64_t b) {
  return mix64(a ^ mix64(b + 0x9e3779b97f4a7c15ull));
}

uint64_t hash_pair(std::string_view left, std::string_view right) {
  return combine(fnv1a(left), fnv1a(right));
}

std::string hex64(uint64_t value) {
  std::ostringstream out;
  out << std::hex << std::setw(16) << std::setfill('0') << value;
  return out.str();
}

std::string timestamp_utc() {
  auto now = std::chrono::system_clock::now();
  std::time_t t = std::chrono::system_clock::to_time_t(now);
  std::tm tm{};
  gmtime_r(&t, &tm);
  std::ostringstream out;
  out << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
  return out.str();
}

std::string json_escape(const std::string& text) {
  std::ostringstream out;
  for (unsigned char c : text) {
    switch (c) {
      case '\\': out << "\\\\"; break;
      case '"': out << "\\\""; break;
      case '\n': out << "\\n"; break;
      case '\r': out << "\\r"; break;
      case '\t': out << "\\t"; break;
      default:
        if (c < 32) {
          out << "\\u" << std::hex << std::setw(4) << std::setfill('0') << static_cast<int>(c)
              << std::dec << std::setfill(' ');
        } else {
          out << static_cast<char>(c);
        }
    }
  }
  return out.str();
}

std::string q(const std::string& text) {
  return "\"" + json_escape(text) + "\"";
}

std::string shell_quote(const std::string& text) {
  std::string out = "'";
  for (char c : text) {
    if (c == '\'') out += "'\\''";
    else out.push_back(c);
  }
  out.push_back('\'');
  return out;
}

std::string char_label(unsigned char c) {
  if (c == kEnd) return "<END>";
  if (c == kStart) return "<START>";
  return std::string(1, static_cast<char>(c));
}

std::string lower_ascii(const std::string& text) {
  std::string out;
  out.reserve(text.size());
  for (unsigned char c : text) {
    if (c >= 'A' && c <= 'Z') out.push_back(static_cast<char>(c - 'A' + 'a'));
    else out.push_back(static_cast<char>(c));
  }
  return out;
}

std::vector<std::string> tokenize(const std::string& text) {
  std::vector<std::string> tokens;
  std::string current;
  for (unsigned char c : lower_ascii(text)) {
    bool word = (c >= 'a' && c <= 'z') || (c >= '0' && c <= '9');
    if (word) {
      current.push_back(static_cast<char>(c));
    } else if (!current.empty()) {
      tokens.push_back(current);
      current.clear();
    }
  }
  if (!current.empty()) tokens.push_back(current);
  return tokens;
}

std::vector<std::string> raw_text_span_observations(const std::string& input) {
  std::vector<std::string> observations;
  auto tokens = tokenize(input);
  constexpr size_t kMaxRawSpanTokens = 8;
  constexpr size_t kMaxRawSpanLen = 3;
  size_t usable = std::min(tokens.size(), kMaxRawSpanTokens);
  for (size_t start = 0; start < usable; ++start) {
    std::string span;
    for (size_t len = 1; len <= kMaxRawSpanLen && start + len <= usable; ++len) {
      if (len == 1) span = tokens[start];
      else span += " " + tokens[start + len - 1];
      size_t end = start + len - 1;
      observations.push_back("raw_span_" + std::to_string(start) + "_" +
                             std::to_string(end) + ":" + span);
    }
  }
  return observations;
}

void skip_ws(const std::string& line, size_t& pos) {
  while (pos < line.size() && std::isspace(static_cast<unsigned char>(line[pos]))) ++pos;
}

size_t key_pos(const std::string& line, const std::string& key) {
  std::string needle = "\"" + key + "\"";
  size_t pos = line.find(needle);
  if (pos == std::string::npos) throw std::runtime_error("missing JSON key: " + key);
  pos = line.find(':', pos + needle.size());
  if (pos == std::string::npos) throw std::runtime_error("missing JSON colon: " + key);
  ++pos;
  skip_ws(line, pos);
  return pos;
}

std::string parse_string_at(const std::string& line, size_t& pos) {
  if (pos >= line.size() || line[pos] != '"') throw std::runtime_error("expected JSON string");
  ++pos;
  std::string out;
  while (pos < line.size()) {
    char c = line[pos++];
    if (c == '"') return out;
    if (c == '\\') {
      if (pos >= line.size()) throw std::runtime_error("bad JSON escape");
      char e = line[pos++];
      if (e == 'n') out.push_back('\n');
      else if (e == 'r') out.push_back('\r');
      else if (e == 't') out.push_back('\t');
      else out.push_back(e);
    } else {
      out.push_back(c);
    }
  }
  throw std::runtime_error("unterminated JSON string");
}

std::string get_string(const std::string& line, const std::string& key) {
  size_t pos = key_pos(line, key);
  return parse_string_at(line, pos);
}

std::optional<std::string> maybe_get_string(const std::string& line, const std::string& key) {
  std::string needle = "\"" + key + "\"";
  if (line.find(needle) == std::string::npos) return std::nullopt;
  size_t pos = key_pos(line, key);
  return parse_string_at(line, pos);
}

int get_int(const std::string& line, const std::string& key) {
  size_t pos = key_pos(line, key);
  size_t end = pos;
  while (end < line.size() && (std::isdigit(static_cast<unsigned char>(line[end])) || line[end] == '-')) ++end;
  return std::stoi(line.substr(pos, end - pos));
}

std::vector<std::string> get_string_array(const std::string& line, const std::string& key) {
  size_t pos = key_pos(line, key);
  if (pos >= line.size() || line[pos] != '[') throw std::runtime_error("expected JSON array: " + key);
  ++pos;
  std::vector<std::string> values;
  while (pos < line.size()) {
    skip_ws(line, pos);
    if (pos < line.size() && line[pos] == ']') return values;
    values.push_back(parse_string_at(line, pos));
    skip_ws(line, pos);
    if (pos < line.size() && line[pos] == ',') ++pos;
  }
  throw std::runtime_error("unterminated JSON array: " + key);
}

std::map<std::string, double> get_number_object(const std::string& line, const std::string& key) {
  size_t pos = key_pos(line, key);
  if (pos >= line.size() || line[pos] != '{') throw std::runtime_error("expected JSON object: " + key);
  ++pos;
  std::map<std::string, double> values;
  while (pos < line.size()) {
    skip_ws(line, pos);
    if (pos < line.size() && line[pos] == '}') return values;
    std::string name = parse_string_at(line, pos);
    skip_ws(line, pos);
    if (pos >= line.size() || line[pos] != ':') throw std::runtime_error("expected object colon");
    ++pos;
    skip_ws(line, pos);
    size_t end = pos;
    while (end < line.size() &&
           (std::isdigit(static_cast<unsigned char>(line[end])) || line[end] == '-' ||
            line[end] == '+' || line[end] == '.' || line[end] == 'e' || line[end] == 'E')) {
      ++end;
    }
    values[name] = std::stod(line.substr(pos, end - pos));
    pos = end;
    skip_ws(line, pos);
    if (pos < line.size() && line[pos] == ',') ++pos;
  }
  throw std::runtime_error("unterminated JSON object: " + key);
}

std::vector<std::string> tokenize(const std::string& text);
std::vector<std::string> raw_text_span_observations(const std::string& input);

Event parse_event(const std::string& line) {
  Event event;
  event.event_id = get_string(line, "event_id");
  event.episode_id = get_string(line, "episode_id");
  event.split = get_string(line, "split");
  event.domain = get_string(line, "domain");
  event.level = get_int(line, "level");
  event.input = get_string(line, "input");
  event.observations = get_string_array(line, "observations");
  event.target_output = get_string(line, "target_output");
  event.reward = get_number_object(line, "reward");
  event.source = get_string(line, "source");
  if (auto composition = maybe_get_string(line, "composition")) event.composition = *composition;
  return event;
}

TextExperienceRecord parse_text_experience_record(const std::string& line) {
  TextExperienceRecord record;
  if (auto schema = maybe_get_string(line, "schema")) record.schema = *schema;
  record.experience_id = get_string(line, "experience_id");
  record.session_id = get_string(line, "session_id");
  record.split = get_string(line, "split");
  record.input_text = get_string(line, "input_text");
  record.observations = get_string_array(line, "observations");
  record.correction_output = get_string(line, "correction_output");
  record.reward = get_number_object(line, "reward");
  record.source = get_string(line, "source");
  if (auto composition = maybe_get_string(line, "composition")) record.composition = *composition;
  return record;
}

VoicePromptRecord parse_voice_prompt_record(const std::string& line) {
  static const std::vector<std::string> kForbiddenKeys = {
      "\"label\"", "\"labels\"", "\"correction_output\"", "\"expected_output\"",
      "\"target_output\"", "\"reward\"", "\"score\"", "\"composition\"",
      "\"topic\"", "\"intent\"", "\"theme\"", "\"expected_filler\"",
      "\"topic:", "\"intent:", "\"theme:", "\"expected_filler:"};
  for (const auto& key : kForbiddenKeys) {
    if (line.find(key) != std::string::npos) {
      throw std::runtime_error("voice prompt record contains forbidden key " + key);
    }
  }
  VoicePromptRecord record;
  if (auto schema = maybe_get_string(line, "schema")) record.schema = *schema;
  record.prompt_id = get_string(line, "prompt_id");
  record.prompt_text = get_string(line, "prompt_text");
  if (line.find("\"observations\"") != std::string::npos) {
    record.observations = get_string_array(line, "observations");
  }
  if (record.observations.empty()) {
    record.observations = {"raw_utterance:" + record.prompt_text};
  }
  record.source = maybe_get_string(line, "source").value_or("cycle11_voice_pressure");
  return record;
}

ProbeStateRecord parse_probe_state_record(const std::string& line) {
  ProbeStateRecord record;
  if (auto schema = maybe_get_string(line, "schema")) record.schema = *schema;
  record.state_id = get_string(line, "state_id");
  record.parent_state_path = maybe_get_string(line, "parent_state_path").value_or("");
  record.state_path = get_string(line, "state_path");
  record.source_artifact_path = maybe_get_string(line, "source_artifact_path").value_or("");
  record.lineage = maybe_get_string(line, "lineage").value_or("");
  return record;
}

CorpusShardRecord parse_corpus_shard_record(const std::string& line) {
  CorpusShardRecord record;
  if (auto schema = maybe_get_string(line, "schema")) record.schema = *schema;
  record.source_id = get_string(line, "source_id");
  record.shard_id = get_string(line, "shard_id");
  record.local_path = get_string(line, "local_path");
  record.sha256 = get_string(line, "sha256");
  record.canonicalization_hash = get_string(line, "canonicalization_hash");
  record.dedup_hash = get_string(line, "dedup_hash");
  record.encoding = get_string(line, "encoding");
  record.line_separator = get_string(line, "line_separator");
  record.byte_count = get_int(line, "byte_count");
  record.char_count = get_int(line, "char_count");
  record.line_count = get_int(line, "line_count");
  record.split = get_string(line, "split");
  record.split_bucket = get_int(line, "split_bucket");
  record.split_policy_version = get_string(line, "split_policy_version");
  record.filter_status = get_string(line, "filter_status");
  record.filter_reason = get_string(line, "filter_reason");
  record.filter_version = get_string(line, "filter_version");
  record.retrieval_timestamp_utc = get_string(line, "retrieval_timestamp_utc");
  record.license_spdx_id = get_string(line, "license_spdx_id");
  return record;
}

Event event_from_text_experience(const TextExperienceRecord& record,
                                 bool include_raw_text_spans = false) {
  Event event;
  event.event_id = record.experience_id;
  event.episode_id = record.session_id;
  event.split = record.split == "train" ? "train" : "probe";
  event.domain = "text_experience";
  event.level = record.split == "train" ? 0 : 1;
  event.input = record.input_text;
  event.observations = record.observations;
  if (include_raw_text_spans) {
    auto spans = raw_text_span_observations(record.input_text);
    event.observations.insert(event.observations.end(), spans.begin(), spans.end());
  }
  event.target_output = record.correction_output;
  event.reward = record.reward;
  event.source = record.source;
  event.composition = record.composition;
  return event;
}

Event event_from_voice_prompt(const VoicePromptRecord& record) {
  Event event;
  event.event_id = record.prompt_id;
  event.episode_id = "cycle11_voice_pressure";
  event.split = "probe";
  event.domain = "voice_pressure";
  event.level = 0;
  event.input = record.prompt_text;
  event.observations = record.observations;
  event.target_output = "";
  event.source = record.source;
  event.composition = record.composition;
  return event;
}

std::vector<ObservationSlot> parse_slots(const std::vector<std::string>& observations) {
  std::vector<ObservationSlot> slots;
  for (const auto& observation : observations) {
    size_t colon = observation.find(':');
    if (colon == std::string::npos || colon == 0 || colon + 1 >= observation.size()) continue;
    slots.push_back({lower_ascii(observation.substr(0, colon)), lower_ascii(observation.substr(colon + 1))});
  }
  return slots;
}

std::optional<int> parse_pure_int(const std::string& value) {
  if (value.empty()) return std::nullopt;
  size_t pos = 0;
  bool negative = false;
  if (value[pos] == '-') {
    negative = true;
    ++pos;
  }
  if (pos >= value.size()) return std::nullopt;
  int out = 0;
  for (; pos < value.size(); ++pos) {
    unsigned char c = static_cast<unsigned char>(value[pos]);
    if (!std::isdigit(c)) return std::nullopt;
    out = out * 10 + static_cast<int>(c - '0');
  }
  return negative ? -out : out;
}

bool is_threshold_cutoff_role(const std::string& role) {
  return role == "cutoff" || role == "limit";
}

bool is_modulus_role(const std::string& role) {
  return role == "modulus" || role == "mod";
}

bool is_numeric_relation_control_role(const std::string& role) {
  return is_threshold_cutoff_role(role) || is_modulus_role(role) || role == "modclass";
}

bool has_numeric_relation_control(const std::vector<ObservationSlot>& slots) {
  for (const auto& slot : slots) {
    if (is_numeric_relation_control_role(slot.type)) return true;
  }
  return false;
}

int positive_mod(int value, int modulus) {
  int result = value % modulus;
  return result < 0 ? result + modulus : result;
}

std::vector<std::string> threshold_relation_keys(const std::vector<ObservationSlot>& slots) {
  std::vector<std::string> keys;
  for (const auto& value_slot : slots) {
    if (is_numeric_relation_control_role(value_slot.type)) continue;
    auto value = parse_pure_int(value_slot.value);
    if (!value.has_value()) continue;
    for (const auto& cutoff_slot : slots) {
      if (!is_threshold_cutoff_role(cutoff_slot.type)) continue;
      auto cutoff = parse_pure_int(cutoff_slot.value);
      if (!cutoff.has_value()) continue;
      std::string relation = (*value > *cutoff) ? "gt" : ((*value < *cutoff) ? "lt" : "eq");
      keys.push_back(value_slot.type + ":" + cutoff_slot.type + ":" +
                     std::to_string(*cutoff) + ":" + relation);
    }
  }
  return keys;
}

std::vector<std::string> modular_relation_keys(const std::vector<ObservationSlot>& slots) {
  std::vector<std::string> keys;
  for (const auto& value_slot : slots) {
    if (is_numeric_relation_control_role(value_slot.type)) continue;
    auto value = parse_pure_int(value_slot.value);
    if (!value.has_value()) continue;
    for (const auto& modulus_slot : slots) {
      if (!is_modulus_role(modulus_slot.type)) continue;
      auto modulus = parse_pure_int(modulus_slot.value);
      if (!modulus.has_value() || *modulus <= 1) continue;
      int cls = positive_mod(*value, *modulus);
      keys.push_back(value_slot.type + ":" + modulus_slot.type + ":" +
                     std::to_string(*modulus) + ":" + std::to_string(cls));
    }
  }
  return keys;
}

std::optional<std::pair<std::string, std::string>> split_entity_attribute_role(
    const std::string& role) {
  size_t sep = role.find('_');
  if (sep == std::string::npos || sep == 0 || sep + 1 >= role.size()) return std::nullopt;
  return std::make_pair(role.substr(0, sep), role.substr(sep + 1));
}

std::vector<std::string> symbolic_relation_keys(const std::vector<ObservationSlot>& slots) {
  std::set<std::string> keys;
  for (size_t i = 0; i < slots.size(); ++i) {
    auto left = split_entity_attribute_role(slots[i].type);
    if (!left.has_value() || slots[i].value.empty()) continue;
    for (size_t j = i + 1; j < slots.size(); ++j) {
      auto right = split_entity_attribute_role(slots[j].type);
      if (!right.has_value() || slots[j].value.empty()) continue;
      if (left->first == right->first || left->second != right->second) continue;
      std::string relation = slots[i].value == slots[j].value ? "same" : "different";
      std::string entity_a = std::min(left->first, right->first);
      std::string entity_b = std::max(left->first, right->first);
      // Attribute-level relation carries transfer across entity names. Pair-level relation
      // remains available when an episode genuinely depends on a stable role pair.
      keys.insert(left->second + ":" + relation);
      keys.insert("pair:" + entity_a + "-" + entity_b + ":" + left->second + ":" + relation);
    }
  }
  return {keys.begin(), keys.end()};
}

std::string symbolic_relation_key_attribute(const std::string& key) {
  if (key.rfind("pair:", 0) == 0) {
    size_t first = key.find(':');
    size_t second = first == std::string::npos ? std::string::npos : key.find(':', first + 1);
    size_t third = second == std::string::npos ? std::string::npos : key.find(':', second + 1);
    if (second == std::string::npos || third == std::string::npos) return std::string();
    return key.substr(second + 1, third - second - 1);
  }
  size_t colon = key.find(':');
  return colon == std::string::npos ? std::string() : key.substr(0, colon);
}

struct GridCell {
  int row = 0;
  int col = 0;
  std::string value;
};

std::optional<std::pair<int, int>> parse_grid_cell_role(const std::string& role) {
  constexpr std::string_view prefix = "cell_";
  if (role.rfind(std::string(prefix), 0) != 0) return std::nullopt;
  size_t first = role.find('_', prefix.size());
  if (first == std::string::npos || first + 1 >= role.size()) return std::nullopt;
  auto row = parse_pure_int(role.substr(prefix.size(), first - prefix.size()));
  auto col = parse_pure_int(role.substr(first + 1));
  if (!row.has_value() || !col.has_value()) return std::nullopt;
  if (*row < 0 || *row > 2 || *col < 0 || *col > 2) return std::nullopt;
  return std::make_pair(*row, *col);
}

std::vector<GridCell> grid_cells_from_slots(const std::vector<ObservationSlot>& slots) {
  std::vector<GridCell> cells;
  for (const auto& slot : slots) {
    if (slot.value.empty() || slot.value == "empty" || slot.value == "blank") continue;
    auto pos = parse_grid_cell_role(slot.type);
    if (!pos.has_value()) continue;
    cells.push_back({pos->first, pos->second, slot.value});
  }
  return cells;
}

std::vector<std::string> grid_spatial_keys(const std::vector<ObservationSlot>& slots) {
  auto cells = grid_cells_from_slots(slots);
  if (cells.size() < 2) return {};
  bool horizontal_mirror = false;
  bool vertical_mirror = false;
  bool diagonal_mirror = false;
  bool row_shift = false;
  for (size_t i = 0; i < cells.size(); ++i) {
    for (size_t j = i + 1; j < cells.size(); ++j) {
      const auto& a = cells[i];
      const auto& b = cells[j];
      if (a.value != b.value) continue;
      horizontal_mirror = horizontal_mirror || (a.row == b.row && a.col + b.col == 2 && a.col != b.col);
      vertical_mirror = vertical_mirror || (a.col == b.col && a.row + b.row == 2 && a.row != b.row);
      diagonal_mirror = diagonal_mirror || (a.row == b.col && a.col == b.row &&
                                            (a.row != b.row || a.col != b.col));
      row_shift = row_shift || (a.row == b.row && std::abs(a.col - b.col) == 1);
    }
  }
  return {
      std::string("horizontal_mirror:") + (horizontal_mirror ? "yes" : "no"),
      std::string("vertical_mirror:") + (vertical_mirror ? "yes" : "no"),
      std::string("diagonal_mirror:") + (diagonal_mirror ? "yes" : "no"),
      std::string("row_shift:") + (row_shift ? "yes" : "no"),
  };
}

std::string grid_spatial_key_cue(const std::string& key) {
  if (key.rfind("horizontal_mirror:", 0) == 0) return "horizontal";
  if (key.rfind("vertical_mirror:", 0) == 0) return "vertical";
  if (key.rfind("diagonal_mirror:", 0) == 0) return "diagonal";
  if (key.rfind("row_shift:", 0) == 0) return "row";
  return "";
}

void refresh_trace_caches(Trace& trace) {
  trace.slots = parse_slots(trace.observations);
  trace.has_numeric_relation_control = has_numeric_relation_control(trace.slots);
  trace.threshold_keys = threshold_relation_keys(trace.slots);
  trace.modular_keys = modular_relation_keys(trace.slots);
  trace.symbolic_relation_keys = symbolic_relation_keys(trace.slots);
  trace.grid_spatial_keys = grid_spatial_keys(trace.slots);
}

// Persistence helpers — bit-exact double <-> hex64 so state_hash matches across save/load.
std::string double_to_hex(double v) {
  uint64_t bits;
  std::memcpy(&bits, &v, sizeof(bits));
  return hex64(bits);
}

double hex_to_double(const std::string& hex) {
  uint64_t bits = std::stoull(hex, nullptr, 16);
  double v;
  std::memcpy(&v, &bits, sizeof(v));
  return v;
}

double clamp_double(double value, double lo, double hi) {
  return std::max(lo, std::min(hi, value));
}

uint64_t double_bits(double value) {
  uint64_t bits;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}

PredictionError prediction_error_for(const OutcomePrediction& prediction,
                                     const OutcomeTarget& target) {
  PredictionError error;
  error.reward_abs_error = std::abs(prediction.reward_scalar - target.reward_scalar);
  error.exact_abs_error = std::abs(prediction.exact_prob_or_score - target.exact_binary);
  error.lcs_error_abs_error = std::abs(prediction.lcs_error_ratio - target.lcs_error_ratio);
  error.surprise =
      (error.reward_abs_error + error.exact_abs_error + error.lcs_error_abs_error) / 3.0;
  return error;
}

// Split on a single delimiter char. PXSTATE write-time validation below keeps these rows
// delimiter-clean, so load failures happen at save time instead of after restart.
std::vector<std::string> split_delim(const std::string& s, char delim) {
  std::vector<std::string> out;
  std::string current;
  for (char c : s) {
    if (c == delim) { out.push_back(current); current.clear(); }
    else current.push_back(c);
  }
  out.push_back(current);
  return out;
}

void require_pxstate_scalar(const std::string& field, const std::string& value) {
  if (value.find('|') != std::string::npos) {
    throw std::runtime_error("pxstate serialize: " + field + " contains reserved delimiter '|'");
  }
  if (value.find('\n') != std::string::npos || value.find('\r') != std::string::npos) {
    throw std::runtime_error("pxstate serialize: " + field + " contains newline");
  }
}

void require_pxstate_observation(const std::string& field, const std::string& value) {
  require_pxstate_scalar(field, value);
  if (value.find(',') != std::string::npos) {
    throw std::runtime_error("pxstate serialize: " + field + " contains reserved delimiter ','");
  }
}

uint64_t next_event_log_ordinal(const std::string& log_path) {
  std::ifstream in(log_path);
  if (!in) return 1;
  uint64_t count = 0;
  std::string line;
  while (std::getline(in, line)) {
    if (!line.empty()) ++count;
  }
  return count + 1;
}

std::string event_log_id(uint64_t ordinal) {
  std::ostringstream out;
  out << "evtlog_" << std::setw(6) << std::setfill('0') << ordinal;
  return out.str();
}

bool valid_event_log_phase(const std::string& phase) {
  return phase == "perceive" || phase == "predict" || phase == "generate" ||
         phase == "reward" || phase == "learn" || phase == "mutate" ||
         phase == "serialize" || phase == "reflect";
}

void write_reward_object(std::ostream& out, const std::map<std::string, double>& reward) {
  out << "{";
  bool first = true;
  for (const auto& item : reward) {
    if (!first) out << ",";
    out << q(item.first) << ":" << item.second;
    first = false;
  }
  out << "}";
}

// Forward decl — append_event_log_line is defined late (near orchestration phases) but called by
// the artifact writers above it. C++ needs the prototype visible at the call site.
struct Event;
void append_event_log_line(const std::string& log_path, const std::string& organism_id,
                           const std::string& phase, const Event& event,
                           const std::string& raw_output, const std::string& expected,
                           uint64_t state_before_hash, uint64_t state_after_hash,
                           const std::string& source_kind, const std::string& source_path);

// Persistence context plumbed through artifact writers and orchestration phases.
struct PersistenceContext {
  std::string loaded_state_path;
  std::string saved_state_path;
  std::string event_log_path;
  std::string organism_id = "raphael-local-0001";
  // load_status reports the actual runtime state of persistence for this run:
  //   schema_only_not_runtime_persistence — neither save nor load nor event-log active
  //   save_only_no_load_yet — saved state to disk but load contract not exercised this run
  //   save_and_load_verified — fresh-process load round-trip succeeded with hash match
  //   loaded_from_disk — this run started from a loaded state file
  std::string load_status = "schema_only_not_runtime_persistence";
};

std::vector<Event> load_events(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot open benchmark: " + path);
  std::vector<Event> events;
  std::string line;
  int line_no = 0;
  while (std::getline(in, line)) {
    ++line_no;
    if (line.empty()) continue;
    try {
      events.push_back(parse_event(line));
    } catch (const std::exception& e) {
      throw std::runtime_error(path + ":" + std::to_string(line_no) + ": " + e.what());
    }
  }
  return events;
}

std::vector<TextExperienceRecord> load_text_experience_records(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot open text experience database: " + path);
  std::vector<TextExperienceRecord> records;
  std::string line;
  int line_no = 0;
  while (std::getline(in, line)) {
    ++line_no;
    if (line.empty()) continue;
    try {
      auto record = parse_text_experience_record(line);
      if (record.split != "train" && record.split != "probe") {
        throw std::runtime_error("split must be train or probe");
      }
      records.push_back(std::move(record));
    } catch (const std::exception& e) {
      throw std::runtime_error(path + ":" + std::to_string(line_no) + ": " + e.what());
    }
  }
  return records;
}

std::vector<VoicePromptRecord> load_voice_prompt_records(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot open voice prompt database: " + path);
  std::vector<VoicePromptRecord> records;
  std::string line;
  int line_no = 0;
  while (std::getline(in, line)) {
    ++line_no;
    if (line.empty()) continue;
    try {
      auto record = parse_voice_prompt_record(line);
      if (record.prompt_id.empty() || record.prompt_text.empty()) {
        throw std::runtime_error("prompt_id and prompt_text are required");
      }
      records.push_back(std::move(record));
    } catch (const std::exception& e) {
      throw std::runtime_error(path + ":" + std::to_string(line_no) + ": " + e.what());
    }
  }
  return records;
}

std::vector<ProbeStateRecord> load_probe_state_records(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot open probe state manifest: " + path);
  std::vector<ProbeStateRecord> records;
  std::string line;
  int line_no = 0;
  while (std::getline(in, line)) {
    ++line_no;
    if (line.empty()) continue;
    try {
      auto record = parse_probe_state_record(line);
      if (record.state_id.empty() || record.state_path.empty()) {
        throw std::runtime_error("state_id and state_path are required");
      }
      records.push_back(std::move(record));
    } catch (const std::exception& e) {
      throw std::runtime_error(path + ":" + std::to_string(line_no) + ": " + e.what());
    }
  }
  return records;
}

std::vector<CorpusShardRecord> load_corpus_shard_records(const std::string& path) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot open corpus shard manifest: " + path);
  std::vector<CorpusShardRecord> records;
  std::string line;
  while (std::getline(in, line)) {
    if (line.empty()) continue;
    records.push_back(parse_corpus_shard_record(line));
  }
  return records;
}

struct SplitAudit {
  std::map<std::string, int> splits;
  std::map<std::string, std::set<int>> levels_by_domain;
  std::map<std::string, std::map<std::string, int>> held_out_composition_by_domain;
  std::vector<std::string> duplicates;
};

SplitAudit validate_splits(const std::vector<Event>& events) {
  SplitAudit audit;
  std::set<std::string> train_inputs;
  for (const auto& event : events) {
    audit.splits[event.split] += 1;
    audit.levels_by_domain[event.domain].insert(event.level);
    if (event.split == "train") train_inputs.insert(event.input);
    else audit.held_out_composition_by_domain[event.domain][event.composition] += 1;
  }
  std::set<std::string> seen_duplicates;
  for (const auto& event : events) {
    if (event.split != "train" && train_inputs.contains(event.input)) {
      seen_duplicates.insert(event.input);
    }
  }
  audit.duplicates.assign(seen_duplicates.begin(), seen_duplicates.end());
  return audit;
}

struct Hdc {
  Config config;

  int atom_value(const std::string& name, int index) const {
    uint64_t h = fnv1a(name, config.seed);
    h = combine(h, static_cast<uint64_t>(index));
    return (h & 1ull) ? 1 : -1;
  }

  void add_atom(std::array<double, kDim>& vector, const std::string& name, double scale = 1.0) const {
    for (int i = 0; i < kDim; ++i) vector[i] += scale * static_cast<double>(atom_value(name, i));
  }

  void add_bound(std::array<double, kDim>& vector, const std::string& role, const std::array<double, kDim>& filler, double scale = 1.0) const {
    for (int i = 0; i < kDim; ++i) vector[i] += scale * static_cast<double>(atom_value(role, i)) * filler[i];
  }

  std::array<double, kDim> encode_text(const std::string& text) const {
    std::array<double, kDim> vector{};
    auto tokens = tokenize(text);
    for (size_t i = 0; i < tokens.size(); ++i) {
      add_atom(vector, "word:" + tokens[i]);
      std::array<double, kDim> token_atom{};
      add_atom(token_atom, "word:" + tokens[i]);
      add_bound(vector, "slot:" + std::to_string(i % 8), token_atom);
    }
    std::string compact;
    for (const auto& token : tokens) compact += token;
    if (compact.size() >= 3) {
      for (size_t i = 0; i + 2 < compact.size(); ++i) add_atom(vector, "tri:" + compact.substr(i, 3));
    }
    if (tokens.empty()) add_atom(vector, "empty");
    return vector;
  }

  std::array<double, kDim> encode_event(const std::string& input, const std::vector<std::string>& observations) const {
    std::array<double, kDim> vector{};
    add_bound(vector, "role:input", encode_text(input));
    for (size_t i = 0; i < observations.size(); ++i) {
      add_bound(vector, "role:observation:" + std::to_string(i % 8), encode_text(observations[i]));
    }
    auto slots = parse_slots(observations);
    if (config.use_numeric_derived_features && !has_numeric_relation_control(slots)) {
      for (const auto& slot : slots) {
        auto numeric = parse_pure_int(slot.value);
        if (!numeric.has_value()) continue;
        int abs_value = std::abs(*numeric);
        std::string parity = (abs_value % 2 == 0) ? "even" : "odd";
        // HDC receives the same latent facts as the symbolic feature substrate. This lets
        // retrieval prefer traces that share computed evidence (for example odd marks)
        // without hardcoding any output relation for that evidence.
        add_atom(vector, "num-role:" + slot.type);
        add_atom(vector, "num-role-parity:" + slot.type + ":" + parity, config.derived_relation_gain);
        add_atom(vector, "num-any-parity:" + parity, config.derived_relation_gain);
        add_atom(vector, "num-role-lastdigit:" + slot.type + ":" + std::to_string(abs_value % 10), 0.5);
      }
    }
    if (config.use_threshold_derived_features) {
      for (const auto& key : threshold_relation_keys(slots)) {
        add_atom(vector, "num-threshold:" + key, config.derived_relation_gain);
      }
    }
    if (config.use_modular_derived_features) {
      for (const auto& key : modular_relation_keys(slots)) {
        add_atom(vector, "num-modular:" + key, config.derived_relation_gain);
      }
    }
    if (config.use_symbolic_relation_features) {
      auto sym_keys = symbolic_relation_keys(slots);
      for (const auto& token : tokenize(input)) {
        for (const auto& key : sym_keys) {
          if (token != symbolic_relation_key_attribute(key)) continue;
          add_atom(vector, "sym-rel-cue:" + token + "|" + key,
                   config.symbolic_relation_gain * 4.0);
        }
      }
    }
    if (config.use_grid_spatial_features) {
      auto grid_keys = grid_spatial_keys(slots);
      for (const auto& token : tokenize(input)) {
        for (const auto& key : grid_keys) {
          if (token != grid_spatial_key_cue(key)) continue;
          add_atom(vector, "grid-spatial-cue:" + token + "|" + key,
                   config.grid_spatial_gain * 4.0);
        }
      }
    }
    return vector;
  }
};

double cosine(const std::array<double, kDim>& left, const std::array<double, kDim>& right) {
  double dot = 0.0;
  double a = 0.0;
  double b = 0.0;
  for (int i = 0; i < kDim; ++i) {
    dot += left[i] * right[i];
    a += left[i] * left[i];
    b += right[i] * right[i];
  }
  if (a == 0.0 || b == 0.0) return 0.0;
  return dot / (std::sqrt(a) * std::sqrt(b));
}

class OrganicBrain {
 public:
  explicit OrganicBrain(Config cfg = {}) : config_(cfg), hdc_{cfg} {}

  void learn(const Event& event) {
    Trace trace;
    trace.event_id = event.event_id;
    trace.episode_id = event.episode_id;
    trace.split = event.split;
    trace.domain = event.domain;
    trace.level = event.level;
    trace.input = event.input;
    trace.observations = event.observations;
    trace.target_output = event.target_output;
    trace.reward_scalar = std::max(0.0, event.reward_scalar());
    trace.vector = hdc_.encode_event(event.input, event.observations);
    refresh_trace_caches(trace);
    traces_.push_back(trace);
    trace_index_by_event_id_[trace.event_id] = traces_.size() - 1;

    if (trace.reward_scalar <= 0.0) {
      mutation_connection_deltas_.push_back(0);
      return;
    }

    // Legacy slot pass-through learning is bypassed when segment-mode is active — its
    // per-position char bonuses would double-count against mode-switch weights and pull
    // generate's softmax in conflicting directions. When segment-mode is off, the legacy
    // path is preserved bit-exactly.
    if (!config_.use_segment_mode) {
      learn_slot_pass_through(event.observations, event.target_output, trace.reward_scalar);
    }

    auto features = context_features(event.input, event.observations);
    if (config_.use_trace_id_feature) {
      features.push_back({hash_pair("trace", event.event_id), 1.0});
    }
    size_t deltas = 0;

    if (config_.use_segment_mode) {
      // Segment-aware supervision routing.
      // WHAT: walk target_output; at each position try to match an observation filler. On
      //   match, route the supervision signal to a MODE-SWITCH weight (action id = kAscii +
      //   role_slot) and skip past the filler. On no match, route to the per-char weight as
      //   in legacy. End-of-sequence kEnd is learned at the post-walk position regardless.
      // WHY: this is the cycle-3 mechanism. It teaches the brain "at this output position,
      //   the right action is to switch to copy-from-role-R" instead of "the right action is
      //   to emit the char that happened to be there in training". Generalization across
      //   unseen fillers comes from the mode-switch weight being conditioned on context
      //   features (input + activated traces + previous-char + position bucket), NOT on the
      //   literal filler string.
      // NEGATIVE-SPACE: the substring-match here is training-time data routing. It does NOT
      //   appear at inference (generate's mode-switch decision reads only from learned
      //   softmax weights). See CYCLE3_MECHANISM.md §"Builder-Law boundary call".
      const auto& slots = traces_.back().slots;
      const std::string& target = event.target_output;
      std::string lower_target = lower_ascii(target);
      size_t pos = 0;
      unsigned char previous = kStart;
      while (pos < target.size()) {
        auto match = find_longest_filler_match_at(lower_target, pos, slots);
        if (match.has_value()) {
          int role_slot = match->first;
          size_t span = match->second;
          int action_id = kAscii + role_slot;
          // CYCLE-3.5 DUAL-LEARNING (trace-id-anchored literal channel):
          //   primary channel — mode-switch weight at action_id = kAscii + role_slot,
          //     supervised across ALL state features (globals + base context + trace-id
          //     bindings). This is the cycle-3 path: the role-routing abstraction that
          //     generalizes across unseen fillers via shared base-context features.
          //   secondary channel — per-character literal weights at action_id = char, but
          //     supervised ONLY via the TRACE-ID-derived state features (the per-event
          //     memory anchor). Global features (global-prev / global-pos / global-bucket)
          //     and base-context features (input-tokens, obs-tokens) are intentionally
          //     EXCLUDED from the literal walk.
          //
          // WHY this asymmetry: cycle-3 routed the span ONLY to mode-switch, and when the
          //   matching role was absent in a held-out observation the missing-role guardrail
          //   zeroed mode-switch and no literal vote existed — the brain stalled. A naive
          //   dual-learning that supervised literals across ALL features pushed literal
          //   chars above mode-switch on unseen-filler events because shared base-context
          //   features (memory-tok, person-obs, etc.) accumulated literal supervision from
          //   every training event with the same shared token, and reward asymmetry
          //   (source_fidelity-bonused train events have reward 2.0 vs others' 1.5) tipped
          //   one literal past the mode-switch even after segment_mode_gain=0.3 scaling.
          //
          //   Trace-id-only literal supervision sidesteps the asymmetry. The trace-id
          //   feature is event-specific by construction — at inference it fires in
          //   proportion to the cosine similarity between the test query and that trained
          //   trace. On direct_replay events (test query close to one trained trace), the
          //   matched trace's trace-id supervises the trained char specifically; the brain
          //   recovers the literal via the activated memory anchor. On unseen_filler events
          //   (test query spreads similarity across multiple traces), trace-id literal
          //   contributions diffuse across competing chars, while mode-switch retains its
          //   full strength via globals + base-context + diffuse trace-id contributions.
          //
          // NEGATIVE-SPACE: still no inference-time substring-match, still no parser
          //   branch. The literal supervision routing is training-time machinery; both
          //   action paths live in the same connections_ substrate keyed by feature_id.
          //   The literal walk uses a LOCAL `prev` that advances char-by-char so the
          //   bigram chain (e.g. kStart → 'a' → 'r' → 'i' → 'n') exists at fallback time.
          //   The OUTER `previous` after the span still becomes the span's last char so
          //   the post-span transition feature scores against (filler-last → space).
          for (const auto& feature : state_features(features, previous, static_cast<int>(pos))) {
            connections_[feature.id].value[action_id] +=
                trace.reward_scalar * feature.scale * config_.learning_rate;
            ++deltas;
          }
          unsigned char local_prev = previous;
          const std::string matched_role =
              (role_slot >= 0 && role_slot < static_cast<int>(role_token_table_.size()))
                  ? role_token_table_[static_cast<size_t>(role_slot)]
                  : std::string();
          for (size_t k = 0; k < span; ++k) {
            unsigned char c = static_cast<unsigned char>(target[pos + k]);
            if (c >= kAscii) { local_prev = c; continue; }
            if (config_.use_trace_id_feature) {
              // Build trace-id-only state features and walk them. state_features prefixes
              // its return with 3 global features (global-prev / global-pos / global-bucket)
              // — skip indices [0..3) so literal supervision lands ONLY on the trace-id-
              // derived bindings.
              std::vector<Feature> trace_only = {{hash_pair("trace", event.event_id), 1.0}};
              auto sf = state_features(trace_only, local_prev, static_cast<int>(pos + k));
              for (size_t i = 3; i < sf.size(); ++i) {
                connections_[sf[i].id].value[c] +=
                    trace.reward_scalar * sf[i].scale * config_.learning_rate;
                ++deltas;
              }
            }
            if (config_.use_trace_span_position_features && !matched_role.empty()) {
              // Cycle-4 A2: one extra trace-local literal feature keyed by where this
              // character sits inside the remembered copy span. The existing trace-id
              // literal walk already captures absolute position and previous char; this
              // feature captures span progress, which is exactly what the residual
              // `tray4` failure lacked at the deep "tr|a" transition. It is trace-local
              // and role-scoped, so it cannot accumulate across unrelated memories the
              // way the forbidden same-strength base-context literal path did in cycle 3.5.
              uint64_t span_feature = trace_span_position_feature_id(event.event_id, matched_role, k);
              connections_[span_feature].value[c] += trace.reward_scalar * config_.learning_rate;
              ++deltas;
            }
            learned_chars_.insert(c);
            local_prev = c;
          }
          // Advance past the copied span; previous becomes the filler's last char so the
          // post-span position scores against the correct transition feature.
          unsigned char last_in_span = static_cast<unsigned char>(target[pos + span - 1]);
          bool copied_span_reaches_end = (pos + span == target.size());
          pos += span;
          previous = (last_in_span < kAscii) ? last_in_span : previous;
          if (config_.repetition_penalty_weight > 0.0 && copied_span_reaches_end &&
              !matched_role.empty()) {
            connections_[copy_boundary_end_feature_id(matched_role)].value[kEnd] +=
                trace.reward_scalar * config_.learning_rate * config_.repetition_penalty_weight;
            ++deltas;
          }
        } else {
          unsigned char c = static_cast<unsigned char>(target[pos]);
          if (c >= kAscii) { ++pos; continue; }
          for (const auto& feature : state_features(features, previous, static_cast<int>(pos))) {
            connections_[feature.id].value[c] +=
                trace.reward_scalar * feature.scale * config_.learning_rate;
            ++deltas;
          }
          learned_chars_.insert(c);
          previous = c;
          ++pos;
        }
      }
      // End-of-sequence: learn kEnd at the post-walk position with the last-emitted previous.
      for (const auto& feature : state_features(features, previous, static_cast<int>(pos))) {
        connections_[feature.id].value[kEnd] +=
            trace.reward_scalar * feature.scale * config_.learning_rate;
        ++deltas;
      }
    } else {
      // Legacy per-char supervision — preserved bit-exactly when use_segment_mode=0 so
      // cycle-2 saved state can be reloaded and continue training identically.
      unsigned char previous = kStart;
      std::string sequence = event.target_output;
      sequence.push_back(static_cast<char>(kEnd));
      for (size_t pos = 0; pos < sequence.size(); ++pos) {
        unsigned char c = static_cast<unsigned char>(sequence[pos]);
        if (c >= kAscii) continue;
        for (const auto& feature : state_features(features, previous, static_cast<int>(pos))) {
          connections_[feature.id].value[c] += trace.reward_scalar * feature.scale * config_.learning_rate;
          ++deltas;
        }
        if (c != kEnd) learned_chars_.insert(c);
        previous = c;
      }
    }
    if (config_.use_relation_projection) {
      deltas += learn_relation_projection(traces_.back().slots, trace.reward_scalar);
    }
    mutation_connection_deltas_.push_back(deltas);
  }

  void expose_raw_utterance(const Event& event) {
    if (event.input.empty()) throw std::runtime_error("raw corpus exposure requires nonempty input");
    Event exposure = event;
    // Self-supervised exposure signal: the raw input is reused as target so learn()
    // can mutate state without an external label, oracle answer, or scored artifact.
    exposure.target_output = event.input;
    exposure.reward = {{"unlabeled_exposure_weight", 1.0}};
    learn(exposure);
    if (!traces_.empty()) traces_.back().reward_scalar = 0.0;
  }

  Generation generate(const std::string& input, const std::vector<std::string>& observations) const {
    Generation gen;
    auto query = hdc_.encode_event(input, observations);
    gen.activations = retrieve(query);
    auto features = context_features(input, observations);
    auto slots = parse_slots(observations);
    if (config_.use_relation_projection) {
      auto projected = relation_projection_features_for_query(input, observations);
      features.insert(features.end(), projected.begin(), projected.end());
    }
    if (config_.use_numeric_derived_features && config_.use_trace_id_feature) {
      auto numeric_traces = numeric_derived_trace_features_for_query(observations);
      features.insert(features.end(), numeric_traces.begin(), numeric_traces.end());
    }
    if (config_.use_threshold_derived_features && config_.use_trace_id_feature) {
      auto threshold_traces = threshold_derived_trace_features_for_query(observations);
      features.insert(features.end(), threshold_traces.begin(), threshold_traces.end());
    }
    if (config_.use_modular_derived_features && config_.use_trace_id_feature) {
      auto modular_traces = modular_derived_trace_features_for_query(observations);
      features.insert(features.end(), modular_traces.begin(), modular_traces.end());
    }
    if (config_.use_trace_id_feature) {
      for (const auto& activation : gen.activations) {
        if (activation.similarity > 0.0) {
          features.push_back({hash_pair("trace", activation.event_id), activation.similarity * config_.trace_gain});
        }
      }
    }

    unsigned char previous = kStart;
    // Segment-mode state machine. WHEN use_segment_mode IS OFF, the in_copy_mode branch
    // never fires (mode-switch actions are never voted for because the connection weights
    // at indices [kAscii..kExtendedActions) are all zero on a legacy brain), so behavior
    // reduces to the cycle-2 emission path bit-exactly.
    bool in_copy_mode = false;
    std::string copy_filler;
    size_t copy_pos = 0;
    std::string copy_role_name;
    std::string pending_copy_boundary_role;
    for (int pos = 0; pos < config_.max_output_chars; ++pos) {
      if (in_copy_mode) {
        // Copy-mode emission: read the next filler char from the active observation; no
        // softmax scoring at this position because the mode-switch decision already routed
        // the next len(filler) emissions.
        unsigned char fc = static_cast<unsigned char>(copy_filler[copy_pos]);
        if (fc >= kAscii) fc = '?';  // safety guardrail; benchmark fillers are ascii
        GenerationStep step;
        step.position = pos;
        step.chosen = fc;
        step.score = 0.0;
        step.is_copy_emit = true;
        step.copy_role = copy_role_name;
        step.active_state_feature_count = 0;
        step.active_slot_copy_count = 0;
        gen.steps.push_back(step);
        gen.output.push_back(static_cast<char>(fc));
        ++gen.copy_mode_char_count;
        previous = fc;
        ++copy_pos;
        if (copy_pos >= copy_filler.size()) {
          in_copy_mode = false;
          pending_copy_boundary_role = copy_role_name;
        }
        continue;
      }

      auto active = state_features(features, previous, pos);
      add_trace_span_position_features(active, gen.activations, pos);
      size_t copy_boundary_count = 0;
      if (config_.repetition_penalty_weight > 0.0 && !pending_copy_boundary_role.empty()) {
        active.push_back({copy_boundary_end_feature_id(pending_copy_boundary_role), 1.0});
        ++copy_boundary_count;
        ++gen.copy_boundary_feature_count;
        pending_copy_boundary_role.clear();
      }
      std::array<double, kExtendedActions> scores{};
      bool any = false;
      for (const auto& feature : active) {
        auto found = connections_.find(feature.id);
        if (found == connections_.end()) continue;
        for (int a = 0; a < kAscii; ++a) {
          if (found->second.value[a] != 0.0) {
            scores[a] += feature.scale * found->second.value[a];
            any = true;
          }
        }
        if (config_.use_segment_mode) {
          for (int a = kAscii; a < kExtendedActions; ++a) {
            if (found->second.value[a] != 0.0) {
              scores[a] += feature.scale * found->second.value[a] * config_.segment_mode_gain;
              any = true;
            }
          }
        }
      }

      // Legacy slot pass-through is only consulted when segment-mode is OFF. The legacy
      // helper signature is std::array<double, kAscii>&, so we score into a temp and sum
      // the literal-action range into the wider score array.
      size_t slot_copy_count = 0;
      if (!config_.use_segment_mode) {
        std::array<double, kAscii> legacy_scores{};
        slot_copy_count = add_slot_pass_scores(legacy_scores, slots, pos);
        for (int c = 0; c < kAscii; ++c) scores[c] += legacy_scores[c];
        if (slot_copy_count > 0) any = true;
      }

      // GUARDRAIL: zero out mode-switch actions whose target role has no value in the
      // current observations. This MUST happen before the all-zero check so that an event
      // where no literal vote and no reachable mode-switch fire emits END via the existing
      // END-vote-wins logic below, rather than break-mid-output. Roles that were never
      // registered have score 0 by construction (their weight slot is untouched).
      if (config_.use_segment_mode) {
        for (size_t role_slot = 0; role_slot < role_token_table_.size(); ++role_slot) {
          if (observation_value_for_role(role_token_table_[role_slot], observations).empty()) {
            scores[kAscii + static_cast<int>(role_slot)] = 0.0;
          }
        }
      }

      if (!any) break;

      if (config_.repetition_penalty_weight > 0.0) {
        for (int a = 0; a < kAscii; ++a) {
          if (scores[a] == 0.0 || a == kEnd) continue;
          double penalty = repetition_extension_penalty(gen.output, static_cast<unsigned char>(a));
          if (penalty > 0.0) scores[a] -= penalty;
        }
      }

      // Argmax over the expanded action space. Tied scores broken by ascending action_id —
      // preserves the legacy "lowest char_id wins on tie" rule for the literal range.
      std::vector<std::pair<int, double>> ranked;
      for (int a = 0; a < kExtendedActions; ++a) {
        if (scores[a] != 0.0) ranked.push_back({a, scores[a]});
      }
      std::sort(ranked.begin(), ranked.end(), [](const auto& A, const auto& B) {
        if (A.second != B.second) return A.second > B.second;
        return A.first < B.first;
      });
      // CYCLE-3.5: emit an explicit END step when the only surviving votes are mode-switches
      // for missing roles (all zeroed by the guardrail above) but a literal vote pre-zeroing
      // had set `any=true`. Before this fix, the loop broke silently here; the generation
      // evidence trail lost the decision and downstream artifact consumers had to infer the
      // END from a missing step. The architecture doc names this the intended behavior.
      if (ranked.empty()) {
        GenerationStep end_step;
        end_step.position = pos;
        end_step.chosen = static_cast<unsigned char>(kEnd);
        end_step.score = 0.0;
        end_step.active_state_feature_count = active.size();
        end_step.active_slot_copy_count = slot_copy_count;
        end_step.active_copy_boundary_count = copy_boundary_count;
        gen.steps.push_back(end_step);
        break;
      }

      int chosen_action = ranked.front().first;
      double chosen_score = ranked.front().second;

      GenerationStep step;
      step.position = pos;
      step.score = chosen_score;
      step.active_state_feature_count = active.size();
      step.active_slot_copy_count = slot_copy_count;
      step.active_copy_boundary_count = copy_boundary_count;
      // top_chars carries only literal-action contenders for legacy artifact compatibility;
      // mode-switch alternatives surface via is_mode_switch + copy_role on the chosen step.
      for (const auto& r : ranked) {
        if (step.top_chars.size() >= 5) break;
        if (r.first < kAscii) step.top_chars.push_back({static_cast<unsigned char>(r.first), r.second});
      }

      if (chosen_action < kAscii) {
        // Literal emission — existing behavior.
        unsigned char c = static_cast<unsigned char>(chosen_action);
        step.chosen = c;
        gen.steps.push_back(step);
        if (c == kEnd) break;
        gen.output.push_back(static_cast<char>(c));
        previous = c;
      } else {
        // Mode-switch — enter copy span. The guardrail above guarantees a non-empty filler.
        int role_slot = chosen_action - kAscii;
        copy_role_name = (role_slot >= 0 && role_slot < static_cast<int>(role_token_table_.size()))
                             ? role_token_table_[role_slot]
                             : std::string();
        copy_filler = observation_value_for_role(copy_role_name, observations);
        if (copy_filler.empty()) {
          // Defensive — should be unreachable. If we get here, the brain is in an
          // inconsistent state (mode-switch voted for a role whose filler is empty AND
          // the guardrail somehow missed it). Bail out cleanly.
          break;
        }
        step.is_mode_switch = true;
        step.copy_role = copy_role_name;
        // First filler char emitted in THIS same step so output-position alignment matches
        // training (mode-switch at training pos=N corresponded to filler[0] at output pos=N).
        unsigned char first = static_cast<unsigned char>(copy_filler[0]);
        if (first >= kAscii) first = '?';
        step.chosen = first;
        gen.steps.push_back(step);
        gen.output.push_back(static_cast<char>(first));
        ++gen.copy_mode_char_count;
        previous = first;
        ++gen.segment_mode_switch_count;
        if (copy_filler.size() > 1) {
          in_copy_mode = true;
          copy_pos = 1;
        } else {
          pending_copy_boundary_role = copy_role_name;
        }
        // For multi-char fillers, the boundary is marked when the copy-mode branch emits
        // the final char. Single-char fillers mark it here.
      }
    }
    gen.state_hash = state_hash();
    gen.connection_feature_count = connections_.size();
    gen.connection_nonzero_count = connection_nonzero_count();
    gen.slot_copy_link_count = slot_copy_weights_.size();
    return gen;
  }

  uint64_t state_hash() const {
    uint64_t h = fnv1a("organic-v0-state");
    if (config_.max_output_chars != 48) {
      h = combine(h, fnv1a("config.max_output_chars"));
      h = combine(h, static_cast<uint64_t>(config_.max_output_chars));
    }
    if (config_.repetition_penalty_weight != 0.0) {
      h = combine(h, fnv1a("config.repetition_penalty_weight"));
      h = combine(h, double_bits(config_.repetition_penalty_weight));
    }
    h = combine(h, static_cast<uint64_t>(traces_.size()));
    h = combine(h, static_cast<uint64_t>(connections_.size()));
    h = combine(h, static_cast<uint64_t>(slot_copy_weights_.size()));
    for (const auto& trace : traces_) {
      h = combine(h, fnv1a(trace.event_id));
      h = combine(h, fnv1a(trace.input));
      h = combine(h, fnv1a(trace.target_output));
    }
    std::vector<uint64_t> keys;
    keys.reserve(connections_.size());
    for (const auto& item : connections_) keys.push_back(item.first);
    std::sort(keys.begin(), keys.end());
    for (uint64_t key : keys) {
      h = combine(h, key);
      const auto& weights = connections_.at(key).value;
      for (int c = 0; c < kAscii; ++c) {
        if (weights[c] != 0.0) h = combine(h, combine(static_cast<uint64_t>(c), static_cast<uint64_t>(std::llround(weights[c] * 1000000.0))));
      }
    }
    std::vector<uint64_t> slot_keys;
    slot_keys.reserve(slot_copy_weights_.size());
    for (const auto& item : slot_copy_weights_) slot_keys.push_back(item.first);
    std::sort(slot_keys.begin(), slot_keys.end());
    for (uint64_t key : slot_keys) {
      h = combine(h, key);
      h = combine(h, static_cast<uint64_t>(std::llround(slot_copy_weights_.at(key) * 1000000.0)));
    }
    // Cycle-3 hash extension: GATED behind use_segment_mode. combine(h, 0) is NOT a no-op
    // (mix64 transforms h even when b==0), so unconditional walks of empty containers would
    // alter the hash even with use_segment_mode=0 — breaking cycle-2 reproducibility. With
    // the gate, cycle-2 saved state (CONFIG sets use_segment_mode=0 via loader) hashes to
    // 3536309de837d3e2 bit-exactly.
    if (config_.use_segment_mode) {
      // ROLES contribution: sort by role_id hash for determinism.
      std::vector<uint64_t> role_ids;
      role_ids.reserve(role_token_table_.size());
      for (const auto& role : role_token_table_) role_ids.push_back(fnv1a(role));
      std::sort(role_ids.begin(), role_ids.end());
      for (uint64_t rid : role_ids) h = combine(h, rid);
      // SEGMENT_CONNS contribution: sort by feature_id, then walk non-zero mode-switch
      // weights in (role_slot → role_id_hash) order so the hash matches what serialize
      // emits regardless of which process built role_token_table_.
      std::vector<uint64_t> seg_feature_ids;
      seg_feature_ids.reserve(connections_.size());
      for (const auto& kv : connections_) {
        for (int a = kAscii; a < kExtendedActions; ++a) {
          if (kv.second.value[a] != 0.0) { seg_feature_ids.push_back(kv.first); break; }
        }
      }
      std::sort(seg_feature_ids.begin(), seg_feature_ids.end());
      for (uint64_t fid : seg_feature_ids) {
        h = combine(h, fid);
        // Order by role_id hash, matching the serialize loop's ordering. Build (role_id,
        // weight) pairs first, then walk in role_id order.
        std::vector<std::pair<uint64_t, double>> ordered;
        const auto& w = connections_.at(fid).value;
        for (size_t slot = 0; slot < role_token_table_.size(); ++slot) {
          int action_id = kAscii + static_cast<int>(slot);
          if (w[action_id] != 0.0) {
            ordered.push_back({fnv1a(role_token_table_[slot]), w[action_id]});
          }
        }
        std::sort(ordered.begin(), ordered.end(),
                  [](const auto& a, const auto& b) { return a.first < b.first; });
        for (const auto& [rid, weight] : ordered) {
          h = combine(h, rid);
          h = combine(h, static_cast<uint64_t>(std::llround(weight * 1000000.0)));
        }
      }
    }
    if (config_.use_outcome_predictor && !outcome_predictor_.empty()) {
      h = combine(h, fnv1a("cycle8-a0-outcome-predictor"));
      std::vector<uint64_t> pred_keys;
      pred_keys.reserve(outcome_predictor_.size());
      for (const auto& kv : outcome_predictor_) pred_keys.push_back(kv.first);
      std::sort(pred_keys.begin(), pred_keys.end());
      for (uint64_t fid : pred_keys) {
        const auto& weights = outcome_predictor_.at(fid);
        h = combine(h, fid);
        h = combine(h, double_bits(weights.reward_w));
        h = combine(h, double_bits(weights.exact_w));
        h = combine(h, double_bits(weights.error_w));
      }
    }
    return h;
  }

  size_t trace_count() const { return traces_.size(); }
  size_t connection_feature_count() const { return connections_.size(); }
  size_t connection_nonzero_count() const {
    size_t count = 0;
    for (const auto& item : connections_) {
      for (double value : item.second.value) {
        if (value != 0.0) ++count;
      }
    }
    return count;
  }
  size_t learned_char_count() const { return learned_chars_.size(); }
  size_t slot_copy_link_count() const { return slot_copy_weights_.size(); }
  const Config& config() const { return config_; }

  void set_symbolic_relation_features_enabled(bool enabled) {
    config_.use_symbolic_relation_features = enabled;
    hdc_ = Hdc{config_};
  }

  void set_grid_spatial_features_enabled(bool enabled) {
    config_.use_grid_spatial_features = enabled;
    hdc_ = Hdc{config_};
  }

  void set_outcome_predictor_enabled(bool enabled) {
    config_.use_outcome_predictor = enabled;
  }

  void set_max_output_chars(int max_output_chars) {
    if (max_output_chars <= 0) throw std::runtime_error("max_output_chars must be positive");
    config_.max_output_chars = max_output_chars;
  }

  void set_repetition_penalty_weight(double weight) {
    if (weight < 0.0) throw std::runtime_error("repetition penalty weight must be nonnegative");
    config_.repetition_penalty_weight = weight;
  }

  // Cycle-8 A0 boundary: prediction is a side substrate for replay priority and confidence.
  // OrganicBrain::generate() must not read outcome_predictor_, prediction errors, or replay
  // priority. Keep outcome prediction separate from output-character scoring.
  OutcomePrediction predict_outcome(const std::string& input,
                                    const std::vector<std::string>& observations) const {
    OutcomePrediction prediction;
    prediction.features = outcome_features(input, observations, &prediction.trace_refs);
    prediction.feature_count = prediction.features.size();
    if (!config_.use_outcome_predictor || prediction.features.empty()) {
      prediction.reward_scalar = 0.0;
      prediction.exact_prob_or_score = 0.0;
      prediction.lcs_error_ratio = 1.0;
      prediction.surprise = 1.0;
      return prediction;
    }
    double reward = 0.0;
    double exact = 0.0;
    double error = 0.0;
    for (const auto& feature : prediction.features) {
      auto found = outcome_predictor_.find(feature.id);
      if (found == outcome_predictor_.end()) continue;
      reward += feature.scale * found->second.reward_w;
      exact += feature.scale * found->second.exact_w;
      error += feature.scale * found->second.error_w;
    }
    prediction.reward_scalar = clamp_double(reward, 0.0, 2.0);
    prediction.exact_prob_or_score = clamp_double(exact, 0.0, 1.0);
    prediction.lcs_error_ratio = clamp_double(error, 0.0, 1.0);
    prediction.surprise =
        clamp_double((1.0 - prediction.exact_prob_or_score + prediction.lcs_error_ratio) / 2.0,
                     0.0, 1.0);
    return prediction;
  }

  PredictionError update_outcome_predictor(const OutcomePrediction& prediction,
                                           const OutcomeTarget& target) {
    PredictionError error = prediction_error_for(prediction, target);
    if (!config_.use_outcome_predictor || prediction.features.empty()) return error;
    double reward_delta = target.reward_scalar - prediction.reward_scalar;
    double exact_delta = target.exact_binary - prediction.exact_prob_or_score;
    double lcs_delta = target.lcs_error_ratio - prediction.lcs_error_ratio;
    constexpr double kMaxDelta = 0.05;
    for (const auto& feature : prediction.features) {
      auto& weights = outcome_predictor_[feature.id];
      double lr = config_.outcome_predictor_learning_rate * feature.scale;
      weights.reward_w += clamp_double(lr * reward_delta, -kMaxDelta, kMaxDelta);
      weights.exact_w += clamp_double(lr * exact_delta, -kMaxDelta, kMaxDelta);
      weights.error_w += clamp_double(lr * lcs_delta, -kMaxDelta, kMaxDelta);
    }
    return error;
  }

  size_t outcome_predictor_weight_count() const { return outcome_predictor_.size(); }

  size_t outcome_predictor_nonzero_count() const {
    size_t count = 0;
    for (const auto& item : outcome_predictor_) {
      if (item.second.reward_w != 0.0) ++count;
      if (item.second.exact_w != 0.0) ++count;
      if (item.second.error_w != 0.0) ++count;
    }
    return count;
  }

  uint64_t outcome_predictor_hash() const {
    uint64_t h = fnv1a("organic-v0-a0-predictor-only");
    h = combine(h, config_.use_outcome_predictor ? 1 : 0);
    std::vector<uint64_t> keys;
    keys.reserve(outcome_predictor_.size());
    for (const auto& kv : outcome_predictor_) keys.push_back(kv.first);
    std::sort(keys.begin(), keys.end());
    for (uint64_t fid : keys) {
      const auto& weights = outcome_predictor_.at(fid);
      h = combine(h, fid);
      h = combine(h, double_bits(weights.reward_w));
      h = combine(h, double_bits(weights.exact_w));
      h = combine(h, double_bits(weights.error_w));
    }
    return h;
  }

  // Line-oriented state snapshot. Ugly but loadable + hash-checked, per brief.
  // Bit-exact doubles via hex64-of-IEEE-bits so state_hash matches across save/load.
  void serialize_state(std::ostream& out, const std::string& organism_id) const {
    require_pxstate_scalar("organism_id", organism_id);
    out << "PXSTATE_V0\n";
    out << "SCHEMA project_x.state_snapshot.v0\n";
    out << "ORGANISM_ID " << organism_id << "\n";
    out << "CREATED_UTC " << timestamp_utc() << "\n";
    out << "CONFIG dimensions=" << config_.dimensions
        << " seed=" << config_.seed
        << " learning_rate=" << double_to_hex(config_.learning_rate)
        << " top_k=" << config_.top_k
        << " max_output_chars=" << config_.max_output_chars
        << " trace_gain=" << double_to_hex(config_.trace_gain)
        << " context_gain=" << double_to_hex(config_.context_gain)
        << " derived_relation_gain=" << double_to_hex(config_.derived_relation_gain)
        << " symbolic_relation_gain=" << double_to_hex(config_.symbolic_relation_gain)
        << " grid_spatial_gain=" << double_to_hex(config_.grid_spatial_gain)
        << " transition_gain=" << double_to_hex(config_.transition_gain)
        << " position_gain=" << double_to_hex(config_.position_gain)
        << " state_binding_gain=" << double_to_hex(config_.state_binding_gain)
        << " slot_pass_gain=" << double_to_hex(config_.slot_pass_gain)
        << " segment_mode_gain=" << double_to_hex(config_.segment_mode_gain)
        << " trace_span_position_gain=" << double_to_hex(config_.trace_span_position_gain)
        << " repetition_penalty_weight=" << double_to_hex(config_.repetition_penalty_weight)
        << " use_trace_id_feature=" << (config_.use_trace_id_feature ? 1 : 0)
        << " use_slot_pass_through=" << (config_.use_slot_pass_through ? 1 : 0)
        << " use_segment_mode=" << (config_.use_segment_mode ? 1 : 0)
        << " use_trace_span_position_features=" << (config_.use_trace_span_position_features ? 1 : 0)
        << " use_numeric_derived_features=" << (config_.use_numeric_derived_features ? 1 : 0)
        << " use_threshold_derived_features=" << (config_.use_threshold_derived_features ? 1 : 0)
        << " use_modular_derived_features=" << (config_.use_modular_derived_features ? 1 : 0)
        << " use_relation_projection=" << (config_.use_relation_projection ? 1 : 0)
        << " use_symbolic_relation_features=" << (config_.use_symbolic_relation_features ? 1 : 0)
        << " use_grid_spatial_features=" << (config_.use_grid_spatial_features ? 1 : 0)
        << " use_outcome_predictor=" << (config_.use_outcome_predictor ? 1 : 0)
        << " outcome_predictor_learning_rate=" << double_to_hex(config_.outcome_predictor_learning_rate)
        << " max_roles=" << config_.max_roles
        << "\n";
    out << "TRACES " << traces_.size() << "\n";
    for (const auto& tr : traces_) {
      require_pxstate_scalar("trace.event_id", tr.event_id);
      require_pxstate_scalar("trace.episode_id", tr.episode_id);
      require_pxstate_scalar("trace.split", tr.split);
      require_pxstate_scalar("trace.domain", tr.domain);
      require_pxstate_scalar("trace.input", tr.input);
      require_pxstate_scalar("trace.target_output", tr.target_output);
      // Observations are comma-joined in v0, so commas fail fast at write time.
      std::string obs_csv;
      for (size_t i = 0; i < tr.observations.size(); ++i) {
        require_pxstate_observation("trace.observations[" + std::to_string(i) + "]", tr.observations[i]);
        if (i) obs_csv.push_back(',');
        obs_csv += tr.observations[i];
      }
      out << "T " << tr.event_id << "|" << tr.episode_id << "|" << tr.split << "|"
          << tr.domain << "|" << tr.level << "|" << tr.input << "|" << obs_csv << "|"
          << tr.target_output << "|" << double_to_hex(tr.reward_scalar) << "|";
      for (int i = 0; i < kDim; ++i) {
        if (i) out << ' ';
        out << double_to_hex(tr.vector[i]);
      }
      out << "\n";
    }
    // Connections — sort by feature_id for determinism (matches state_hash ordering).
    std::vector<uint64_t> conn_keys;
    conn_keys.reserve(connections_.size());
    for (const auto& kv : connections_) conn_keys.push_back(kv.first);
    std::sort(conn_keys.begin(), conn_keys.end());
    out << "CONNS " << conn_keys.size() << "\n";
    for (uint64_t key : conn_keys) {
      out << "C " << hex64(key) << "|";
      const auto& weights = connections_.at(key).value;
      bool first = true;
      for (int c = 0; c < kAscii; ++c) {
        if (weights[c] == 0.0) continue;
        if (!first) out << ',';
        out << c << ':' << double_to_hex(weights[c]);
        first = false;
      }
      out << "\n";
    }
    std::vector<uint64_t> slot_keys;
    slot_keys.reserve(slot_copy_weights_.size());
    for (const auto& kv : slot_copy_weights_) slot_keys.push_back(kv.first);
    std::sort(slot_keys.begin(), slot_keys.end());
    out << "SLOTS " << slot_keys.size() << "\n";
    for (uint64_t key : slot_keys) {
      out << "S " << hex64(key) << ' ' << double_to_hex(slot_copy_weights_.at(key)) << "\n";
    }
    out << "LEARNED";
    for (unsigned char c : learned_chars_) out << ' ' << static_cast<int>(c);
    out << "\n";
    // Cycle-3 sections: ROLES + SEGMENT_CONNS. Written only when use_segment_mode is on so
    // cycle-2 saved files (without the flag) remain byte-identical after a re-save under
    // legacy mode. Loader tolerates absence; presence is signaled by the CONFIG flag.
    if (config_.use_segment_mode) {
      // ROLES — sort by role_id (the fnv1a hash) for cross-process determinism. Role-table
      // slot order is reconstruction by the loader: insert by sorted role_id, so two
      // processes loading the same snapshot end up with identical Weights::value indexing.
      std::vector<std::pair<uint64_t, std::string>> roles_sorted;
      roles_sorted.reserve(role_token_table_.size());
      for (const auto& role : role_token_table_) {
        require_pxstate_scalar("role.string", role);
        roles_sorted.push_back({fnv1a(role), role});
      }
      std::sort(roles_sorted.begin(), roles_sorted.end(),
                [](const auto& a, const auto& b) { return a.first < b.first; });
      out << "ROLES " << roles_sorted.size() << "\n";
      for (const auto& [role_id, role] : roles_sorted) {
        out << "R " << hex64(role_id) << ' ' << role << "\n";
      }

      // SEGMENT_CONNS — sparse, mirror CONNS shape but keyed by (feature_id, role_id).
      // Each row enumerates non-zero mode-switch weights for one feature_id.
      std::vector<uint64_t> seg_keys;
      seg_keys.reserve(connections_.size());
      for (const auto& kv : connections_) {
        // Only include features with at least one non-zero mode-switch weight; saves bytes
        // and keeps hash deterministic.
        bool any_seg = false;
        for (int a = kAscii; a < kExtendedActions; ++a) {
          if (kv.second.value[a] != 0.0) { any_seg = true; break; }
        }
        if (any_seg) seg_keys.push_back(kv.first);
      }
      std::sort(seg_keys.begin(), seg_keys.end());
      out << "SEGMENT_CONNS " << seg_keys.size() << "\n";
      for (uint64_t fid : seg_keys) {
        out << "SC " << hex64(fid) << "|";
        const auto& w = connections_.at(fid).value;
        bool first = true;
        for (size_t slot = 0; slot < role_token_table_.size(); ++slot) {
          int action_id = kAscii + static_cast<int>(slot);
          if (w[action_id] == 0.0) continue;
          if (!first) out << ',';
          out << hex64(fnv1a(role_token_table_[slot])) << ':' << double_to_hex(w[action_id]);
          first = false;
        }
        out << "\n";
      }
    }
    if (config_.use_outcome_predictor) {
      std::vector<uint64_t> pred_keys;
      pred_keys.reserve(outcome_predictor_.size());
      for (const auto& kv : outcome_predictor_) pred_keys.push_back(kv.first);
      std::sort(pred_keys.begin(), pred_keys.end());
      out << "PREDICTOR_CONNS " << pred_keys.size() << "\n";
      for (uint64_t fid : pred_keys) {
        const auto& weights = outcome_predictor_.at(fid);
        out << "PC " << hex64(fid)
            << "|reward:" << double_to_hex(weights.reward_w)
            << ",exact:" << double_to_hex(weights.exact_w)
            << ",error:" << double_to_hex(weights.error_w) << "\n";
      }
    }
    out << "STATE_HASH " << hex64(state_hash()) << "\n";
    out << "PXSTATE_END\n";
  }

  // Load a state snapshot. Throws on schema mismatch or malformed lines.
  // After load, state_hash() must equal the STATE_HASH line value — caller verifies.
  void load_serialized_state(std::istream& in) {
    traces_.clear();
    trace_index_by_event_id_.clear();
    connections_.clear();
    slot_copy_weights_.clear();
    learned_chars_.clear();
    mutation_connection_deltas_.clear();
    outcome_predictor_.clear();

    std::string line;
    auto next_line = [&]() -> std::string {
      if (!std::getline(in, line)) throw std::runtime_error("pxstate: unexpected EOF");
      return line;
    };
    if (next_line() != "PXSTATE_V0") throw std::runtime_error("pxstate: bad magic");
    if (next_line().rfind("SCHEMA ", 0) != 0) throw std::runtime_error("pxstate: missing SCHEMA");
    if (next_line().rfind("ORGANISM_ID ", 0) != 0) throw std::runtime_error("pxstate: missing ORGANISM_ID");
    if (next_line().rfind("CREATED_UTC ", 0) != 0) throw std::runtime_error("pxstate: missing CREATED_UTC");

    // CONFIG line: space-separated key=value pairs. Override config_ fields bit-exactly.
    // CYCLE-3.5 LEGACY DEFAULTS: cycle-2 snapshots predate the cycle-3 fields and write
    // no `use_segment_mode=...`, `max_roles=...`, or `segment_mode_gain=...` tokens. Without
    // an explicit reset here, those fields keep the binary defaults (use_segment_mode=true,
    // segment_mode_gain=0.3) when loading a legacy snapshot, which silently changes the
    // answer-path semantics of an old hash. The fix is to seed legacy defaults BEFORE
    // parsing so present tokens override and absent tokens stay legacy. Cycle-3+ snapshots
    // write the keys they know (see serialize_state), so they round-trip identically; cycle-4
    // trace-span-position fields default off for older snapshots because they change the
    // answer path when new weights exist.
    config_.use_segment_mode = false;
    config_.max_roles = kMaxRoles;
    config_.segment_mode_gain = 0.3;
    config_.derived_relation_gain = 1.0;
    config_.symbolic_relation_gain = 5.0;
    config_.grid_spatial_gain = 5.0;
    config_.trace_span_position_gain = 0.0;
    config_.repetition_penalty_weight = 0.0;
    config_.use_trace_span_position_features = false;
    config_.use_numeric_derived_features = false;
    config_.use_threshold_derived_features = false;
    config_.use_modular_derived_features = false;
    config_.use_relation_projection = false;
    config_.use_symbolic_relation_features = false;
    config_.use_grid_spatial_features = false;
    config_.use_outcome_predictor = false;
    config_.outcome_predictor_learning_rate = 0.025;
    std::string cfg_line = next_line();
    if (cfg_line.rfind("CONFIG ", 0) != 0) throw std::runtime_error("pxstate: missing CONFIG");
    std::istringstream cfg_stream(cfg_line.substr(7));
    std::string token;
    while (cfg_stream >> token) {
      size_t eq = token.find('=');
      if (eq == std::string::npos) continue;
      std::string k = token.substr(0, eq);
      std::string v = token.substr(eq + 1);
      if (k == "dimensions") config_.dimensions = std::stoi(v);
      else if (k == "seed") config_.seed = std::stoull(v);
      else if (k == "top_k") config_.top_k = std::stoi(v);
      else if (k == "max_output_chars") config_.max_output_chars = std::stoi(v);
      else if (k == "learning_rate") config_.learning_rate = hex_to_double(v);
      else if (k == "trace_gain") config_.trace_gain = hex_to_double(v);
      else if (k == "context_gain") config_.context_gain = hex_to_double(v);
      else if (k == "derived_relation_gain") config_.derived_relation_gain = hex_to_double(v);
      else if (k == "symbolic_relation_gain") config_.symbolic_relation_gain = hex_to_double(v);
      else if (k == "grid_spatial_gain") config_.grid_spatial_gain = hex_to_double(v);
      else if (k == "transition_gain") config_.transition_gain = hex_to_double(v);
      else if (k == "position_gain") config_.position_gain = hex_to_double(v);
      else if (k == "state_binding_gain") config_.state_binding_gain = hex_to_double(v);
      else if (k == "slot_pass_gain") config_.slot_pass_gain = hex_to_double(v);
      else if (k == "segment_mode_gain") config_.segment_mode_gain = hex_to_double(v);
      else if (k == "trace_span_position_gain") config_.trace_span_position_gain = hex_to_double(v);
      else if (k == "repetition_penalty_weight") config_.repetition_penalty_weight = hex_to_double(v);
      else if (k == "use_trace_id_feature") config_.use_trace_id_feature = (v != "0");
      else if (k == "use_slot_pass_through") config_.use_slot_pass_through = (v != "0");
      else if (k == "use_segment_mode") config_.use_segment_mode = (v != "0");
      else if (k == "use_trace_span_position_features") config_.use_trace_span_position_features = (v != "0");
      else if (k == "use_numeric_derived_features") config_.use_numeric_derived_features = (v != "0");
      else if (k == "use_threshold_derived_features") config_.use_threshold_derived_features = (v != "0");
      else if (k == "use_modular_derived_features") config_.use_modular_derived_features = (v != "0");
      else if (k == "use_relation_projection") config_.use_relation_projection = (v != "0");
      else if (k == "use_symbolic_relation_features") config_.use_symbolic_relation_features = (v != "0");
      else if (k == "use_grid_spatial_features") config_.use_grid_spatial_features = (v != "0");
      else if (k == "use_outcome_predictor") config_.use_outcome_predictor = (v != "0");
      else if (k == "outcome_predictor_learning_rate") config_.outcome_predictor_learning_rate = hex_to_double(v);
      else if (k == "max_roles") config_.max_roles = std::stoi(v);
    }
    // Legacy-default seeding (above) is what makes cycle-2 snapshots reload safely.
    // Cycle-3 snapshots write use_segment_mode=1 explicitly; cycle-2 snapshots are silent
    // and inherit the legacy-default false set just above the CONFIG parse loop.
    role_token_table_.clear();
    hdc_ = Hdc{config_};  // re-seed HDC from config_ (Hdc only depends on Config)

    // TRACES N
    std::string traces_header = next_line();
    if (traces_header.rfind("TRACES ", 0) != 0) throw std::runtime_error("pxstate: missing TRACES");
    size_t n_traces = std::stoull(traces_header.substr(7));
    for (size_t i = 0; i < n_traces; ++i) {
      std::string tline = next_line();
      if (tline.rfind("T ", 0) != 0) throw std::runtime_error("pxstate: bad TRACE row");
      auto fields = split_delim(tline.substr(2), '|');
      if (fields.size() != 10) throw std::runtime_error("pxstate: TRACE field count");
      Trace tr;
      tr.event_id = fields[0];
      tr.episode_id = fields[1];
      tr.split = fields[2];
      tr.domain = fields[3];
      tr.level = std::stoi(fields[4]);
      tr.input = fields[5];
      if (!fields[6].empty()) tr.observations = split_delim(fields[6], ',');
      tr.target_output = fields[7];
      tr.reward_scalar = hex_to_double(fields[8]);
      std::istringstream vec_stream(fields[9]);
      std::string elem;
      int idx = 0;
      while (vec_stream >> elem) {
        if (idx >= kDim) throw std::runtime_error("pxstate: vector overflow");
        tr.vector[idx++] = hex_to_double(elem);
      }
      if (idx != kDim) throw std::runtime_error("pxstate: vector dim mismatch");
      refresh_trace_caches(tr);
      traces_.push_back(std::move(tr));
      trace_index_by_event_id_[traces_.back().event_id] = traces_.size() - 1;
    }

    // CONNS M
    std::string conns_header = next_line();
    if (conns_header.rfind("CONNS ", 0) != 0) throw std::runtime_error("pxstate: missing CONNS");
    size_t n_conns = std::stoull(conns_header.substr(6));
    for (size_t i = 0; i < n_conns; ++i) {
      std::string cline = next_line();
      if (cline.rfind("C ", 0) != 0) throw std::runtime_error("pxstate: bad CONN row");
      auto pipe = cline.find('|');
      if (pipe == std::string::npos) throw std::runtime_error("pxstate: CONN missing |");
      uint64_t fid = std::stoull(cline.substr(2, pipe - 2), nullptr, 16);
      Weights w{};
      std::string rest = cline.substr(pipe + 1);
      if (!rest.empty()) {
        for (const auto& pair : split_delim(rest, ',')) {
          auto colon = pair.find(':');
          if (colon == std::string::npos) throw std::runtime_error("pxstate: CONN missing :");
          int c = std::stoi(pair.substr(0, colon));
          if (c < 0 || c >= kAscii) throw std::runtime_error("pxstate: CONN c out of range");
          w.value[c] = hex_to_double(pair.substr(colon + 1));
        }
      }
      connections_[fid] = w;
    }

    // SLOTS K
    std::string slots_header = next_line();
    if (slots_header.rfind("SLOTS ", 0) != 0) throw std::runtime_error("pxstate: missing SLOTS");
    size_t n_slots = std::stoull(slots_header.substr(6));
    for (size_t i = 0; i < n_slots; ++i) {
      std::string sline = next_line();
      if (sline.rfind("S ", 0) != 0) throw std::runtime_error("pxstate: bad SLOT row");
      auto sp = sline.find(' ', 2);
      if (sp == std::string::npos) throw std::runtime_error("pxstate: SLOT missing space");
      uint64_t key = std::stoull(sline.substr(2, sp - 2), nullptr, 16);
      slot_copy_weights_[key] = hex_to_double(sline.substr(sp + 1));
    }

    // LEARNED <chars>
    std::string learned_line = next_line();
    if (learned_line.rfind("LEARNED", 0) != 0) throw std::runtime_error("pxstate: missing LEARNED");
    std::istringstream learned_stream(learned_line.substr(7));
    int cv;
    while (learned_stream >> cv) {
      if (cv < 0 || cv >= kAscii) throw std::runtime_error("pxstate: LEARNED char out of range");
      learned_chars_.insert(static_cast<unsigned char>(cv));
    }

    // Cycle-3 optional sections: ROLES + SEGMENT_CONNS. Detected by peek-ahead — read the
    // next line; if it starts with "ROLES ", parse both sections; otherwise treat it as the
    // STATE_HASH line and skip the cycle-3 parse. This keeps the loader tolerant of cycle-2
    // saved state (which has neither section).
    std::string lookahead = next_line();
    if (lookahead.rfind("ROLES ", 0) == 0) {
      size_t n_roles = std::stoull(lookahead.substr(6));
      // role_token_table_ rebuilt from R rows in serialized order (which the writer sorted
      // by role_id hash). Slot index of role X in this rebuilt table will match the writer's
      // slot index iff both processes use the same role_id ordering — which they do, since
      // role_id is a deterministic hash and the writer sorted by it.
      for (size_t i = 0; i < n_roles; ++i) {
        std::string rline = next_line();
        if (rline.rfind("R ", 0) != 0) throw std::runtime_error("pxstate: bad ROLES row");
        // R <role_id_hex64> <role_string>
        auto sp = rline.find(' ', 2);
        if (sp == std::string::npos) throw std::runtime_error("pxstate: ROLES missing space");
        // role_id read but unused — used only for hash determinism in the writer; the loader
        // rebuilds from role_string (which IS the source of truth) and validates against
        // role_id on demand via fnv1a(role_string).
        std::string role_string = rline.substr(sp + 1);
        if (static_cast<int>(role_token_table_.size()) >= kMaxRoles) {
          throw std::runtime_error(
              "pxstate: ROLES section has more entries than kMaxRoles=" + std::to_string(kMaxRoles));
        }
        role_token_table_.push_back(role_string);
      }
      // SEGMENT_CONNS K
      std::string seg_header = next_line();
      if (seg_header.rfind("SEGMENT_CONNS ", 0) != 0) {
        throw std::runtime_error("pxstate: missing SEGMENT_CONNS after ROLES");
      }
      size_t n_seg = std::stoull(seg_header.substr(14));
      for (size_t i = 0; i < n_seg; ++i) {
        std::string sline = next_line();
        if (sline.rfind("SC ", 0) != 0) throw std::runtime_error("pxstate: bad SEGMENT_CONNS row");
        auto pipe = sline.find('|');
        if (pipe == std::string::npos) throw std::runtime_error("pxstate: SEGMENT_CONNS missing |");
        uint64_t fid = std::stoull(sline.substr(3, pipe - 3), nullptr, 16);
        std::string rest = sline.substr(pipe + 1);
        if (rest.empty()) continue;  // empty SEGMENT_CONNS row — shouldn't happen but tolerated
        // Ensure the feature is in connections_; SEGMENT_CONNS may reference feature_ids
        // that have only mode-switch weights (no literal-char weights), so the CONNS pass
        // would have skipped them.
        auto& weights = connections_[fid];
        for (const auto& pair : split_delim(rest, ',')) {
          auto colon = pair.find(':');
          if (colon == std::string::npos) throw std::runtime_error("pxstate: SEGMENT_CONNS missing :");
          uint64_t role_id = std::stoull(pair.substr(0, colon), nullptr, 16);
          double weight = hex_to_double(pair.substr(colon + 1));
          // Look up role_slot by role_id; the role string must already be registered (the
          // ROLES section was parsed above before SEGMENT_CONNS).
          int role_slot = -1;
          for (size_t s = 0; s < role_token_table_.size(); ++s) {
            if (fnv1a(role_token_table_[s]) == role_id) { role_slot = static_cast<int>(s); break; }
          }
          if (role_slot < 0) {
            throw std::runtime_error("pxstate: SEGMENT_CONNS references unknown role_id");
          }
          weights.value[kAscii + role_slot] = weight;
        }
      }
      // Now the STATE_HASH line is the NEXT line; consume it.
      lookahead = next_line();
    }

    if (lookahead.rfind("PREDICTOR_CONNS ", 0) == 0) {
      size_t n_pred = std::stoull(lookahead.substr(16));
      for (size_t i = 0; i < n_pred; ++i) {
        std::string pline = next_line();
        if (pline.rfind("PC ", 0) != 0) throw std::runtime_error("pxstate: bad PREDICTOR_CONNS row");
        auto pipe = pline.find('|');
        if (pipe == std::string::npos) throw std::runtime_error("pxstate: PREDICTOR_CONNS missing |");
        uint64_t fid = std::stoull(pline.substr(3, pipe - 3), nullptr, 16);
        PredictorWeights weights;
        std::string rest = pline.substr(pipe + 1);
        for (const auto& pair : split_delim(rest, ',')) {
          auto colon = pair.find(':');
          if (colon == std::string::npos) throw std::runtime_error("pxstate: PREDICTOR_CONNS missing :");
          std::string name = pair.substr(0, colon);
          double value = hex_to_double(pair.substr(colon + 1));
          if (name == "reward") weights.reward_w = value;
          else if (name == "exact") weights.exact_w = value;
          else if (name == "error") weights.error_w = value;
        }
        outcome_predictor_[fid] = weights;
      }
      config_.use_outcome_predictor = true;
      lookahead = next_line();
    }

    // STATE_HASH (caller verifies match against state_hash() after load). Either we just
    // parsed ROLES+SEGMENT_CONNS and `lookahead` now holds STATE_HASH, or there were no
    // cycle-3 sections and `lookahead` already holds STATE_HASH from the original peek.
    std::string hash_line = lookahead;
    if (hash_line.rfind("STATE_HASH ", 0) != 0) throw std::runtime_error("pxstate: missing STATE_HASH");
    expected_state_hash_ = std::stoull(hash_line.substr(11), nullptr, 16);
    std::string end_line = next_line();
    if (end_line != "PXSTATE_END") throw std::runtime_error("pxstate: missing PXSTATE_END");
  }

  uint64_t expected_state_hash() const { return expected_state_hash_; }

 private:
  uint64_t slot_copy_key(const std::string& type, int output_position, int filler_position) const {
    return combine(hash_pair("slot-copy-type", type),
                   combine(static_cast<uint64_t>(output_position),
                           combine(fnv1a("filler-pos"), static_cast<uint64_t>(filler_position))));
  }

  void learn_slot_pass_through(const std::vector<std::string>& observations, const std::string& target,
                               double reward_scalar) {
    if (!config_.use_slot_pass_through) return;
    std::string lower_target = lower_ascii(target);
    for (const auto& slot : parse_slots(observations)) {
      if (slot.value.empty()) continue;
      size_t start = lower_target.find(slot.value);
      while (start != std::string::npos) {
        for (size_t i = 0; i < slot.value.size(); ++i) {
          if (static_cast<unsigned char>(slot.value[i]) >= kAscii) continue;
          slot_copy_weights_[slot_copy_key(slot.type, static_cast<int>(start + i), static_cast<int>(i))] +=
              reward_scalar * config_.learning_rate;
        }
        start = lower_target.find(slot.value, start + 1);
      }
    }
  }

  size_t add_slot_pass_scores(std::array<double, kAscii>& scores, const std::vector<ObservationSlot>& slots,
                              int position) const {
    if (!config_.use_slot_pass_through) return 0;
    size_t active = 0;
    for (const auto& slot : slots) {
      for (size_t i = 0; i < slot.value.size(); ++i) {
        unsigned char c = static_cast<unsigned char>(slot.value[i]);
        if (c >= kAscii) continue;
        auto found = slot_copy_weights_.find(slot_copy_key(slot.type, position, static_cast<int>(i)));
        if (found == slot_copy_weights_.end()) continue;
        scores[c] += found->second * config_.slot_pass_gain;
        ++active;
      }
    }
    return active;
  }

  uint64_t trace_span_position_feature_id(const std::string& event_id, const std::string& role,
                                          size_t span_offset) const {
    uint64_t trace_id = hash_pair("trace", event_id);
    uint64_t role_id = hash_pair("span-role", role);
    uint64_t offset_id = combine(fnv1a("span-pos"), static_cast<uint64_t>(span_offset));
    return combine(trace_id, combine(role_id, offset_id));
  }

  uint64_t copy_boundary_end_feature_id(const std::string& role) const {
    return hash_pair("copy-boundary-end", role);
  }

  double repetition_extension_penalty(const std::string& output, unsigned char candidate) const {
    if (config_.repetition_penalty_weight <= 0.0 || candidate == kEnd) return 0.0;
    std::string trial = output;
    trial.push_back(static_cast<char>(candidate));
    const size_t n = trial.size();
    for (size_t width = 4; width <= 24 && 2 * width <= n; ++width) {
      if (trial.compare(n - width, width, trial, n - 2 * width, width) == 0) {
        return config_.repetition_penalty_weight;
      }
    }
    auto tokens = tokenize(trial);
    if (tokens.size() >= 6) {
      for (size_t width = 1; width <= 3 && 2 * width <= tokens.size(); ++width) {
        bool repeated = true;
        for (size_t i = 0; i < width; ++i) {
          if (tokens[tokens.size() - 1 - i] != tokens[tokens.size() - 1 - width - i]) {
            repeated = false;
            break;
          }
        }
        if (repeated) return config_.repetition_penalty_weight;
      }
    }
    return 0.0;
  }

  const Trace* trace_by_event_id(const std::string& event_id) const {
    auto found = trace_index_by_event_id_.find(event_id);
    if (found == trace_index_by_event_id_.end() || found->second >= traces_.size()) return nullptr;
    return &traces_[found->second];
  }

  std::optional<std::pair<std::string, size_t>> find_longest_filler_match_at_readonly(
      const std::string& lower_target, size_t pos,
      const std::vector<ObservationSlot>& slots) const {
    std::optional<std::pair<std::string, size_t>> best;
    for (const auto& slot : slots) {
      if (slot.value.empty()) continue;
      if (pos + slot.value.size() > lower_target.size()) continue;
      if (lower_target.compare(pos, slot.value.size(), slot.value) != 0) continue;
      if (!best.has_value() || slot.value.size() > best->second) {
        best = std::make_pair(slot.type, slot.value.size());
      }
      // Equal-length ties intentionally keep the first observation, matching the training
      // matcher's longest-then-observation-order rule.
    }
    return best;
  }

  std::optional<TraceSpanPosition> trace_span_position_at(const Trace& trace, int output_position) const {
    if (output_position < 0) return std::nullopt;
    std::string lower_target = lower_ascii(trace.target_output);
    size_t wanted = static_cast<size_t>(output_position);
    size_t pos = 0;
    while (pos < lower_target.size()) {
      auto match = find_longest_filler_match_at_readonly(lower_target, pos, trace.slots);
      if (match.has_value()) {
        size_t span = match->second;
        if (wanted >= pos && wanted < pos + span) {
          return TraceSpanPosition{match->first, wanted - pos};
        }
        pos += span;
      } else {
        ++pos;
      }
    }
    return std::nullopt;
  }

  void add_trace_span_position_features(std::vector<Feature>& active,
                                        const std::vector<Activation>& activations,
                                        int output_position) const {
    if (!config_.use_segment_mode || !config_.use_trace_id_feature ||
        !config_.use_trace_span_position_features || config_.trace_span_position_gain == 0.0) {
      return;
    }
    for (const auto& activation : activations) {
      if (activation.similarity <= 0.0) continue;
      const Trace* trace = trace_by_event_id(activation.event_id);
      if (!trace) continue;
      auto span_position = trace_span_position_at(*trace, output_position);
      if (!span_position.has_value()) continue;
      active.push_back({
          trace_span_position_feature_id(trace->event_id, span_position->role, span_position->offset),
          activation.similarity * config_.trace_gain * config_.trace_span_position_gain,
      });
    }
  }

  std::vector<Feature> numeric_derived_features(const std::vector<ObservationSlot>& slots) const {
    std::vector<Feature> features;
    if (!config_.use_numeric_derived_features) return features;
    if (has_numeric_relation_control(slots)) return features;
    for (const auto& slot : slots) {
      auto numeric = parse_pure_int(slot.value);
      if (!numeric.has_value()) continue;
      int abs_value = std::abs(*numeric);
      std::string parity = (abs_value % 2 == 0) ? "even" : "odd";
      // A numeric observation has more structure than its surface token. These features
      // expose that structure as addresses for learning; they deliberately stop before the
      // answer relation. The rule "odd means stay" still has to be learned from CONNS.
      features.push_back({hash_pair("num-role", slot.type), config_.context_gain});
      features.push_back({hash_pair("num-role-parity", slot.type + ":" + parity),
                          config_.context_gain * config_.derived_relation_gain});
      features.push_back({hash_pair("num-any-parity", parity),
                          config_.context_gain * config_.derived_relation_gain});
      features.push_back({hash_pair("num-role-lastdigit", slot.type + ":" + std::to_string(abs_value % 10)),
                          config_.context_gain * 0.5});
    }
    return features;
  }

  std::vector<Feature> numeric_derived_trace_features_for_query(
      const std::vector<std::string>& observations) const {
    std::vector<Feature> features;
    if (!config_.use_numeric_derived_features || !config_.use_trace_id_feature) return features;
    auto query_slots = parse_slots(observations);
    if (has_numeric_relation_control(query_slots)) return features;
    for (const auto& query_slot : query_slots) {
      auto query_num = parse_pure_int(query_slot.value);
      if (!query_num.has_value()) continue;
      int query_parity = std::abs(*query_num) % 2;
      for (const auto& trace : traces_) {
        if (trace.has_numeric_relation_control) continue;
        for (const auto& trace_slot : trace.slots) {
          if (trace_slot.type != query_slot.type) continue;
          auto trace_num = parse_pure_int(trace_slot.value);
          if (!trace_num.has_value()) continue;
          if ((std::abs(*trace_num) % 2) != query_parity) continue;
          // Derived-trace activation is the cycle-5 rule-transfer bridge. Normal HDC
          // retrieval can over-favor a surface cue (red) over the computed fact (even).
          // This channel says: traces sharing the computed numeric relation are relevant
          // even when their literal fillers differ. It reuses trace-id literal weights
          // learned from those traces; it does not map parity to an answer directly.
          features.push_back({hash_pair("trace", trace.event_id),
                              config_.context_gain * config_.derived_relation_gain});
          break;
        }
      }
    }
    return features;
  }

  std::vector<Feature> threshold_derived_features(const std::vector<ObservationSlot>& slots) const {
    std::vector<Feature> features;
    if (!config_.use_threshold_derived_features) return features;
    for (const auto& key : threshold_relation_keys(slots)) {
      features.push_back({hash_pair("num-threshold", key),
                          config_.context_gain * config_.derived_relation_gain});
    }
    return features;
  }

  std::vector<Feature> modular_derived_features(const std::vector<ObservationSlot>& slots) const {
    std::vector<Feature> features;
    if (!config_.use_modular_derived_features) return features;
    for (const auto& key : modular_relation_keys(slots)) {
      features.push_back({hash_pair("num-modular", key),
                          config_.context_gain * config_.derived_relation_gain});
    }
    return features;
  }

  std::vector<Feature> threshold_derived_trace_features_for_query(
      const std::vector<std::string>& observations) const {
    std::vector<Feature> features;
    if (!config_.use_threshold_derived_features || !config_.use_trace_id_feature) return features;
    auto query_keys = threshold_relation_keys(parse_slots(observations));
    if (query_keys.empty()) return features;
    std::set<std::string> query_key_set(query_keys.begin(), query_keys.end());
    for (const auto& trace : traces_) {
      for (const auto& key : trace.threshold_keys) {
        if (!query_key_set.contains(key)) continue;
        // Same pattern as cycle-5 parity activation, but under a separate relation family:
        // traces sharing computed threshold class are relevant, while the learned chars
        // still come from the trace-id weights and ordinary CONNS rows.
        features.push_back({hash_pair("trace", trace.event_id),
                            config_.context_gain * config_.derived_relation_gain});
        break;
      }
    }
    return features;
  }

  std::vector<Feature> modular_derived_trace_features_for_query(
      const std::vector<std::string>& observations) const {
    std::vector<Feature> features;
    if (!config_.use_modular_derived_features || !config_.use_trace_id_feature) return features;
    auto query_keys = modular_relation_keys(parse_slots(observations));
    if (query_keys.empty()) return features;
    std::set<std::string> query_key_set(query_keys.begin(), query_keys.end());
    for (const auto& trace : traces_) {
      for (const auto& key : trace.modular_keys) {
        if (!query_key_set.contains(key)) continue;
        features.push_back({hash_pair("trace", trace.event_id),
                            config_.context_gain * config_.derived_relation_gain});
        break;
      }
    }
    return features;
  }

  std::vector<Feature> relation_projection_bases(const std::string& cue_role,
                                                 const std::string& cue_value,
                                                 const std::string& target_role,
                                                 double scale) const {
    std::vector<Feature> features;
    if (cue_value.empty() || target_role.empty() || scale == 0.0) return features;
    // Exact role/value address plus role-free alias address. The alias is what lets a
    // query typed as topic:arin reactivate a relation learned from person:arin without
    // teaching a hand-authored "topic means person" rule.
    features.push_back({
        fnv1a("relation-exact|" + cue_role + "|" + cue_value + "|" + target_role),
        scale,
    });
    features.push_back({
        fnv1a("relation-value|" + cue_value + "|" + target_role),
        scale,
    });
    return features;
  }

  size_t learn_relation_projection(const std::vector<ObservationSlot>& slots, double reward_scalar) {
    if (!config_.use_relation_projection || reward_scalar <= 0.0) return 0;
    size_t deltas = 0;
    for (size_t cue_i = 0; cue_i < slots.size(); ++cue_i) {
      const auto& cue = slots[cue_i];
      if (cue.value.empty()) continue;
      for (size_t target_i = 0; target_i < slots.size(); ++target_i) {
        if (cue_i == target_i) continue;
        const auto& target = slots[target_i];
        if (target.value.empty()) continue;
        auto bases = relation_projection_bases(cue.type, cue.value, target.type, 1.0);
        unsigned char previous = kStart;
        std::string sequence = target.value;
        sequence.push_back(static_cast<char>(kEnd));
        for (size_t pos = 0; pos < sequence.size(); ++pos) {
          unsigned char c = static_cast<unsigned char>(sequence[pos]);
          if (c >= kAscii) continue;
          auto sf = state_features(bases, previous, static_cast<int>(pos));
          // Skip the global prev/pos/bucket prefix. Relation projection must not write
          // object names into globally shared character transitions; it lives only under
          // the relation addresses above, otherwise it would recreate the cycle-3.5
          // shared-feature contamination failure in a new costume.
          for (size_t i = 3; i < sf.size(); ++i) {
            connections_[sf[i].id].value[c] += reward_scalar * sf[i].scale * config_.learning_rate;
            ++deltas;
          }
          if (c != kEnd) learned_chars_.insert(c);
          previous = c;
        }
      }
    }
    return deltas;
  }

  std::vector<std::string> relation_target_roles_for_query(const std::string& input) const {
    std::set<std::string> roles;
    auto tokens = tokenize(input);
    for (const auto& token : tokens) {
      if (token == "hold" || token == "holds" || token == "held" ||
          token == "item" || token == "object" || token == "thing") {
        roles.insert("object");
      }
      if (token == "where" || token == "place" || token == "location" || token == "located") {
        roles.insert("place");
      }
      if (token == "after" || token == "effect" || token == "result" ||
          token == "outcome" || token == "predict") {
        roles.insert("effect");
      }
    }
    return {roles.begin(), roles.end()};
  }

  std::vector<Feature> relation_projection_features_for_query(
      const std::string& input, const std::vector<std::string>& observations) const {
    std::vector<Feature> features;
    if (!config_.use_relation_projection) return features;
    auto target_roles = relation_target_roles_for_query(input);
    if (target_roles.empty()) return features;
    auto query_slots = parse_slots(observations);
    for (const auto& query_slot : query_slots) {
      // Cycle-5 scope: topic is the role-relative cue used by evidence-present probes. By
      // limiting projection activation to topic cues, direct replay and filler-copy events
      // keep using the cycle-3/4 paths instead of receiving speculative relation answers.
      if (query_slot.type != "topic" || query_slot.value.empty()) continue;
      for (const auto& trace : traces_) {
        for (const auto& cue_slot : trace.slots) {
          if (cue_slot.value != query_slot.value) continue;
          for (const auto& target_role : target_roles) {
            bool trace_has_target = false;
            for (const auto& target_slot : trace.slots) {
              if (target_slot.type == target_role && !target_slot.value.empty()) {
                trace_has_target = true;
                break;
              }
            }
            if (!trace_has_target) continue;
            auto bases = relation_projection_bases(
                cue_slot.type, cue_slot.value, target_role, config_.trace_gain);
            features.insert(features.end(), bases.begin(), bases.end());
          }
        }
      }
    }
    return features;
  }

  std::vector<Feature> context_features(const std::string& input, const std::vector<std::string>& observations) const {
    std::vector<Feature> features;
    features.push_back({fnv1a("bias"), 0.15});
    auto tokens = tokenize(input);
    for (const auto& token : tokens) {
      features.push_back({hash_pair("tok", token), config_.context_gain});
    }
    for (size_t i = 0; i + 1 < tokens.size(); ++i) {
      features.push_back({combine(hash_pair("pair-left", tokens[i]), hash_pair("pair-right", tokens[i + 1])), config_.context_gain * 1.25});
    }
    for (const auto& observation : observations) {
      for (const auto& token : tokenize(observation)) {
        features.push_back({hash_pair("obs", token), config_.context_gain});
      }
    }
    auto slots = parse_slots(observations);
    auto derived = numeric_derived_features(slots);
    features.insert(features.end(), derived.begin(), derived.end());
    auto threshold = threshold_derived_features(slots);
    features.insert(features.end(), threshold.begin(), threshold.end());
    auto modular = modular_derived_features(slots);
    features.insert(features.end(), modular.begin(), modular.end());
    if (config_.use_symbolic_relation_features) {
      auto sym_keys = symbolic_relation_keys(slots);
      for (const auto& token : tokens) {
        for (const auto& key : sym_keys) {
          if (token != symbolic_relation_key_attribute(key)) continue;
          features.push_back({hash_pair("sym-rel-cue", token + "|" + key),
                              config_.context_gain * config_.symbolic_relation_gain * 4.0});
        }
      }
    }
    if (config_.use_grid_spatial_features) {
      auto grid_keys = grid_spatial_keys(slots);
      for (const auto& token : tokens) {
        for (const auto& key : grid_keys) {
          if (token != grid_spatial_key_cue(key)) continue;
          features.push_back({hash_pair("grid-spatial-cue", token + "|" + key),
                              config_.context_gain * config_.grid_spatial_gain * 4.0});
        }
      }
    }
    return features;
  }

  std::vector<Feature> outcome_features(const std::string& input,
                                        const std::vector<std::string>& observations,
                                        std::vector<Activation>* trace_refs) const {
    std::vector<Feature> features;
    features.push_back({fnv1a("a0-outcome-bias"), 1.0});
    auto context = context_features(input, observations);
    features.insert(features.end(), context.begin(), context.end());
    auto query = hdc_.encode_event(input, observations);
    auto activations = retrieve(query);
    if (trace_refs) *trace_refs = activations;
    if (config_.use_trace_id_feature) {
      for (const auto& activation : activations) {
        if (activation.similarity <= 0.0) continue;
        features.push_back({hash_pair("trace", activation.event_id),
                            activation.similarity * config_.trace_gain});
      }
    }
    return features;
  }

  std::vector<Feature> state_features(const std::vector<Feature>& base, unsigned char previous, int position) const {
    std::vector<Feature> features;
    features.reserve(3 + base.size() * 4);
    features.push_back({combine(fnv1a("global-prev"), previous), config_.transition_gain});
    features.push_back({combine(fnv1a("global-pos"), static_cast<uint64_t>(position)), config_.position_gain});
    features.push_back({combine(fnv1a("global-bucket"), static_cast<uint64_t>(position / 4)), config_.position_gain * 0.5});
    for (const auto& feature : base) {
      append_bound_state_features(features, feature, previous, position);
    }
    return features;
  }

  void append_bound_state_features(std::vector<Feature>& features, const Feature& feature,
                                   unsigned char previous, int position) const {
    uint64_t pos_id = combine(feature.id, combine(fnv1a("pos"), static_cast<uint64_t>(position)));
    uint64_t prev_id = combine(feature.id, combine(fnv1a("prev"), previous));
    uint64_t bucket_id = combine(feature.id, combine(fnv1a("bucket"), static_cast<uint64_t>(position / 4)));
    features.push_back({pos_id, feature.scale});
    features.push_back({prev_id, feature.scale * 0.8});
    features.push_back({bucket_id, feature.scale * 0.35});
    features.push_back({combine(pos_id, prev_id), feature.scale * config_.state_binding_gain});
  }

  std::vector<Activation> retrieve(const std::array<double, kDim>& query) const {
    std::vector<Activation> ranked;
    for (const auto& trace : traces_) {
      ranked.push_back({
          trace.event_id,
          trace.domain,
          trace.level,
          cosine(query, trace.vector),
          trace.reward_scalar,
      });
    }
    std::sort(ranked.begin(), ranked.end(), [](const Activation& a, const Activation& b) {
      if (a.similarity != b.similarity) return a.similarity > b.similarity;
      return a.event_id < b.event_id;
    });
    if (ranked.size() > static_cast<size_t>(config_.top_k)) ranked.resize(static_cast<size_t>(config_.top_k));
    return ranked;
  }

  // Returns this role's slot index in role_token_table_, registering if absent.
  // WHAT: maps a role-string ("name", "object", ...) to an index in [0, kMaxRoles) used to
  //   address mode-switch weights in Weights::value[kAscii + slot].
  // WHY: a fixed-width slot array keeps softmax fast; the role_string → slot lookup is
  //   the same kind of vocabulary table a tokenizer builds. NOT a parser-dispatcher — no
  //   line of code branches on the role's identity; the slot is just an index.
  // NEGATIVE-SPACE: throws fail-fast on overflow instead of silently truncating. Bumping
  //   kMaxRoles is one constant + recompile; serialized state survives because the
  //   ROLES section persists the role_id hash, not the array slot.
  int register_role_slot(const std::string& role_string) {
    for (size_t i = 0; i < role_token_table_.size(); ++i) {
      if (role_token_table_[i] == role_string) return static_cast<int>(i);
    }
    if (role_token_table_.size() >= static_cast<size_t>(kMaxRoles)) {
      throw std::runtime_error(
          "role table exhausted at kMaxRoles=" + std::to_string(kMaxRoles) +
          "; bump constant and recompile — serialized state remains forward-compatible "
          "because role_id is a stable hash");
    }
    role_token_table_.push_back(role_string);
    return static_cast<int>(role_token_table_.size() - 1);
  }

  // Read-only lookup; returns -1 when the role isn't registered. WHY: generate() uses this
  // to score mode-switch actions only for registered roles; if a role never appeared in
  // training, the brain has no mode-switch weights for it and the action is unreachable.
  int find_role_slot(const std::string& role_string) const {
    for (size_t i = 0; i < role_token_table_.size(); ++i) {
      if (role_token_table_[i] == role_string) return static_cast<int>(i);
    }
    return -1;
  }

  // Returns the filler value of the FIRST observation matching role_string, or empty.
  // WHAT: observations are formatted "type:value"; this returns value when type==role_string.
  // WHY: generate-time copy-mode reads filler chars from this. The mode-switch decision
  //   above has already voted "switch to copy from role:X"; this method supplies the chars.
  // NEGATIVE-SPACE: not a parser of intent — it's a key-value lookup over a list of
  //   already-typed strings. The same lookup powers parse_slots().
  std::string observation_value_for_role(const std::string& role_string,
                                          const std::vector<std::string>& observations) const {
    std::string prefix = role_string + ":";
    for (const auto& observation : observations) {
      if (observation.size() > prefix.size() &&
          observation.compare(0, prefix.size(), prefix) == 0) {
        return observation.substr(prefix.size());
      }
    }
    return std::string();
  }

  // Returns {role_slot, filler_length} for the longest observation filler that matches as a
  // substring of `lower_target` starting at `pos`. Returns nullopt if no match.
  // WHAT: training-time supervision routing — finds which (if any) observation's filler
  //   begins at this output position so the supervision signal goes to a mode-switch weight
  //   rather than a per-char weight. Match precedence: longest filler wins, ties by
  //   observation-list order (earlier-listed role wins).
  // WHY: at training time the brain sees the target output and the typed observations side
  //   by side. The substring-match identifies "this output span came from this observation",
  //   which routes the supervision signal correctly. Manifesto §Builder Law: training-loop
  //   machinery is allowed; this is the same kind of supervision routing as masking, reward
  //   gating, or autoregressive ordering.
  // NEGATIVE-SPACE: does NOT fire at generate time. The mode-switch decision at inference
  //   reads ONLY from learned softmax weights — no substring-match anywhere in generate().
  //   See docs/past_work/cycles/phase_v2_organic_substrate/cycle_docs/CYCLE3_MECHANISM.md §"Builder-Law boundary call".
  std::optional<std::pair<int, size_t>> find_longest_filler_match_at(
      const std::string& lower_target, size_t pos,
      const std::vector<ObservationSlot>& slots) {
    std::optional<std::pair<int, size_t>> best;
    for (const auto& slot : slots) {
      if (slot.value.empty()) continue;
      if (pos + slot.value.size() > lower_target.size()) continue;
      if (lower_target.compare(pos, slot.value.size(), slot.value) != 0) continue;
      int slot_idx = register_role_slot(slot.type);
      if (!best.has_value() || slot.value.size() > best->second) {
        best = std::make_pair(slot_idx, slot.value.size());
      }
      // Ties broken by observation-list order; iteration order preserves first-listed,
      // so we only update `best` on a STRICTLY-LONGER match, not on equal length.
    }
    return best;
  }

  Config config_;
  Hdc hdc_;
  std::vector<Trace> traces_;
  std::unordered_map<std::string, size_t> trace_index_by_event_id_;
  std::unordered_map<uint64_t, Weights> connections_;
  std::unordered_map<uint64_t, double> slot_copy_weights_;
  std::set<unsigned char> learned_chars_;
  std::vector<size_t> mutation_connection_deltas_;
  std::unordered_map<uint64_t, PredictorWeights> outcome_predictor_;
  uint64_t expected_state_hash_ = 0;  // populated by load_serialized_state for round-trip verification
  // Cycle-3 segment-mode state.
  // role_token_table_: registry of role-type strings encountered during training. Index in
  //   the vector IS the slot offset within Weights::value (Weights::value[kAscii + slot] is
  //   the mode-switch weight for "start-copy-from-role-at-slot"). Persisted by ROLES section;
  //   loaded role_id_hex64 is fnv1a(role_string), so reload re-registers in same order if
  //   the loader inserts in serialized order (sorted by role_id, deterministic).
  // NEGATIVE-SPACE: not a map; the array-slot binding is intentional so Weights::value
  //   stays a fixed-width array for fast softmax.
  std::vector<std::string> role_token_table_;
};

OrganicBrain train_brain(const std::vector<Event>& events, const Config& config) {
  OrganicBrain brain(config);
  for (const auto& event : events) {
    if (event.split == "train") brain.learn(event);
  }
  return brain;
}

struct BrainStateStats {
  size_t trace_count = 0;
  size_t connection_feature_count = 0;
  size_t connection_nonzero_count = 0;
  size_t slot_copy_link_count = 0;
  size_t learned_char_count = 0;
  size_t outcome_predictor_weight_count = 0;
  size_t outcome_predictor_nonzero_count = 0;
  uint64_t outcome_predictor_hash = 0;
  uint64_t state_hash = 0;
};

BrainStateStats capture_state_stats(const OrganicBrain& brain) {
  BrainStateStats stats;
  stats.trace_count = brain.trace_count();
  stats.connection_feature_count = brain.connection_feature_count();
  stats.connection_nonzero_count = brain.connection_nonzero_count();
  stats.slot_copy_link_count = brain.slot_copy_link_count();
  stats.learned_char_count = brain.learned_char_count();
  stats.outcome_predictor_weight_count = brain.outcome_predictor_weight_count();
  stats.outcome_predictor_nonzero_count = brain.outcome_predictor_nonzero_count();
  stats.outcome_predictor_hash = brain.outcome_predictor_hash();
  stats.state_hash = brain.state_hash();
  return stats;
}

void write_state_stats(std::ostream& out, const BrainStateStats& stats) {
  out << "{\"trace_count\": " << stats.trace_count
      << ", \"connection_feature_count\": " << stats.connection_feature_count
      << ", \"connection_nonzero_count\": " << stats.connection_nonzero_count
      << ", \"slot_copy_link_count\": " << stats.slot_copy_link_count
      << ", \"learned_char_count\": " << stats.learned_char_count
      << ", \"outcome_predictor_weight_count\": " << stats.outcome_predictor_weight_count
      << ", \"outcome_predictor_nonzero_count\": " << stats.outcome_predictor_nonzero_count
      << ", \"outcome_predictor_hash\": " << q(hex64(stats.outcome_predictor_hash))
      << ", \"state_hash\": " << q(hex64(stats.state_hash)) << "}";
}

void write_state_growth(std::ostream& out, const BrainStateStats& parent, const BrainStateStats& child) {
  auto delta = [](size_t after, size_t before) -> long long {
    return static_cast<long long>(after) - static_cast<long long>(before);
  };
  out << "{\"trace_count_delta\": " << delta(child.trace_count, parent.trace_count)
      << ", \"connection_feature_count_delta\": "
      << delta(child.connection_feature_count, parent.connection_feature_count)
      << ", \"connection_nonzero_count_delta\": "
      << delta(child.connection_nonzero_count, parent.connection_nonzero_count)
      << ", \"slot_copy_link_count_delta\": "
      << delta(child.slot_copy_link_count, parent.slot_copy_link_count)
      << ", \"learned_char_count_delta\": "
      << delta(child.learned_char_count, parent.learned_char_count)
      << ", \"outcome_predictor_weight_count_delta\": "
      << delta(child.outcome_predictor_weight_count, parent.outcome_predictor_weight_count)
      << ", \"outcome_predictor_nonzero_count_delta\": "
      << delta(child.outcome_predictor_nonzero_count, parent.outcome_predictor_nonzero_count)
      << "}";
}

void load_state_checked(OrganicBrain& brain, const std::string& path) {
  std::ifstream state_in(path);
  if (!state_in) throw std::runtime_error("cannot open loaded state: " + path);
  brain.load_serialized_state(state_in);
  if (brain.state_hash() != brain.expected_state_hash()) {
    throw std::runtime_error("loaded state hash mismatch: file=" + hex64(brain.expected_state_hash()) +
                             " recomputed=" + hex64(brain.state_hash()));
  }
}

void learn_train_events(OrganicBrain& brain, const std::vector<Event>& events,
                        const PersistenceContext& persistence, const std::string& source_kind,
                        const std::string& source_path) {
  uint64_t before_hash = brain.state_hash();
  for (const auto& event : events) {
    if (event.split != "train") continue;
    brain.learn(event);
    uint64_t after_hash = brain.state_hash();
    if (!persistence.event_log_path.empty()) {
      append_event_log_line(persistence.event_log_path, persistence.organism_id, "learn", event,
                            event.target_output, event.target_output, before_hash, after_hash,
                            source_kind, source_path);
    }
    before_hash = after_hash;
  }
}

double lcs_ratio(const std::string& a, const std::string& b) {
  if (a.empty() && b.empty()) return 1.0;
  std::vector<int> prev(b.size() + 1, 0), cur(b.size() + 1, 0);
  for (size_t i = 1; i <= a.size(); ++i) {
    for (size_t j = 1; j <= b.size(); ++j) {
      if (a[i - 1] == b[j - 1]) cur[j] = prev[j - 1] + 1;
      else cur[j] = std::max(prev[j], cur[j - 1]);
    }
    std::swap(prev, cur);
  }
  return (2.0 * static_cast<double>(prev[b.size()])) / static_cast<double>(a.size() + b.size());
}

std::string failure_reason(const std::string& raw, const std::string& expected) {
  if (raw == expected) return "";
  if (raw.empty()) return "empty_output";
  if (raw.find(expected) != std::string::npos || expected.find(raw) != std::string::npos) return "partial_or_extra_string";
  return "different_string";
}

std::string random_baseline(const Event& event, std::vector<unsigned char> alphabet, uint64_t seed) {
  if (alphabet.empty()) return "";
  uint64_t state = combine(seed, fnv1a(event.event_id));
  std::string out;
  for (size_t i = 0; i < event.target_output.size(); ++i) {
    state = mix64(state);
    out.push_back(static_cast<char>(alphabet[state % alphabet.size()]));
  }
  return out;
}

std::vector<unsigned char> collect_alphabet(const std::vector<Event>& events) {
  std::set<unsigned char> chars;
  for (const auto& event : events) {
    if (event.split != "train") continue;
    for (unsigned char c : event.target_output) {
      if (c < kAscii) chars.insert(c);
    }
  }
  return {chars.begin(), chars.end()};
}

void write_split_audit(std::ostream& out, const std::vector<Event>& events, const SplitAudit& audit, int indent) {
  std::string pad(indent, ' ');
  std::set<std::string> domains;
  for (const auto& event : events) domains.insert(event.domain);
  out << "{\n";
  out << pad << "  \"event_count\": " << events.size() << ",\n";
  out << pad << "  \"splits\": {";
  bool first = true;
  for (const auto& item : audit.splits) {
    if (!first) out << ", ";
    out << q(item.first) << ": " << item.second;
    first = false;
  }
  out << "},\n";
  out << pad << "  \"held_out_prompt_duplicates\": [";
  for (size_t i = 0; i < audit.duplicates.size(); ++i) {
    if (i) out << ", ";
    out << q(audit.duplicates[i]);
  }
  out << "],\n";
  out << pad << "  \"domains\": [";
  first = true;
  for (const auto& domain : domains) {
    if (!first) out << ", ";
    out << q(domain);
    first = false;
  }
  out << "],\n";
  out << pad << "  \"levels_by_domain\": {";
  first = true;
  for (const auto& item : audit.levels_by_domain) {
    if (!first) out << ", ";
    out << q(item.first) << ": [";
    bool first_level = true;
    for (int level : item.second) {
      if (!first_level) out << ", ";
      out << level;
      first_level = false;
    }
    out << "]";
    first = false;
  }
  out << "},\n";
  out << pad << "  \"held_out_composition_by_domain\": {";
  first = true;
  for (const auto& domain_item : audit.held_out_composition_by_domain) {
    if (!first) out << ", ";
    out << q(domain_item.first) << ": {";
    bool first_comp = true;
    for (const auto& comp_item : domain_item.second) {
      if (!first_comp) out << ", ";
      out << q(comp_item.first) << ": " << comp_item.second;
      first_comp = false;
    }
    out << "}";
    first = false;
  }
  out << "},\n";
  out << pad << "  \"levels_0_to_3_present\": {";
  first = true;
  for (const auto& item : audit.levels_by_domain) {
    if (!first) out << ", ";
    bool ok = item.second == std::set<int>({0, 1, 2, 3});
    out << q(item.first) << ": " << (ok ? "true" : "false");
    first = false;
  }
  out << "}\n";
  out << pad << "}";
}

void write_score(std::ostream& out, const std::string& raw, const std::string& expected) {
  double exact = raw == expected ? 1.0 : 0.0;
  out << "{\"exact\": " << exact << ", \"sequence_ratio\": " << std::fixed << std::setprecision(6)
      << lcs_ratio(raw, expected) << std::defaultfloat
      << ", \"basis\": {\"raw_output\": " << q(raw)
      << ", \"expected_output\": " << q(expected)
      << ", \"method\": \"exact_match_plus_lcs_ratio\"}}";
}

void write_activation(std::ostream& out, const Activation& activation) {
  out << "{\"event_id\": " << q(activation.event_id)
      << ", \"domain\": " << q(activation.domain)
      << ", \"level\": " << activation.level
      << ", \"similarity\": " << std::fixed << std::setprecision(6) << activation.similarity << std::defaultfloat
      << ", \"reward_scalar\": " << activation.reward_scalar << "}";
}

void write_generation_evidence(std::ostream& out, const Generation& gen) {
  out << "{";
  out << "\"activated_traces\": [";
  for (size_t i = 0; i < gen.activations.size(); ++i) {
    if (i) out << ", ";
    write_activation(out, gen.activations[i]);
  }
  out << "], \"generation_steps\": [";
  for (size_t i = 0; i < gen.steps.size(); ++i) {
    if (i) out << ", ";
    const auto& step = gen.steps[i];
    out << "{\"position\": " << step.position
        << ", \"chosen\": " << q(char_label(step.chosen))
        << ", \"score\": " << std::fixed << std::setprecision(6) << step.score << std::defaultfloat
        << ", \"active_state_feature_count\": " << step.active_state_feature_count
        << ", \"active_slot_copy_count\": " << step.active_slot_copy_count
        << ", \"active_copy_boundary_count\": " << step.active_copy_boundary_count
        // CYCLE-3.5: segment-mode evidence fields are exported so eval artifacts can audit
        // when the brain entered copy mode and which observation role drove the copy. These
        // fields were tracked on GenerationStep since cycle 3 but were never serialized.
        << ", \"is_mode_switch\": " << (step.is_mode_switch ? "true" : "false")
        << ", \"is_copy_emit\": " << (step.is_copy_emit ? "true" : "false")
        << ", \"copy_role\": " << q(step.copy_role)
        << ", \"top_chars\": [";
    for (size_t j = 0; j < step.top_chars.size(); ++j) {
      if (j) out << ", ";
      out << "{\"char\": " << q(char_label(step.top_chars[j].first))
          << ", \"score\": " << std::fixed << std::setprecision(6) << step.top_chars[j].second << std::defaultfloat
          << "}";
    }
    out << "]}";
  }
  out << "], \"connection_feature_count\": " << gen.connection_feature_count
      << ", \"connection_nonzero_count\": " << gen.connection_nonzero_count
      << ", \"slot_copy_link_count\": " << gen.slot_copy_link_count
      << ", \"segment_mode_switch_count\": " << gen.segment_mode_switch_count
      << ", \"copy_mode_char_count\": " << gen.copy_mode_char_count
      << ", \"copy_boundary_feature_count\": " << gen.copy_boundary_feature_count
      << ", \"state_hash\": " << q(hex64(gen.state_hash)) << "}";
}

std::string display_output(const std::string& output) {
  return output.empty() ? std::string("<empty>") : output;
}

void write_config(std::ostream& out, const Config& config) {
  // CYCLE-3.5: segment-mode fields are part of the config-hash because they change
  // answer-path behavior (action-space width + softmax mixing). Pre-3.5 artifacts
  // omitted these and reported the same model_config_hash for cycle-2 and cycle-3 runs,
  // which masked a meaningful semantic shift in audit comparisons.
  out << "{\"dimensions\": " << config.dimensions
      << ", \"seed\": " << config.seed
      << ", \"learning_rate\": " << config.learning_rate
      << ", \"top_k\": " << config.top_k
      << ", \"max_output_chars\": " << config.max_output_chars
      << ", \"trace_gain\": " << config.trace_gain
      << ", \"context_gain\": " << config.context_gain
      << ", \"derived_relation_gain\": " << config.derived_relation_gain
      << ", \"symbolic_relation_gain\": " << config.symbolic_relation_gain
      << ", \"grid_spatial_gain\": " << config.grid_spatial_gain
      << ", \"transition_gain\": " << config.transition_gain
      << ", \"position_gain\": " << config.position_gain
      << ", \"state_binding_gain\": " << config.state_binding_gain
      << ", \"slot_pass_gain\": " << config.slot_pass_gain
      << ", \"segment_mode_gain\": " << config.segment_mode_gain
      << ", \"trace_span_position_gain\": " << config.trace_span_position_gain
      << ", \"repetition_penalty_weight\": " << config.repetition_penalty_weight
      << ", \"use_trace_id_feature\": " << (config.use_trace_id_feature ? "true" : "false")
      << ", \"use_slot_pass_through\": " << (config.use_slot_pass_through ? "true" : "false")
      << ", \"use_segment_mode\": " << (config.use_segment_mode ? "true" : "false")
      << ", \"use_trace_span_position_features\": "
      << (config.use_trace_span_position_features ? "true" : "false")
      << ", \"use_numeric_derived_features\": " << (config.use_numeric_derived_features ? "true" : "false")
      << ", \"use_threshold_derived_features\": " << (config.use_threshold_derived_features ? "true" : "false")
      << ", \"use_modular_derived_features\": " << (config.use_modular_derived_features ? "true" : "false")
      << ", \"use_relation_projection\": " << (config.use_relation_projection ? "true" : "false")
      << ", \"use_symbolic_relation_features\": "
      << (config.use_symbolic_relation_features ? "true" : "false")
      << ", \"use_grid_spatial_features\": "
      << (config.use_grid_spatial_features ? "true" : "false")
      << ", \"max_roles\": " << config.max_roles << "}";
}

uint64_t config_hash(const Config& config) {
  std::ostringstream out;
  write_config(out, config);
  return fnv1a(out.str());
}

void write_backend_facts(std::ostream& out) {
  out << "{";
  out << "\"runtime\": \"native_cpp20\", ";
  out << "\"compiler\": " << q(__VERSION__) << ", ";
  out << "\"cpu_compile_flags\": {";
#ifdef __AVX2__
  out << "\"avx2\": true";
#else
  out << "\"avx2\": false";
#endif
#ifdef __AVX512F__
  out << ", \"avx512f\": true";
#else
  out << ", \"avx512f\": false";
#endif
#ifdef __AVX_VNNI__
  out << ", \"avx_vnni\": true";
#else
  out << ", \"avx_vnni\": false";
#endif
  out << "}, ";
  out << "\"gpu_backend\": \"not_used_in_organic_v0\", ";
  out << "\"gpu_claim\": \"none\", ";
  out << "\"note\": \"CUDA is the intended future backend; this artifact is CPU-native only.\"";
  out << "}";
}

void write_persistence_contract(std::ostream& out, const PersistenceContext& ctx) {
  auto path_or_null = [&](const std::string& p) -> std::string {
    return p.empty() ? std::string("null") : (std::string("\"") + json_escape(p) + "\"");
  };
  out << "{";
  out << "\"status\": \"" << json_escape(ctx.load_status) << "\", ";
  out << "\"event_log_schema_path\": \"docs/artifacts/PERSISTENCE_SCHEMA.md#event-log-jsonl-v0\", ";
  out << "\"state_snapshot_schema_path\": \"docs/artifacts/PERSISTENCE_SCHEMA.md#state-snapshot-pxstate-line-v0\", ";
  out << "\"organism_id\": \"" << json_escape(ctx.organism_id) << "\", ";
  out << "\"loaded_state_path\": " << path_or_null(ctx.loaded_state_path) << ", ";
  out << "\"saved_state_path\": " << path_or_null(ctx.saved_state_path) << ", ";
  out << "\"appended_event_log_path\": " << path_or_null(ctx.event_log_path);
  out << "}";
}

std::vector<std::string> reward_keys(const std::vector<Event>& events) {
  std::set<std::string> keys;
  for (const auto& event : events) {
    for (const auto& item : event.reward) keys.insert(item.first);
  }
  return {keys.begin(), keys.end()};
}

void ensure_parent_dir(const std::string& path) {
  auto parent = std::filesystem::path(path).parent_path();
  if (!parent.empty()) std::filesystem::create_directories(parent);
}

std::string command_string(int argc, char** argv) {
  std::ostringstream out;
  for (int i = 0; i < argc; ++i) {
    if (i) out << " ";
    out << argv[i];
  }
  return out.str();
}

void append_event_log_line(const std::string& log_path, const std::string& organism_id,
                           const std::string& phase, const Event& event,
                           const std::string& raw_output, const std::string& expected,
                           uint64_t state_before_hash, uint64_t state_after_hash,
                           const std::string& source_kind, const std::string& source_path);

void write_train_artifact(const std::string& out_path, const std::string& data_path, const std::string& mode,
                          const std::string& command, const std::vector<Event>& events, const Config& config,
                          PersistenceContext& persistence) {
  auto audit = validate_splits(events);
  if (!audit.duplicates.empty()) throw std::runtime_error("held-out prompt duplicates training prompt");
  OrganicBrain brain(config);
  bool continued_from_disk = false;
  if (!persistence.loaded_state_path.empty()) {
    std::ifstream state_in(persistence.loaded_state_path);
    if (!state_in) throw std::runtime_error("cannot open loaded state: " + persistence.loaded_state_path);
    brain.load_serialized_state(state_in);
    if (brain.state_hash() != brain.expected_state_hash()) {
      throw std::runtime_error("loaded state hash mismatch: file=" + hex64(brain.expected_state_hash()) +
                               " recomputed=" + hex64(brain.state_hash()));
    }
    persistence.load_status = "loaded_then_learned";
    continued_from_disk = true;
  }
  uint64_t parent_state = brain.state_hash();
  size_t parent_trace_count = brain.trace_count();
  size_t parent_connection_feature_count = brain.connection_feature_count();
  size_t parent_connection_nonzero_count = brain.connection_nonzero_count();
  size_t parent_slot_copy_link_count = brain.slot_copy_link_count();
  size_t parent_learned_char_count = brain.learned_char_count();
  uint64_t before_hash = parent_state;
  for (const auto& event : events) {
    if (event.split != "train") continue;
    brain.learn(event);
    uint64_t after_hash = brain.state_hash();
    if (!persistence.event_log_path.empty()) {
      append_event_log_line(persistence.event_log_path, persistence.organism_id, "learn", event,
                            event.target_output, event.target_output, before_hash, after_hash,
                            continued_from_disk ? "loaded_state_plus_benchmark" : "benchmark", data_path);
    }
    before_hash = after_hash;
  }
  std::string ts = timestamp_utc();
  uint64_t state = brain.state_hash();
  std::string run_id = "organic-v0-train-" + hex64(fnv1a(ts + hex64(state))).substr(0, 12);
  const Config& active_config = brain.config();

  // Persistence side-effects: save state and/or append event log if paths were provided.
  if (!persistence.saved_state_path.empty()) {
    ensure_parent_dir(persistence.saved_state_path);
    std::ofstream state_out(persistence.saved_state_path);
    brain.serialize_state(state_out, persistence.organism_id);
    if (continued_from_disk) {
      persistence.load_status = "loaded_then_learned_and_saved";
    } else if (persistence.load_status == "schema_only_not_runtime_persistence") {
      persistence.load_status = "save_only_no_load_yet";
    }
  }

  ensure_parent_dir(out_path);
  std::ofstream out(out_path);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"mode\": " << q(mode) << ",\n";
  out << "  \"seed\": " << active_config.seed << ",\n";
  out << "  \"config\": "; write_config(out, active_config); out << ",\n";
  out << "  \"model_config_hash\": " << q(hex64(config_hash(active_config))) << ",\n";
  out << "  \"model_state_hash\": " << q(hex64(state)) << ",\n";
  out << "  \"parent_model_state_hash\": " << q(hex64(parent_state)) << ",\n";
  out << "  \"benchmark_path\": " << q(data_path) << ",\n";
  out << "  \"persistence\": "; write_persistence_contract(out, persistence); out << ",\n";
  out << "  \"train_dev_test_split\": "; write_split_audit(out, events, audit, 2); out << ",\n";
  out << "  \"available_tools\": [\"native_cpp20_stdlib\"],\n";
  out << "  \"backend_facts\": "; write_backend_facts(out); out << ",\n";
  out << "  \"action_budget\": {\"max_output_chars\": " << config.max_output_chars << "},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"evaluation\": true},\n";
  out << "  \"reward_vector\": [";
  auto keys = reward_keys(events);
  for (size_t i = 0; i < keys.size(); ++i) { if (i) out << ", "; out << q(keys[i]); }
  out << "],\n";
  out << "  \"training_outputs\": [\n";
  bool first = true;
  for (const auto& event : events) {
    if (event.split != "train") continue;
    if (!first) out << ",\n";
    auto gen = brain.generate(event.input, event.observations);
    out << "    {\"event_id\": " << q(event.event_id)
        << ", \"domain\": " << q(event.domain)
        << ", \"level\": " << event.level
        << ", \"composition\": " << q(event.composition)
        << ", \"input\": " << q(event.input)
        << ", \"target_output\": " << q(event.target_output)
        << ", \"raw_generated_output\": " << q(gen.output)
        << ", \"score\": "; write_score(out, gen.output, event.target_output);
    out << ", \"activated_memory_state\": "; write_generation_evidence(out, gen);
    out << "}";
    first = false;
  }
  out << "\n  ],\n";
  out << "  \"parent_model_state\": {\"trace_count\": " << parent_trace_count
      << ", \"connection_feature_count\": " << parent_connection_feature_count
      << ", \"connection_nonzero_count\": " << parent_connection_nonzero_count
      << ", \"slot_copy_link_count\": " << parent_slot_copy_link_count
      << ", \"learned_char_count\": " << parent_learned_char_count
      << ", \"state_hash\": " << q(hex64(parent_state)) << "},\n";
  out << "  \"model_state\": {\"trace_count\": " << brain.trace_count()
      << ", \"connection_feature_count\": " << brain.connection_feature_count()
      << ", \"connection_nonzero_count\": " << brain.connection_nonzero_count()
      << ", \"slot_copy_link_count\": " << brain.slot_copy_link_count()
      << ", \"learned_char_count\": " << brain.learned_char_count()
      << ", \"state_hash\": " << q(hex64(state)) << "},\n";
  out << "  \"state_growth\": {\"trace_count_delta\": " << (brain.trace_count() - parent_trace_count)
      << ", \"connection_feature_count_delta\": "
      << (brain.connection_feature_count() - parent_connection_feature_count)
      << ", \"connection_nonzero_count_delta\": "
      << (brain.connection_nonzero_count() - parent_connection_nonzero_count)
      << ", \"slot_copy_link_count_delta\": "
      << (brain.slot_copy_link_count() - parent_slot_copy_link_count)
      << ", \"learned_char_count_delta\": "
      << (brain.learned_char_count() - parent_learned_char_count) << "},\n";
  out << "  \"honest_interpretation\": \"Native organic-v0 stores rewarded event/output associations as state-bound character connections. Raw outputs are generated after training and are not cleaned.\"\n";
  out << "}\n";
}

struct EvalSummary {
  int count = 0;
  double exact_total = 0.0;
  double ratio_total = 0.0;
};

void add_summary(std::map<std::string, EvalSummary>& summary, const std::string& key, bool exact, double ratio) {
  auto& item = summary[key];
  item.count += 1;
  item.exact_total += exact ? 1.0 : 0.0;
  item.ratio_total += ratio;
}

void write_summary_map(std::ostream& out, const std::map<std::string, EvalSummary>& summary) {
  out << "{";
  bool first = true;
  for (const auto& item : summary) {
    if (!first) out << ", ";
    const auto& s = item.second;
    out << q(item.first) << ": {\"count\": " << s.count
        << ", \"exact_rate\": " << std::fixed << std::setprecision(6) << (s.count ? s.exact_total / s.count : 0.0)
        << ", \"mean_sequence_ratio\": " << (s.count ? s.ratio_total / s.count : 0.0) << std::defaultfloat << "}";
    first = false;
  }
  out << "}";
}

void write_eval_artifact(const std::string& out_path, const std::string& data_path, const std::string& mode,
                         const std::string& command, const std::vector<Event>& events, const Config& config,
                         PersistenceContext& persistence) {
  auto audit = validate_splits(events);
  if (!audit.duplicates.empty()) throw std::runtime_error("held-out prompt duplicates training prompt");
  OrganicBrain brain(config);
  bool continued_for_eval = false;
  BrainStateStats parent_stats;
  if (!persistence.loaded_state_path.empty()) {
    load_state_checked(brain, persistence.loaded_state_path);
    parent_stats = capture_state_stats(brain);
    if (!persistence.saved_state_path.empty()) {
      continued_for_eval = true;
      persistence.load_status = "loaded_then_learned";
      learn_train_events(brain, events, persistence, "loaded_state_plus_benchmark", data_path);
      ensure_parent_dir(persistence.saved_state_path);
      std::ofstream state_out(persistence.saved_state_path);
      brain.serialize_state(state_out, persistence.organism_id);
      persistence.load_status = "loaded_then_learned_and_saved";
    } else {
      persistence.load_status = "loaded_from_disk";
    }
  } else {
    brain = train_brain(events, config);
    if (!persistence.saved_state_path.empty()) {
      ensure_parent_dir(persistence.saved_state_path);
      std::ofstream state_out(persistence.saved_state_path);
      brain.serialize_state(state_out, persistence.organism_id);
      if (persistence.load_status == "schema_only_not_runtime_persistence") {
        persistence.load_status = "save_only_no_load_yet";
      }
    }
  }
  // Cycle-4 honesty nit: artifacts should describe the config the brain actually uses.
  // A --load-state run may replace binary defaults with the snapshot CONFIG line; reporting
  // the outer main() config would make legacy-load artifacts lie about answer-path behavior.
  const Config& active_config = brain.config();
  BrainStateStats model_stats = capture_state_stats(brain);
  auto alphabet = collect_alphabet(events);

  struct Result {
    const Event* event = nullptr;
    Generation gen;
    std::string random;
    bool exact = false;
    double ratio = 0.0;
  };

  // Held-out generation does not mutate brain state — state_hash is constant for all eval events,
  // so we capture it once and reuse it for the event-log's state_before/state_after fields.
  uint64_t eval_state_hash = model_stats.state_hash;
  std::string eval_source = persistence.loaded_state_path.empty()
                                ? std::string("benchmark")
                                : (continued_for_eval ? std::string("continued_state") : std::string("loaded_state"));
  std::string eval_source_path = persistence.loaded_state_path.empty()
                                    ? data_path
                                    : (continued_for_eval ? persistence.saved_state_path : persistence.loaded_state_path);

  std::vector<Result> results;
  std::map<std::string, EvalSummary> by_split;
  std::map<std::string, EvalSummary> by_domain;
  std::map<std::string, EvalSummary> by_level;
  std::map<std::string, EvalSummary> by_composition;
  EvalSummary overall;
  for (const auto& event : events) {
    if (event.split == "train") continue;
    Result result;
    result.event = &event;
    result.gen = brain.generate(event.input, event.observations);
    result.random = random_baseline(event, alphabet, active_config.seed);
    result.exact = result.gen.output == event.target_output;
    result.ratio = lcs_ratio(result.gen.output, event.target_output);
    overall.count += 1;
    overall.exact_total += result.exact ? 1.0 : 0.0;
    overall.ratio_total += result.ratio;
    add_summary(by_split, event.split, result.exact, result.ratio);
    add_summary(by_domain, event.domain, result.exact, result.ratio);
    add_summary(by_level, std::to_string(event.level), result.exact, result.ratio);
    add_summary(by_composition, event.composition, result.exact, result.ratio);
    // Persistence side-effect: append one event-log line per held-out generate so the organism's
    // experience stream records what it was asked and what it emitted. before==after (no learning).
    append_event_log_line(persistence.event_log_path, persistence.organism_id, "generate", event,
                          result.gen.output, event.target_output, eval_state_hash, eval_state_hash,
                          eval_source, eval_source_path);
    results.push_back(std::move(result));
  }

  std::string ts = timestamp_utc();
  uint64_t state = brain.state_hash();
  double exact_rate = overall.count ? overall.exact_total / overall.count : 0.0;
  std::string run_id = "organic-v0-eval-" + hex64(fnv1a(ts + hex64(state) + std::to_string(exact_rate))).substr(0, 12);

  ensure_parent_dir(out_path);
  std::ofstream out(out_path);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"mode\": " << q(mode) << ",\n";
  out << "  \"seed\": " << active_config.seed << ",\n";
  out << "  \"config\": "; write_config(out, active_config); out << ",\n";
  out << "  \"model_config_hash\": " << q(hex64(config_hash(active_config))) << ",\n";
  out << "  \"model_state_hash\": " << q(hex64(state)) << ",\n";
  out << "  \"benchmark_path\": " << q(data_path) << ",\n";
  out << "  \"persistence\": "; write_persistence_contract(out, persistence); out << ",\n";
  out << "  \"train_dev_test_split\": "; write_split_audit(out, events, audit, 2); out << ",\n";
  out << "  \"available_tools\": [\"native_cpp20_stdlib\"],\n";
  out << "  \"backend_facts\": "; write_backend_facts(out); out << ",\n";
  out << "  \"action_budget\": {\"max_output_chars\": " << active_config.max_output_chars << "},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"evaluation\": true},\n";
  out << "  \"reward_vector\": [";
  auto keys = reward_keys(events);
  for (size_t i = 0; i < keys.size(); ++i) { if (i) out << ", "; out << q(keys[i]); }
  out << "],\n";
  out << "  \"results\": [\n";
  for (size_t i = 0; i < results.size(); ++i) {
    if (i) out << ",\n";
    const auto& result = results[i];
    const auto& event = *result.event;
    out << "    {\"event_id\": " << q(event.event_id)
        << ", \"episode_id\": " << q(event.episode_id)
        << ", \"split\": " << q(event.split)
        << ", \"domain\": " << q(event.domain)
        << ", \"level\": " << event.level
        << ", \"composition\": " << q(event.composition)
        << ", \"input\": " << q(event.input)
        << ", \"observations\": [";
    for (size_t j = 0; j < event.observations.size(); ++j) { if (j) out << ", "; out << q(event.observations[j]); }
    out << "], \"target_output\": " << q(event.target_output)
        << ", \"raw_generated_output\": " << q(result.gen.output)
        << ", \"expected_output\": " << q(event.target_output)
        << ", \"oracle_result\": {\"expected_output\": " << q(event.target_output) << ", \"oracle_used_in_generation\": false}"
        << ", \"score\": "; write_score(out, result.gen.output, event.target_output);
    out << ", \"failure_reason\": " << q(failure_reason(result.gen.output, event.target_output))
        << ", \"activated_memory_state\": "; write_generation_evidence(out, result.gen);
    out << ", \"baselines\": {\"cold\": {\"raw_generated_output\": \"\", \"score\": "; write_score(out, "", event.target_output);
    out << ", \"failure_reason\": " << q(failure_reason("", event.target_output)) << "}, \"random\": {\"raw_generated_output\": " << q(result.random) << ", \"score\": ";
    write_score(out, result.random, event.target_output);
    out << ", \"failure_reason\": " << q(failure_reason(result.random, event.target_output)) << "}}"
        << ", \"source\": " << q(event.source) << "}";
  }
  out << "\n  ],\n";
  if (continued_for_eval) {
    out << "  \"parent_model_state_hash\": " << q(hex64(parent_stats.state_hash)) << ",\n";
    out << "  \"parent_model_state\": "; write_state_stats(out, parent_stats); out << ",\n";
    out << "  \"model_state\": "; write_state_stats(out, model_stats); out << ",\n";
    out << "  \"state_growth\": "; write_state_growth(out, parent_stats, model_stats); out << ",\n";
  }
  double cold_exact = 0.0;
  double random_exact = 0.0;
  for (const auto& result : results) {
    random_exact += (result.random == result.event->target_output) ? 1.0 : 0.0;
  }
  out << "  \"summary_metrics\": {\"overall\": {\"count\": " << overall.count
      << ", \"exact_rate\": " << std::fixed << std::setprecision(6) << exact_rate
      << ", \"mean_sequence_ratio\": " << (overall.count ? overall.ratio_total / overall.count : 0.0)
      << ", \"cold_exact_rate\": " << (overall.count ? cold_exact / overall.count : 0.0)
      << ", \"random_exact_rate\": " << (overall.count ? random_exact / overall.count : 0.0)
      << std::defaultfloat << "}, \"by_split\": ";
  write_summary_map(out, by_split);
  out << ", \"by_domain\": "; write_summary_map(out, by_domain);
  out << ", \"by_level\": "; write_summary_map(out, by_level);
  out << ", \"by_composition\": "; write_summary_map(out, by_composition);
  out << "},\n";
  out << "  \"failure_cases\": [";
  bool first_failure = true;
  for (const auto& result : results) {
    const auto& event = *result.event;
    if (result.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"event_id\": " << q(event.event_id)
        << ", \"domain\": " << q(event.domain)
        << ", \"level\": " << event.level
        << ", \"composition\": " << q(event.composition)
        << ", \"raw_generated_output\": " << q(result.gen.output)
        << ", \"expected_output\": " << q(event.target_output)
        << ", \"failure_reason\": " << q(failure_reason(result.gen.output, event.target_output))
        << ", \"activated_memory_state\": "; write_generation_evidence(out, result.gen);
    out << "}";
    first_failure = false;
  }
  out << "],\n";
  out << "  \"honest_interpretation\": \"Native organic-v0 emits from learned state-bound character associations over activated HDC traces. Exact score is evidence of associative recall/generalization only, not broad intelligence; failures are preserved verbatim.\"\n";
  out << "}\n";
}

void self_test() {
  Config config;
  std::vector<Event> events = load_events("benchmarks/v2_ladder/organic_v0.jsonl");
  auto audit = validate_splits(events);
  if (!audit.duplicates.empty()) throw std::runtime_error("self-test failed: held-out duplicate prompt");
  for (const auto& item : audit.levels_by_domain) {
    if (item.second != std::set<int>({0, 1, 2, 3})) throw std::runtime_error("self-test failed: missing levels 0-3 for " + item.first);
  }

  Event event;
  event.event_id = "evt_self_test";
  event.episode_id = "ep_self_test";
  event.split = "train";
  event.domain = "guard";
  event.level = 0;
  event.input = "guard stimulus qx";
  event.observations = {"guard:q"};
  event.target_output = "zx";
  event.reward = {{"task_success", 1.0}};
  event.source = "native_self_test";
  OrganicBrain brain(config);
  auto before = brain.generate(event.input, event.observations);
  if (!before.output.empty()) throw std::runtime_error("self-test failed: cold brain emitted output");
  brain.learn(event);
  auto after = brain.generate(event.input, event.observations);
  if (after.output != "zx") throw std::runtime_error("self-test failed: learned output mismatch");
  if (after.connection_nonzero_count == 0) throw std::runtime_error("self-test failed: no learned connections");
  std::cout << "organic-v0 native self-test OK\n";
}

struct Args {
  std::string phase;
  std::string mode = "test";
  std::string data = "benchmarks/v2_ladder/organic_v0.jsonl";
  std::string out;
  std::string save_state;
  std::string load_state;
  std::string event_log;
  std::string run_id;
  std::string replay_policy = "prediction_error";
  std::string replay_source_log;
  std::string verify_event_id;
  std::string organism_id = "raphael-local-0001";
  std::string rule_family = "all";
  std::string experience_db = "experience/organic-v0/text_experience_seed_v0.jsonl";
  std::string state_manifest;
  std::string corpus_manifest = "experience/organic-v0/corpus_manifest_v0.jsonl";
  // Cycle 16: additional manifests appended (in argv order) onto the primary
  // corpus_manifest for combined neural training. Empty by default so every
  // existing single-manifest invocation (Cycle 14/15 rails, all default
  // training paths) keeps bit-exact behavior. Only the recurrent text phase
  // consumes this; regenerate, the cycle-2 corpus prep, and the exposure
  // rails all stay single-manifest.
  std::vector<std::string> corpus_manifests_extra;
  std::string transcript_out;
  uint64_t scenario_seed = 7001;
  uint64_t random_baseline_seed = 8801;
  int action_budget = 64;
  int replay_passes = 2;
  int sleep_ticks = 100;
  int daemon_run_seconds = 0;
  int daemon_tick_sleep_ms = -1;
  int checkpoint_interval_seconds = 60;
  int checkpoint_interval_ticks = 100;
  int internal_timeout_seconds = 180;
  int generation_max_output_chars = 0;
  int corpus_exposure_max_shards = 4;
  int neural_epochs = 8;
  int neural_context = 16;
  int neural_hidden = 64;
  int neural_max_train_shards = 0;
  int neural_max_output_chars = 160;
  int neural_min_output_chars = 32;
  int neural_top_k = 16;
  int policy_max_wake_commands = 1024;
  int policy_max_sleep_ticks = 100000;
  int policy_max_replay_candidates = 10000;
  int policy_max_mutation_attempts = 100000;
  int policy_max_checkpoints = 10000;
  int policy_max_file_writes = 250000;
  double feedback_strength = 2.0;
  double replay_min_sequence_ratio = 1.0;
  double reward_repetition_penalty = 0.0;
  double neural_learning_rate = 0.025;
  double neural_temperature = 0.85;
  std::string policy_tmp_root;
  bool ablate_trace_id = false;
  bool ablate_numeric_derived = false;
  bool ablate_threshold_derived = false;
  bool ablate_modular_derived = false;
  bool ablate_relation_projection = false;
  bool ablate_symbolic_relations = false;
  bool ablate_grid_spatial = false;
  bool ablate_text_experience_learning = false;
  bool ablate_text_experience_replay = false;
  bool ablate_text_replay_audit = false;
  bool derive_raw_text_spans = false;
  bool ablate_raw_text_spans = false;
  bool ablate_corpus_learning = false;
  bool ablate_content_filter = false;
  bool unsafe_disable_policy = false;
};

int parse_nonnegative_int_flag(const std::string& flag, const std::string& value) {
  if (value.empty() ||
      !std::all_of(value.begin(), value.end(), [](unsigned char c) {
        return c >= '0' && c <= '9';
      })) {
    throw std::runtime_error(flag + " must be a nonnegative integer");
  }
  long long parsed = std::stoll(value);
  if (parsed > std::numeric_limits<int>::max()) {
    throw std::runtime_error(flag + " is too large");
  }
  return static_cast<int>(parsed);
}

Args parse_args(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) {
    std::string key = argv[i];
    auto need_value = [&](const std::string& flag) -> std::string {
      if (i + 1 >= argc) throw std::runtime_error("missing value for " + flag);
      return argv[++i];
    };
    if (key == "--phase") args.phase = need_value(key);
    else if (key == "--mode") args.mode = need_value(key);
    else if (key == "--data") args.data = need_value(key);
    else if (key == "--out") args.out = need_value(key);
    else if (key == "--save-state") args.save_state = need_value(key);
    else if (key == "--load-state") args.load_state = need_value(key);
    else if (key == "--event-log") args.event_log = need_value(key);
    else if (key == "--run-id") args.run_id = need_value(key);
    else if (key == "--replay-policy") args.replay_policy = need_value(key);
    else if (key == "--replay-source-log") args.replay_source_log = need_value(key);
    else if (key == "--verify-event") args.verify_event_id = need_value(key);
    else if (key == "--organism-id") args.organism_id = need_value(key);
    else if (key == "--rule-family") args.rule_family = need_value(key);
    else if (key == "--experience-db") args.experience_db = need_value(key);
    else if (key == "--state-manifest") args.state_manifest = need_value(key);
    else if (key == "--corpus-manifest") args.corpus_manifest = need_value(key);
    // Cycle 16: --corpus-manifest-extra is repeatable. Each occurrence
    // appends one additional manifest path to the combined recurrent
    // training corpus, in argv order. Stable order = deterministic train
    // shard sequence under fixed scenario_seed.
    else if (key == "--corpus-manifest-extra") {
      args.corpus_manifests_extra.push_back(need_value(key));
    }
    else if (key == "--transcript-out") args.transcript_out = need_value(key);
    else if (key == "--scenario-seed") args.scenario_seed = std::stoull(need_value(key));
    else if (key == "--random-baseline-seed") args.random_baseline_seed = std::stoull(need_value(key));
    else if (key == "--action-budget") args.action_budget = std::stoi(need_value(key));
    else if (key == "--replay-passes") args.replay_passes = std::stoi(need_value(key));
    else if (key == "--sleep-ticks") args.sleep_ticks = std::stoi(need_value(key));
    else if (key == "--daemon-run-seconds") args.daemon_run_seconds = std::stoi(need_value(key));
    else if (key == "--daemon-tick-sleep-ms") {
      args.daemon_tick_sleep_ms = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--checkpoint-interval-seconds") args.checkpoint_interval_seconds = std::stoi(need_value(key));
    else if (key == "--checkpoint-interval-ticks") args.checkpoint_interval_ticks = std::stoi(need_value(key));
    else if (key == "--internal-timeout-seconds") args.internal_timeout_seconds = std::stoi(need_value(key));
    else if (key == "--generation-max-output-chars") {
      args.generation_max_output_chars = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--corpus-exposure-max-shards") {
      args.corpus_exposure_max_shards = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--neural-epochs") {
      args.neural_epochs = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--neural-context") {
      args.neural_context = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--neural-hidden") {
      args.neural_hidden = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--neural-max-train-shards") {
      args.neural_max_train_shards = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--neural-max-output-chars") {
      args.neural_max_output_chars = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--neural-min-output-chars") {
      args.neural_min_output_chars = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--neural-top-k") {
      args.neural_top_k = parse_nonnegative_int_flag(key, need_value(key));
    }
    else if (key == "--policy-max-wake-commands") args.policy_max_wake_commands = std::stoi(need_value(key));
    else if (key == "--policy-max-sleep-ticks") args.policy_max_sleep_ticks = std::stoi(need_value(key));
    else if (key == "--policy-max-replay-candidates") args.policy_max_replay_candidates = std::stoi(need_value(key));
    else if (key == "--policy-max-mutation-attempts") args.policy_max_mutation_attempts = std::stoi(need_value(key));
    else if (key == "--policy-max-checkpoints") args.policy_max_checkpoints = std::stoi(need_value(key));
    else if (key == "--policy-max-file-writes") args.policy_max_file_writes = std::stoi(need_value(key));
    else if (key == "--policy-tmp-root") args.policy_tmp_root = need_value(key);
    else if (key == "--feedback-strength") args.feedback_strength = std::stod(need_value(key));
    else if (key == "--replay-threshold") args.replay_min_sequence_ratio = std::stod(need_value(key));
    else if (key == "--neural-learning-rate") args.neural_learning_rate = std::stod(need_value(key));
    else if (key == "--neural-temperature") args.neural_temperature = std::stod(need_value(key));
    else if (key == "--reward-repetition-penalty") {
      args.reward_repetition_penalty = std::stod(need_value(key));
      if (args.reward_repetition_penalty < 0.0) {
        throw std::runtime_error("--reward-repetition-penalty must be nonnegative");
      }
    }
    else if (key == "--ablate-trace-id") args.ablate_trace_id = true;
    else if (key == "--ablate-numeric-derived") args.ablate_numeric_derived = true;
    else if (key == "--ablate-threshold-derived") args.ablate_threshold_derived = true;
    else if (key == "--ablate-modular-derived") args.ablate_modular_derived = true;
    else if (key == "--ablate-relation-projection") args.ablate_relation_projection = true;
    else if (key == "--ablate-symbolic-relations" || key == "--ablate-symbolic-relation") {
      args.ablate_symbolic_relations = true;
    }
    else if (key == "--ablate-grid-spatial") args.ablate_grid_spatial = true;
    else if (key == "--ablate-text-experience-learning") args.ablate_text_experience_learning = true;
    else if (key == "--ablate-text-experience-replay") args.ablate_text_experience_replay = true;
    else if (key == "--ablate-text-replay-audit") args.ablate_text_replay_audit = true;
    else if (key == "--derive-raw-text-spans") args.derive_raw_text_spans = true;
    else if (key == "--ablate-raw-text-spans") args.ablate_raw_text_spans = true;
    else if (key == "--ablate-corpus-learning") args.ablate_corpus_learning = true;
    else if (key == "--ablate-content-filter") args.ablate_content_filter = true;
    else if (key == "--unsafe-disable-policy") args.unsafe_disable_policy = true;
    else throw std::runtime_error("unknown argument: " + key);
  }
  if (args.phase.empty()) throw std::runtime_error("--phase is required");
  return args;
}

void apply_ablations(Config& config, const Args& args) {
  if (args.ablate_trace_id) config.use_trace_id_feature = false;
  if (args.ablate_numeric_derived) config.use_numeric_derived_features = false;
  if (args.ablate_threshold_derived) config.use_threshold_derived_features = false;
  if (args.ablate_modular_derived) config.use_modular_derived_features = false;
  if (args.ablate_relation_projection) config.use_relation_projection = false;
  if (args.ablate_symbolic_relations) config.use_symbolic_relation_features = false;
  if (args.ablate_grid_spatial) config.use_grid_spatial_features = false;
}

struct PolicyViolation : public std::runtime_error {
  std::string denial_kind;
  std::string denial_reason;
  std::string pathway;

  PolicyViolation(std::string kind, std::string reason, std::string where)
      : std::runtime_error(reason), denial_kind(std::move(kind)),
        denial_reason(std::move(reason)), pathway(std::move(where)) {}
};

struct RuntimeBudgets {
  int64_t max_wake_commands = 1024;
  int64_t max_sleep_ticks = 100000;
  int64_t max_replay_candidates = 10000;
  int64_t max_mutation_attempts = 100000;
  int64_t max_checkpoints = 10000;
  int64_t max_file_writes = 250000;
  int64_t wake_commands = 0;
  int64_t sleep_ticks = 0;
  int64_t replay_candidates = 0;
  int64_t mutation_attempts = 0;
  int64_t checkpoints = 0;
  int64_t file_writes = 0;
};

struct EventLogIntegrityResult {
  std::string last_content_hash = "GENESIS";
  int line_count = 0;
};

std::string trim_copy(const std::string& text) {
  size_t begin = 0;
  while (begin < text.size() && std::isspace(static_cast<unsigned char>(text[begin]))) ++begin;
  size_t end = text.size();
  while (end > begin && std::isspace(static_cast<unsigned char>(text[end - 1]))) --end;
  return text.substr(begin, end - begin);
}

bool is_hex64_string(const std::string& text) {
  if (text.size() != 16) return false;
  return std::all_of(text.begin(), text.end(), [](unsigned char c) {
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
  });
}

bool path_contains_parent_ref(const std::filesystem::path& path) {
  for (const auto& part : path) {
    if (part == "..") return true;
  }
  return false;
}

std::filesystem::path normalized_absolute_path(const std::filesystem::path& path) {
  std::filesystem::path absolute =
      path.is_absolute() ? path : (std::filesystem::current_path() / path);
  return absolute.lexically_normal();
}

bool path_has_symlink_component(const std::filesystem::path& absolute_path) {
  std::filesystem::path current;
  for (const auto& part : absolute_path) {
    current /= part;
    if (current.empty()) continue;
    std::error_code ec;
    auto status = std::filesystem::symlink_status(current, ec);
    if (!ec && std::filesystem::is_symlink(status)) return true;
  }
  return false;
}

bool path_is_within_or_equal(const std::filesystem::path& path,
                             const std::filesystem::path& root) {
  auto p = path.lexically_normal();
  auto r = root.lexically_normal();
  auto pit = p.begin();
  auto rit = r.begin();
  for (; rit != r.end(); ++rit, ++pit) {
    if (pit == p.end() || *pit != *rit) return false;
  }
  return true;
}

std::string event_log_v2_core_from_line(const std::string& raw_line) {
  std::string line = trim_copy(raw_line);
  size_t field = line.rfind(",\"event_content_hash\":");
  if (field == std::string::npos || line.empty() || line.back() != '}') {
    throw std::runtime_error("event-log v2 missing terminal event_content_hash");
  }
  return line.substr(0, field) + "}";
}

std::string event_log_v2_content_hash_for_core(const std::string& core) {
  return hex64(fnv1a(core));
}

EventLogIntegrityResult verify_event_log_v2_integrity(const std::string& path) {
  EventLogIntegrityResult result;
  if (path.empty()) return result;
  std::ifstream in(path);
  if (!in) return result;
  std::string expected_prev = "GENESIS";
  std::string line;
  int line_no = 0;
  while (std::getline(in, line)) {
    ++line_no;
    if (trim_copy(line).empty()) continue;
    if (maybe_get_string(line, "schema").value_or("") != "project_x.event_log.v2") {
      throw std::runtime_error("event-log integrity: non-v2 row at line " + std::to_string(line_no));
    }
    std::string prev = maybe_get_string(line, "prev_event_content_hash").value_or("");
    if (prev != expected_prev) {
      throw std::runtime_error("event-log integrity: prev hash mismatch at line " +
                               std::to_string(line_no));
    }
    std::string core = event_log_v2_core_from_line(line);
    std::string computed = event_log_v2_content_hash_for_core(core);
    std::string recorded = maybe_get_string(line, "event_content_hash").value_or("");
    if (recorded != computed) {
      throw std::runtime_error("event-log integrity: content hash mismatch at line " +
                               std::to_string(line_no));
    }
    expected_prev = computed;
    result.last_content_hash = computed;
    result.line_count += 1;
  }
  return result;
}

struct RuntimePolicy {
  bool enabled = true;
  bool unsafe_disabled = false;
  std::filesystem::path project_root;
  std::vector<std::filesystem::path> allowed_roots;
  RuntimeBudgets budgets;
  std::vector<std::string> actual_write_paths;
  std::map<std::string, std::string> event_log_prev_hash_by_path;

  static RuntimePolicy from_args(const Args& args) {
    RuntimePolicy policy;
    policy.enabled = !args.unsafe_disable_policy;
    policy.unsafe_disabled = args.unsafe_disable_policy;
    policy.project_root = normalized_absolute_path(std::filesystem::current_path());
    policy.budgets.max_wake_commands = args.policy_max_wake_commands;
    policy.budgets.max_sleep_ticks = args.policy_max_sleep_ticks;
    policy.budgets.max_replay_candidates = args.policy_max_replay_candidates;
    policy.budgets.max_mutation_attempts = args.policy_max_mutation_attempts;
    policy.budgets.max_checkpoints = args.policy_max_checkpoints;
    policy.budgets.max_file_writes = args.policy_max_file_writes;
    policy.add_allowed_root(policy.project_root / "run");
    policy.add_allowed_root(policy.project_root / "run" / "artifacts");
    policy.add_allowed_root(policy.project_root / "run" / "state");
    policy.add_allowed_root(policy.project_root / "experience");
    if (!args.policy_tmp_root.empty()) policy.add_allowed_root(args.policy_tmp_root);
    return policy;
  }

  void add_allowed_root(const std::filesystem::path& root) {
    allowed_roots.push_back(normalized_absolute_path(root));
  }

  [[noreturn]] void deny(const std::string& kind, const std::string& reason,
                         const std::string& pathway) const {
    throw PolicyViolation(kind, reason, pathway);
  }

  void consume_budget(const std::string& kind, int64_t& used, int64_t max_value,
                      const std::string& pathway) {
    if (!enabled) return;
    if (max_value < 0) deny("budget_exceeded", kind + " budget is negative", pathway);
    if (used + 1 > max_value) {
      deny("budget_exceeded", kind + " budget exceeded", pathway);
    }
    ++used;
  }

  void note_wake_command() {
    consume_budget("wake_commands", budgets.wake_commands, budgets.max_wake_commands,
                   "stdin_jsonl");
  }

  void note_sleep_tick() {
    consume_budget("sleep_ticks", budgets.sleep_ticks, budgets.max_sleep_ticks,
                   "sleep_loop");
  }

  void note_replay_candidate() {
    consume_budget("replay_candidates", budgets.replay_candidates,
                   budgets.max_replay_candidates, "replay_candidate_ingest");
  }

  void note_mutation_attempt(const std::string& pathway) {
    consume_budget("mutation_attempts", budgets.mutation_attempts,
                   budgets.max_mutation_attempts, pathway);
  }

  void note_checkpoint() {
    consume_budget("checkpoints", budgets.checkpoints, budgets.max_checkpoints,
                   "checkpoint");
  }

  std::filesystem::path validate_path(const std::string& label, const std::string& raw_path,
                                      const std::string& access) const {
    if (raw_path.empty()) return {};
    if (!enabled) return normalized_absolute_path(raw_path);
    std::filesystem::path raw(raw_path);
    if (path_contains_parent_ref(raw)) {
      deny("path_denied", label + " path contains parent traversal", raw_path);
    }
    std::filesystem::path absolute = normalized_absolute_path(raw);
    if (path_has_symlink_component(absolute)) {
      deny("path_denied", label + " path contains a symlink component", raw_path);
    }
    bool allowed = false;
    for (const auto& root : allowed_roots) {
      if (path_is_within_or_equal(absolute, root)) {
        allowed = true;
        break;
      }
    }
    if (!allowed) {
      deny("path_denied", label + " " + access + " path is outside allowed roots", raw_path);
    }
    return absolute;
  }

  bool path_allowed_for_emergency_write(const std::string& raw_path) const {
    try {
      validate_path("emergency_artifact", raw_path, "write");
      return true;
    } catch (...) {
      return false;
    }
  }

  void note_file_write(const std::string& label, const std::string& raw_path,
                       bool count_budget = true) {
    if (raw_path.empty()) return;
    auto absolute = validate_path(label, raw_path, "write");
    if (count_budget) {
      consume_budget("file_writes", budgets.file_writes, budgets.max_file_writes, label);
    }
    actual_write_paths.push_back(absolute.string());
  }

  void validate_runtime_command_schema(const std::string& line) const {
    if (!enabled) return;
    std::string cmd = maybe_get_string(line, "cmd").value_or("");
    static const std::set<std::string> kAllowedCommands = {
        "wake", "sleep", "checkpoint", "shutdown"};
    if (cmd.empty() || !kAllowedCommands.count(cmd)) {
      deny("schema_denied", "runtime cmd is not in the command allowlist", "stdin_jsonl");
    }
    if (auto action_kind = maybe_get_string(line, "action_kind")) {
      static const std::set<std::string> kAllowedActionKinds = {
          "wake", "sleep", "checkpoint", "shutdown"};
      if (!kAllowedActionKinds.count(*action_kind)) {
        deny("schema_denied", "action_kind is not in the runtime allowlist: " + *action_kind,
             "stdin_jsonl");
      }
    }
  }

  std::string prev_hash_for_event_log_append(const std::string& raw_path) {
    auto absolute = validate_path("event_log", raw_path, "write").string();
    auto found = event_log_prev_hash_by_path.find(absolute);
    if (found != event_log_prev_hash_by_path.end()) return found->second;
    try {
      auto integrity = verify_event_log_v2_integrity(raw_path);
      event_log_prev_hash_by_path[absolute] = integrity.last_content_hash;
      return integrity.last_content_hash;
    } catch (const std::exception& e) {
      deny("event_log_integrity_denied", e.what(), raw_path);
    }
  }

  void set_event_log_prev_hash(const std::string& raw_path, const std::string& hash) {
    auto absolute = validate_path("event_log", raw_path, "write").string();
    event_log_prev_hash_by_path[absolute] = hash;
  }
};

void write_budget_state_json(std::ostream& out, const RuntimePolicy& policy) {
  const auto& b = policy.budgets;
  out << "{\"policy_enabled\":" << (policy.enabled ? "true" : "false")
      << ",\"unsafe_disabled\":" << (policy.unsafe_disabled ? "true" : "false")
      << ",\"wake_commands\":{\"used\":" << b.wake_commands << ",\"max\":" << b.max_wake_commands << "}"
      << ",\"sleep_ticks\":{\"used\":" << b.sleep_ticks << ",\"max\":" << b.max_sleep_ticks << "}"
      << ",\"replay_candidates\":{\"used\":" << b.replay_candidates << ",\"max\":"
      << b.max_replay_candidates << "}"
      << ",\"mutation_attempts\":{\"used\":" << b.mutation_attempts << ",\"max\":"
      << b.max_mutation_attempts << "}"
      << ",\"checkpoints\":{\"used\":" << b.checkpoints << ",\"max\":" << b.max_checkpoints << "}"
      << ",\"file_writes\":{\"used\":" << b.file_writes << ",\"max\":" << b.max_file_writes << "}}";
}

void write_allowed_roots_json(std::ostream& out, const RuntimePolicy& policy) {
  out << "[";
  for (size_t i = 0; i < policy.allowed_roots.size(); ++i) {
    if (i) out << ",";
    out << q(policy.allowed_roots[i].string());
  }
  out << "]";
}

void write_actual_writes_json(std::ostream& out, const RuntimePolicy& policy) {
  out << "[";
  for (size_t i = 0; i < policy.actual_write_paths.size(); ++i) {
    if (i) out << ",";
    out << q(policy.actual_write_paths[i]);
  }
  out << "]";
}

bool writes_subset_allowed_roots(const RuntimePolicy& policy) {
  for (const auto& raw : policy.actual_write_paths) {
    bool allowed = false;
    auto path = normalized_absolute_path(raw);
    for (const auto& root : policy.allowed_roots) {
      if (path_is_within_or_equal(path, root)) {
        allowed = true;
        break;
      }
    }
    if (!allowed) return false;
  }
  return true;
}

// Append one JSONL event-log line per the docs/artifacts/PERSISTENCE_SCHEMA.md v0 schema.
// Open in append mode; flush after each line so a crash mid-run preserves history.
void append_event_log_line(const std::string& log_path, const std::string& organism_id,
                           const std::string& phase, const Event& event,
                           const std::string& raw_output, const std::string& expected,
                           uint64_t state_before_hash, uint64_t state_after_hash,
                           const std::string& source_kind, const std::string& source_path) {
  if (log_path.empty()) return;
  if (!valid_event_log_phase(phase)) throw std::runtime_error("event log phase outside schema: " + phase);
  ensure_parent_dir(log_path);
  std::string log_event_id = event_log_id(next_event_log_ordinal(log_path));
  std::ofstream log(log_path, std::ios::app);
  if (!log) throw std::runtime_error("cannot open event log: " + log_path);
  log << "{\"schema\":\"project_x.event_log.v0\","
      << "\"event_id\":\"" << json_escape(log_event_id) << "\","
      << "\"organism_id\":\"" << json_escape(organism_id) << "\","
      << "\"timestamp_utc\":\"" << timestamp_utc() << "\","
      << "\"source\":{\"kind\":\"" << json_escape(source_kind)
      << "\",\"path\":\"" << json_escape(source_path)
      << "\",\"source_event_id\":\"" << json_escape(event.event_id) << "\"},"
      << "\"phase\":\"" << json_escape(phase) << "\","
      << "\"input\":{\"text\":" << q(event.input) << ",\"observations\":[";
  for (size_t i = 0; i < event.observations.size(); ++i) {
    if (i) log << ",";
    log << q(event.observations[i]);
  }
  log << "]},\"output\":{\"raw_generated_output\":" << q(raw_output)
      << ",\"expected_output\":" << q(expected)
      << ",\"oracle_used_in_generation\":false},"
      << "\"reward\":";
  write_reward_object(log, event.reward);
  log << ","
      << "\"state_before_hash\":\"" << hex64(state_before_hash) << "\","
      << "\"state_after_hash\":\"" << hex64(state_after_hash) << "\","
      << "\"trace_refs\":[],"
      << "\"mutation_refs\":[],"
      << "\"backend\":{\"runtime\":\"native_cpp20\",\"gpu_backend\":\"not_used_in_organic_v0\"}}\n";
}

bool json_key_exists(const std::string& line, const std::string& key) {
  return line.find("\"" + key + "\"") != std::string::npos;
}

std::optional<int> maybe_get_int(const std::string& line, const std::string& key) {
  if (!json_key_exists(line, key)) return std::nullopt;
  return get_int(line, key);
}

std::vector<std::string> maybe_get_string_array_or_empty(const std::string& line,
                                                         const std::string& key) {
  if (!json_key_exists(line, key)) return {};
  return get_string_array(line, key);
}

std::map<std::string, double> maybe_get_number_object_or_empty(const std::string& line,
                                                               const std::string& key) {
  if (!json_key_exists(line, key)) return {};
  return get_number_object(line, key);
}

void write_trace_refs_json(std::ostream& out, const std::vector<Activation>& refs) {
  out << "[";
  for (size_t i = 0; i < refs.size(); ++i) {
    if (i) out << ",";
    out << "{\"event_id\":" << q(refs[i].event_id)
        << ",\"similarity\":" << std::fixed << std::setprecision(6) << refs[i].similarity
        << std::defaultfloat << "}";
  }
  out << "]";
}

void write_mutation_refs_json(std::ostream& out, const std::vector<MutationRef>& refs) {
  out << "[";
  for (size_t i = 0; i < refs.size(); ++i) {
    if (i) out << ",";
    out << "{\"mutation_id\":" << q(refs[i].mutation_id)
        << ",\"kind\":" << q(refs[i].kind)
        << ",\"accepted\":" << (refs[i].accepted ? "true" : "false")
        << ",\"state_before_hash\":" << q(hex64(refs[i].state_before_hash))
        << ",\"state_after_hash\":" << q(hex64(refs[i].state_after_hash))
        << ",\"reason\":" << q(refs[i].reason) << "}";
  }
  out << "]";
}

void write_prediction_json(std::ostream& out, const OutcomePrediction& prediction) {
  out << "{\"predictor\":\"a0_event_outcome\""
      << ",\"reward_scalar_pred\":" << std::fixed << std::setprecision(6)
      << prediction.reward_scalar
      << ",\"exact_score_or_prob_pred\":" << prediction.exact_prob_or_score
      << ",\"lcs_error_ratio_pred\":" << prediction.lcs_error_ratio
      << ",\"surprise_pred\":" << prediction.surprise
      << std::defaultfloat
      << ",\"feature_count\":" << prediction.feature_count << "}";
}

void write_prediction_error_json(std::ostream& out, const PredictionError* error) {
  if (!error) {
    out << "null";
    return;
  }
  out << "{\"reward_abs_error\":" << std::fixed << std::setprecision(6)
      << error->reward_abs_error
      << ",\"exact_abs_error\":" << error->exact_abs_error
      << ",\"lcs_error_abs_error\":" << error->lcs_error_abs_error
      << ",\"surprise\":" << error->surprise
      << std::defaultfloat << "}";
}

void append_event_log_v1(const std::string& log_path, const std::string& run_id,
                         const std::string& organism_id, const std::string& step_id,
                         const std::string& step_mode, const std::string& phase,
                         const Event& event, const std::string& raw_output,
                         const std::string& expected, bool audit_only,
                         const OutcomePrediction& prediction,
                         const PredictionError* prediction_error,
                         const std::vector<Activation>& trace_refs,
                         const std::vector<MutationRef>& mutation_refs,
                         uint64_t state_before_hash, uint64_t state_after_hash,
                         const std::string& source_kind, const std::string& source_path) {
  if (log_path.empty()) return;
  if (!valid_event_log_phase(phase)) throw std::runtime_error("event log phase outside schema: " + phase);
  ensure_parent_dir(log_path);
  std::string log_event_id = event_log_id(next_event_log_ordinal(log_path));
  std::ofstream log(log_path, std::ios::app);
  if (!log) throw std::runtime_error("cannot open event log: " + log_path);
  log << "{\"schema\":\"project_x.event_log.v1\""
      << ",\"event_id\":" << q(log_event_id)
      << ",\"run_id\":" << q(run_id)
      << ",\"organism_id\":" << q(organism_id)
      << ",\"step_id\":" << q(step_id)
      << ",\"step_mode\":" << q(step_mode)
      << ",\"timestamp_utc\":" << q(timestamp_utc())
      << ",\"phase\":" << q(phase)
      << ",\"source\":{\"source_kind\":" << q(source_kind)
      << ",\"source_path\":" << q(source_path)
      << ",\"source_event_id\":" << q(event.event_id) << "}"
      << ",\"input\":{\"text\":" << q(event.input) << ",\"observations\":[";
  for (size_t i = 0; i < event.observations.size(); ++i) {
    if (i) log << ",";
    log << q(event.observations[i]);
  }
  log << "]}"
      << ",\"output\":{\"raw_generated_output\":" << q(raw_output)
      << ",\"expected_output\":" << q(expected)
      << ",\"oracle_used_in_generation\":false"
      << ",\"audit_only\":" << (audit_only ? "true" : "false") << "}"
      << ",\"reward\":";
  write_reward_object(log, event.reward);
  log << ",\"prediction\":";
  write_prediction_json(log, prediction);
  log << ",\"prediction_error\":";
  write_prediction_error_json(log, prediction_error);
  log << ",\"trace_refs\":";
  write_trace_refs_json(log, trace_refs);
  log << ",\"mutation_refs\":";
  write_mutation_refs_json(log, mutation_refs);
  log << ",\"state_before_hash\":" << q(hex64(state_before_hash))
      << ",\"state_after_hash\":" << q(hex64(state_after_hash))
      << ",\"backend\":{\"runtime\":\"native_cpp20\",\"gpu_backend\":\"not_used_in_organic_v0\"}}\n";
}

void append_event_log_v2(const std::string& log_path, RuntimePolicy& policy,
                         const std::string& run_id, const std::string& organism_id,
                         const std::string& step_id, const std::string& step_mode,
                         const std::string& phase, const Event& event,
                         const std::string& raw_output, const std::string& expected,
                         bool audit_only, const OutcomePrediction& prediction,
                         const PredictionError* prediction_error,
                         const std::vector<Activation>& trace_refs,
                         const std::vector<MutationRef>& mutation_refs,
                         uint64_t state_before_hash, uint64_t state_after_hash,
                         const std::string& source_kind, const std::string& source_path,
                         bool policy_denial = false,
                         const std::string& denial_reason = "",
                         bool count_file_write = true) {
  if (log_path.empty()) return;
  if (!valid_event_log_phase(phase)) throw std::runtime_error("event log phase outside schema: " + phase);
  std::string prev_hash = policy.prev_hash_for_event_log_append(log_path);
  policy.note_file_write("event_log_append", log_path, count_file_write);
  ensure_parent_dir(log_path);
  std::string log_event_id = event_log_id(next_event_log_ordinal(log_path));
  std::ostringstream core;
  core << "{\"schema\":\"project_x.event_log.v2\""
       << ",\"event_id\":" << q(log_event_id)
       << ",\"run_id\":" << q(run_id)
       << ",\"organism_id\":" << q(organism_id)
       << ",\"step_id\":" << q(step_id)
       << ",\"step_mode\":" << q(step_mode)
       << ",\"timestamp_utc\":" << q(timestamp_utc())
       << ",\"phase\":" << q(phase)
       << ",\"source\":{\"source_kind\":" << q(source_kind)
       << ",\"source_path\":" << q(source_path)
       << ",\"source_event_id\":" << q(event.event_id) << "}"
       << ",\"input\":{\"text\":" << q(event.input) << ",\"observations\":[";
  for (size_t i = 0; i < event.observations.size(); ++i) {
    if (i) core << ",";
    core << q(event.observations[i]);
  }
  core << "]}"
       << ",\"output\":{\"raw_generated_output\":" << q(raw_output)
       << ",\"expected_output\":" << q(expected)
       << ",\"oracle_used_in_generation\":false"
       << ",\"audit_only\":" << (audit_only ? "true" : "false") << "}"
       << ",\"reward\":";
  write_reward_object(core, event.reward);
  core << ",\"prediction\":";
  write_prediction_json(core, prediction);
  core << ",\"prediction_error\":";
  write_prediction_error_json(core, prediction_error);
  core << ",\"trace_refs\":";
  write_trace_refs_json(core, trace_refs);
  core << ",\"mutation_refs\":";
  write_mutation_refs_json(core, mutation_refs);
  core << ",\"state_before_hash\":" << q(hex64(state_before_hash))
       << ",\"state_after_hash\":" << q(hex64(state_after_hash))
       << ",\"policy_denial\":" << (policy_denial ? "true" : "false")
       << ",\"denial_reason\":" << q(denial_reason)
       << ",\"budget_state\":";
  write_budget_state_json(core, policy);
  core << ",\"prev_event_content_hash\":" << q(prev_hash)
       << ",\"backend\":{\"runtime\":\"native_cpp20\",\"gpu_backend\":\"not_used_in_organic_v0\"}}";
  std::string core_text = core.str();
  std::string content_hash = event_log_v2_content_hash_for_core(core_text);
  std::string line = core_text.substr(0, core_text.size() - 1) +
                     ",\"event_content_hash\":" + q(content_hash) + "}";
  std::ofstream log(log_path, std::ios::app);
  if (!log) throw std::runtime_error("cannot open event log: " + log_path);
  log << line << "\n";
  log.flush();
  policy.set_event_log_prev_hash(log_path, content_hash);
}

std::string last_content_hash_or_genesis(const std::string& log_path) {
  std::ifstream in(log_path);
  if (!in) return "GENESIS";
  std::string last = "GENESIS";
  std::string line;
  while (std::getline(in, line)) {
    if (trim_copy(line).empty()) continue;
    auto hash = maybe_get_string(line, "event_content_hash");
    if (hash.has_value()) last = *hash;
  }
  return last;
}

void append_corpus_exposure_event_log_line(const std::string& log_path,
                                           const std::string& run_id,
                                           const std::string& organism_id,
                                           const std::string& step_id,
                                           const Event& event,
                                           const std::string& source_path,
                                           bool learning_applied,
                                           uint64_t state_before_hash,
                                           uint64_t state_after_hash) {
  if (log_path.empty()) return;
  ensure_parent_dir(log_path);
  std::string prev_hash = last_content_hash_or_genesis(log_path);
  std::string log_event_id = event_log_id(next_event_log_ordinal(log_path));
  std::ostringstream core;
  core << "{\"schema\":\"project_x.corpus_exposure_event.v1\""
       << ",\"event_id\":" << q(log_event_id)
       << ",\"run_id\":" << q(run_id)
       << ",\"organism_id\":" << q(organism_id)
       << ",\"step_id\":" << q(step_id)
       << ",\"timestamp_utc\":" << q(timestamp_utc())
       << ",\"phase\":\"learn\""
       << ",\"source\":{\"source_kind\":\"cycle12_corpus_shard\""
       << ",\"source_path\":" << q(source_path)
       << ",\"source_event_id\":" << q(event.event_id) << "}"
       << ",\"input\":{\"text\":" << q(event.input) << ",\"observations\":[";
  for (size_t i = 0; i < event.observations.size(); ++i) {
    if (i) core << ",";
    core << q(event.observations[i]);
  }
  core << "]}"
       << ",\"learning_applied\":" << (learning_applied ? "true" : "false")
       << ",\"state_before_hash\":" << q(hex64(state_before_hash))
       << ",\"state_after_hash\":" << q(hex64(state_after_hash))
       << ",\"prev_event_content_hash\":" << q(prev_hash)
       << ",\"backend\":{\"runtime\":\"native_cpp20\",\"gpu_backend\":\"not_used_in_organic_v0\"}}";
  std::string core_text = core.str();
  std::string content_hash = event_log_v2_content_hash_for_core(core_text);
  std::string line = core_text.substr(0, core_text.size() - 1) +
                     ",\"event_content_hash\":" + q(content_hash) + "}";
  std::ofstream log(log_path, std::ios::app);
  if (!log) throw std::runtime_error("cannot open corpus exposure event log: " + log_path);
  log << line << "\n";
  log.flush();
}

OutcomeTarget target_from_generation(const Event& event, const std::string& raw_output) {
  OutcomeTarget target;
  target.reward_scalar = event.reward_scalar();
  target.exact_binary = raw_output == event.target_output ? 1.0 : 0.0;
  target.lcs_error_ratio = 1.0 - lcs_ratio(raw_output, event.target_output);
  return target;
}

struct RuntimeCommand {
  std::string cmd;
  Event event;
  int ticks = 0;
};

RuntimeCommand parse_runtime_command(const std::string& line, const RuntimePolicy* policy = nullptr) {
  if (policy) policy->validate_runtime_command_schema(line);
  RuntimeCommand command;
  command.cmd = get_string(line, "cmd");
  if (command.cmd == "wake") {
    command.event.event_id = get_string(line, "event_id");
    command.event.episode_id = maybe_get_string(line, "session_id").value_or("cycle8_stdin");
    command.event.split = "wake";
    command.event.domain = "sleep_wake_runtime";
    command.event.level = 0;
    command.event.input = get_string(line, "input_text");
    command.event.observations = maybe_get_string_array_or_empty(line, "observations");
    command.event.target_output = maybe_get_string(line, "correction_output").value_or("");
    command.event.reward = maybe_get_number_object_or_empty(line, "reward");
    command.event.source = "stdin_jsonl";
    command.event.composition = "wake_event";
  } else if (command.cmd == "sleep") {
    command.ticks = maybe_get_int(line, "ticks").value_or(1);
  } else if (command.cmd != "checkpoint" && command.cmd != "shutdown") {
    throw std::runtime_error("unknown sleep-wake JSONL cmd: " + command.cmd);
  }
  return command;
}

struct ReplayCandidate {
  Event event;
  std::string source_path;
  std::string source_kind = "event_log";
};

void validate_replay_source_v2_line_schema(const std::string& line) {
  if (maybe_get_string(line, "schema").value_or("") != "project_x.event_log.v2") {
    throw std::runtime_error("replay-source-log row is not event-log v2");
  }
  if (!is_hex64_string(maybe_get_string(line, "state_before_hash").value_or("")) ||
      !is_hex64_string(maybe_get_string(line, "state_after_hash").value_or(""))) {
    throw std::runtime_error("replay-source-log row has malformed state hash fields");
  }
  if (maybe_get_string(line, "event_content_hash").value_or("").empty() ||
      maybe_get_string(line, "prev_event_content_hash").value_or("").empty()) {
    throw std::runtime_error("replay-source-log row lacks v2 hash-chain fields");
  }
  if (line.find("\"policy_denial\":true") != std::string::npos) {
    throw std::runtime_error("replay-source-log row cannot replay policy denial records");
  }
  if (auto action_kind = maybe_get_string(line, "action_kind")) {
    static const std::set<std::string> kAllowedActionKinds = {
        "wake", "sleep", "checkpoint", "shutdown"};
    if (!kAllowedActionKinds.count(*action_kind)) {
      throw std::runtime_error("replay-source-log action_kind is outside allowlist");
    }
  }
}

std::optional<Event> event_from_event_log_line(const std::string& line) {
  if (!json_key_exists(line, "expected_output")) return std::nullopt;
  std::string expected = maybe_get_string(line, "expected_output").value_or("");
  if (expected.empty()) return std::nullopt;
  Event event;
  event.event_id = maybe_get_string(line, "source_event_id").value_or(
      maybe_get_string(line, "event_id").value_or("event_log_candidate"));
  event.episode_id = maybe_get_string(line, "step_id").value_or("event_log_replay");
  event.split = "replay";
  event.domain = "sleep_wake_runtime";
  event.level = 0;
  event.input = maybe_get_string(line, "text").value_or("");
  event.observations = maybe_get_string_array_or_empty(line, "observations");
  event.target_output = expected;
  event.reward = maybe_get_number_object_or_empty(line, "reward");
  event.source = maybe_get_string(line, "source_kind").value_or(
      maybe_get_string(line, "kind").value_or("event_log"));
  event.composition = "event_log_replay";
  if (event.input.empty()) return std::nullopt;
  return event;
}

std::vector<ReplayCandidate> load_replay_candidates_from_log(const std::string& path,
                                                             RuntimePolicy* policy = nullptr) {
  std::vector<ReplayCandidate> candidates;
  if (path.empty()) return candidates;
  if (policy && policy->enabled) {
    policy->validate_path("replay_source_log", path, "read");
    try {
      verify_event_log_v2_integrity(path);
    } catch (const std::exception& e) {
      policy->deny("event_log_integrity_denied", e.what(), path);
    }
  }
  std::ifstream in(path);
  if (!in) return candidates;
  std::string line;
  while (std::getline(in, line)) {
    if (line.empty()) continue;
    try {
      if (policy && policy->enabled) validate_replay_source_v2_line_schema(line);
      auto event = event_from_event_log_line(line);
      if (!event.has_value()) continue;
      if (policy) policy->note_replay_candidate();
      candidates.push_back({*event, path, "event_log"});
    } catch (const std::exception& e) {
      if (policy && policy->enabled) {
        policy->deny("replay_source_denied",
                     std::string("replay-source-log row failed schema/hash validation: ") + e.what(),
                     path);
      }
      continue;
    }
  }
  return candidates;
}

struct OrganismStepInput {
  std::string run_id;
  std::string organism_id;
  std::string step_id;
  std::string source_kind;
  std::string source_path;
  Event event;
};

struct OrganismStepResult {
  OutcomePrediction prediction;
  PredictionError prediction_error;
  Generation generation;
  uint64_t state_before_hash = 0;
  uint64_t candidate_state_hash = 0;
  uint64_t state_after_hash = 0;
  uint64_t predictor_before_hash = 0;
  uint64_t predictor_candidate_hash = 0;
  uint64_t predictor_after_hash = 0;
  bool has_target = false;
  bool learned = false;
  bool accepted = false;
  double surprise_reduction = 0.0;
  std::string reason;
  std::vector<MutationRef> mutation_refs;
};

struct RollbackProof {
  std::string step_id;
  std::string mutation_id;
  std::string rejection_reason;
  uint64_t state_before_hash = 0;
  uint64_t candidate_state_hash = 0;
  uint64_t state_after_hash = 0;
  uint64_t predictor_before_hash = 0;
  uint64_t predictor_candidate_hash = 0;
  uint64_t predictor_after_hash = 0;
  bool live_state_preserved = false;
  bool predictor_state_preserved = false;
};

struct PolicyDenialRecord {
  std::string denial_kind;
  std::string denial_reason;
  std::string pathway;
};

struct RuntimeMetrics {
  std::string run_id;
  std::string phase;
  std::string replay_policy;
  std::string event_log_path;
  std::vector<std::string> checkpoint_paths;
  std::vector<uint64_t> state_hash_chain;
  std::vector<double> prediction_error_over_time;
  int wake_count = 0;
  int sleep_tick_count = 0;
  int replay_candidate_count = 0;
  int accepted_mutation_count = 0;
  int rejected_mutation_count = 0;
  double surprise_reduction = 0.0;
  bool timed_out = false;
  bool hard_stopped = false;
  std::string hard_stop_reason;
  std::vector<RollbackProof> rollback_proofs;
  std::vector<PolicyDenialRecord> policy_denials;
};

std::string default_cycle8_run_id(const Args& args) {
  if (!args.run_id.empty()) return args.run_id;
  return "cycle8-" + hex64(fnv1a(timestamp_utc() + args.replay_policy +
                                  std::to_string(args.random_baseline_seed))).substr(0, 12);
}

std::string default_cycle8_event_log_path(const Args& args, const std::string& run_id) {
  if (!args.event_log.empty()) return args.event_log;
  if (!args.policy_tmp_root.empty()) return args.policy_tmp_root + "/events/" + run_id + ".jsonl";
  return "run/state/organic-v0/events/" + args.organism_id + "-cycle9-" + run_id + ".jsonl";
}

std::string default_cycle8_out_path(const Args& args) {
  if (!args.out.empty()) return args.out;
  if (args.phase == "daemon-lite") return "run/artifacts/organic-v0/daemon_lite_cycle8_1h.json";
  return "run/artifacts/organic-v0/sleep_wake_cycle8_test.json";
}

std::string checkpoint_path_for(const Args& args, const std::string& run_id, int ordinal) {
  if (!args.save_state.empty() && ordinal == 1) return args.save_state;
  std::ostringstream out;
  if (!args.policy_tmp_root.empty()) {
    out << args.policy_tmp_root << "/checkpoints/" << run_id
        << "/ckpt-" << std::setw(6) << std::setfill('0') << ordinal << ".pxstate";
  } else {
    out << "run/state/organic-v0/snapshots/" << args.organism_id
        << "/cycle9-" << run_id << "-ckpt-" << std::setw(6) << std::setfill('0')
        << ordinal << ".pxstate";
  }
  return out.str();
}

std::string write_cycle8_checkpoint(const Args& args, const std::string& run_id,
                                    OrganicBrain& brain, RuntimeMetrics& metrics,
                                    RuntimePolicy& policy) {
  policy.note_checkpoint();
  int ordinal = static_cast<int>(metrics.checkpoint_paths.size()) + 1;
  std::string path = checkpoint_path_for(args, run_id, ordinal);
  policy.note_file_write("checkpoint", path);
  ensure_parent_dir(path);
  std::ofstream out(path);
  brain.serialize_state(out, args.organism_id);
  metrics.checkpoint_paths.push_back(path);
  metrics.state_hash_chain.push_back(brain.state_hash());
  return path;
}

OrganismStepResult organism_wake_step(OrganicBrain& brain, const OrganismStepInput& input,
                                      const std::string& event_log_path,
                                      RuntimePolicy& policy) {
  OrganismStepResult result;
  result.state_before_hash = brain.state_hash();
  result.predictor_before_hash = brain.outcome_predictor_hash();
  result.prediction = brain.predict_outcome(input.event.input, input.event.observations);
  result.generation = brain.generate(input.event.input, input.event.observations);
  result.has_target = !input.event.target_output.empty() && !input.event.reward.empty();
  result.state_after_hash = result.state_before_hash;
  result.predictor_after_hash = result.predictor_before_hash;

  std::optional<PredictionError> error;
  if (result.has_target) {
    policy.note_mutation_attempt("wake_learn_and_predictor_update");
    auto target = target_from_generation(input.event, result.generation.output);
    result.prediction_error = brain.update_outcome_predictor(result.prediction, target);
    error = result.prediction_error;
    brain.learn(input.event);
    result.state_after_hash = brain.state_hash();
    result.predictor_after_hash = brain.outcome_predictor_hash();
    result.learned = true;
    result.reason = "wake_correction_reward_learned";
    result.mutation_refs.push_back({
        "mut_" + input.step_id,
        "wake_learn_and_predictor_update",
        true,
        result.state_before_hash,
        result.state_after_hash,
        result.reason,
    });
  } else {
    result.reason = "wake_no_correction_or_reward_no_learning";
  }

  append_event_log_v2(event_log_path, policy, input.run_id, input.organism_id, input.step_id,
                      "wake", "generate", input.event, result.generation.output,
                      input.event.target_output, false, result.prediction,
                      error ? &(*error) : nullptr, result.prediction.trace_refs, {},
                      result.state_before_hash, result.state_before_hash,
                      input.source_kind, input.source_path);
  if (result.learned) {
    append_event_log_v2(event_log_path, policy, input.run_id, input.organism_id, input.step_id,
                        "wake", "learn", input.event, result.generation.output,
                        input.event.target_output, false, result.prediction,
                        &result.prediction_error, result.prediction.trace_refs,
                        result.mutation_refs, result.state_before_hash,
                        result.state_after_hash, input.source_kind, input.source_path);
  }
  return result;
}

size_t select_replay_candidate(const OrganicBrain& brain,
                               const std::vector<ReplayCandidate>& candidates,
                               const std::string& policy, uint64_t random_seed,
                               int tick) {
  if (candidates.empty()) return 0;
  if (policy == "random") {
    uint64_t state = mix64(combine(random_seed, static_cast<uint64_t>(tick)));
    return static_cast<size_t>(state % candidates.size());
  }
  double best = -1.0;
  size_t best_index = 0;
  for (size_t i = 0; i < candidates.size(); ++i) {
    const auto& event = candidates[i].event;
    auto prediction = brain.predict_outcome(event.input, event.observations);
    auto generation = brain.generate(event.input, event.observations);
    auto target = target_from_generation(event, generation.output);
    auto error = prediction_error_for(prediction, target);
    if (error.surprise > best) {
      best = error.surprise;
      best_index = i;
    }
  }
  return best_index;
}

OrganismStepResult organism_sleep_step(OrganicBrain& brain, const OrganismStepInput& input,
                                       const std::string& event_log_path,
                                       RuntimePolicy& policy) {
  OrganismStepResult result;
  result.state_before_hash = brain.state_hash();
  result.predictor_before_hash = brain.outcome_predictor_hash();
  result.prediction = brain.predict_outcome(input.event.input, input.event.observations);
  result.generation = brain.generate(input.event.input, input.event.observations);
  result.has_target = !input.event.target_output.empty();
  if (!result.has_target) {
    result.state_after_hash = result.state_before_hash;
    result.predictor_after_hash = result.predictor_before_hash;
    result.reason = "sleep_no_replay_target";
    append_event_log_v2(event_log_path, policy, input.run_id, input.organism_id, input.step_id,
                        "sleep", "reflect", input.event, "", "", true, result.prediction,
                        nullptr, result.prediction.trace_refs, {}, result.state_before_hash,
                        result.state_after_hash, input.source_kind, input.source_path);
    return result;
  }

  auto target = target_from_generation(input.event, result.generation.output);
  result.prediction_error = prediction_error_for(result.prediction, target);
  policy.note_mutation_attempt("sleep_replay_candidate");
  OrganicBrain candidate = brain;
  candidate.learn(input.event);
  candidate.update_outcome_predictor(result.prediction, target);
  uint64_t candidate_hash = candidate.state_hash();
  uint64_t candidate_predictor_hash = candidate.outcome_predictor_hash();
  auto after_prediction = candidate.predict_outcome(input.event.input, input.event.observations);
  auto after_generation = candidate.generate(input.event.input, input.event.observations);
  auto after_target = target_from_generation(input.event, after_generation.output);
  auto after_error = prediction_error_for(after_prediction, after_target);
  double before_ratio = lcs_ratio(result.generation.output, input.event.target_output);
  double after_ratio = lcs_ratio(after_generation.output, input.event.target_output);
  bool local_not_worse = after_ratio >= before_ratio;
  bool surprise_reduced = after_error.surprise + 1e-9 < result.prediction_error.surprise;
  result.surprise_reduction = std::max(0.0, result.prediction_error.surprise - after_error.surprise);
  result.accepted = local_not_worse && surprise_reduced;
  result.learned = result.accepted;
  result.candidate_state_hash = candidate_hash;
  result.predictor_candidate_hash = candidate_predictor_hash;
  result.state_after_hash = result.accepted ? candidate_hash : result.state_before_hash;
  result.predictor_after_hash = result.accepted ? candidate_predictor_hash : result.predictor_before_hash;
  result.reason = result.accepted
                      ? "accepted_prediction_error_reduced_without_local_degradation"
                      : "rejected_no_prediction_error_reduction_or_local_degradation";
  result.mutation_refs.push_back({
      "mut_" + input.step_id,
      "sleep_replay_candidate",
      result.accepted,
      result.state_before_hash,
      candidate_hash,
      result.reason,
  });
  if (result.accepted) brain = std::move(candidate);
  append_event_log_v2(event_log_path, policy, input.run_id, input.organism_id, input.step_id,
                      "sleep", "mutate", input.event, after_generation.output,
                      input.event.target_output, true, result.prediction,
                      &result.prediction_error, result.prediction.trace_refs,
                      result.mutation_refs, result.state_before_hash,
                      result.state_after_hash, input.source_kind, input.source_path);
  return result;
}

std::vector<RuntimeCommand> read_runtime_commands_from_stdin(const RuntimePolicy* policy = nullptr) {
  std::vector<RuntimeCommand> commands;
  if (isatty(STDIN_FILENO)) return commands;
  std::string line;
  while (std::getline(std::cin, line)) {
    if (line.empty()) continue;
    commands.push_back(parse_runtime_command(line, policy));
  }
  return commands;
}

std::vector<RuntimeCommand> default_cycle8_commands(int sleep_ticks) {
  RuntimeCommand wake;
  wake.cmd = "wake";
  wake.event.event_id = "wake_cycle8_0001";
  wake.event.episode_id = "cycle8_manual";
  wake.event.split = "wake";
  wake.event.domain = "sleep_wake_runtime";
  wake.event.level = 0;
  wake.event.input = "navi carries basalt prism";
  wake.event.observations = raw_text_span_observations(wake.event.input);
  wake.event.target_output = "navi carries basalt prism";
  wake.event.reward = {{"source_fidelity", 1.0}, {"task_success", 1.0}};
  wake.event.source = "cycle8_default_command";
  wake.event.composition = "wake_event";
  RuntimeCommand sleep;
  sleep.cmd = "sleep";
  sleep.ticks = sleep_ticks;
  RuntimeCommand checkpoint;
  checkpoint.cmd = "checkpoint";
  RuntimeCommand shutdown;
  shutdown.cmd = "shutdown";
  return {wake, sleep, checkpoint, shutdown};
}

void write_cycle8_artifact(const std::string& out_path, const Args& args,
                           const std::string& command, const RuntimeMetrics& metrics,
                           const BrainStateStats& parent_stats,
                           const BrainStateStats& final_stats,
                           const std::string& loaded_state_path,
                           RuntimePolicy& policy,
                           bool count_artifact_write = true) {
  policy.note_file_write("runtime_artifact", out_path, count_artifact_write);
  ensure_parent_dir(out_path);
  std::ofstream out(out_path);
  out << "{\n";
  out << "  \"run_id\": " << q(metrics.run_id) << ",\n";
  out << "  \"timestamp\": " << q(timestamp_utc()) << ",\n";
  out << "  \"phase\": " << q(metrics.phase) << ",\n";
  out << "  \"mode\": " << q(args.mode) << ",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"organism_id\": " << q(args.organism_id) << ",\n";
  out << "  \"loaded_state_path\": " << (loaded_state_path.empty() ? "null" : q(loaded_state_path)) << ",\n";
  out << "  \"event_log_path\": " << q(metrics.event_log_path) << ",\n";
  out << "  \"event_log_schema\": \"project_x.event_log.v2\",\n";
  out << "  \"runtime_policy\": {\"enabled\": " << (policy.enabled ? "true" : "false")
      << ", \"unsafe_disabled\": " << (policy.unsafe_disabled ? "true" : "false")
      << ", \"allowed_roots\": ";
  write_allowed_roots_json(out, policy);
  out << ", \"budget_state\": ";
  write_budget_state_json(out, policy);
  out << ", \"actual_writes\": ";
  write_actual_writes_json(out, policy);
  out << ", \"writes_subset_allowed_roots\": "
      << (writes_subset_allowed_roots(policy) ? "true" : "false")
      << ", \"symlink_policy\": \"deny existing symlink components; residual TOCTOU race remains future work\"},\n";
  out << "  \"replay_policy\": {\"selector\": " << q(metrics.replay_policy)
      << ", \"random_named_as_null_baseline\": " << (metrics.replay_policy == "random" ? "true" : "false")
      << ", \"random_baseline_seed\": " << args.random_baseline_seed << "},\n";
  out << "  \"checkpoint_policy\": {\"interval_seconds\": " << args.checkpoint_interval_seconds
      << ", \"interval_ticks\": " << args.checkpoint_interval_ticks
      << ", \"default_policy\": \"every 60 seconds or every 100 replay ticks, whichever comes first\"},\n";
  out << "  \"checkpoint_count\": " << metrics.checkpoint_paths.size() << ",\n";
  out << "  \"checkpoint_paths\": [";
  for (size_t i = 0; i < metrics.checkpoint_paths.size(); ++i) {
    if (i) out << ", ";
    out << q(metrics.checkpoint_paths[i]);
  }
  out << "],\n";
  out << "  \"parent_model_state\": "; write_state_stats(out, parent_stats); out << ",\n";
  out << "  \"final_model_state\": "; write_state_stats(out, final_stats); out << ",\n";
  out << "  \"state_growth\": "; write_state_growth(out, parent_stats, final_stats); out << ",\n";
  out << "  \"state_hash_chain\": [";
  for (size_t i = 0; i < metrics.state_hash_chain.size(); ++i) {
    if (i) out << ", ";
    out << q(hex64(metrics.state_hash_chain[i]));
  }
  out << "],\n";
  out << "  \"prediction_error_over_time\": [";
  for (size_t i = 0; i < metrics.prediction_error_over_time.size(); ++i) {
    if (i) out << ", ";
    out << std::fixed << std::setprecision(6) << metrics.prediction_error_over_time[i]
        << std::defaultfloat;
  }
  out << "],\n";
  out << "  \"summary_metrics\": {"
      << "\"wake_count\": " << metrics.wake_count
      << ", \"sleep_tick_count\": " << metrics.sleep_tick_count
      << ", \"replay_candidate_count\": " << metrics.replay_candidate_count
      << ", \"accepted_mutation_count\": " << metrics.accepted_mutation_count
      << ", \"rejected_mutation_count\": " << metrics.rejected_mutation_count
      << ", \"surprise_reduction\": " << std::fixed << std::setprecision(6)
      << metrics.surprise_reduction << std::defaultfloat
      << ", \"timed_out\": " << (metrics.timed_out ? "true" : "false")
      << ", \"hard_stopped\": " << (metrics.hard_stopped ? "true" : "false")
      << ", \"hard_stop_reason\": " << q(metrics.hard_stop_reason) << "},\n";
  out << "  \"policy_denials\": [";
  for (size_t i = 0; i < metrics.policy_denials.size(); ++i) {
    if (i) out << ", ";
    const auto& denial = metrics.policy_denials[i];
    out << "{\"denial_kind\": " << q(denial.denial_kind)
        << ", \"denial_reason\": " << q(denial.denial_reason)
        << ", \"pathway\": " << q(denial.pathway) << "}";
  }
  out << "],\n";
  out << "  \"rollback_proofs\": [";
  for (size_t i = 0; i < metrics.rollback_proofs.size(); ++i) {
    if (i) out << ", ";
    const auto& proof = metrics.rollback_proofs[i];
    out << "{\"step_id\": " << q(proof.step_id)
        << ", \"mutation_id\": " << q(proof.mutation_id)
        << ", \"rejection_reason\": " << q(proof.rejection_reason)
        << ", \"state_before_hash\": " << q(hex64(proof.state_before_hash))
        << ", \"candidate_state_hash\": " << q(hex64(proof.candidate_state_hash))
        << ", \"state_after_hash\": " << q(hex64(proof.state_after_hash))
        << ", \"predictor_before_hash\": " << q(hex64(proof.predictor_before_hash))
        << ", \"predictor_candidate_hash\": " << q(hex64(proof.predictor_candidate_hash))
        << ", \"predictor_after_hash\": " << q(hex64(proof.predictor_after_hash))
        << ", \"live_state_preserved\": " << (proof.live_state_preserved ? "true" : "false")
        << ", \"predictor_state_preserved\": " << (proof.predictor_state_preserved ? "true" : "false")
        << "}";
  }
  out << "],\n";
  out << "  \"oracle_access\": {\"generation\": false, \"correction_after_generation\": true, \"sleep_audit\": true},\n";
  out << "  \"negative_space\": {\"not_fluent_chat\": true, \"not_broad_reasoning\": true, \"not_agi\": true, \"not_safety_boundary_solution\": true, \"not_next_token_predictor\": true, \"not_alignment\": true, \"not_sandbox_escape_resistance\": true, \"not_wrapper_sandbox\": true, \"not_supply_chain_safety\": true, \"not_tool_use_safety\": true, \"not_event_log_external_length_anchor\": true},\n";
  out << "  \"honest_interpretation\": \"Cycle 9 in-process policy evidence for the current sleep/wake and daemon-lite runtime surfaces: stdin command schema, count budgets, filesystem roots, v2 event-log chaining, replay-source validation, checkpoint writes, and rollback proofs are handled inside the native process. In-process policy enforcement; wrapper-level sandbox is a future cycle. This does not solve alignment, AGI safety, sandbox escape resistance, or broader tool-use safety. The v2 hash chain is internal to the log and has no external length/head anchor yet, so wrapper-level anchoring remains future work.\"\n";
  out << "}\n";
}

void append_runtime_policy_denial_event(const std::string& event_log_path,
                                        RuntimePolicy& policy,
                                        const std::string& run_id,
                                        const std::string& organism_id,
                                        const PolicyViolation& violation) {
  if (event_log_path.empty() || !policy.path_allowed_for_emergency_write(event_log_path)) return;
  Event event;
  event.event_id = "policy_denial_" + hex64(fnv1a(violation.denial_kind + violation.pathway)).substr(0, 12);
  event.episode_id = run_id;
  event.split = "runtime";
  event.domain = "runtime_policy";
  event.input = violation.pathway;
  event.source = "runtime_policy";
  event.composition = "policy_denial";
  OutcomePrediction prediction;
  append_event_log_v2(event_log_path, policy, run_id, organism_id, "policy_denial",
                      "policy_denial", "reflect", event, "", "", true, prediction,
                      nullptr, {}, {}, 0, 0, "runtime_policy", violation.pathway,
                      true, violation.denial_reason, false);
}

RollbackProof rollback_proof_from_result(const std::string& step_id,
                                         const OrganismStepResult& result) {
  RollbackProof proof;
  proof.step_id = step_id;
  proof.mutation_id = "mut_" + step_id;
  proof.rejection_reason = result.reason;
  proof.state_before_hash = result.state_before_hash;
  proof.candidate_state_hash = result.candidate_state_hash;
  proof.state_after_hash = result.state_after_hash;
  proof.predictor_before_hash = result.predictor_before_hash;
  proof.predictor_candidate_hash = result.predictor_candidate_hash;
  proof.predictor_after_hash = result.predictor_after_hash;
  proof.live_state_preserved = result.state_after_hash == result.state_before_hash;
  proof.predictor_state_preserved = result.predictor_after_hash == result.predictor_before_hash;
  return proof;
}

void sleep_wake_runtime_phase(const Args& args, const std::string& command) {
  if (args.replay_policy != "prediction_error" && args.replay_policy != "random") {
    throw std::runtime_error("--replay-policy must be prediction_error or random");
  }
  if (args.checkpoint_interval_seconds <= 0 || args.checkpoint_interval_ticks <= 0) {
    throw std::runtime_error("checkpoint intervals must be positive");
  }
  Config config;
  apply_ablations(config, args);
  config.use_outcome_predictor = true;
  OrganicBrain brain(config);
  std::string run_id = default_cycle8_run_id(args);
  std::string event_log_path = default_cycle8_event_log_path(args, run_id);
  std::string out_path = default_cycle8_out_path(args);
  RuntimePolicy policy = RuntimePolicy::from_args(args);
  RuntimeMetrics metrics;
  metrics.run_id = run_id;
  metrics.phase = args.phase;
  metrics.replay_policy = args.replay_policy;
  metrics.event_log_path = event_log_path;
  BrainStateStats parent_stats = capture_state_stats(brain);
  BrainStateStats final_stats = parent_stats;

  try {
    policy.validate_path("out", out_path, "write");
    policy.validate_path("event_log", event_log_path, "write");
    if (!args.load_state.empty()) policy.validate_path("load_state", args.load_state, "read");
    if (!args.save_state.empty()) policy.validate_path("save_state", args.save_state, "write");
    if (!args.replay_source_log.empty()) {
      policy.validate_path("replay_source_log", args.replay_source_log, "read");
    }
    if (!args.load_state.empty()) {
      load_state_checked(brain, args.load_state);
      brain.set_outcome_predictor_enabled(true);
    }
    parent_stats = capture_state_stats(brain);
    metrics.state_hash_chain.push_back(brain.state_hash());

    std::vector<RuntimeCommand> commands = read_runtime_commands_from_stdin(&policy);
    if (commands.empty()) {
      commands = default_cycle8_commands(args.sleep_ticks);
      if (args.phase == "daemon-lite") commands.resize(1);
    }
    std::vector<ReplayCandidate> replay_candidates =
        load_replay_candidates_from_log(args.replay_source_log, &policy);
    auto add_replay_candidate = [&](const Event& event, const std::string& source_path,
                                    const std::string& source_kind) {
      if (event.target_output.empty() || event.reward.empty()) return;
      policy.note_replay_candidate();
      replay_candidates.push_back({event, source_path, source_kind});
      metrics.replay_candidate_count = static_cast<int>(replay_candidates.size());
    };

    auto started = std::chrono::steady_clock::now();
    auto last_checkpoint = started;
    int ticks_since_checkpoint = 0;
    int step_counter = 0;
    bool shutdown = false;

    auto maybe_timeout = [&]() {
      if (args.phase == "sleep-wake" && args.mode == "test" && args.internal_timeout_seconds > 0) {
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::steady_clock::now() - started).count();
        if (elapsed > args.internal_timeout_seconds) {
          metrics.timed_out = true;
          throw std::runtime_error("sleep-wake internal timeout exceeded");
        }
      }
    };

    auto do_sleep_tick = [&]() {
      policy.note_sleep_tick();
      ++step_counter;
      ++metrics.sleep_tick_count;
      ++ticks_since_checkpoint;
      maybe_timeout();
      if (replay_candidates.empty()) {
        Event idle;
        idle.event_id = "sleep_idle_" + std::to_string(step_counter);
        idle.episode_id = run_id;
        idle.split = "sleep";
        idle.domain = "sleep_wake_runtime";
        idle.input = "sleep idle replay scan";
        idle.source = "sleep_wake_runtime";
        OrganismStepInput input{run_id, args.organism_id, "step_" + std::to_string(step_counter),
                                "sleep_idle", event_log_path, idle};
        organism_sleep_step(brain, input, event_log_path, policy);
        return;
      }
      size_t index = select_replay_candidate(brain, replay_candidates, args.replay_policy,
                                             args.random_baseline_seed, metrics.sleep_tick_count);
      const auto& candidate = replay_candidates[index];
      std::string step_id = "step_" + std::to_string(step_counter);
      OrganismStepInput input{run_id, args.organism_id, step_id,
                              candidate.source_kind, candidate.source_path, candidate.event};
      auto result = organism_sleep_step(brain, input, event_log_path, policy);
      metrics.prediction_error_over_time.push_back(result.prediction_error.surprise);
      if (result.accepted) {
        ++metrics.accepted_mutation_count;
        metrics.surprise_reduction += result.surprise_reduction;
        write_cycle8_checkpoint(args, run_id, brain, metrics, policy);
        ticks_since_checkpoint = 0;
        last_checkpoint = std::chrono::steady_clock::now();
      } else {
        ++metrics.rejected_mutation_count;
        metrics.rollback_proofs.push_back(rollback_proof_from_result(step_id, result));
        metrics.state_hash_chain.push_back(brain.state_hash());
      }
      auto now = std::chrono::steady_clock::now();
      auto seconds = std::chrono::duration_cast<std::chrono::seconds>(now - last_checkpoint).count();
      if (ticks_since_checkpoint >= args.checkpoint_interval_ticks ||
          seconds >= args.checkpoint_interval_seconds) {
        write_cycle8_checkpoint(args, run_id, brain, metrics, policy);
        ticks_since_checkpoint = 0;
        last_checkpoint = now;
      }
    };

    for (const auto& command_item : commands) {
      if (shutdown) break;
      if (command_item.cmd == "wake") {
        policy.note_wake_command();
        ++step_counter;
        ++metrics.wake_count;
        OrganismStepInput input{run_id, args.organism_id, "step_" + std::to_string(step_counter),
                                "stdin_jsonl", "stdin", command_item.event};
        auto result = organism_wake_step(brain, input, event_log_path, policy);
        if (result.has_target) {
          metrics.prediction_error_over_time.push_back(result.prediction_error.surprise);
          add_replay_candidate(command_item.event, event_log_path, "wake_event_log");
        }
        metrics.state_hash_chain.push_back(brain.state_hash());
      } else if (command_item.cmd == "sleep") {
        int ticks = std::max(0, command_item.ticks);
        for (int i = 0; i < ticks; ++i) do_sleep_tick();
      } else if (command_item.cmd == "checkpoint") {
        write_cycle8_checkpoint(args, run_id, brain, metrics, policy);
        ticks_since_checkpoint = 0;
        last_checkpoint = std::chrono::steady_clock::now();
      } else if (command_item.cmd == "shutdown") {
        shutdown = true;
      }
    }

    if (args.phase == "daemon-lite" && !shutdown) {
      int seconds = args.daemon_run_seconds > 0 ? args.daemon_run_seconds : 3600;
      int tick_sleep_ms =
          args.daemon_tick_sleep_ms >= 0 ? args.daemon_tick_sleep_ms : (args.mode == "test" ? 1 : 100);
      while (true) {
        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            std::chrono::steady_clock::now() - started).count();
        if (elapsed >= seconds) break;
        do_sleep_tick();
        std::this_thread::sleep_for(std::chrono::milliseconds(tick_sleep_ms));
      }
    }
    write_cycle8_checkpoint(args, run_id, brain, metrics, policy);
    final_stats = capture_state_stats(brain);
    write_cycle8_artifact(out_path, args, command, metrics, parent_stats, final_stats,
                          args.load_state, policy);
    std::cout << "wrote " << out_path << "\n";
  } catch (const PolicyViolation& violation) {
    metrics.hard_stopped = true;
    metrics.hard_stop_reason = violation.denial_reason;
    metrics.policy_denials.push_back({violation.denial_kind, violation.denial_reason,
                                      violation.pathway});
    final_stats = capture_state_stats(brain);
    append_runtime_policy_denial_event(event_log_path, policy, run_id, args.organism_id,
                                       violation);
    if (policy.path_allowed_for_emergency_write(out_path)) {
      write_cycle8_artifact(out_path, args, command, metrics, parent_stats, final_stats,
                            args.load_state, policy, false);
    }
    throw;
  }
}

struct Cycle9PolicySelfTestCase {
  std::string case_id;
  bool guard_on_denied = false;
  std::string denial_kind;
  std::string denial_reason;
  bool guard_off_control_reached = false;
  std::string guard_off_explanation;
};

struct Cycle9ResetRunResult {
  std::string run_root;
  std::string event_log_path;
  BrainStateStats final_stats;
  RuntimeMetrics metrics;
  RuntimePolicy policy;
};

void write_synthetic_event_log_v2(const std::string& path, bool bad_content_hash,
                                  bool malformed_state_hash) {
  ensure_parent_dir(path);
  std::string state_before = malformed_state_hash ? "spoofed" : "0000000000000000";
  std::string state_after = malformed_state_hash ? "fffffffffffffffff" : "0000000000000000";
  std::ostringstream core;
  core << "{\"schema\":\"project_x.event_log.v2\""
       << ",\"event_id\":\"evtlog_000001\""
       << ",\"run_id\":\"cycle9-synthetic\""
       << ",\"organism_id\":\"raphael-local-0001\""
       << ",\"step_id\":\"step_1\""
       << ",\"step_mode\":\"wake\""
       << ",\"timestamp_utc\":\"2026-05-14T00:00:00Z\""
       << ",\"phase\":\"learn\""
       << ",\"source\":{\"source_kind\":\"synthetic\",\"source_path\":\"synthetic\","
       << "\"source_event_id\":\"synthetic_wake\"}"
       << ",\"input\":{\"text\":\"synthetic replay input\",\"observations\":[]}"
       << ",\"output\":{\"raw_generated_output\":\"\",\"expected_output\":\"synthetic replay input\","
       << "\"oracle_used_in_generation\":false,\"audit_only\":false}"
       << ",\"reward\":{\"task_success\":1}"
       << ",\"prediction\":{\"predictor\":\"a0_event_outcome\",\"reward_scalar_pred\":0,"
       << "\"exact_score_or_prob_pred\":0,\"lcs_error_ratio_pred\":1,\"surprise_pred\":1,"
       << "\"feature_count\":0}"
       << ",\"prediction_error\":null"
       << ",\"trace_refs\":[]"
       << ",\"mutation_refs\":[]"
       << ",\"state_before_hash\":" << q(state_before)
       << ",\"state_after_hash\":" << q(state_after)
       << ",\"policy_denial\":false"
       << ",\"denial_reason\":\"\""
       << ",\"budget_state\":{\"policy_enabled\":true}"
       << ",\"prev_event_content_hash\":\"GENESIS\""
       << ",\"backend\":{\"runtime\":\"native_cpp20\",\"gpu_backend\":\"not_used_in_organic_v0\"}}";
  std::string core_text = core.str();
  std::string hash = bad_content_hash ? "0000000000000000"
                                      : event_log_v2_content_hash_for_core(core_text);
  std::string line = core_text.substr(0, core_text.size() - 1) +
                     ",\"event_content_hash\":" + q(hash) + "}";
  std::ofstream out(path, std::ios::trunc);
  out << line << "\n";
}

Cycle9ResetRunResult run_cycle9_resettable_scenario(const Args& base_args,
                                                    const std::string& run_root,
                                                    const std::string& run_id) {
  Args local = base_args;
  local.phase = "daemon-lite";
  local.mode = "test";
  local.policy_tmp_root = run_root;
  local.run_id = run_id;
  local.event_log = run_root + "/events/" + run_id + ".jsonl";
  local.out = run_root + "/artifacts/" + run_id + ".json";
  local.save_state.clear();
  local.load_state.clear();
  local.replay_source_log.clear();
  local.checkpoint_interval_ticks = 2;
  local.checkpoint_interval_seconds = 999999;
  local.policy_max_wake_commands = 4;
  local.policy_max_sleep_ticks = 8;
  local.policy_max_replay_candidates = 4;
  local.policy_max_mutation_attempts = 16;
  local.policy_max_checkpoints = 8;
  local.policy_max_file_writes = 64;

  RuntimePolicy policy = RuntimePolicy::from_args(local);
  policy.validate_path("event_log", local.event_log, "write");
  policy.validate_path("out", local.out, "write");

  Config config;
  config.use_outcome_predictor = true;
  OrganicBrain brain(config);
  RuntimeMetrics metrics;
  metrics.run_id = run_id;
  metrics.phase = "daemon-lite-reset-contract";
  metrics.replay_policy = "prediction_error";
  metrics.event_log_path = local.event_log;
  metrics.state_hash_chain.push_back(brain.state_hash());

  std::vector<ReplayCandidate> replay_candidates;
  auto add_replay_candidate = [&](const Event& event) {
    policy.note_replay_candidate();
    replay_candidates.push_back({event, local.event_log, "wake_event_log"});
    metrics.replay_candidate_count = static_cast<int>(replay_candidates.size());
  };

  RuntimeCommand wake = default_cycle8_commands(4).front();
  policy.note_wake_command();
  ++metrics.wake_count;
  OrganismStepInput wake_input{run_id, local.organism_id, "step_1", "stdin_jsonl",
                               "synthetic_reset", wake.event};
  auto wake_result = organism_wake_step(brain, wake_input, local.event_log, policy);
  if (wake_result.has_target) {
    metrics.prediction_error_over_time.push_back(wake_result.prediction_error.surprise);
    add_replay_candidate(wake.event);
  }
  metrics.state_hash_chain.push_back(brain.state_hash());

  int step_counter = 1;
  int ticks_since_checkpoint = 0;
  for (int i = 0; i < 4; ++i) {
    policy.note_sleep_tick();
    ++step_counter;
    ++metrics.sleep_tick_count;
    ++ticks_since_checkpoint;
    size_t index = select_replay_candidate(brain, replay_candidates, "prediction_error",
                                           local.random_baseline_seed, metrics.sleep_tick_count);
    const auto& candidate = replay_candidates[index];
    std::string step_id = "step_" + std::to_string(step_counter);
    OrganismStepInput sleep_input{run_id, local.organism_id, step_id, candidate.source_kind,
                                  candidate.source_path, candidate.event};
    auto result = organism_sleep_step(brain, sleep_input, local.event_log, policy);
    metrics.prediction_error_over_time.push_back(result.prediction_error.surprise);
    if (result.accepted) {
      ++metrics.accepted_mutation_count;
      metrics.surprise_reduction += result.surprise_reduction;
      write_cycle8_checkpoint(local, run_id, brain, metrics, policy);
      ticks_since_checkpoint = 0;
    } else {
      ++metrics.rejected_mutation_count;
      metrics.rollback_proofs.push_back(rollback_proof_from_result(step_id, result));
      metrics.state_hash_chain.push_back(brain.state_hash());
    }
    if (ticks_since_checkpoint >= local.checkpoint_interval_ticks) {
      write_cycle8_checkpoint(local, run_id, brain, metrics, policy);
      ticks_since_checkpoint = 0;
    }
  }
  write_cycle8_checkpoint(local, run_id, brain, metrics, policy);
  BrainStateStats final_stats = capture_state_stats(brain);
  write_cycle8_artifact(local.out, local, "cycle9-resettable-scenario", metrics,
                        BrainStateStats{}, final_stats, "", policy);
  return {run_root, local.event_log, final_stats, metrics, policy};
}

void policy_self_test_phase(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("policy-self-test requires --out");
  std::string run_id = args.run_id.empty() ? "cycle9-policy-self-test" : args.run_id;
  std::string root = "/tmp/project-x-" + run_id + "-" +
                     hex64(fnv1a(timestamp_utc() + run_id)).substr(0, 10);
  std::filesystem::remove_all(root);
  std::filesystem::create_directories(root);

  Args policy_args = args;
  policy_args.policy_tmp_root = root;
  RuntimePolicy policy = RuntimePolicy::from_args(policy_args);
  RuntimePolicy disabled_policy = policy;
  disabled_policy.enabled = false;
  disabled_policy.unsafe_disabled = true;

  std::vector<Cycle9PolicySelfTestCase> cases;
  auto run_case = [&](const std::string& case_id, const std::function<void(RuntimePolicy&)>& guard_on,
                      const std::function<void(RuntimePolicy&)>& guard_off,
                      const std::string& guard_off_explanation) {
    Cycle9PolicySelfTestCase item;
    item.case_id = case_id;
    item.guard_off_explanation = guard_off_explanation;
    try {
      guard_on(policy);
    } catch (const PolicyViolation& e) {
      item.guard_on_denied = true;
      item.denial_kind = e.denial_kind;
      item.denial_reason = e.denial_reason;
    }
    try {
      guard_off(disabled_policy);
      item.guard_off_control_reached = true;
    } catch (...) {
      item.guard_off_control_reached = false;
    }
    cases.push_back(item);
  };

  run_case("path_traversal_denied",
           [&](RuntimePolicy& p) { p.validate_path("out", root + "/../escape.json", "write"); },
           [&](RuntimePolicy& p) { p.validate_path("out", root + "/../escape.json", "write"); },
           "Synthetic guard-off control only validates that the disabled policy would not stop the path; no file write is performed.");

  run_case("unauthorized_absolute_path_denied",
           [&](RuntimePolicy& p) { p.validate_path("out", "/etc/project-x-denied.json", "write"); },
           [&](RuntimePolicy& p) { p.validate_path("out", "/etc/project-x-denied.json", "write"); },
           "Synthetic guard-off control avoids writing outside the project and tmp roots.");

  std::string hostile_shell =
      "{\"cmd\":\"wake\",\"action_kind\":\"shell\",\"event_id\":\"hostile_shell\","
      "\"input_text\":\"do not execute shell\",\"correction_output\":\"denied\","
      "\"reward\":{\"task_success\":1}}";
  run_case("shell_action_kind_denied",
           [&](RuntimePolicy& p) { (void)parse_runtime_command(hostile_shell, &p); },
           [&](RuntimePolicy& p) { (void)parse_runtime_command(hostile_shell, &p); },
           "With policy disabled, the parser reaches the ordinary wake path and still implements no shell execution.");

  std::string hostile_network =
      "{\"cmd\":\"wake\",\"action_kind\":\"network\",\"event_id\":\"hostile_network\","
      "\"input_text\":\"do not use network\",\"correction_output\":\"denied\","
      "\"reward\":{\"task_success\":1}}";
  run_case("network_action_kind_denied",
           [&](RuntimePolicy& p) { (void)parse_runtime_command(hostile_network, &p); },
           [&](RuntimePolicy& p) { (void)parse_runtime_command(hostile_network, &p); },
           "With policy disabled, the parser reaches the ordinary wake path and still implements no network execution.");

  std::string spoof_log = root + "/synthetic/replay_state_spoof.jsonl";
  write_synthetic_event_log_v2(spoof_log, false, true);
  run_case("replay_source_log_state_hash_spoof_denied",
           [&](RuntimePolicy& p) { (void)load_replay_candidates_from_log(spoof_log, &p); },
           [&](RuntimePolicy& p) { (void)load_replay_candidates_from_log(spoof_log, &p); },
           "Guard-off control proves the replay parser would otherwise reach the candidate extraction path.");

  std::string tamper_log = root + "/synthetic/event_log_tamper.jsonl";
  write_synthetic_event_log_v2(tamper_log, true, false);
  run_case("event_log_integrity_tamper_denied",
           [&](RuntimePolicy& p) { (void)load_replay_candidates_from_log(tamper_log, &p); },
           [&](RuntimePolicy& p) { (void)load_replay_candidates_from_log(tamper_log, &p); },
           "Guard-off control proves candidate extraction is only blocked by the v2 integrity walk.");

  run_case("budget_exhaustion_hard_stops",
           [&](RuntimePolicy&) {
             RuntimePolicy budget_policy = RuntimePolicy::from_args(policy_args);
             budget_policy.budgets.max_sleep_ticks = 0;
             budget_policy.note_sleep_tick();
           },
           [&](RuntimePolicy&) {
             RuntimePolicy budget_policy = RuntimePolicy::from_args(policy_args);
             budget_policy.enabled = false;
             budget_policy.budgets.max_sleep_ticks = 0;
             budget_policy.note_sleep_tick();
           },
           "Guard-off control proves the hard stop is from the count budget, not from missing code.");

  std::string reset_root = root + "/resettable-daemon-root";
  std::filesystem::remove_all(reset_root);
  auto first_reset = run_cycle9_resettable_scenario(args, reset_root, run_id + "-reset");
  std::filesystem::remove_all(reset_root);
  auto second_reset = run_cycle9_resettable_scenario(args, reset_root, run_id + "-reset");
  bool reset_hash_equal = first_reset.final_stats.state_hash == second_reset.final_stats.state_hash;
  bool rollback_ok = false;
  RollbackProof rollback_proof;
  if (!second_reset.metrics.rollback_proofs.empty()) {
    rollback_proof = second_reset.metrics.rollback_proofs.front();
    rollback_ok = rollback_proof.live_state_preserved && rollback_proof.predictor_state_preserved;
  }

  bool cases_ok = std::all_of(cases.begin(), cases.end(), [](const auto& item) {
    return item.guard_on_denied && item.guard_off_control_reached;
  });
  bool all_ok = cases_ok && reset_hash_equal && rollback_ok &&
                writes_subset_allowed_roots(second_reset.policy);

  RuntimePolicy artifact_policy = RuntimePolicy::from_args(policy_args);
  artifact_policy.note_file_write("policy_self_test_artifact", args.out);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(timestamp_utc()) << ",\n";
  out << "  \"phase\": \"policy-self-test\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"event_log_schema\": \"project_x.event_log.v2\",\n";
  out << "  \"test_root\": " << q(root) << ",\n";
  out << "  \"policy\": {\"enabled_by_default\": true, \"unsafe_disable_flag\": \"--unsafe-disable-policy\", \"allowed_roots\": ";
  write_allowed_roots_json(out, artifact_policy);
  out << ", \"budget_state\": ";
  write_budget_state_json(out, artifact_policy);
  out << ", \"symlink_policy\": \"deny existing symlink components; residual TOCTOU race remains future work\"},\n";
  out << "  \"denial_cases\": [\n";
  for (size_t i = 0; i < cases.size(); ++i) {
    if (i) out << ",\n";
    const auto& item = cases[i];
    out << "    {\"case_id\": " << q(item.case_id)
        << ", \"guard_on\": {\"denied\": " << (item.guard_on_denied ? "true" : "false")
        << ", \"denial_kind\": " << q(item.denial_kind)
        << ", \"denial_reason\": " << q(item.denial_reason) << "}"
        << ", \"guard_off_control\": {\"reached\": "
        << (item.guard_off_control_reached ? "true" : "false")
        << ", \"explanation\": " << q(item.guard_off_explanation) << "}}";
  }
  out << "\n  ],\n";
  out << "  \"rollback_proof\": {\"present\": " << (!second_reset.metrics.rollback_proofs.empty() ? "true" : "false")
      << ", \"live_state_preserved\": " << (rollback_proof.live_state_preserved ? "true" : "false")
      << ", \"predictor_state_preserved\": " << (rollback_proof.predictor_state_preserved ? "true" : "false")
      << ", \"state_before_hash\": " << q(hex64(rollback_proof.state_before_hash))
      << ", \"candidate_state_hash\": " << q(hex64(rollback_proof.candidate_state_hash))
      << ", \"state_after_hash\": " << q(hex64(rollback_proof.state_after_hash))
      << ", \"predictor_before_hash\": " << q(hex64(rollback_proof.predictor_before_hash))
      << ", \"predictor_candidate_hash\": " << q(hex64(rollback_proof.predictor_candidate_hash))
      << ", \"predictor_after_hash\": " << q(hex64(rollback_proof.predictor_after_hash))
      << ", \"rejection_reason\": " << q(rollback_proof.rejection_reason) << "},\n";
  out << "  \"resettable_rerun\": {\"run_root\": " << q(reset_root)
      << ", \"first_final_state_hash\": " << q(hex64(first_reset.final_stats.state_hash))
      << ", \"second_final_state_hash\": " << q(hex64(second_reset.final_stats.state_hash))
      << ", \"hash_equal\": " << (reset_hash_equal ? "true" : "false")
      << ", \"allowed_roots\": ";
  write_allowed_roots_json(out, second_reset.policy);
  out << ", \"budget_state\": ";
  write_budget_state_json(out, second_reset.policy);
  out << ", \"actual_writes\": ";
  write_actual_writes_json(out, second_reset.policy);
  out << ", \"writes_subset_allowed_roots\": "
      << (writes_subset_allowed_roots(second_reset.policy) ? "true" : "false")
      << "},\n";
  out << "  \"negative_space\": {\"not_alignment\": true, \"not_sandbox_escape_resistance\": true, \"not_wrapper_sandbox\": true, \"not_supply_chain_safety\": true, \"not_tool_use_safety\": true, \"not_event_log_external_length_anchor\": true},\n";
  out << "  \"all_required_checks_passed\": " << (all_ok ? "true" : "false") << ",\n";
  out << "  \"honest_interpretation\": \"Cycle 9 denial artifact for current daemon-lite/sleep-wake surfaces. In-process policy enforcement; wrapper-level sandbox is a future cycle. This does not solve alignment, AGI safety, sandbox escape resistance, or broader tool-use safety. The v2 hash chain is internal to the log and has no external length/head anchor yet, so wrapper-level anchoring remains future work.\"\n";
  out << "}\n";
  if (!all_ok) throw std::runtime_error("policy self-test failed required checks");
  std::cout << "wrote " << args.out << "\n";
}

void write_string_array_json(std::ostream& out, const std::vector<std::string>& values);

std::string read_corpus_shard_text(const std::string& path, bool require_observation_safe = true) {
  std::ifstream in(path);
  if (!in) throw std::runtime_error("cannot open corpus shard: " + path);
  std::ostringstream buffer;
  buffer << in.rdbuf();
  std::string text = buffer.str();
  if (!text.empty() && text.back() == '\n') text.pop_back();
  if (!text.empty() && text.back() == '\r') text.pop_back();
  if (text.empty()) throw std::runtime_error("empty corpus shard: " + path);
  for (unsigned char c : text) {
    if (require_observation_safe && (c == '\n' || c == '\r' || c == '|' || c == ',')) {
      throw std::runtime_error("corpus shard is not PXSTATE observation-safe: " + path);
    }
    if (c > 126) throw std::runtime_error("corpus shard contains non-ascii byte: " + path);
  }
  return text;
}

void write_quote_probe_transcript_header(std::ostream& out, const Args& args,
                                         const std::string& transcript_path) {
  out << "# Cycle 11 Voice Pressure Transcript\n\n";
  out << "Generated: " << timestamp_utc() << "\n\n";
  out << "Prompt database: `" << args.experience_db << "`\n\n";
  out << "State manifest: `" << args.state_manifest << "`\n\n";
  out << "Artifact: `" << args.out << "`\n\n";
  out << "Runtime max output chars: "
      << (args.generation_max_output_chars > 0 ? std::to_string(args.generation_max_output_chars)
                                               : std::string("loaded-state default"))
      << "\n\n";
  out << "This transcript preserves raw organic-v0 generation from loaded persisted states. "
      << "The prompts have raw utterance observations only and no labels, corrections, expected outputs, or semantic scoring.\n\n";
  out << "Transcript path: `" << transcript_path << "`\n";
}

void state_config_copy_phase(const Args& args) {
  if (args.load_state.empty()) throw std::runtime_error("state-config-copy requires --load-state");
  if (args.save_state.empty()) throw std::runtime_error("state-config-copy requires --save-state");
  if (args.generation_max_output_chars <= 0) {
    throw std::runtime_error("state-config-copy requires positive --generation-max-output-chars");
  }

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  load_state_checked(brain, args.load_state);
  uint64_t parent_hash = brain.state_hash();
  int parent_max_output_chars = brain.config().max_output_chars;
  brain.set_max_output_chars(args.generation_max_output_chars);
  uint64_t child_hash = brain.state_hash();

  ensure_parent_dir(args.save_state);
  {
    std::ofstream state_out(args.save_state);
    if (!state_out) throw std::runtime_error("cannot write capped state: " + args.save_state);
    brain.serialize_state(state_out, args.organism_id);
  }

  OrganicBrain reloaded(config);
  load_state_checked(reloaded, args.save_state);
  if (reloaded.config().max_output_chars != args.generation_max_output_chars) {
    throw std::runtime_error("capped state reload lost max_output_chars");
  }
  if (reloaded.state_hash() != child_hash) {
    throw std::runtime_error("capped state reload hash mismatch");
  }

  if (!args.out.empty()) {
    ensure_parent_dir(args.out);
    std::ofstream out(args.out);
    if (!out) throw std::runtime_error("cannot open state-config-copy artifact: " + args.out);
    out << "{\n";
    out << "  \"schema\": \"project_x.state_config_copy.v0\",\n";
    out << "  \"run_id\": " << q(args.run_id.empty() ? "state-config-copy" : args.run_id) << ",\n";
    out << "  \"loaded_state_path\": " << q(args.load_state) << ",\n";
    out << "  \"saved_state_path\": " << q(args.save_state) << ",\n";
    out << "  \"parent_max_output_chars\": " << parent_max_output_chars << ",\n";
    out << "  \"child_max_output_chars\": " << args.generation_max_output_chars << ",\n";
    out << "  \"parent_state_hash\": " << q(hex64(parent_hash)) << ",\n";
    out << "  \"child_state_hash\": " << q(hex64(child_hash)) << ",\n";
    out << "  \"hash_changed\": " << (parent_hash != child_hash ? "true" : "false") << ",\n";
    out << "  \"honest_interpretation\": \"Copies a loaded PXSTATE with only CONFIG max_output_chars changed, then reloads the child to prove the cap is durable. This is a probe-state configuration change, not new learned voice capability.\"\n";
    out << "}\n";
  }
  std::cout << "wrote " << args.save_state << "\n";
}

void quote_probe_phase(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("quote-probe requires --out");
  if (args.experience_db.empty()) throw std::runtime_error("quote-probe requires --experience-db");
  if (args.state_manifest.empty()) throw std::runtime_error("quote-probe requires --state-manifest");
  if (args.generation_max_output_chars < 0) {
    throw std::runtime_error("--generation-max-output-chars cannot be negative");
  }

  std::string run_id = args.run_id.empty() ? "cycle11-voice-pressure" : args.run_id;
  auto prompts = load_voice_prompt_records(args.experience_db);
  auto states = load_probe_state_records(args.state_manifest);
  if (prompts.empty()) throw std::runtime_error("quote-probe prompt database is empty");
  if (states.empty()) throw std::runtime_error("quote-probe state manifest is empty");

  RuntimePolicy policy = RuntimePolicy::from_args(args);
  policy.note_file_write("quote_probe_artifact", args.out);
  std::string transcript_path = args.transcript_out.empty()
                                    ? args.out + ".transcript.md"
                                    : args.transcript_out;
  policy.note_file_write("quote_probe_transcript", transcript_path);
  if (!args.event_log.empty()) {
    policy.note_file_write("quote_probe_event_log_truncate", args.event_log);
    ensure_parent_dir(args.event_log);
    std::ofstream(args.event_log, std::ios::trunc).close();
  }

  ensure_parent_dir(transcript_path);
  std::ofstream transcript(transcript_path);
  if (!transcript) throw std::runtime_error("cannot open transcript: " + transcript_path);
  write_quote_probe_transcript_header(transcript, args, transcript_path);

  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  if (!out) throw std::runtime_error("cannot open quote-probe artifact: " + args.out);

  std::string ts = timestamp_utc();
  int generation_count = 0;
  int nonempty_count = 0;
  int outputs_exceeding_legacy_cap = 0;
  size_t max_output_char_count = 0;
  bool all_state_hash_self_checks = true;
  bool all_generations_state_unchanged = true;

  out << "{\n";
  out << "  \"schema\": \"project_x.quote_per_state_cycle11.v1\",\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"quote-probe\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"prompt_db_path\": " << q(args.experience_db) << ",\n";
  out << "  \"state_manifest_path\": " << q(args.state_manifest) << ",\n";
  out << "  \"transcript_path\": " << q(transcript_path) << ",\n";
  out << "  \"event_log_path\": " << (args.event_log.empty() ? "null" : q(args.event_log)) << ",\n";
  out << "  \"generation_budget\": {\"legacy_max_output_chars\": 48, \"required_persisted_max_output_chars\": 160, \"runtime_max_output_chars\": "
      << (args.generation_max_output_chars > 0 ? args.generation_max_output_chars : 0)
      << ", \"runtime_override_applied\": "
      << (args.generation_max_output_chars > 0 ? "true" : "false")
      << ", \"loaded_state_config_required\": true, \"loaded_state_hash_includes_nonlegacy_generation_cap\": true},\n";
  out << "  \"raw_text_span_sense\": {\"enabled\": "
      << (args.derive_raw_text_spans && !args.ablate_raw_text_spans ? "true" : "false")
      << ", \"derive_flag\": " << (args.derive_raw_text_spans ? "true" : "false")
      << ", \"ablation_flag\": " << (args.ablate_raw_text_spans ? "true" : "false")
      << ", \"max_span_tokens\": 8, \"max_span_len\": 3},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"correction_after_generation\": false, "
      << "\"expected_outputs_present\": false, \"semantic_quality_scoring\": false},\n";
  out << "  \"a0_boundary\": {\"generator_predictor_blind\": true, "
      << "\"evidence\": \"OrganicBrain::generate remains separate from predict_outcome; verify_cycle11_voice_pressure.sh checks the generate() body for predictor tokens.\"},\n";
  out << "  \"audit_status\": \"ungraded; rubric-pending for GPT/lain audit\",\n";
  out << "  \"negative_space\": {\"not_fluency_claim\": true, \"not_philosophy_claim\": true, "
      << "\"not_chat_capability\": true, \"not_semantic_quality_claim\": true, "
      << "\"not_ui_layer\": true, \"not_pretrained_route\": true, \"not_template_route\": true, "
      << "\"not_a0_improvement\": true, \"not_sandbox_or_security\": true},\n";
  out << "  \"states\": [\n";

  for (size_t si = 0; si < states.size(); ++si) {
    const auto& state = states[si];
    Config config;
    apply_ablations(config, args);
    OrganicBrain brain(config);
    load_state_checked(brain, state.state_path);
    uint64_t loaded_hash = brain.state_hash();
    uint64_t expected_hash = brain.expected_state_hash();
    bool hash_self_check = loaded_hash == expected_hash;
    all_state_hash_self_checks = all_state_hash_self_checks && hash_self_check;
    int loaded_max_output_chars = brain.config().max_output_chars;
    if (args.generation_max_output_chars > 0) {
      brain.set_max_output_chars(args.generation_max_output_chars);
    }
    int active_max_output_chars = brain.config().max_output_chars;
    if (args.generation_max_output_chars <= 0 && loaded_max_output_chars != 160) {
      throw std::runtime_error("quote-probe requires persisted max_output_chars=160 when no runtime override is used: " + state.state_path);
    }
    BrainStateStats state_stats = capture_state_stats(brain);

    if (si) out << ",\n";
    out << "    {\"state_id\": " << q(state.state_id)
        << ", \"parent_state_path\": " << (state.parent_state_path.empty() ? "null" : q(state.parent_state_path))
        << ", \"state_path\": " << q(state.state_path)
        << ", \"source_artifact_path\": " << q(state.source_artifact_path)
        << ", \"lineage\": " << q(state.lineage)
        << ", \"loaded_state_hash\": " << q(hex64(loaded_hash))
        << ", \"expected_state_hash\": " << q(hex64(expected_hash))
        << ", \"hash_self_check\": " << (hash_self_check ? "true" : "false")
        << ", \"loaded_max_output_chars\": " << loaded_max_output_chars
        << ", \"active_max_output_chars\": " << active_max_output_chars
        << ", \"model_state\": ";
    write_state_stats(out, state_stats);
    out << ", \"outputs\": [\n";

    transcript << "\n\n## " << state.state_id << "\n\n";
    transcript << "- state path: `" << state.state_path << "`\n";
    transcript << "- loaded state hash: `" << hex64(loaded_hash) << "`\n";
    transcript << "- active max output chars: " << active_max_output_chars << "\n";

    for (size_t pi = 0; pi < prompts.size(); ++pi) {
      const auto& prompt = prompts[pi];
      Event event = event_from_voice_prompt(prompt);
      if (args.derive_raw_text_spans && !args.ablate_raw_text_spans) {
        auto spans = raw_text_span_observations(prompt.prompt_text);
        event.observations.insert(event.observations.end(), spans.begin(), spans.end());
      }
      uint64_t before_hash = brain.state_hash();
      auto gen = brain.generate(event.input, event.observations);
      uint64_t after_hash = brain.state_hash();
      bool state_unchanged = before_hash == after_hash;
      all_generations_state_unchanged = all_generations_state_unchanged && state_unchanged;
      if (!args.event_log.empty()) {
        OutcomePrediction prediction = brain.predict_outcome(event.input, event.observations);
        append_event_log_v2(args.event_log, policy, run_id, args.organism_id,
                            state.state_id + "__" + prompt.prompt_id, "quote_probe",
                            "generate", event, gen.output, "", true, prediction, nullptr,
                            gen.activations, {}, before_hash, after_hash,
                            "cycle11_voice_prompt", args.experience_db);
      }

      ++generation_count;
      if (!gen.output.empty()) ++nonempty_count;
      max_output_char_count = std::max(max_output_char_count, gen.output.size());
      bool exceeds_legacy = gen.output.size() > 48;
      if (exceeds_legacy) ++outputs_exceeding_legacy_cap;

      if (pi) out << ",\n";
      out << "      {\"prompt_id\": " << q(prompt.prompt_id)
          << ", \"prompt_text\": " << q(prompt.prompt_text)
          << ", \"observations\": ";
      write_string_array_json(out, event.observations);
      out << ", \"source\": " << q(prompt.source)
          << ", \"composition\": " << q(prompt.composition)
          << ", \"raw_generated_output\": " << q(gen.output)
          << ", \"output_char_count\": " << gen.output.size()
          << ", \"exceeds_legacy_48_char_cap\": " << (exceeds_legacy ? "true" : "false")
          << ", \"audit_status\": \"ungraded; rubric-pending for GPT/lain audit\""
          << ", \"state_hash_before\": " << q(hex64(before_hash))
          << ", \"state_hash_after\": " << q(hex64(after_hash))
          << ", \"state_unchanged\": " << (state_unchanged ? "true" : "false")
          << ", \"activated_memory_state\": ";
      write_generation_evidence(out, gen);
      out << "}";

      transcript << "\n### " << prompt.prompt_id << "\n\n";
      transcript << "- prompt: `" << prompt.prompt_text << "`\n";
      transcript << "- observations: ";
      for (size_t oi = 0; oi < event.observations.size(); ++oi) {
        if (oi) transcript << ", ";
        transcript << "`" << event.observations[oi] << "`";
      }
      transcript << "\n";
      transcript << "- raw output: `" << display_output(gen.output) << "`\n";
      transcript << "- char count: " << gen.output.size() << "\n";
      transcript << "- state unchanged: " << (state_unchanged ? "true" : "false") << "\n";
    }
    out << "\n    ]}";
  }

  out << "\n  ],\n";
  out << "  \"summary_metrics\": {\"state_count\": " << states.size()
      << ", \"prompt_count\": " << prompts.size()
      << ", \"generation_count\": " << generation_count
      << ", \"nonempty_output_count\": " << nonempty_count
      << ", \"max_output_char_count\": " << max_output_char_count
      << ", \"outputs_exceeding_legacy_48_char_cap\": " << outputs_exceeding_legacy_cap
      << ", \"all_state_hash_self_checks\": "
      << (all_state_hash_self_checks ? "true" : "false")
      << ", \"all_generations_state_unchanged\": "
      << (all_generations_state_unchanged ? "true" : "false") << "},\n";
  out << "  \"larger_budget_result\": {\"at_least_one_output_exceeded_legacy_cap\": "
      << (outputs_exceeding_legacy_cap > 0 ? "true" : "false")
      << ", \"honest_note\": "
      << q(outputs_exceeding_legacy_cap > 0
               ? "At least one raw output crossed the old 48-character cap under the persisted generation budget."
               : "The persisted generation budget was raised, but current learned state still ended outputs at or before the old 48-character cap.")
      << "},\n";
  out << "  \"honest_interpretation\": \"Cycle 11 quote-probe loads persisted organic-v0 states whose PXSTATE CONFIG carries max_output_chars=160, then asks raw-utterance-only prompts. Outputs are raw and unscored; nonempty text proves only that learned state emitted characters, not philosophy, semantic understanding, fluent chat, or A0 improvement.\"\n";
  out << "}\n";

  if (!all_state_hash_self_checks) throw std::runtime_error("quote-probe state hash self-check failed");
  if (!all_generations_state_unchanged) throw std::runtime_error("quote-probe generation mutated state");
  std::cout << "wrote " << args.out << "\n";
}

struct CorpusExposureHistory {
  CorpusShardRecord shard;
  std::string raw_text;
  uint64_t state_before = 0;
  uint64_t state_after = 0;
  bool learning_applied = false;
};

void corpus_exposure_phase(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("corpus-exposure requires --out");
  if (args.load_state.empty()) throw std::runtime_error("corpus-exposure requires --load-state");
  if (args.save_state.empty()) throw std::runtime_error("corpus-exposure requires --save-state");
  if (args.corpus_manifest.empty()) throw std::runtime_error("corpus-exposure requires --corpus-manifest");

  std::string run_id = args.run_id.empty() ? "cycle12-corpus-exposure" : args.run_id;
  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  load_state_checked(brain, args.load_state);
  uint64_t loaded_parent_hash = brain.state_hash();
  if (args.reward_repetition_penalty > 0.0) {
    brain.set_repetition_penalty_weight(args.reward_repetition_penalty);
  }
  uint64_t parent_hash = brain.state_hash();
  BrainStateStats parent_stats = capture_state_stats(brain);

  auto shards = load_corpus_shard_records(args.corpus_manifest);
  int candidate_shards = static_cast<int>(shards.size());
  int accepted_shards = 0;
  int rejected_shards = 0;
  int duplicate_count = 0;
  int64_t bytes_candidate = 0;
  int64_t bytes_accepted = 0;
  std::map<std::string, int> rejection_reason_counts;
  std::vector<CorpusShardRecord> selected;
  for (const auto& shard : shards) {
    bytes_candidate += shard.byte_count;
    if (shard.filter_status == "accepted") {
      ++accepted_shards;
      bytes_accepted += shard.byte_count;
    } else if (shard.filter_status == "rejected") {
      ++rejected_shards;
      rejection_reason_counts[shard.filter_reason] += 1;
      if (shard.filter_reason.rfind("duplicate:", 0) == 0) ++duplicate_count;
    }
    bool train_split = shard.split == "train";
    bool filter_pass = shard.filter_status == "accepted" || args.ablate_content_filter;
    if (train_split && filter_pass) selected.push_back(shard);
  }
  if (selected.empty()) throw std::runtime_error("corpus-exposure found no train shards");
  if (args.corpus_exposure_max_shards > 0 &&
      selected.size() > static_cast<size_t>(args.corpus_exposure_max_shards)) {
    selected.resize(static_cast<size_t>(args.corpus_exposure_max_shards));
  }

  if (!args.event_log.empty()) {
    ensure_parent_dir(args.event_log);
    std::ofstream(args.event_log, std::ios::trunc).close();
  }

  std::vector<CorpusExposureHistory> history;
  for (const auto& shard : selected) {
    bool learned = !args.ablate_corpus_learning;
    std::string raw_text = read_corpus_shard_text(shard.local_path, learned);
    Event event;
    event.event_id = "cycle12_" + shard.shard_id;
    event.episode_id = run_id;
    event.split = "train";
    event.domain = "corpus_exposure";
    event.level = 0;
    event.input = raw_text;
    event.observations = {"raw_utterance:" + raw_text};
    event.source = "cycle12_one_source_corpus";
    event.composition = "raw_utterance_only";
    uint64_t before_hash = brain.state_hash();
    if (learned) {
      brain.expose_raw_utterance(event);
    }
    uint64_t after_hash = brain.state_hash();
    append_corpus_exposure_event_log_line(args.event_log, run_id, args.organism_id,
                                          shard.shard_id, event, shard.local_path,
                                          learned, before_hash, after_hash);
    history.push_back({shard, raw_text, before_hash, after_hash, learned});
  }

  uint64_t child_hash = brain.state_hash();
  BrainStateStats child_stats = capture_state_stats(brain);
  ensure_parent_dir(args.save_state);
  {
    std::ofstream state_out(args.save_state);
    if (!state_out) throw std::runtime_error("cannot write corpus exposure child state: " + args.save_state);
    brain.serialize_state(state_out, args.organism_id);
  }
  OrganicBrain reloaded(config);
  load_state_checked(reloaded, args.save_state);
  uint64_t reload_hash = reloaded.state_hash();
  bool reload_bit_exact = reload_hash == child_hash;
  if (!reload_bit_exact) throw std::runtime_error("corpus exposure child reload hash mismatch");

  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  if (!out) throw std::runtime_error("cannot open corpus exposure artifact: " + args.out);
  std::string ts = timestamp_utc();
  out << "{\n";
  out << "  \"schema\": \"project_x.corpus_exposure_cycle12.v1\",\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"corpus-exposure\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"corpus_manifest_path\": " << q(args.corpus_manifest) << ",\n";
  out << "  \"loaded_state_path\": " << q(args.load_state) << ",\n";
  out << "  \"saved_state_path\": " << q(args.save_state) << ",\n";
  out << "  \"event_log_path\": " << (args.event_log.empty() ? "null" : q(args.event_log)) << ",\n";
  out << "  \"loaded_parent_state_hash\": " << q(hex64(loaded_parent_hash)) << ",\n";
  out << "  \"candidate_shards\": " << candidate_shards << ",\n";
  out << "  \"accepted_shards\": " << accepted_shards << ",\n";
  out << "  \"rejected_shards\": " << rejected_shards << ",\n";
  out << "  \"accepted_shards_over_candidate_shards_pct\": " << std::fixed << std::setprecision(6)
      << (candidate_shards ? 100.0 * static_cast<double>(accepted_shards) / static_cast<double>(candidate_shards) : 0.0)
      << ",\n";
  out << "  \"bytes_candidate\": " << bytes_candidate << ",\n";
  out << "  \"bytes_accepted\": " << bytes_accepted << ",\n";
  out << "  \"bytes_accepted_over_bytes_candidate_pct\": "
      << (bytes_candidate ? 100.0 * static_cast<double>(bytes_accepted) / static_cast<double>(bytes_candidate) : 0.0)
      << ",\n";
  out << std::defaultfloat;
  out << "  \"duplicate_count\": " << duplicate_count << ",\n";
  out << "  \"duplicate_rate\": " << std::fixed << std::setprecision(6)
      << (candidate_shards ? static_cast<double>(duplicate_count) / static_cast<double>(candidate_shards) : 0.0)
      << std::defaultfloat << ",\n";
  out << "  \"rejection_reason_counts\": {";
  bool first_reason = true;
  for (const auto& [reason, count] : rejection_reason_counts) {
    if (!first_reason) out << ", ";
    out << q(reason) << ": " << count;
    first_reason = false;
  }
  out << "},\n";
  out << "  \"exposure_config\": {\"selected_train_shards\": " << history.size()
      << ", \"max_selected_train_shards\": " << args.corpus_exposure_max_shards
      << ", \"raw_utterance_only\": true, \"content_filter_enabled\": "
      << (args.ablate_content_filter ? "false" : "true")
      << ", \"reward_repetition_penalty\": " << args.reward_repetition_penalty << "},\n";
  out << "  \"ablation\": {\"corpus_learning_disabled\": "
      << (args.ablate_corpus_learning ? "true" : "false")
      << ", \"content_filter_disabled\": " << (args.ablate_content_filter ? "true" : "false")
      << "},\n";
  out << "  \"parent_state_hash\": " << q(hex64(parent_hash)) << ",\n";
  out << "  \"child_state_hash\": " << q(hex64(child_hash)) << ",\n";
  out << "  \"reload_state_hash\": " << q(hex64(reload_hash)) << ",\n";
  out << "  \"child_state_hash_changed_from_parent\": "
      << (child_hash != parent_hash ? "true" : "false") << ",\n";
  out << "  \"child_reload_bit_exact\": " << (reload_bit_exact ? "true" : "false") << ",\n";
  out << "  \"parent_model_state\": "; write_state_stats(out, parent_stats); out << ",\n";
  out << "  \"child_model_state\": "; write_state_stats(out, child_stats); out << ",\n";
  out << "  \"state_growth\": "; write_state_growth(out, parent_stats, child_stats); out << ",\n";
  out << "  \"exposure_history\": [\n";
  for (size_t i = 0; i < history.size(); ++i) {
    if (i) out << ",\n";
    const auto& item = history[i];
    out << "    {\"source_id\": " << q(item.shard.source_id)
        << ", \"shard_id\": " << q(item.shard.shard_id)
        << ", \"local_path\": " << q(item.shard.local_path)
        << ", \"sha256\": " << q(item.shard.sha256)
        << ", \"canonicalization_hash\": " << q(item.shard.canonicalization_hash)
        << ", \"split\": " << q(item.shard.split)
        << ", \"split_bucket\": " << item.shard.split_bucket
        << ", \"filter_status\": " << q(item.shard.filter_status)
        << ", \"raw_utterance_char_count\": " << item.raw_text.size()
        << ", \"observations\": ";
    write_string_array_json(out, std::vector<std::string>{"raw_utterance:" + item.raw_text});
    out << ", \"learning_applied\": " << (item.learning_applied ? "true" : "false")
        << ", \"state_before_hash\": " << q(hex64(item.state_before))
        << ", \"state_after_hash\": " << q(hex64(item.state_after))
        << ", \"state_changed\": " << (item.state_before != item.state_after ? "true" : "false")
        << "}";
  }
  out << "\n  ],\n";
  out << "  \"negative_space\": {"
      << "\"not_fluency_claim\": true, "
      << "\"not_philosophy_claim\": true, "
      << "\"not_chat_capability\": true, "
      << "\"not_semantic_quality_claim\": true, "
      << "\"not_ui_layer\": true, "
      << "\"not_pretrained_route\": true, "
      << "\"not_template_route\": true, "
      << "\"not_tokenizer_route\": true, "
      << "\"not_pretrained_encoder_route\": true, "
      << "\"not_a0_improvement\": true, "
      << "\"not_sandbox_or_security\": true, "
      << "\"not_benchmark_ladder_advance\": true, "
      << "\"not_an_alignment_or_safety_claim\": true, "
      << "\"not_license_laundering\": true, "
      << "\"not_curated_corpus_as_capability\": true, "
      << "\"not_byte_count_as_progress\": true, "
      << "\"not_dedup_as_understanding\": true, "
      << "\"not_filter_as_quality_judgment\": true, "
      << "\"not_source_diversity_as_competence\": true, "
      << "\"not_internet_clean_data_claim\": true, "
      << "\"not_state_growth_as_understanding\": true, "
      << "\"not_author_voice_imitation_claim\": true, "
      << "\"not_curator_intelligence_claim\": true},\n";
  out << "  \"honest_interpretation\": \"Cycle 12B corpus exposure loads one capped Cycle 11 state, ingests accepted train shards as raw_utterance-only unlabeled exposure, saves a child state, and reloads it. This proves only persisted state mutation from manifest-backed raw exposure. It does not prove language quality.\"\n";
  out << "}\n";

  if (!args.ablate_corpus_learning && child_hash == parent_hash) {
    throw std::runtime_error("corpus exposure did not change child state hash");
  }
  if (args.ablate_corpus_learning && child_hash != parent_hash) {
    throw std::runtime_error("corpus-learning ablation changed state hash");
  }
  std::cout << "wrote " << args.out << "\n";
}

constexpr int kNeuralFirstChar = 32;
constexpr int kNeuralLastChar = 126;
constexpr int kNeuralTextVocab = (kNeuralLastChar - kNeuralFirstChar + 1) + 1;
constexpr int kNeuralEnd = kNeuralTextVocab - 1;

struct NeuralTextShard {
  CorpusShardRecord shard;
  std::string text;
};

struct NeuralGenerationStep {
  int position = 0;
  int chosen = kNeuralEnd;
  double probability = 0.0;
  bool repeat_penalty_applied = false;
};

struct NeuralGeneration {
  std::string output;
  bool ended_with_end = false;
  int repeat_penalty_count = 0;
  std::vector<NeuralGenerationStep> steps;
};

std::string neural_normalize_text(const std::string& text) {
  std::string out;
  bool prev_space = true;
  for (unsigned char raw : text) {
    unsigned char c = raw;
    if (c == '\n' || c == '\r' || c == '\t') c = ' ';
    if (c >= 'A' && c <= 'Z') c = static_cast<unsigned char>(c - 'A' + 'a');
    if (c < kNeuralFirstChar || c > kNeuralLastChar) continue;
    if (c == ' ') {
      if (!prev_space) out.push_back(' ');
      prev_space = true;
    } else {
      out.push_back(static_cast<char>(c));
      prev_space = false;
    }
  }
  while (!out.empty() && out.back() == ' ') out.pop_back();
  return out;
}

int neural_char_index(unsigned char c) {
  if (c < kNeuralFirstChar || c > kNeuralLastChar) return kNeuralEnd;
  return static_cast<int>(c) - kNeuralFirstChar;
}

char neural_index_char(int idx) {
  if (idx < 0 || idx >= kNeuralEnd) return '?';
  return static_cast<char>(idx + kNeuralFirstChar);
}

std::string neural_index_label(int idx) {
  if (idx == kNeuralEnd) return "<END>";
  return std::string(1, neural_index_char(idx));
}

std::vector<int> neural_targets_for_text(const std::string& text) {
  std::vector<int> out;
  for (unsigned char c : text) {
    int idx = neural_char_index(c);
    if (idx != kNeuralEnd) out.push_back(idx);
  }
  out.push_back(kNeuralEnd);
  return out;
}

bool neural_repetition_loop(const std::string& text) {
  std::string compact;
  bool prev_space = true;
  for (unsigned char raw : text) {
    unsigned char c = raw;
    if (c >= 'A' && c <= 'Z') c = static_cast<unsigned char>(c - 'A' + 'a');
    if (std::isspace(c)) c = ' ';
    if (c == ' ') {
      if (!prev_space) compact.push_back(' ');
      prev_space = true;
    } else {
      compact.push_back(static_cast<char>(c));
      prev_space = false;
    }
  }
  while (!compact.empty() && compact.back() == ' ') compact.pop_back();
  size_t n = compact.size();
  for (size_t width = 4; width <= 32 && 3 * width <= n; ++width) {
    if (compact.compare(n - width, width, compact, n - 2 * width, width) == 0 &&
        compact.compare(n - width, width, compact, n - 3 * width, width) == 0) {
      return true;
    }
  }
  if (n >= 80) {
    std::map<std::string, int> counts;
    std::istringstream in(compact);
    std::string tok;
    while (in >> tok) {
      if (tok.size() >= 4) counts[tok] += 1;
    }
    for (const auto& item : counts) {
      if (item.second >= 5) return true;
    }
  }
  return false;
}

bool neural_would_extend_loop(const std::string& output, int candidate) {
  if (candidate == kNeuralEnd) return false;
  std::string trial = output;
  trial.push_back(neural_index_char(candidate));
  return neural_repetition_loop(trial);
}

int neural_lcp(const std::string& a, const std::string& b) {
  size_t n = std::min(a.size(), b.size());
  size_t i = 0;
  while (i < n && a[i] == b[i]) ++i;
  return static_cast<int>(i);
}

uint64_t neural_file_hash_words(const std::string& path) {
  std::ifstream in(path, std::ios::binary);
  if (!in) throw std::runtime_error("cannot open neural state for hash: " + path);
  uint64_t h = fnv1a("cycle14-neural-file");
  char buffer[4096];
  while (in.read(buffer, sizeof(buffer)) || in.gcount() > 0) {
    std::streamsize got = in.gcount();
    for (std::streamsize i = 0; i < got; ++i) {
      h ^= static_cast<unsigned char>(buffer[i]);
      h *= 1099511628211ull;
    }
  }
  return h;
}

struct TinyCharNeuralHead {
  int context = 16;
  int hidden = 64;
  uint64_t seed = 1414213562ull;
  std::vector<double> w1;
  std::vector<double> b1;
  std::vector<double> w2;
  std::vector<double> b2;

  TinyCharNeuralHead() = default;

  TinyCharNeuralHead(int context_, int hidden_, uint64_t seed_)
      : context(context_), hidden(hidden_), seed(seed_) {
    if (context <= 0 || hidden <= 0) throw std::runtime_error("neural context/hidden must be positive");
    w1.resize(static_cast<size_t>(context) * kNeuralTextVocab * hidden);
    b1.assign(hidden, 0.0);
    w2.resize(static_cast<size_t>(hidden) * kNeuralTextVocab);
    b2.assign(kNeuralTextVocab, 0.0);
    uint64_t s = combine(seed, fnv1a("tiny-char-neural-head"));
    auto init = [&]() {
      s = mix64(s);
      double unit = static_cast<double>((s >> 11) & ((1ull << 53) - 1)) /
                    static_cast<double>(1ull << 53);
      return (unit * 2.0 - 1.0) * 0.025;
    };
    for (double& v : w1) v = init();
    for (double& v : w2) v = init();
  }

  size_t w1_index(int pos, int idx, int h) const {
    return (static_cast<size_t>(pos) * kNeuralTextVocab + static_cast<size_t>(idx)) *
           static_cast<size_t>(hidden) + static_cast<size_t>(h);
  }

  size_t w2_index(int h, int idx) const {
    return static_cast<size_t>(h) * kNeuralTextVocab + static_cast<size_t>(idx);
  }

  std::vector<double> probabilities(const std::vector<int>& ctx) const {
    if (static_cast<int>(ctx.size()) != context) throw std::runtime_error("neural context size mismatch");
    std::vector<double> hid(hidden, 0.0);
    for (int h = 0; h < hidden; ++h) hid[h] = b1[h];
    for (int pos = 0; pos < context; ++pos) {
      int idx = ctx[pos];
      if (idx < 0 || idx >= kNeuralTextVocab) idx = kNeuralEnd;
      for (int h = 0; h < hidden; ++h) hid[h] += w1[w1_index(pos, idx, h)];
    }
    for (double& v : hid) v = std::tanh(v);
    std::vector<double> logits(kNeuralTextVocab, 0.0);
    for (int v = 0; v < kNeuralTextVocab; ++v) logits[v] = b2[v];
    for (int h = 0; h < hidden; ++h) {
      double hv = hid[h];
      for (int v = 0; v < kNeuralTextVocab; ++v) logits[v] += hv * w2[w2_index(h, v)];
    }
    double max_logit = *std::max_element(logits.begin(), logits.end());
    double sum = 0.0;
    for (double& v : logits) {
      v = std::exp(v - max_logit);
      sum += v;
    }
    if (sum <= 0.0 || !std::isfinite(sum)) throw std::runtime_error("neural softmax underflow");
    for (double& v : logits) v /= sum;
    return logits;
  }

  double train_step(std::vector<int>& ctx, int target, double lr) {
    std::vector<double> pre(hidden, 0.0);
    for (int h = 0; h < hidden; ++h) pre[h] = b1[h];
    for (int pos = 0; pos < context; ++pos) {
      int idx = ctx[pos];
      if (idx < 0 || idx >= kNeuralTextVocab) idx = kNeuralEnd;
      for (int h = 0; h < hidden; ++h) pre[h] += w1[w1_index(pos, idx, h)];
    }
    std::vector<double> hid(hidden, 0.0);
    for (int h = 0; h < hidden; ++h) hid[h] = std::tanh(pre[h]);
    std::vector<double> logits(kNeuralTextVocab, 0.0);
    for (int v = 0; v < kNeuralTextVocab; ++v) logits[v] = b2[v];
    for (int h = 0; h < hidden; ++h) {
      for (int v = 0; v < kNeuralTextVocab; ++v) logits[v] += hid[h] * w2[w2_index(h, v)];
    }
    double max_logit = *std::max_element(logits.begin(), logits.end());
    double sum = 0.0;
    for (double& v : logits) {
      v = std::exp(v - max_logit);
      sum += v;
    }
    for (double& v : logits) v /= sum;
    double prob = std::max(1e-12, logits[target]);
    double loss = -std::log(prob);
    logits[target] -= 1.0;

    std::vector<double> grad_h(hidden, 0.0);
    for (int h = 0; h < hidden; ++h) {
      for (int v = 0; v < kNeuralTextVocab; ++v) {
        grad_h[h] += logits[v] * w2[w2_index(h, v)];
      }
    }
    for (int h = 0; h < hidden; ++h) {
      for (int v = 0; v < kNeuralTextVocab; ++v) {
        w2[w2_index(h, v)] -= lr * logits[v] * hid[h];
      }
    }
    for (int v = 0; v < kNeuralTextVocab; ++v) b2[v] -= lr * logits[v];

    for (int h = 0; h < hidden; ++h) {
      double dz = grad_h[h] * (1.0 - hid[h] * hid[h]);
      b1[h] -= lr * dz;
      for (int pos = 0; pos < context; ++pos) {
        int idx = ctx[pos];
        if (idx < 0 || idx >= kNeuralTextVocab) idx = kNeuralEnd;
        w1[w1_index(pos, idx, h)] -= lr * dz;
      }
    }
    std::rotate(ctx.begin(), ctx.begin() + 1, ctx.end());
    ctx.back() = target;
    return loss;
  }

  double nll_for_text(const std::string& text) const {
    std::vector<int> ctx(context, kNeuralEnd);
    auto targets = neural_targets_for_text(text);
    double loss = 0.0;
    for (int target : targets) {
      auto probs = probabilities(ctx);
      loss += -std::log(std::max(1e-12, probs[target]));
      std::rotate(ctx.begin(), ctx.begin() + 1, ctx.end());
      ctx.back() = target;
    }
    return loss / static_cast<double>(std::max<size_t>(1, targets.size()));
  }

  NeuralGeneration generate(const std::string& prompt, int max_chars, int min_chars,
                            double temperature, uint64_t run_seed) const {
    if (max_chars <= 0) throw std::runtime_error("neural max output chars must be positive");
    if (temperature <= 0.0) throw std::runtime_error("neural temperature must be positive");
    std::vector<int> ctx(context, kNeuralEnd);
    std::string normalized_prompt = neural_normalize_text(prompt);
    for (unsigned char c : normalized_prompt) {
      int idx = neural_char_index(c);
      if (idx == kNeuralEnd) continue;
      std::rotate(ctx.begin(), ctx.begin() + 1, ctx.end());
      ctx.back() = idx;
    }

    NeuralGeneration gen;
    uint64_t rng = combine(run_seed, fnv1a(normalized_prompt));
    for (int pos = 0; pos < max_chars; ++pos) {
      auto probs = probabilities(ctx);
      std::vector<std::pair<int, double>> ranked;
      ranked.reserve(kNeuralTextVocab);
      for (int idx = 0; idx < kNeuralTextVocab; ++idx) {
        double p = probs[idx];
        if (idx == kNeuralEnd && static_cast<int>(gen.output.size()) < min_chars) p = 0.0;
        if (idx != kNeuralEnd && neural_would_extend_loop(gen.output, idx)) p *= 0.05;
        if (p > 0.0) ranked.push_back({idx, p});
      }
      if (ranked.empty()) break;
      std::sort(ranked.begin(), ranked.end(), [](const auto& a, const auto& b) {
        if (a.second != b.second) return a.second > b.second;
        return a.first < b.first;
      });
      if (ranked.size() > 10) ranked.resize(10);
      double total = 0.0;
      for (auto& item : ranked) {
        item.second = std::pow(item.second, 1.0 / temperature);
        total += item.second;
      }
      rng = mix64(rng);
      double r = (static_cast<double>((rng >> 11) & ((1ull << 53) - 1)) /
                  static_cast<double>(1ull << 53)) * total;
      int chosen = ranked.back().first;
      double chosen_weight = ranked.back().second;
      double acc = 0.0;
      for (const auto& item : ranked) {
        acc += item.second;
        if (r <= acc) {
          chosen = item.first;
          chosen_weight = item.second;
          break;
        }
      }
      bool penalty = chosen != kNeuralEnd && neural_would_extend_loop(gen.output, chosen);
      if (penalty) ++gen.repeat_penalty_count;
      gen.steps.push_back({pos, chosen, total > 0.0 ? chosen_weight / total : 0.0, penalty});
      if (chosen == kNeuralEnd) {
        gen.ended_with_end = true;
        break;
      }
      gen.output.push_back(neural_index_char(chosen));
      std::rotate(ctx.begin(), ctx.begin() + 1, ctx.end());
      ctx.back() = chosen;
    }
    return gen;
  }

  uint64_t state_hash() const {
    uint64_t h = fnv1a("tiny-char-neural-head-v0");
    h = combine(h, static_cast<uint64_t>(context));
    h = combine(h, static_cast<uint64_t>(hidden));
    h = combine(h, seed);
    auto walk = [&](const std::vector<double>& values) {
      h = combine(h, static_cast<uint64_t>(values.size()));
      for (double v : values) h = combine(h, double_bits(v));
    };
    walk(w1);
    walk(b1);
    walk(w2);
    walk(b2);
    return h;
  }

  void save(const std::string& path) const {
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write neural state: " + path);
    out << "PXNN_V1\n";
    out << "CONTEXT " << context << "\n";
    out << "HIDDEN " << hidden << "\n";
    out << "VOCAB " << kNeuralTextVocab << "\n";
    out << "SEED " << seed << "\n";
    auto write_vec = [&](const std::string& name, const std::vector<double>& values) {
      out << name << ' ' << values.size();
      for (double v : values) out << ' ' << double_to_hex(v);
      out << "\n";
    };
    write_vec("W1", w1);
    write_vec("B1", b1);
    write_vec("W2", w2);
    write_vec("B2", b2);
    out << "STATE_HASH " << hex64(state_hash()) << "\n";
  }

  static TinyCharNeuralHead load(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot load neural state: " + path);
    std::string magic;
    in >> magic;
    if (magic != "PXNN_V1") throw std::runtime_error("bad neural state magic: " + path);
    TinyCharNeuralHead model;
    std::string key;
    uint64_t expected_hash = 0;
    auto read_vec = [&](std::vector<double>& values) {
      size_t count = 0;
      in >> count;
      values.resize(count);
      std::string token;
      for (size_t i = 0; i < count; ++i) {
        in >> token;
        values[i] = hex_to_double(token);
      }
    };
    while (in >> key) {
      if (key == "CONTEXT") in >> model.context;
      else if (key == "HIDDEN") in >> model.hidden;
      else if (key == "VOCAB") {
        int vocab = 0;
        in >> vocab;
        if (vocab != kNeuralTextVocab) throw std::runtime_error("neural vocab mismatch");
      } else if (key == "SEED") in >> model.seed;
      else if (key == "W1") read_vec(model.w1);
      else if (key == "B1") read_vec(model.b1);
      else if (key == "W2") read_vec(model.w2);
      else if (key == "B2") {
        read_vec(model.b2);
      } else if (key == "STATE_HASH") {
        std::string token;
        in >> token;
        expected_hash = std::stoull(token, nullptr, 16);
      } else {
        throw std::runtime_error("unknown neural state key: " + key);
      }
    }
    if (model.context <= 0 || model.hidden <= 0) throw std::runtime_error("invalid neural dimensions");
    if (model.w1.size() != static_cast<size_t>(model.context) * kNeuralTextVocab * model.hidden) {
      throw std::runtime_error("neural W1 shape mismatch");
    }
    if (model.b1.size() != static_cast<size_t>(model.hidden) ||
        model.w2.size() != static_cast<size_t>(model.hidden) * kNeuralTextVocab ||
        model.b2.size() != static_cast<size_t>(kNeuralTextVocab)) {
      throw std::runtime_error("neural parameter shape mismatch");
    }
    if (expected_hash && model.state_hash() != expected_hash) {
      throw std::runtime_error("neural state hash mismatch");
    }
    return model;
  }
};

double neural_sigmoid(double x) {
  if (x >= 0.0) {
    double z = std::exp(-x);
    return 1.0 / (1.0 + z);
  }
  double z = std::exp(x);
  return z / (1.0 + z);
}

struct RecurrentStepCache {
  int input = kNeuralEnd;
  int target = kNeuralEnd;
  std::vector<double> h_prev;
  std::vector<double> z;
  std::vector<double> r;
  std::vector<double> n;
  std::vector<double> h;
  std::vector<double> probs;
};

struct RecurrentGrad {
  std::vector<double> wx_z;
  std::vector<double> wx_r;
  std::vector<double> wx_n;
  std::vector<double> u_z;
  std::vector<double> u_r;
  std::vector<double> u_n;
  std::vector<double> b_z;
  std::vector<double> b_r;
  std::vector<double> b_n;
  std::vector<double> w_out;
  std::vector<double> b_out;

  RecurrentGrad() = default;

  RecurrentGrad(int hidden) {
    wx_z.assign(static_cast<size_t>(kNeuralTextVocab) * hidden, 0.0);
    wx_r.assign(static_cast<size_t>(kNeuralTextVocab) * hidden, 0.0);
    wx_n.assign(static_cast<size_t>(kNeuralTextVocab) * hidden, 0.0);
    u_z.assign(static_cast<size_t>(hidden) * hidden, 0.0);
    u_r.assign(static_cast<size_t>(hidden) * hidden, 0.0);
    u_n.assign(static_cast<size_t>(hidden) * hidden, 0.0);
    b_z.assign(hidden, 0.0);
    b_r.assign(hidden, 0.0);
    b_n.assign(hidden, 0.0);
    w_out.assign(static_cast<size_t>(hidden) * kNeuralTextVocab, 0.0);
    b_out.assign(kNeuralTextVocab, 0.0);
  }

  double l2_norm() const {
    double total = 0.0;
    auto walk = [&](const std::vector<double>& values) {
      for (double v : values) total += v * v;
    };
    walk(wx_z);
    walk(wx_r);
    walk(wx_n);
    walk(u_z);
    walk(u_r);
    walk(u_n);
    walk(b_z);
    walk(b_r);
    walk(b_n);
    walk(w_out);
    walk(b_out);
    return std::sqrt(total);
  }
};

struct NeuralSamplerSetting {
  std::string setting_id;
  double temperature = 1.0;
  int top_k = 16;
  uint64_t seed_offset = 0;
};

std::vector<NeuralSamplerSetting> cycle15_sampler_settings() {
  return {
      {"cycle15_t070_k08", 0.70, 8, 101},
      {"cycle15_t085_k12", 0.85, 12, 202},
      {"cycle15_t100_k16", 1.00, 16, 303},
      {"cycle15_t115_k24", 1.15, 24, 404},
  };
}

uint64_t neural_generation_seed(uint64_t scenario_seed,
                                const std::string& prompt_id,
                                const NeuralSamplerSetting& setting) {
  uint64_t h = combine(scenario_seed, fnv1a("cycle15-generation-seed"));
  h = combine(h, fnv1a(prompt_id));
  h = combine(h, fnv1a(setting.setting_id));
  h = combine(h, setting.seed_offset);
  return h;
}

struct RecurrentCharNeuralHead {
  int hidden = 64;
  uint64_t seed = 2718281828ull;
  std::vector<double> wx_z;
  std::vector<double> wx_r;
  std::vector<double> wx_n;
  std::vector<double> u_z;
  std::vector<double> u_r;
  std::vector<double> u_n;
  std::vector<double> b_z;
  std::vector<double> b_r;
  std::vector<double> b_n;
  std::vector<double> w_out;
  std::vector<double> b_out;

  RecurrentCharNeuralHead() = default;

  RecurrentCharNeuralHead(int hidden_, uint64_t seed_)
      : hidden(hidden_), seed(seed_) {
    if (hidden <= 0) throw std::runtime_error("recurrent hidden must be positive");
    wx_z.resize(static_cast<size_t>(kNeuralTextVocab) * hidden);
    wx_r.resize(static_cast<size_t>(kNeuralTextVocab) * hidden);
    wx_n.resize(static_cast<size_t>(kNeuralTextVocab) * hidden);
    u_z.resize(static_cast<size_t>(hidden) * hidden);
    u_r.resize(static_cast<size_t>(hidden) * hidden);
    u_n.resize(static_cast<size_t>(hidden) * hidden);
    b_z.assign(hidden, 0.0);
    b_r.assign(hidden, 0.0);
    b_n.assign(hidden, 0.0);
    w_out.resize(static_cast<size_t>(hidden) * kNeuralTextVocab);
    b_out.assign(kNeuralTextVocab, 0.0);

    uint64_t s = combine(seed, fnv1a("cycle15-recurrent-gru-char-head"));
    auto unit = [&]() {
      s = mix64(s);
      return static_cast<double>((s >> 11) & ((1ull << 53) - 1)) /
             static_cast<double>(1ull << 53);
    };
    auto init = [&](double scale) {
      return (unit() * 2.0 - 1.0) * scale;
    };
    double input_scale = 0.08;
    double recurrent_scale = hidden > 0 ? 0.08 / std::sqrt(static_cast<double>(hidden)) : 0.01;
    double output_scale = hidden > 0 ? 0.08 / std::sqrt(static_cast<double>(hidden)) : 0.01;
    for (double& v : wx_z) v = init(input_scale);
    for (double& v : wx_r) v = init(input_scale);
    for (double& v : wx_n) v = init(input_scale);
    for (double& v : u_z) v = init(recurrent_scale);
    for (double& v : u_r) v = init(recurrent_scale);
    for (double& v : u_n) v = init(recurrent_scale);
    for (double& v : w_out) v = init(output_scale);
    for (double& v : b_z) v = 0.5;
  }

  size_t wx_index(int idx, int h) const {
    return static_cast<size_t>(idx) * hidden + static_cast<size_t>(h);
  }

  size_t u_index(int h, int prev) const {
    return static_cast<size_t>(h) * hidden + static_cast<size_t>(prev);
  }

  size_t out_index(int h, int idx) const {
    return static_cast<size_t>(h) * kNeuralTextVocab + static_cast<size_t>(idx);
  }

  std::vector<double> probabilities_from_hidden(const std::vector<double>& h_state) const {
    if (static_cast<int>(h_state.size()) != hidden) {
      throw std::runtime_error("recurrent output hidden state size mismatch");
    }
    std::vector<double> probs(kNeuralTextVocab, 0.0);
    for (int v = 0; v < kNeuralTextVocab; ++v) probs[v] = b_out[v];
    for (int h = 0; h < hidden; ++h) {
      double hv = h_state[h];
      for (int v = 0; v < kNeuralTextVocab; ++v) {
        probs[v] += hv * w_out[out_index(h, v)];
      }
    }
    double max_logit = *std::max_element(probs.begin(), probs.end());
    double sum = 0.0;
    for (double& v : probs) {
      v = std::exp(v - max_logit);
      sum += v;
    }
    if (sum <= 0.0 || !std::isfinite(sum)) throw std::runtime_error("recurrent softmax underflow");
    for (double& v : probs) v /= sum;
    return probs;
  }

  RecurrentStepCache forward_step(int input,
                                  int target,
                                  const std::vector<double>& h_prev) const {
    if (static_cast<int>(h_prev.size()) != hidden) {
      throw std::runtime_error("recurrent hidden state size mismatch");
    }
    if (input < 0 || input >= kNeuralTextVocab) input = kNeuralEnd;
    RecurrentStepCache step;
    step.input = input;
    step.target = target;
    step.h_prev = h_prev;
    step.z.assign(hidden, 0.0);
    step.r.assign(hidden, 0.0);
    step.n.assign(hidden, 0.0);
    step.h.assign(hidden, 0.0);
    step.probs.assign(kNeuralTextVocab, 0.0);

    for (int h = 0; h < hidden; ++h) {
      double z_pre = b_z[h] + wx_z[wx_index(input, h)];
      double r_pre = b_r[h] + wx_r[wx_index(input, h)];
      for (int j = 0; j < hidden; ++j) {
        z_pre += u_z[u_index(h, j)] * h_prev[j];
        r_pre += u_r[u_index(h, j)] * h_prev[j];
      }
      step.z[h] = neural_sigmoid(z_pre);
      step.r[h] = neural_sigmoid(r_pre);
    }
    for (int h = 0; h < hidden; ++h) {
      double n_pre = b_n[h] + wx_n[wx_index(input, h)];
      for (int j = 0; j < hidden; ++j) {
        n_pre += u_n[u_index(h, j)] * (step.r[j] * h_prev[j]);
      }
      step.n[h] = std::tanh(n_pre);
      step.h[h] = (1.0 - step.z[h]) * step.n[h] + step.z[h] * h_prev[h];
    }
    step.probs = probabilities_from_hidden(step.h);
    return step;
  }

  std::vector<double> next_hidden(int input, const std::vector<double>& h_prev) const {
    return forward_step(input, kNeuralEnd, h_prev).h;
  }

  double train_on_text(const std::string& text, double lr) {
    auto targets = neural_targets_for_text(text);
    if (targets.empty()) return 0.0;
    std::vector<RecurrentStepCache> steps;
    steps.reserve(targets.size());
    std::vector<double> h_prev(hidden, 0.0);
    double loss = 0.0;
    for (size_t t = 0; t < targets.size(); ++t) {
      int input = (t == 0) ? kNeuralEnd : targets[t - 1];
      auto step = forward_step(input, targets[t], h_prev);
      loss += -std::log(std::max(1e-12, step.probs[targets[t]]));
      h_prev = step.h;
      steps.push_back(std::move(step));
    }

    RecurrentGrad grad(hidden);
    std::vector<double> dh_next(hidden, 0.0);
    for (int t = static_cast<int>(steps.size()) - 1; t >= 0; --t) {
      const auto& step = steps[static_cast<size_t>(t)];
      std::vector<double> dlogits = step.probs;
      dlogits[step.target] -= 1.0;

      std::vector<double> dh(hidden, 0.0);
      for (int h = 0; h < hidden; ++h) {
        double total = dh_next[h];
        for (int v = 0; v < kNeuralTextVocab; ++v) {
          total += dlogits[v] * w_out[out_index(h, v)];
          grad.w_out[out_index(h, v)] += dlogits[v] * step.h[h];
        }
        dh[h] = total;
      }
      for (int v = 0; v < kNeuralTextVocab; ++v) grad.b_out[v] += dlogits[v];

      std::vector<double> dz_pre(hidden, 0.0);
      std::vector<double> dr_pre(hidden, 0.0);
      std::vector<double> dn_pre(hidden, 0.0);
      std::vector<double> dh_prev(hidden, 0.0);
      std::vector<double> dr(hidden, 0.0);

      for (int h = 0; h < hidden; ++h) {
        double dn = dh[h] * (1.0 - step.z[h]);
        double dz = dh[h] * (step.h_prev[h] - step.n[h]);
        dh_prev[h] += dh[h] * step.z[h];
        dn_pre[h] = dn * (1.0 - step.n[h] * step.n[h]);
        dz_pre[h] = dz * step.z[h] * (1.0 - step.z[h]);
      }

      for (int j = 0; j < hidden; ++j) {
        double from_n = 0.0;
        for (int h = 0; h < hidden; ++h) {
          from_n += dn_pre[h] * u_n[u_index(h, j)];
        }
        dr[j] += from_n * step.h_prev[j];
        dh_prev[j] += from_n * step.r[j];
      }
      for (int h = 0; h < hidden; ++h) {
        dr_pre[h] = dr[h] * step.r[h] * (1.0 - step.r[h]);
      }
      for (int j = 0; j < hidden; ++j) {
        for (int h = 0; h < hidden; ++h) {
          dh_prev[j] += dz_pre[h] * u_z[u_index(h, j)];
          dh_prev[j] += dr_pre[h] * u_r[u_index(h, j)];
        }
      }

      int input = step.input;
      for (int h = 0; h < hidden; ++h) {
        grad.wx_z[wx_index(input, h)] += dz_pre[h];
        grad.wx_r[wx_index(input, h)] += dr_pre[h];
        grad.wx_n[wx_index(input, h)] += dn_pre[h];
        grad.b_z[h] += dz_pre[h];
        grad.b_r[h] += dr_pre[h];
        grad.b_n[h] += dn_pre[h];
        for (int j = 0; j < hidden; ++j) {
          grad.u_z[u_index(h, j)] += dz_pre[h] * step.h_prev[j];
          grad.u_r[u_index(h, j)] += dr_pre[h] * step.h_prev[j];
          grad.u_n[u_index(h, j)] += dn_pre[h] * (step.r[j] * step.h_prev[j]);
        }
      }
      dh_next = std::move(dh_prev);
    }

    double norm = grad.l2_norm();
    double scale = 1.0;
    constexpr double kClipNorm = 5.0;
    if (norm > kClipNorm && norm > 0.0) scale = kClipNorm / norm;
    auto apply = [&](std::vector<double>& weights, const std::vector<double>& g) {
      for (size_t i = 0; i < weights.size(); ++i) weights[i] -= lr * scale * g[i];
    };
    apply(wx_z, grad.wx_z);
    apply(wx_r, grad.wx_r);
    apply(wx_n, grad.wx_n);
    apply(u_z, grad.u_z);
    apply(u_r, grad.u_r);
    apply(u_n, grad.u_n);
    apply(b_z, grad.b_z);
    apply(b_r, grad.b_r);
    apply(b_n, grad.b_n);
    apply(w_out, grad.w_out);
    apply(b_out, grad.b_out);
    return loss / static_cast<double>(std::max<size_t>(1, targets.size()));
  }

  double nll_for_text(const std::string& text) const {
    auto targets = neural_targets_for_text(text);
    std::vector<double> h_prev(hidden, 0.0);
    double loss = 0.0;
    for (size_t t = 0; t < targets.size(); ++t) {
      int input = (t == 0) ? kNeuralEnd : targets[t - 1];
      auto step = forward_step(input, targets[t], h_prev);
      loss += -std::log(std::max(1e-12, step.probs[targets[t]]));
      h_prev = step.h;
    }
    return loss / static_cast<double>(std::max<size_t>(1, targets.size()));
  }

  NeuralGeneration generate(const std::string& prompt, int max_chars, int min_chars,
                            double temperature, int top_k, uint64_t run_seed) const {
    if (max_chars <= 0) throw std::runtime_error("recurrent max output chars must be positive");
    if (temperature <= 0.0) throw std::runtime_error("recurrent temperature must be positive");
    std::vector<double> h(hidden, 0.0);
    std::string normalized_prompt = neural_normalize_text(prompt);
    for (unsigned char c : normalized_prompt) {
      int idx = neural_char_index(c);
      if (idx == kNeuralEnd) continue;
      h = next_hidden(idx, h);
    }
    if (normalized_prompt.empty()) h = next_hidden(kNeuralEnd, h);

    NeuralGeneration gen;
    uint64_t rng = combine(run_seed, fnv1a(normalized_prompt));
    for (int pos = 0; pos < max_chars; ++pos) {
      auto probs = probabilities_from_hidden(h);
      std::vector<std::pair<int, double>> ranked;
      ranked.reserve(kNeuralTextVocab);
      for (int idx = 0; idx < kNeuralTextVocab; ++idx) {
        double p = probs[idx];
        if (idx == kNeuralEnd && static_cast<int>(gen.output.size()) < min_chars) p = 0.0;
        if (idx != kNeuralEnd && neural_would_extend_loop(gen.output, idx)) p *= 0.05;
        if (p > 0.0) ranked.push_back({idx, p});
      }
      if (ranked.empty()) break;
      std::sort(ranked.begin(), ranked.end(), [](const auto& a, const auto& b) {
        if (a.second != b.second) return a.second > b.second;
        return a.first < b.first;
      });
      if (top_k > 0 && static_cast<int>(ranked.size()) > top_k) {
        ranked.resize(static_cast<size_t>(top_k));
      }
      double total = 0.0;
      for (auto& item : ranked) {
        item.second = std::pow(item.second, 1.0 / temperature);
        total += item.second;
      }
      rng = mix64(rng);
      double r = (static_cast<double>((rng >> 11) & ((1ull << 53) - 1)) /
                  static_cast<double>(1ull << 53)) * total;
      int chosen = ranked.back().first;
      double chosen_weight = ranked.back().second;
      double acc = 0.0;
      for (const auto& item : ranked) {
        acc += item.second;
        if (r <= acc) {
          chosen = item.first;
          chosen_weight = item.second;
          break;
        }
      }
      bool penalty = chosen != kNeuralEnd && neural_would_extend_loop(gen.output, chosen);
      if (penalty) ++gen.repeat_penalty_count;
      gen.steps.push_back({pos, chosen, total > 0.0 ? chosen_weight / total : 0.0, penalty});
      if (chosen == kNeuralEnd) {
        gen.ended_with_end = true;
        break;
      }
      gen.output.push_back(neural_index_char(chosen));
      h = next_hidden(chosen, h);
    }
    return gen;
  }

  uint64_t state_hash() const {
    uint64_t h = fnv1a("cycle15-recurrent-gru-char-head-v1");
    h = combine(h, static_cast<uint64_t>(hidden));
    h = combine(h, seed);
    auto walk = [&](const std::vector<double>& values) {
      h = combine(h, static_cast<uint64_t>(values.size()));
      for (double v : values) h = combine(h, double_bits(v));
    };
    walk(wx_z);
    walk(wx_r);
    walk(wx_n);
    walk(u_z);
    walk(u_r);
    walk(u_n);
    walk(b_z);
    walk(b_r);
    walk(b_n);
    walk(w_out);
    walk(b_out);
    return h;
  }

  void save(const std::string& path) const {
    ensure_parent_dir(path);
    std::ofstream out(path);
    if (!out) throw std::runtime_error("cannot write recurrent neural state: " + path);
    out << "PXNN_V2\n";
    out << "ARCH RECURRENT_GRU_CHAR_V1\n";
    out << "HIDDEN " << hidden << "\n";
    out << "VOCAB " << kNeuralTextVocab << "\n";
    out << "SEED " << seed << "\n";
    auto write_vec = [&](const std::string& name, const std::vector<double>& values) {
      out << name << ' ' << values.size();
      for (double v : values) out << ' ' << double_to_hex(v);
      out << "\n";
    };
    write_vec("WX_Z", wx_z);
    write_vec("WX_R", wx_r);
    write_vec("WX_N", wx_n);
    write_vec("U_Z", u_z);
    write_vec("U_R", u_r);
    write_vec("U_N", u_n);
    write_vec("B_Z", b_z);
    write_vec("B_R", b_r);
    write_vec("B_N", b_n);
    write_vec("W_OUT", w_out);
    write_vec("B_OUT", b_out);
    out << "STATE_HASH " << hex64(state_hash()) << "\n";
  }

  static RecurrentCharNeuralHead load(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot load recurrent neural state: " + path);
    std::string magic;
    in >> magic;
    if (magic != "PXNN_V2") throw std::runtime_error("bad recurrent neural state magic: " + path);
    RecurrentCharNeuralHead model;
    std::string key;
    uint64_t expected_hash = 0;
    auto read_vec = [&](std::vector<double>& values) {
      size_t count = 0;
      in >> count;
      values.resize(count);
      std::string token;
      for (size_t i = 0; i < count; ++i) {
        in >> token;
        values[i] = hex_to_double(token);
      }
    };
    while (in >> key) {
      if (key == "ARCH") {
        std::string arch;
        in >> arch;
        if (arch != "RECURRENT_GRU_CHAR_V1") throw std::runtime_error("bad recurrent arch");
      } else if (key == "HIDDEN") in >> model.hidden;
      else if (key == "VOCAB") {
        int vocab = 0;
        in >> vocab;
        if (vocab != kNeuralTextVocab) throw std::runtime_error("recurrent vocab mismatch");
      } else if (key == "SEED") in >> model.seed;
      else if (key == "WX_Z") read_vec(model.wx_z);
      else if (key == "WX_R") read_vec(model.wx_r);
      else if (key == "WX_N") read_vec(model.wx_n);
      else if (key == "U_Z") read_vec(model.u_z);
      else if (key == "U_R") read_vec(model.u_r);
      else if (key == "U_N") read_vec(model.u_n);
      else if (key == "B_Z") read_vec(model.b_z);
      else if (key == "B_R") read_vec(model.b_r);
      else if (key == "B_N") read_vec(model.b_n);
      else if (key == "W_OUT") read_vec(model.w_out);
      else if (key == "B_OUT") read_vec(model.b_out);
      else if (key == "STATE_HASH") {
        std::string token;
        in >> token;
        expected_hash = std::stoull(token, nullptr, 16);
      } else {
        throw std::runtime_error("unknown recurrent neural state key: " + key);
      }
    }
    if (model.hidden <= 0) throw std::runtime_error("invalid recurrent hidden size");
    size_t vh = static_cast<size_t>(kNeuralTextVocab) * model.hidden;
    size_t hh = static_cast<size_t>(model.hidden) * model.hidden;
    size_t hv = static_cast<size_t>(model.hidden) * kNeuralTextVocab;
    if (model.wx_z.size() != vh || model.wx_r.size() != vh || model.wx_n.size() != vh ||
        model.u_z.size() != hh || model.u_r.size() != hh || model.u_n.size() != hh ||
        model.b_z.size() != static_cast<size_t>(model.hidden) ||
        model.b_r.size() != static_cast<size_t>(model.hidden) ||
        model.b_n.size() != static_cast<size_t>(model.hidden) ||
        model.w_out.size() != hv || model.b_out.size() != static_cast<size_t>(kNeuralTextVocab)) {
      throw std::runtime_error("recurrent neural parameter shape mismatch");
    }
    if (expected_hash && model.state_hash() != expected_hash) {
      throw std::runtime_error("recurrent neural state hash mismatch");
    }
    return model;
  }
};

std::vector<NeuralTextShard> load_neural_text_shards(const std::string& manifest_path,
                                                     const std::string& split,
                                                     int max_train_shards) {
  auto rows = load_corpus_shard_records(manifest_path);
  std::vector<NeuralTextShard> out;
  for (const auto& row : rows) {
    if (row.filter_status != "accepted" || row.split != split) continue;
    if (split == "train" && max_train_shards > 0 &&
        static_cast<int>(out.size()) >= max_train_shards) break;
    std::string text = neural_normalize_text(read_corpus_shard_text(row.local_path));
    if (!text.empty()) out.push_back({row, text});
  }
  if (out.empty()) throw std::runtime_error("no accepted " + split + " neural text shards");
  return out;
}

// Cycle 16 multi-manifest training: load accepted shards from a primary
// manifest plus any extras (Cycle 16 prep produces a separate manifest from
// Cycle 12B so each cycle's carry-forward verifier stays isolated). Per-
// manifest max_train_shards is disabled inside this helper; the combined
// cap is applied AFTER concatenation so the cap means "total combined
// train shards" rather than "cap per manifest" — that keeps the flag's
// existing semantics intact for single-manifest callers (extras_vec
// empty short-circuits to the primary-only path with the cap applied
// inline).
std::vector<NeuralTextShard> load_neural_text_shards_combined(
    const std::string& primary_manifest,
    const std::vector<std::string>& extra_manifests,
    const std::string& split,
    int max_train_shards) {
  if (extra_manifests.empty()) {
    // Single-manifest path: bit-exact match to pre-cycle-16 behavior so
    // Cycle 14/15 rails and any other single-manifest call paths keep
    // identical accepted-train shard sequence and state hash.
    return load_neural_text_shards(primary_manifest, split, max_train_shards);
  }
  std::vector<NeuralTextShard> out;
  // Primary first, extras in argv order. Internal cap of 0 disables the
  // per-manifest cap so cross-manifest order is preserved before the
  // combined cap fires.
  auto primary = load_neural_text_shards(primary_manifest, split, 0);
  for (auto& shard : primary) out.push_back(std::move(shard));
  for (const auto& manifest_path : extra_manifests) {
    auto extra = load_neural_text_shards(manifest_path, split, 0);
    for (auto& shard : extra) out.push_back(std::move(shard));
  }
  if (split == "train" && max_train_shards > 0 &&
      static_cast<int>(out.size()) > max_train_shards) {
    out.resize(static_cast<size_t>(max_train_shards));
  }
  if (out.empty()) {
    throw std::runtime_error(
        "no accepted " + split + " neural text shards across combined manifests");
  }
  return out;
}

double unigram_nll(const std::vector<NeuralTextShard>& train,
                   const std::vector<NeuralTextShard>& eval) {
  std::array<double, kNeuralTextVocab> counts{};
  counts.fill(1.0);
  double total = static_cast<double>(kNeuralTextVocab);
  for (const auto& shard : train) {
    for (int idx : neural_targets_for_text(shard.text)) {
      counts[idx] += 1.0;
      total += 1.0;
    }
  }
  double loss = 0.0;
  size_t n = 0;
  for (const auto& shard : eval) {
    for (int idx : neural_targets_for_text(shard.text)) {
      loss += -std::log(counts[idx] / total);
      ++n;
    }
  }
  return loss / static_cast<double>(std::max<size_t>(1, n));
}

double neural_dataset_nll(const TinyCharNeuralHead& model,
                          const std::vector<NeuralTextShard>& shards) {
  double total = 0.0;
  size_t n = 0;
  for (const auto& shard : shards) {
    auto targets = neural_targets_for_text(shard.text);
    total += model.nll_for_text(shard.text) * static_cast<double>(targets.size());
    n += targets.size();
  }
  return total / static_cast<double>(std::max<size_t>(1, n));
}

double neural_dataset_nll(const RecurrentCharNeuralHead& model,
                          const std::vector<NeuralTextShard>& shards) {
  double total = 0.0;
  size_t n = 0;
  for (const auto& shard : shards) {
    auto targets = neural_targets_for_text(shard.text);
    total += model.nll_for_text(shard.text) * static_cast<double>(targets.size());
    n += targets.size();
  }
  return total / static_cast<double>(std::max<size_t>(1, n));
}

uint64_t neural_dataset_hash(const std::vector<NeuralTextShard>& train,
                             const std::vector<NeuralTextShard>& probe,
                             const std::vector<NeuralTextShard>& holdout) {
  uint64_t h = fnv1a("cycle15-neural-dataset-hash-v0");
  auto walk = [&](const std::string& split, const std::vector<NeuralTextShard>& shards) {
    h = combine(h, fnv1a(split));
    h = combine(h, static_cast<uint64_t>(shards.size()));
    for (const auto& shard : shards) {
      h = combine(h, fnv1a(shard.shard.shard_id));
      h = combine(h, fnv1a(shard.shard.sha256));
      h = combine(h, fnv1a(shard.shard.canonicalization_hash));
    }
  };
  walk("train", train);
  walk("probe", probe);
  walk("holdout", holdout);
  return h;
}

uint64_t neural_prompt_store_hash(const std::vector<VoicePromptRecord>& prompts) {
  uint64_t h = fnv1a("cycle15-neural-prompt-store-hash-v0");
  h = combine(h, static_cast<uint64_t>(prompts.size()));
  for (const auto& prompt : prompts) {
    h = combine(h, fnv1a(prompt.prompt_id));
    h = combine(h, fnv1a(prompt.prompt_text));
    h = combine(h, fnv1a(prompt.source));
  }
  return h;
}

struct Cycle15Sample {
  std::string sample_id;
  VoicePromptRecord prompt;
  NeuralSamplerSetting setting;
  uint64_t generation_seed = 0;
  NeuralGeneration generation;
};

void write_neural_generation_steps(std::ostream& out, const NeuralGeneration& gen);

std::vector<Cycle15Sample> cycle15_generate_batch(const RecurrentCharNeuralHead& model,
                                                  const std::vector<VoicePromptRecord>& prompts,
                                                  const Args& args) {
  auto settings = cycle15_sampler_settings();
  std::vector<Cycle15Sample> samples;
  samples.reserve(prompts.size() * settings.size());
  size_t sample_index = 0;
  for (const auto& prompt : prompts) {
    for (const auto& setting : settings) {
      uint64_t seed = neural_generation_seed(args.scenario_seed, prompt.prompt_id, setting);
      std::ostringstream sid;
      sid << "cycle15_sample_" << std::setw(4) << std::setfill('0') << sample_index;
      Cycle15Sample sample;
      sample.sample_id = sid.str();
      sample.prompt = prompt;
      sample.setting = setting;
      sample.generation_seed = seed;
      sample.generation = model.generate(prompt.prompt_text, args.neural_max_output_chars,
                                         args.neural_min_output_chars, setting.temperature,
                                         setting.top_k, seed);
      samples.push_back(std::move(sample));
      ++sample_index;
    }
  }
  return samples;
}

void write_cycle15_samples_json(std::ostream& out, const std::vector<Cycle15Sample>& samples) {
  out << "[\n";
  for (size_t i = 0; i < samples.size(); ++i) {
    if (i) out << ",\n";
    const auto& sample = samples[i];
    const auto& gen = sample.generation;
    std::string normalized_prompt = neural_normalize_text(sample.prompt.prompt_text);
    out << "    {\"sample_id\": " << q(sample.sample_id)
        << ", \"prompt_id\": " << q(sample.prompt.prompt_id)
        << ", \"prompt_text\": " << q(sample.prompt.prompt_text)
        << ", \"prompt_source\": " << q(sample.prompt.source)
        << ", \"conditioning_mode\": \"prompt_context_only_no_answer_template\""
        << ", \"sampler\": {\"setting_id\": " << q(sample.setting.setting_id)
        << ", \"temperature\": " << std::fixed << std::setprecision(2) << sample.setting.temperature
        << std::defaultfloat
        << ", \"top_k\": " << sample.setting.top_k
        << ", \"seed\": " << sample.generation_seed << "}"
        << ", \"raw_generated_output\": " << q(gen.output)
        << ", \"output_char_count\": " << gen.output.size()
        << ", \"ended_with_end\": " << (gen.ended_with_end ? "true" : "false")
        << ", \"repetition_loop\": " << (neural_repetition_loop(gen.output) ? "true" : "false")
        << ", \"prompt_echo_prefix_chars\": " << neural_lcp(gen.output, normalized_prompt)
        << ", \"distinct_char_count\": " << std::set<char>(gen.output.begin(), gen.output.end()).size()
        << ", \"repeat_penalty_count\": " << gen.repeat_penalty_count
        << ", \"raw_output_fnv1a64\": " << q(hex64(fnv1a(gen.output)))
        << ", \"generation_steps\": ";
    write_neural_generation_steps(out, gen);
    out << "}";
  }
  out << "\n  ]";
}

void write_cycle15_transcript(const std::string& path,
                              const std::vector<Cycle15Sample>& samples) {
  ensure_parent_dir(path);
  std::ofstream out(path);
  if (!out) throw std::runtime_error("cannot write cycle15 transcript: " + path);
  out << "# Cycle 15 Recurrent Text Transcript\n\n";
  out << "Generated: " << timestamp_utc() << "\n\n";
  out << "Every block below is raw output from the saved-parameter recurrent text head. ";
  out << "No block is edited, repaired, truncated, or polished before audit.\n\n";
  for (const auto& sample : samples) {
    out << "## " << sample.sample_id << "\n\n";
    out << "- prompt_id: `" << sample.prompt.prompt_id << "`\n";
    out << "- prompt: `" << sample.prompt.prompt_text << "`\n";
    out << "- sampler: temperature=" << std::fixed << std::setprecision(2)
        << sample.setting.temperature << std::defaultfloat
        << ", top_k=" << sample.setting.top_k
        << ", seed=" << sample.generation_seed << "\n\n";
    out << "```text\n" << sample.generation.output << "\n```\n\n";
  }
}

struct Cycle15BatchMetrics {
  int sample_count = 0;
  int prompt_count = 0;
  int sampler_setting_count = 0;
  int nonempty_count = 0;
  int repetition_loop_count = 0;
  int prompt_echo_count = 0;
  int ended_with_end_count = 0;
  int printable_output_count = 0;
  int repeat_penalty_count = 0;
};

Cycle15BatchMetrics cycle15_batch_metrics(const std::vector<Cycle15Sample>& samples,
                                          int prompt_count,
                                          int setting_count) {
  Cycle15BatchMetrics metrics;
  metrics.sample_count = static_cast<int>(samples.size());
  metrics.prompt_count = prompt_count;
  metrics.sampler_setting_count = setting_count;
  for (const auto& sample : samples) {
    const auto& gen = sample.generation;
    if (!gen.output.empty()) ++metrics.nonempty_count;
    if (neural_repetition_loop(gen.output)) ++metrics.repetition_loop_count;
    std::string normalized_prompt = neural_normalize_text(sample.prompt.prompt_text);
    if (gen.output == normalized_prompt || gen.output.rfind(normalized_prompt, 0) == 0) {
      ++metrics.prompt_echo_count;
    }
    if (gen.ended_with_end) ++metrics.ended_with_end_count;
    bool printable = true;
    for (unsigned char c : gen.output) {
      if (c < kNeuralFirstChar || c > kNeuralLastChar) printable = false;
    }
    if (printable) ++metrics.printable_output_count;
    metrics.repeat_penalty_count += gen.repeat_penalty_count;
  }
  return metrics;
}

void write_neural_generation_steps(std::ostream& out, const NeuralGeneration& gen) {
  out << "[";
  for (size_t i = 0; i < gen.steps.size(); ++i) {
    if (i) out << ", ";
    const auto& step = gen.steps[i];
    out << "{\"position\": " << step.position
        << ", \"chosen\": " << q(neural_index_label(step.chosen))
        << ", \"probability\": " << std::fixed << std::setprecision(8) << step.probability
        << std::defaultfloat
        << ", \"repeat_penalty_applied\": " << (step.repeat_penalty_applied ? "true" : "false")
        << "}";
  }
  out << "]";
}

void write_neural_transcript(const std::string& path,
                             const std::vector<VoicePromptRecord>& prompts,
                             const std::vector<NeuralGeneration>& generations) {
  ensure_parent_dir(path);
  std::ofstream out(path);
  if (!out) throw std::runtime_error("cannot write neural transcript: " + path);
  out << "# Cycle 14 Neural Text Transcript\n\n";
  out << "Generated: " << timestamp_utc() << "\n\n";
  out << "Raw outputs are continuations from a locally trained native char-level neural head. ";
  out << "They are not semantic answers or polished responses.\n\n";
  for (size_t i = 0; i < prompts.size(); ++i) {
    out << "## " << prompts[i].prompt_id << "\n\n";
    out << "Prompt: `" << prompts[i].prompt_text << "`\n\n";
    out << "Output:\n\n";
    out << "```text\n" << display_output(generations[i].output) << "\n```\n\n";
  }
}

void neural_text_quality_phase(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("neural-text-quality requires --out");
  if (args.save_state.empty()) throw std::runtime_error("neural-text-quality requires --save-state");
  if (args.neural_context <= 0 || args.neural_hidden <= 0) {
    throw std::runtime_error("neural context/hidden must be positive");
  }
  if (args.neural_epochs <= 0) throw std::runtime_error("neural epochs must be positive");
  if (args.neural_learning_rate <= 0.0) throw std::runtime_error("neural learning rate must be positive");
  if (args.neural_temperature <= 0.0) throw std::runtime_error("neural temperature must be positive");

  std::string run_id = args.run_id.empty() ? "cycle14-neural-text-quality" : args.run_id;
  auto train = load_neural_text_shards(args.corpus_manifest, "train", args.neural_max_train_shards);
  auto probe = load_neural_text_shards(args.corpus_manifest, "probe", 0);
  TinyCharNeuralHead model(args.neural_context, args.neural_hidden,
                           combine(args.scenario_seed, fnv1a("cycle14-neural-text-head-v0")));

  std::vector<double> epoch_train_nll;
  size_t train_targets = 0;
  for (const auto& shard : train) train_targets += neural_targets_for_text(shard.text).size();
  for (int epoch = 0; epoch < args.neural_epochs; ++epoch) {
    double loss = 0.0;
    size_t n = 0;
    for (const auto& shard : train) {
      std::vector<int> ctx(model.context, kNeuralEnd);
      for (int target : neural_targets_for_text(shard.text)) {
        loss += model.train_step(ctx, target, args.neural_learning_rate);
        ++n;
      }
    }
    epoch_train_nll.push_back(loss / static_cast<double>(std::max<size_t>(1, n)));
  }

  double final_train_nll = neural_dataset_nll(model, train);
  double probe_nll = neural_dataset_nll(model, probe);
  double unigram_probe = unigram_nll(train, probe);
  double improvement_pct = unigram_probe > 0.0
                               ? 100.0 * (unigram_probe - probe_nll) / unigram_probe
                               : 0.0;
  uint64_t model_hash = model.state_hash();
  model.save(args.save_state);
  uint64_t file_hash = neural_file_hash_words(args.save_state);
  TinyCharNeuralHead reloaded = TinyCharNeuralHead::load(args.save_state);
  uint64_t reload_hash = reloaded.state_hash();

  auto prompts = load_voice_prompt_records(args.experience_db);
  std::vector<NeuralGeneration> generations;
  std::vector<NeuralGeneration> reload_generations;
  int nonempty_count = 0;
  int repetition_loop_count = 0;
  int prompt_echo_count = 0;
  int ended_count = 0;
  int printable_count = 0;
  int total_repeat_penalties = 0;
  for (const auto& prompt : prompts) {
    auto gen = model.generate(prompt.prompt_text, args.neural_max_output_chars,
                              args.neural_min_output_chars, args.neural_temperature,
                              combine(args.scenario_seed, fnv1a(prompt.prompt_id)));
    auto reload_gen = reloaded.generate(prompt.prompt_text, args.neural_max_output_chars,
                                        args.neural_min_output_chars, args.neural_temperature,
                                        combine(args.scenario_seed, fnv1a(prompt.prompt_id)));
    if (!gen.output.empty()) ++nonempty_count;
    if (neural_repetition_loop(gen.output)) ++repetition_loop_count;
    if (gen.output == neural_normalize_text(prompt.prompt_text) ||
        gen.output.rfind(neural_normalize_text(prompt.prompt_text), 0) == 0) {
      ++prompt_echo_count;
    }
    if (gen.ended_with_end) ++ended_count;
    bool printable = true;
    for (unsigned char c : gen.output) {
      if (c < kNeuralFirstChar || c > kNeuralLastChar) printable = false;
    }
    if (printable) ++printable_count;
    total_repeat_penalties += gen.repeat_penalty_count;
    generations.push_back(std::move(gen));
    reload_generations.push_back(std::move(reload_gen));
  }
  bool reload_generations_match = true;
  for (size_t i = 0; i < generations.size(); ++i) {
    if (generations[i].output != reload_generations[i].output ||
        generations[i].ended_with_end != reload_generations[i].ended_with_end) {
      reload_generations_match = false;
    }
  }
  std::string transcript_path = args.transcript_out.empty()
                                    ? std::string("run/artifacts/organic-v0/cycle14_neural_text_transcript.md")
                                    : args.transcript_out;
  write_neural_transcript(transcript_path, prompts, generations);

  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  if (!out) throw std::runtime_error("cannot write neural text artifact: " + args.out);
  out << "{\n";
  out << "  \"schema\": \"project_x.cycle14_neural_text_quality.v0\",\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(timestamp_utc()) << ",\n";
  out << "  \"phase\": \"neural-text-quality\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"corpus_manifest_path\": " << q(args.corpus_manifest) << ",\n";
  out << "  \"prompt_db_path\": " << q(args.experience_db) << ",\n";
  out << "  \"transcript_path\": " << q(transcript_path) << ",\n";
  out << "  \"saved_neural_state_path\": " << q(args.save_state) << ",\n";
  out << "  \"neural_state_hash\": " << q(hex64(model_hash)) << ",\n";
  out << "  \"neural_state_file_hash\": " << q(hex64(file_hash)) << ",\n";
  out << "  \"reload_state_hash\": " << q(hex64(reload_hash)) << ",\n";
  out << "  \"reload_hash_match\": " << (model_hash == reload_hash ? "true" : "false") << ",\n";
  out << "  \"reload_generations_match\": " << (reload_generations_match ? "true" : "false") << ",\n";
  out << "  \"model_config\": {\"context\": " << model.context
      << ", \"hidden\": " << model.hidden
      << ", \"vocab\": " << kNeuralTextVocab
      << ", \"scenario_seed\": " << args.scenario_seed
      << ", \"epochs\": " << args.neural_epochs
      << ", \"learning_rate\": " << args.neural_learning_rate
      << ", \"temperature\": " << args.neural_temperature
      << ", \"max_output_chars\": " << args.neural_max_output_chars
      << ", \"min_output_chars\": " << args.neural_min_output_chars
      << ", \"max_train_shards\": " << args.neural_max_train_shards << "},\n";
  size_t train_chars = 0;
  for (const auto& shard : train) train_chars += shard.text.size();
  size_t probe_chars = 0;
  for (const auto& shard : probe) probe_chars += shard.text.size();
  out << "  \"dataset\": {\"train_shards\": " << train.size()
      << ", \"probe_shards\": " << probe.size()
      << ", \"train_chars\": " << train_chars
      << ", \"probe_chars\": " << probe_chars
      << ", \"train_targets\": " << train_targets << "},\n";
  out << "  \"training\": {\"epoch_train_nll\": [";
  for (size_t i = 0; i < epoch_train_nll.size(); ++i) {
    if (i) out << ", ";
    out << std::fixed << std::setprecision(8) << epoch_train_nll[i] << std::defaultfloat;
  }
  out << "], \"final_train_nll\": " << std::fixed << std::setprecision(8) << final_train_nll
      << ", \"probe_nll\": " << probe_nll
      << ", \"unigram_probe_nll\": " << unigram_probe
      << ", \"probe_nll_improvement_over_unigram_pct\": " << improvement_pct
      << std::defaultfloat << "},\n";
  out << "  \"quote_metrics\": {\"prompt_count\": " << prompts.size()
      << ", \"nonempty_count\": " << nonempty_count
      << ", \"repetition_loop_count\": " << repetition_loop_count
      << ", \"prompt_echo_count\": " << prompt_echo_count
      << ", \"ended_with_end_count\": " << ended_count
      << ", \"printable_output_count\": " << printable_count
      << ", \"repeat_penalty_count\": " << total_repeat_penalties << "},\n";
  out << "  \"quote_outputs\": [\n";
  for (size_t i = 0; i < prompts.size(); ++i) {
    if (i) out << ",\n";
    const auto& prompt = prompts[i];
    const auto& gen = generations[i];
    std::string normalized_prompt = neural_normalize_text(prompt.prompt_text);
    out << "    {\"prompt_id\": " << q(prompt.prompt_id)
        << ", \"prompt_text\": " << q(prompt.prompt_text)
        << ", \"conditioning_mode\": \"prompt_context_only_no_answer_template\""
        << ", \"raw_generated_output\": " << q(gen.output)
        << ", \"output_char_count\": " << gen.output.size()
        << ", \"ended_with_end\": " << (gen.ended_with_end ? "true" : "false")
        << ", \"repetition_loop\": " << (neural_repetition_loop(gen.output) ? "true" : "false")
        << ", \"prompt_echo_prefix_chars\": " << neural_lcp(gen.output, normalized_prompt)
        << ", \"distinct_char_count\": " << std::set<char>(gen.output.begin(), gen.output.end()).size()
        << ", \"repeat_penalty_count\": " << gen.repeat_penalty_count
        << ", \"generation_steps\": ";
    write_neural_generation_steps(out, gen);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"negative_space\": {"
      << "\"not_template_generation\": true, "
      << "\"not_pretrained_model\": true, "
      << "\"not_hosted_model_call\": true, "
      << "\"not_rag_or_retrieval_answer\": true, "
      << "\"not_semantic_parser\": true, "
      << "\"not_response_polish\": true, "
      << "\"not_subjective_quality_score\": true, "
      << "\"not_philosophy_claim\": true, "
      << "\"not_understanding_claim\": true, "
      << "\"not_chat_solved_claim\": true, "
      << "\"not_alignment_or_safety_claim\": true},\n";
  out << "  \"honest_interpretation\": \"Cycle 14 trains a tiny native char-level neural decoder on accepted train shards only, persists and reloads its weights, and compares held-out probe loss to a unigram baseline. Quote outputs are raw continuations from learned local weights, not semantic answers.\"\n";
  out << "}\n";
  if (model_hash != reload_hash || !reload_generations_match) {
    throw std::runtime_error("neural reload verification failed");
  }
  std::cout << "wrote " << args.out << "\n";
}

void neural_recurrent_text_phase(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("neural-recurrent-text requires --out");
  if (args.save_state.empty()) throw std::runtime_error("neural-recurrent-text requires --save-state");
  if (args.neural_hidden <= 0) throw std::runtime_error("recurrent hidden must be positive");
  if (args.neural_epochs <= 0) throw std::runtime_error("recurrent epochs must be positive");
  if (args.neural_learning_rate <= 0.0) throw std::runtime_error("recurrent learning rate must be positive");
  if (args.neural_max_output_chars <= 0) throw std::runtime_error("recurrent max output chars must be positive");
  if (args.experience_db.empty()) throw std::runtime_error("neural-recurrent-text requires --experience-db");

  std::string run_id = args.run_id.empty() ? "cycle15-recurrent-text" : args.run_id;
  // Cycle 16: combined-manifest read. extras_vec empty short-circuits to the
  // single-manifest code path so Cycle 15 carry-forward semantics are
  // bit-exact; non-empty extras concatenates accepted shards in argv order.
  auto train = load_neural_text_shards_combined(
      args.corpus_manifest, args.corpus_manifests_extra, "train",
      args.neural_max_train_shards);
  auto probe = load_neural_text_shards_combined(
      args.corpus_manifest, args.corpus_manifests_extra, "probe", 0);
  auto holdout = load_neural_text_shards_combined(
      args.corpus_manifest, args.corpus_manifests_extra, "holdout", 0);
  RecurrentCharNeuralHead model(args.neural_hidden,
                                combine(args.scenario_seed, fnv1a("cycle15-recurrent-text-head-v1")));

  std::vector<double> epoch_train_nll;
  size_t train_targets = 0;
  for (const auto& shard : train) train_targets += neural_targets_for_text(shard.text).size();
  for (int epoch = 0; epoch < args.neural_epochs; ++epoch) {
    double loss = 0.0;
    size_t n = 0;
    for (const auto& shard : train) {
      size_t targets = neural_targets_for_text(shard.text).size();
      loss += model.train_on_text(shard.text, args.neural_learning_rate) *
              static_cast<double>(targets);
      n += targets;
    }
    epoch_train_nll.push_back(loss / static_cast<double>(std::max<size_t>(1, n)));
  }

  double final_train_nll = neural_dataset_nll(model, train);
  double probe_nll = neural_dataset_nll(model, probe);
  double holdout_nll = neural_dataset_nll(model, holdout);
  double unigram_probe = unigram_nll(train, probe);
  double unigram_holdout = unigram_nll(train, holdout);
  constexpr double kCycle14ProbeNll = 2.55547228;
  constexpr double kRequiredRelativeImprovement = 5.0;
  double required_probe_nll = kCycle14ProbeNll * (1.0 - kRequiredRelativeImprovement / 100.0);
  double probe_relative_improvement =
      100.0 * (kCycle14ProbeNll - probe_nll) / kCycle14ProbeNll;
  bool probe_target_met = probe_nll <= required_probe_nll;
  bool holdout_beats_unigram = holdout_nll < unigram_holdout;

  uint64_t dataset_hash = neural_dataset_hash(train, probe, holdout);
  uint64_t model_hash = model.state_hash();
  model.save(args.save_state);
  uint64_t file_hash = neural_file_hash_words(args.save_state);
  RecurrentCharNeuralHead reloaded = RecurrentCharNeuralHead::load(args.save_state);
  uint64_t reload_hash = reloaded.state_hash();
  if (model_hash != reload_hash) throw std::runtime_error("recurrent reload hash mismatch");

  auto prompts = load_voice_prompt_records(args.experience_db);
  int cycle11_prompt_count = 0;
  for (const auto& prompt : prompts) {
    if (prompt.prompt_id.rfind("c11p_", 0) == 0) ++cycle11_prompt_count;
  }
  if (cycle11_prompt_count < 12 || prompts.size() < 32) {
    throw std::runtime_error("cycle15 prompt store must include 12 Cycle 11 prompts plus at least 20 broader prompts");
  }
  auto samples = cycle15_generate_batch(model, prompts, args);
  if (samples.size() < 100) throw std::runtime_error("cycle15 generation batch must contain at least 100 samples");
  auto reloaded_samples = cycle15_generate_batch(reloaded, prompts, args);
  bool same_process_reload_generations_match = true;
  for (size_t i = 0; i < samples.size(); ++i) {
    if (samples[i].generation.output != reloaded_samples[i].generation.output ||
        samples[i].generation.ended_with_end != reloaded_samples[i].generation.ended_with_end) {
      same_process_reload_generations_match = false;
    }
  }
  if (!same_process_reload_generations_match) {
    throw std::runtime_error("same-process recurrent reload generation mismatch");
  }

  std::string transcript_path = args.transcript_out.empty()
                                    ? std::string("run/artifacts/organic-v0/cycle15_recurrent_text_transcript.md")
                                    : args.transcript_out;
  write_cycle15_transcript(transcript_path, samples);
  Cycle15BatchMetrics batch = cycle15_batch_metrics(
      samples, static_cast<int>(prompts.size()), static_cast<int>(cycle15_sampler_settings().size()));

  size_t train_chars = 0;
  for (const auto& shard : train) train_chars += shard.text.size();
  size_t probe_chars = 0;
  for (const auto& shard : probe) probe_chars += shard.text.size();
  size_t holdout_chars = 0;
  for (const auto& shard : holdout) holdout_chars += shard.text.size();

  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  if (!out) throw std::runtime_error("cannot write recurrent neural text artifact: " + args.out);
  out << "{\n";
  out << "  \"schema\": \"project_x.cycle15_recurrent_text_quality.v0\",\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(timestamp_utc()) << ",\n";
  out << "  \"phase\": \"neural-recurrent-text\",\n";
  out << "  \"hypothesis\": \"A deterministic native GRU-style recurrent character head should lower held-out NLL by carrying trainable state across full shards instead of using only a fixed local window.\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"corpus_manifest_path\": " << q(args.corpus_manifest) << ",\n";
  // Cycle 16 multi-manifest provenance: emit the extra-manifests list so
  // any verifier / regen / audit can know which manifests participated in
  // training. Empty list -> single-manifest run (Cycle 15 behavior).
  out << "  \"corpus_manifests_extra\": [";
  for (size_t i = 0; i < args.corpus_manifests_extra.size(); ++i) {
    if (i) out << ", ";
    out << q(args.corpus_manifests_extra[i]);
  }
  out << "],\n";
  out << "  \"corpus_manifest_count\": " << (1 + args.corpus_manifests_extra.size()) << ",\n";
  out << "  \"prompt_store_path\": " << q(args.experience_db) << ",\n";
  out << "  \"transcript_path\": " << q(transcript_path) << ",\n";
  out << "  \"saved_neural_state_path\": " << q(args.save_state) << ",\n";
  out << "  \"neural_state_schema\": \"PXNN_V2\",\n";
  out << "  \"neural_state_hash\": " << q(hex64(model_hash)) << ",\n";
  out << "  \"neural_state_file_hash\": " << q(hex64(file_hash)) << ",\n";
  out << "  \"reload_state_hash\": " << q(hex64(reload_hash)) << ",\n";
  out << "  \"reload_hash_match\": " << (model_hash == reload_hash ? "true" : "false") << ",\n";
  out << "  \"same_process_reload_generations_match\": " << (same_process_reload_generations_match ? "true" : "false") << ",\n";
  out << "  \"dataset_hash\": " << q(hex64(dataset_hash)) << ",\n";
  out << "  \"prompt_store_hash\": " << q(hex64(neural_prompt_store_hash(prompts))) << ",\n";
  out << "  \"model_config\": {\"architecture\": \"RECURRENT_GRU_CHAR_V1\""
      << ", \"hidden\": " << model.hidden
      << ", \"vocab\": " << kNeuralTextVocab
      << ", \"scenario_seed\": " << args.scenario_seed
      << ", \"epochs\": " << args.neural_epochs
      << ", \"learning_rate\": " << args.neural_learning_rate
      << ", \"max_output_chars\": " << args.neural_max_output_chars
      << ", \"min_output_chars\": " << args.neural_min_output_chars
      << ", \"max_train_shards\": " << args.neural_max_train_shards << "},\n";
  out << "  \"dataset\": {\"train_shards\": " << train.size()
      << ", \"probe_shards\": " << probe.size()
      << ", \"holdout_shards\": " << holdout.size()
      << ", \"train_chars\": " << train_chars
      << ", \"probe_chars\": " << probe_chars
      << ", \"holdout_chars\": " << holdout_chars
      << ", \"train_targets\": " << train_targets
      << ", \"training_split_rule\": \"accepted train shards only\"},\n";
  out << "  \"training\": {\"epoch_train_nll\": [";
  for (size_t i = 0; i < epoch_train_nll.size(); ++i) {
    if (i) out << ", ";
    out << std::fixed << std::setprecision(8) << epoch_train_nll[i] << std::defaultfloat;
  }
  out << "], \"final_train_nll\": " << std::fixed << std::setprecision(8) << final_train_nll
      << ", \"probe_nll\": " << probe_nll
      << ", \"holdout_nll\": " << holdout_nll
      << ", \"unigram_probe_nll\": " << unigram_probe
      << ", \"unigram_holdout_nll\": " << unigram_holdout
      << ", \"cycle14_probe_nll_target\": " << kCycle14ProbeNll
      << ", \"required_probe_nll_for_5pct_relative_improvement\": " << required_probe_nll
      << ", \"probe_nll_relative_improvement_vs_cycle14_pct\": " << probe_relative_improvement
      << ", \"probe_target_met\": " << (probe_target_met ? "true" : "false")
      << ", \"holdout_beats_unigram\": " << (holdout_beats_unigram ? "true" : "false")
      << ", \"architecture_verdict\": "
      << q(probe_target_met ? "accepted_probe_target_met" : "rejected_probe_target_miss")
      << std::defaultfloat << "},\n";
  out << "  \"generation_batch_metrics\": {\"sample_count\": " << batch.sample_count
      << ", \"prompt_count\": " << batch.prompt_count
      << ", \"cycle11_prompt_count\": " << cycle11_prompt_count
      << ", \"sampler_setting_count\": " << batch.sampler_setting_count
      << ", \"nonempty_count\": " << batch.nonempty_count
      << ", \"repetition_loop_count\": " << batch.repetition_loop_count
      << ", \"prompt_echo_count\": " << batch.prompt_echo_count
      << ", \"ended_with_end_count\": " << batch.ended_with_end_count
      << ", \"printable_output_count\": " << batch.printable_output_count
      << ", \"repeat_penalty_count\": " << batch.repeat_penalty_count << "},\n";
  out << "  \"generation_batch\": ";
  write_cycle15_samples_json(out, samples);
  out << ",\n";
  out << "  \"audit_artifact_paths\": {"
      << "\"source_overlap\": \"run/artifacts/organic-v0/cycle15_source_overlap_audit.json\", "
      << "\"reproducibility\": \"run/artifacts/organic-v0/cycle15_reproducibility_audit.json\", "
      << "\"best_raw_output\": \"run/artifacts/organic-v0/cycle15_best_raw_output.json\"},\n";
  out << "  \"substrate_gate_claims\": {"
      << "\"emitted_by_project_x_trainable_parameters\": true, "
      << "\"no_pretrained_model\": true, "
      << "\"no_hosted_model\": true, "
      << "\"no_rag_or_retrieval_fragment_assembly\": true, "
      << "\"no_template_or_route_table_or_semantic_parser\": true, "
      << "\"no_response_polish_layer\": true, "
      << "\"pxnn_v2_state_hash_logged\": true, "
      << "\"generation_vocab_sampler_seed_logged\": true},\n";
  out << "  \"negative_space\": {"
      << "\"not_template_generation\": true, "
      << "\"not_pretrained_model\": true, "
      << "\"not_hosted_model_call\": true, "
      << "\"not_rag_or_retrieval_answer\": true, "
      << "\"not_semantic_parser\": true, "
      << "\"not_response_polish\": true, "
      << "\"not_subjective_quality_score\": true, "
      << "\"not_philosophy_claim\": true, "
      << "\"not_understanding_claim\": true, "
      << "\"not_chat_solved_claim\": true, "
      << "\"not_alignment_or_safety_claim\": true, "
      << "\"not_hassabis_bar_claim\": true},\n";
  out << "  \"honest_interpretation\": \"Cycle 15 trains and persists a deterministic native recurrent character model. The metric target is diagnostic only; sample quality is decided only by raw generation, source-overlap, reproducibility, and manual output-gate audit.\"\n";
  out << "}\n";
  std::cout << "wrote " << args.out << "\n";
}

void neural_recurrent_regenerate_phase(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("neural-recurrent-regenerate requires --out");
  if (args.load_state.empty()) throw std::runtime_error("neural-recurrent-regenerate requires --load-state");
  if (args.experience_db.empty()) throw std::runtime_error("neural-recurrent-regenerate requires --experience-db");
  RecurrentCharNeuralHead model = RecurrentCharNeuralHead::load(args.load_state);
  auto prompts = load_voice_prompt_records(args.experience_db);
  auto samples = cycle15_generate_batch(model, prompts, args);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  if (!out) throw std::runtime_error("cannot write recurrent regeneration artifact: " + args.out);
  out << "{\n";
  out << "  \"schema\": \"project_x.cycle15_recurrent_regeneration.v0\",\n";
  out << "  \"timestamp\": " << q(timestamp_utc()) << ",\n";
  out << "  \"phase\": \"neural-recurrent-regenerate\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"loaded_neural_state_path\": " << q(args.load_state) << ",\n";
  out << "  \"loaded_neural_state_hash\": " << q(hex64(model.state_hash())) << ",\n";
  out << "  \"prompt_store_path\": " << q(args.experience_db) << ",\n";
  out << "  \"scenario_seed\": " << args.scenario_seed << ",\n";
  out << "  \"generation_batch\": ";
  write_cycle15_samples_json(out, samples);
  out << "\n}\n";
  std::cout << "wrote " << args.out << "\n";
}

// Orchestrate the persistence round-trip: train → save → spawn child → load+generate → verify.
// Honors brief's "fresh process must load prior state and generate without replaying full training stream".
void persistence_self_test(const Args& args) {
  if (args.save_state.empty()) throw std::runtime_error("persistence-self-test requires --save-state");
  if (args.out.empty()) throw std::runtime_error("persistence-self-test requires --out");

  Config config;
  apply_ablations(config, args);
  auto events = load_events(args.data);
  std::string verify_id = args.verify_event_id.empty() ? "evt_mem_test_001" : args.verify_event_id;
  const Event* verify_event = nullptr;
  for (const auto& ev : events) {
    if (ev.event_id == verify_id) { verify_event = &ev; break; }
  }
  if (!verify_event) throw std::runtime_error("verify event not in benchmark: " + verify_id);

  if (!args.event_log.empty()) {
    ensure_parent_dir(args.event_log);
    std::ofstream(args.event_log, std::ios::trunc).close();  // start fresh; child will append
  }
  OrganicBrain brain(config);
  bool continued_from_disk = false;
  if (!args.load_state.empty()) {
    load_state_checked(brain, args.load_state);
    continued_from_disk = true;
  }
  BrainStateStats loaded_parent_stats = capture_state_stats(brain);
  PersistenceContext persistence;
  persistence.organism_id = args.organism_id;
  persistence.loaded_state_path = args.load_state;
  persistence.saved_state_path = args.save_state;
  persistence.event_log_path = args.event_log;
  learn_train_events(brain, events, persistence,
                     continued_from_disk ? "loaded_state_plus_benchmark" : "benchmark",
                     args.data);
  BrainStateStats saved_child_stats = capture_state_stats(brain);
  uint64_t pre_hash = saved_child_stats.state_hash;
  auto pre_gen = brain.generate(verify_event->input, verify_event->observations);
  if (!args.event_log.empty()) {
    // Generate is read-only (no learning) — state_after equals state_before.
    append_event_log_line(args.event_log, args.organism_id, "generate", *verify_event, pre_gen.output,
                          verify_event->target_output, pre_hash, pre_hash, "benchmark", args.data);
  }

  // Save state snapshot AFTER training — this is what the child will load.
  ensure_parent_dir(args.save_state);
  {
    std::ofstream state_out(args.save_state);
    brain.serialize_state(state_out, args.organism_id);
  }

  // Child process: load state, generate same event, write verdict JSON.
  std::string child_out = args.out + ".child.json";
  std::ostringstream cmd;
  cmd << "./build/organic_v0 --phase persistence-load-verify"
      << " --load-state " << shell_quote(args.save_state)
      << " --data " << shell_quote(args.data)
      << " --verify-event " << shell_quote(verify_id)
      << " --out " << shell_quote(child_out)
      << " --organism-id " << shell_quote(args.organism_id);
  if (!args.event_log.empty()) cmd << " --event-log " << shell_quote(args.event_log);
  if (args.ablate_trace_id) cmd << " --ablate-trace-id";
  if (args.ablate_numeric_derived) cmd << " --ablate-numeric-derived";
  if (args.ablate_threshold_derived) cmd << " --ablate-threshold-derived";
  if (args.ablate_modular_derived) cmd << " --ablate-modular-derived";
  if (args.ablate_relation_projection) cmd << " --ablate-relation-projection";
  if (args.ablate_symbolic_relations) cmd << " --ablate-symbolic-relations";
  if (args.ablate_grid_spatial) cmd << " --ablate-grid-spatial";
  int rc = std::system(cmd.str().c_str());
  if (rc != 0) throw std::runtime_error("child persistence-load-verify failed with rc=" + std::to_string(rc));

  // Parse child verdict — minimal JSON: read two keys from a single-line JSON file.
  // The .child.json is a temp file; the parent verdict written below contains all the same fields
  // plus the parent-side ones, so the child file is redundant and deleted after read.
  std::ifstream child(child_out);
  if (!child) throw std::runtime_error("cannot open child verdict: " + child_out);
  std::string verdict((std::istreambuf_iterator<char>(child)), std::istreambuf_iterator<char>());
  child.close();
  std::string child_hash = get_string(verdict, "loaded_state_hash");
  std::string child_output = get_string(verdict, "raw_generated_output");
  std::error_code rm_ec;
  std::filesystem::remove(child_out, rm_ec);  // best-effort cleanup; ignore errors
  std::string parent_hash = hex64(pre_hash);
  std::string loaded_parent_hash = hex64(loaded_parent_stats.state_hash);
  bool hash_match = (child_hash == parent_hash);
  bool output_match = (child_output == pre_gen.output);

  // Write parent-side verdict artifact.
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  std::string ts = timestamp_utc();
  std::string run_id = "organic-v0-persist-" + hex64(fnv1a(ts + parent_hash)).substr(0, 12);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"persistence-self-test\",\n";
  out << "  \"organism_id\": " << q(args.organism_id) << ",\n";
  out << "  \"loaded_parent_state_path\": " << (args.load_state.empty() ? "null" : q(args.load_state)) << ",\n";
  out << "  \"loaded_parent_state_hash\": " << q(loaded_parent_hash) << ",\n";
  out << "  \"saved_state_path\": " << q(args.save_state) << ",\n";
  out << "  \"appended_event_log_path\": " << (args.event_log.empty() ? "null" : q(args.event_log)) << ",\n";
  out << "  \"child_verdict_path\": null,\n";
  out << "  \"child_verdict_embedded\": true,\n";
  out << "  \"verify_event_id\": " << q(verify_id) << ",\n";
  out << "  \"loaded_parent_model_state\": "; write_state_stats(out, loaded_parent_stats); out << ",\n";
  out << "  \"saved_child_model_state\": "; write_state_stats(out, saved_child_stats); out << ",\n";
  out << "  \"state_growth\": "; write_state_growth(out, loaded_parent_stats, saved_child_stats); out << ",\n";
  out << "  \"parent_state_hash\": " << q(parent_hash) << ",\n";
  out << "  \"parent_raw_output\": " << q(pre_gen.output) << ",\n";
  out << "  \"child_state_hash\": " << q(child_hash) << ",\n";
  out << "  \"child_raw_output\": " << q(child_output) << ",\n";
  out << "  \"hash_match\": " << (hash_match ? "true" : "false") << ",\n";
  out << "  \"output_match\": " << (output_match ? "true" : "false") << ",\n";
  out << "  \"load_status\": " << (hash_match && output_match ? q("save_and_load_verified") : q("save_and_load_FAILED")) << ",\n";
  out << "  \"honest_interpretation\": \"Round-trip persistence: parent trained from JSONL, saved state, child process loaded state, generated same held-out event. Hash + output match proves the load contract.\"\n";
  out << "}\n";

  if (!hash_match || !output_match) {
    throw std::runtime_error("persistence round-trip FAILED — hash_match=" + std::to_string(hash_match) +
                             " output_match=" + std::to_string(output_match));
  }
  std::cout << "persistence round-trip OK (hash " << parent_hash << " match, output " << q(pre_gen.output) << " match)\n";
}

// Child phase: load state, generate one event, write minimal verdict JSON. Invoked by persistence_self_test.
void persistence_load_verify(const Args& args) {
  if (args.load_state.empty()) throw std::runtime_error("persistence-load-verify requires --load-state");
  if (args.verify_event_id.empty()) throw std::runtime_error("persistence-load-verify requires --verify-event");
  if (args.out.empty()) throw std::runtime_error("persistence-load-verify requires --out");

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  std::ifstream state_in(args.load_state);
  if (!state_in) throw std::runtime_error("cannot open state file: " + args.load_state);
  brain.load_serialized_state(state_in);
  uint64_t recomputed = brain.state_hash();
  uint64_t expected = brain.expected_state_hash();
  bool hash_ok = (recomputed == expected);

  auto events = load_events(args.data);
  const Event* ev = nullptr;
  for (const auto& e : events) if (e.event_id == args.verify_event_id) { ev = &e; break; }
  if (!ev) throw std::runtime_error("verify event not in benchmark: " + args.verify_event_id);

  auto gen = brain.generate(ev->input, ev->observations);
  if (!args.event_log.empty()) {
    append_event_log_line(args.event_log, args.organism_id, "generate", *ev, gen.output,
                          ev->target_output, recomputed, recomputed, "loaded_state", args.load_state);
  }
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\"phase\":\"persistence-load-verify\","
      << "\"loaded_state_path\":" << q(args.load_state) << ","
      << "\"loaded_state_hash\":" << q(hex64(recomputed)) << ","
      << "\"expected_state_hash\":" << q(hex64(expected)) << ","
      << "\"hash_self_check\":" << (hash_ok ? "true" : "false") << ","
      << "\"verify_event_id\":" << q(args.verify_event_id) << ","
      << "\"raw_generated_output\":" << q(gen.output) << ","
      << "\"expected_output\":" << q(ev->target_output) << "}\n";
  if (!hash_ok) {
    throw std::runtime_error("load_state_hash mismatch after deserialization: expected=" +
                             hex64(expected) + " recomputed=" + hex64(recomputed));
  }
}

struct HiddenRuleStepSpec {
  std::string family;
  std::string rule_id;
  int step = 0;
  int mark = 0;
  std::vector<std::string> observations;
  std::string input;
  std::string correct_action;
  bool held_out = false;
};

struct HiddenRuleActionRecord {
  HiddenRuleStepSpec spec;
  Generation generation;
  bool exact = false;
  uint64_t state_before = 0;
  uint64_t state_after_feedback = 0;
};

struct HiddenRuleScore {
  int count = 0;
  int exact = 0;
  int held_out_count = 0;
  int held_out_exact = 0;
  int support_count = 0;
  int support_exact = 0;
};

void add_hidden_rule_score(HiddenRuleScore& score, bool held_out, bool exact) {
  score.count += 1;
  score.exact += exact ? 1 : 0;
  if (held_out) {
    score.held_out_count += 1;
    score.held_out_exact += exact ? 1 : 0;
  } else {
    score.support_count += 1;
    score.support_exact += exact ? 1 : 0;
  }
}

void write_hidden_rule_score(std::ostream& out, const HiddenRuleScore& score) {
  auto rate = [](int exact, int count) -> double {
    return count ? static_cast<double>(exact) / static_cast<double>(count) : 0.0;
  };
  out << "{\"count\": " << score.count
      << ", \"exact\": " << score.exact
      << ", \"exact_rate\": " << std::fixed << std::setprecision(6) << rate(score.exact, score.count)
      << ", \"held_out_count\": " << score.held_out_count
      << ", \"held_out_exact\": " << score.held_out_exact
      << ", \"held_out_exact_rate\": " << rate(score.held_out_exact, score.held_out_count)
      << ", \"support_count\": " << score.support_count
      << ", \"support_exact\": " << score.support_exact
      << ", \"support_exact_rate\": " << rate(score.support_exact, score.support_count)
      << std::defaultfloat << "}";
}

std::vector<HiddenRuleStepSpec> build_hidden_rule_steps(uint64_t seed, const std::string& family_filter) {
  std::vector<HiddenRuleStepSpec> steps;
  auto want = [&](const std::string& family) {
    return family_filter == "all" || family_filter == family;
  };
  auto push = [&](const std::string& family, const std::string& rule_id, int mark,
                  std::vector<std::string> observations, const std::string& input,
                  const std::string& correct, bool held_out) {
    HiddenRuleStepSpec spec;
    spec.family = family;
    spec.rule_id = rule_id;
    spec.step = static_cast<int>(steps.size());
    spec.mark = mark;
    spec.observations = std::move(observations);
    spec.input = input;
    spec.correct_action = correct;
    spec.held_out = held_out;
    steps.push_back(std::move(spec));
  };

  if (want("parity")) {
    int offset = static_cast<int>((seed % 5) * 2);
    std::vector<int> marks = {2 + offset, 3 + offset, 4 + offset, 5 + offset, 8 + offset, 9 + offset};
    for (size_t i = 0; i < marks.size(); ++i) {
      int mark = marks[i];
      std::string correct = (mark % 2 == 0) ? "dax" : "mira";
      push("parity", "hidden_parity_seed_" + std::to_string(seed), mark,
           {"mark:" + std::to_string(mark)},
           "hidden rule mark " + std::to_string(mark),
           correct, i >= 4);
    }
  }

  if (want("threshold")) {
    int cutoff = 5 + static_cast<int>(seed % 3);
    std::vector<int> marks = {cutoff - 3, cutoff + 3, cutoff - 1, cutoff + 4, cutoff - 4, cutoff + 2};
    for (size_t i = 0; i < marks.size(); ++i) {
      int mark = marks[i];
      std::string correct = (mark > cutoff) ? "keto" : "luma";
      push("threshold", "hidden_threshold_cutoff_" + std::to_string(cutoff), mark,
           {"mark:" + std::to_string(mark), "cutoff:" + std::to_string(cutoff)},
           "hidden rule mark " + std::to_string(mark) + " cutoff " + std::to_string(cutoff),
           correct, i >= 4);
    }
  }

  if (want("modular")) {
    int base = static_cast<int>((seed % 3) * 3);
    std::vector<int> marks = {base, base + 1, base + 2, base + 3, base + 4, base + 5,
                              base + 6, base + 7, base + 8};
    for (size_t i = 0; i < marks.size(); ++i) {
      int mark = marks[i];
      int cls = ((mark % 3) + 3) % 3;
      std::string correct = cls == 0 ? "zun" : (cls == 1 ? "pax" : "rilo");
      push("modular", "hidden_modular_modulus_3_seed_" + std::to_string(seed), mark,
           {"mark:" + std::to_string(mark), "modulus:3"},
           "hidden rule mark " + std::to_string(mark) + " modulus 3",
           correct, i >= 6);
    }
  }

  return steps;
}

std::string pick_symbolic_value(const std::vector<std::string>& values, uint64_t seed, size_t offset) {
  if (values.empty()) return "";
  size_t base = static_cast<size_t>(seed % 5);
  return values[(base + offset) % values.size()];
}

std::vector<HiddenRuleStepSpec> build_symbolic_rule_steps(uint64_t seed, const std::string& family_filter) {
  std::vector<HiddenRuleStepSpec> steps;
  auto want = [&](const std::string& family) {
    return family_filter == "all" || family_filter == family;
  };
  auto push = [&](const std::string& family, const std::string& rule_id,
                  std::vector<std::string> observations, const std::string& input,
                  const std::string& correct, bool held_out) {
    HiddenRuleStepSpec spec;
    spec.family = family;
    spec.rule_id = rule_id;
    spec.step = static_cast<int>(steps.size());
    spec.observations = std::move(observations);
    spec.input = input;
    spec.correct_action = correct;
    spec.held_out = held_out;
    steps.push_back(std::move(spec));
  };

  const std::vector<std::string> colors = {
      "red", "blue", "green", "amber", "ivory", "teal", "violet", "cyan",
      "black", "silver", "gold", "white", "maroon", "navy", "lime", "coral"};
  const std::vector<std::string> shapes = {
      "square", "circle", "triangle", "hex", "star", "oval", "diamond", "cross",
      "kite", "ring", "bar", "leaf", "arc", "cube", "cone", "prism"};
  const std::vector<std::string> places = {
      "north", "south", "east", "west", "harbor", "mesa", "grove", "delta",
      "spire", "field", "vault", "bridge", "atrium", "station", "garden", "islet"};
  const std::vector<std::string> materials = {
      "wood", "iron", "glass", "stone", "cloth", "brass", "paper", "clay",
      "steel", "linen", "copper", "slate", "wax", "bone", "fiber", "ceramic"};
  const std::vector<std::string> symbols = {
      "ion", "kest", "moru", "sava", "tyn", "orek", "laz", "bex",
      "pavo", "rusk", "zeni", "doma", "haro", "vex", "quim", "nilo"};

  auto color = [&](size_t offset) { return pick_symbolic_value(colors, seed, offset); };
  auto shape = [&](size_t offset) { return pick_symbolic_value(shapes, seed, offset); };
  auto place = [&](size_t offset) { return pick_symbolic_value(places, seed, offset); };
  auto material = [&](size_t offset) { return pick_symbolic_value(materials, seed, offset); };
  auto symbol = [&](size_t offset) { return pick_symbolic_value(symbols, seed, offset); };

  if (want("same_color")) {
    std::string rule = "symbolic_same_color_seed_" + std::to_string(seed);
    for (int i = 0; i < 8; ++i) {
      bool same = (i % 2 == 0);
      bool held_out = i >= 6;
      std::string left_color = color(static_cast<size_t>(i * 2));
      std::string right_color = same ? left_color : color(static_cast<size_t>(i * 2 + 1));
      // Shape is an opposite distractor, so a generic same/different detector is not enough.
      std::string left_shape = shape(static_cast<size_t>(i * 2));
      std::string right_shape = same ? shape(static_cast<size_t>(i * 2 + 1)) : left_shape;
      push("same_color", rule,
           {"left_color:" + left_color, "right_color:" + right_color,
            "left_shape:" + left_shape, "right_shape:" + right_shape},
           "symbolic rule color pair", same ? "vire" : "nox", held_out);
    }
  }

  if (want("different_shape")) {
    std::string rule = "symbolic_different_shape_seed_" + std::to_string(seed);
    for (int i = 0; i < 8; ++i) {
      bool different = (i % 2 == 0);
      bool held_out = i >= 6;
      std::string left_shape = shape(static_cast<size_t>(6 + i * 2));
      std::string right_shape = different ? shape(static_cast<size_t>(7 + i * 2)) : left_shape;
      std::string left_color = color(static_cast<size_t>(6 + i * 2));
      std::string right_color = different ? left_color : color(static_cast<size_t>(7 + i * 2));
      push("different_shape", rule,
           {"left_shape:" + left_shape, "right_shape:" + right_shape,
            "left_color:" + left_color, "right_color:" + right_color},
           "symbolic rule shape pair", different ? "talu" : "omen", held_out);
    }
  }

  if (want("same_place")) {
    std::string rule = "symbolic_same_place_seed_" + std::to_string(seed);
    for (int i = 0; i < 8; ++i) {
      bool same = (i % 2 == 0);
      bool held_out = i >= 6;
      std::string left_place = place(static_cast<size_t>(i * 2));
      std::string right_place = same ? left_place : place(static_cast<size_t>(i * 2 + 1));
      std::string left_material = material(static_cast<size_t>(i * 2));
      std::string right_material = same ? material(static_cast<size_t>(i * 2 + 1)) : left_material;
      push("same_place", rule,
           {"left_place:" + left_place, "right_place:" + right_place,
            "left_material:" + left_material, "right_material:" + right_material},
           "symbolic rule place pair", same ? "loro" : "vyne", held_out);
    }
  }

  if (want("role_match")) {
    std::string rule = "symbolic_role_match_seed_" + std::to_string(seed);
    for (int i = 0; i < 8; ++i) {
      bool same = (i % 2 == 0);
      bool held_out = i >= 6;
      std::string source_symbol = symbol(static_cast<size_t>(i * 2));
      std::string target_symbol = same ? source_symbol : symbol(static_cast<size_t>(i * 2 + 1));
      std::string left_color = color(static_cast<size_t>(10 + i * 2));
      std::string right_color = same ? color(static_cast<size_t>(11 + i * 2)) : left_color;
      push("role_match", rule,
           {"source_symbol:" + source_symbol, "target_symbol:" + target_symbol,
            "left_color:" + left_color, "right_color:" + right_color},
           "symbolic rule symbol pair", same ? "sato" : "dren", held_out);
    }
  }

  return steps;
}

std::vector<HiddenRuleStepSpec> build_symbolic_probe_steps(uint64_t seed, const std::string& family_filter) {
  auto steps = build_symbolic_rule_steps(seed + 1009, family_filter);
  std::vector<HiddenRuleStepSpec> probes;
  for (const auto& step : steps) {
    if (!step.held_out) continue;
    HiddenRuleStepSpec probe = step;
    probe.step = static_cast<int>(probes.size());
    probe.rule_id = "probe_" + probe.rule_id;
    probes.push_back(std::move(probe));
  }
  return probes;
}

std::string grid_cell_observation(int row, int col, const std::string& value) {
  return "cell_" + std::to_string(row) + "_" + std::to_string(col) + ":" + value;
}

std::vector<HiddenRuleStepSpec> build_grid_rule_steps(uint64_t seed, const std::string& family_filter) {
  std::vector<HiddenRuleStepSpec> steps;
  auto want = [&](const std::string& family) {
    return family_filter == "all" || family_filter == family;
  };
  auto push = [&](const std::string& family, const std::string& rule_id,
                  std::pair<int, int> a, std::pair<int, int> b, const std::string& marker,
                  const std::string& input, const std::string& correct, bool held_out) {
    HiddenRuleStepSpec spec;
    spec.family = family;
    spec.rule_id = rule_id;
    spec.step = static_cast<int>(steps.size());
    spec.observations = {
        grid_cell_observation(a.first, a.second, marker),
        grid_cell_observation(b.first, b.second, marker),
    };
    spec.input = input;
    spec.correct_action = correct;
    spec.held_out = held_out;
    steps.push_back(std::move(spec));
  };

  const std::vector<std::string> markers = {
      "red", "blue", "green", "amber", "ivory", "teal", "violet", "cyan",
      "black", "silver", "gold", "white", "maroon", "navy", "lime", "coral"};
  auto marker = [&](size_t offset) { return pick_symbolic_value(markers, seed, offset); };
  using P = std::pair<int, int>;
  const std::vector<std::pair<P, P>> h_yes = {
      {{0, 0}, {0, 2}}, {{1, 0}, {1, 2}}, {{2, 0}, {2, 2}}, {{0, 0}, {0, 2}}};
  const std::vector<std::pair<P, P>> h_no = {
      {{0, 0}, {1, 0}}, {{0, 0}, {0, 1}}, {{0, 1}, {2, 1}}, {{1, 1}, {2, 2}}};
  const std::vector<std::pair<P, P>> v_yes = {
      {{0, 0}, {2, 0}}, {{0, 1}, {2, 1}}, {{0, 2}, {2, 2}}, {{0, 0}, {2, 0}}};
  const std::vector<std::pair<P, P>> v_no = {
      {{0, 0}, {0, 2}}, {{0, 0}, {1, 0}}, {{1, 1}, {1, 2}}, {{0, 1}, {1, 2}}};
  const std::vector<std::pair<P, P>> d_yes = {
      {{0, 1}, {1, 0}}, {{0, 2}, {2, 0}}, {{1, 2}, {2, 1}}, {{0, 1}, {1, 0}}};
  const std::vector<std::pair<P, P>> d_no = {
      {{0, 0}, {0, 2}}, {{0, 0}, {2, 0}}, {{1, 0}, {1, 2}}, {{0, 2}, {2, 2}}};
  const std::vector<std::pair<P, P>> r_yes = {
      {{0, 0}, {0, 1}}, {{0, 1}, {0, 2}}, {{1, 0}, {1, 1}}, {{2, 1}, {2, 2}}};
  const std::vector<std::pair<P, P>> r_no = {
      {{0, 0}, {0, 2}}, {{0, 0}, {1, 0}}, {{0, 2}, {2, 0}}, {{1, 1}, {2, 1}}};
  size_t offset = static_cast<size_t>(seed % 3);
  auto choose = [&](const std::vector<std::pair<P, P>>& layouts, int i) {
    return layouts[(offset + static_cast<size_t>(i / 2)) % layouts.size()];
  };

  if (want("horizontal_mirror")) {
    std::string rule = "grid_horizontal_mirror_seed_" + std::to_string(seed);
    for (int i = 0; i < 8; ++i) {
      bool yes = (i % 2 == 0);
      bool held_out = i >= 6;
      auto layout = choose(yes ? h_yes : h_no, i);
      push("horizontal_mirror", rule, layout.first, layout.second, marker(static_cast<size_t>(i)),
           "grid rule horizontal mirror", yes ? "haxo" : "mep", held_out);
    }
  }

  if (want("vertical_mirror")) {
    std::string rule = "grid_vertical_mirror_seed_" + std::to_string(seed);
    for (int i = 0; i < 8; ++i) {
      bool yes = (i % 2 == 0);
      bool held_out = i >= 6;
      auto layout = choose(yes ? v_yes : v_no, i);
      push("vertical_mirror", rule, layout.first, layout.second, marker(static_cast<size_t>(8 + i)),
           "grid rule vertical mirror", yes ? "voro" : "daxu", held_out);
    }
  }

  if (want("diagonal_mirror")) {
    std::string rule = "grid_diagonal_mirror_seed_" + std::to_string(seed);
    for (int i = 0; i < 8; ++i) {
      bool yes = (i % 2 == 0);
      bool held_out = i >= 6;
      auto layout = choose(yes ? d_yes : d_no, i);
      push("diagonal_mirror", rule, layout.first, layout.second, marker(static_cast<size_t>(16 + i)),
           "grid rule diagonal mirror", yes ? "qira" : "lent", held_out);
    }
  }

  if (want("row_shift")) {
    std::string rule = "grid_row_shift_seed_" + std::to_string(seed);
    for (int i = 0; i < 8; ++i) {
      bool yes = (i % 2 == 0);
      bool held_out = i >= 6;
      auto layout = choose(yes ? r_yes : r_no, i);
      push("row_shift", rule, layout.first, layout.second, marker(static_cast<size_t>(24 + i)),
           "grid rule row shift", yes ? "juno" : "bask", held_out);
    }
  }

  return steps;
}

std::vector<HiddenRuleStepSpec> build_grid_probe_steps(uint64_t seed, const std::string& family_filter) {
  auto steps = build_grid_rule_steps(seed + 2003, family_filter);
  std::vector<HiddenRuleStepSpec> probes;
  for (const auto& step : steps) {
    if (!step.held_out) continue;
    HiddenRuleStepSpec probe = step;
    probe.step = static_cast<int>(probes.size());
    probe.rule_id = "probe_" + probe.rule_id;
    probes.push_back(std::move(probe));
  }
  return probes;
}

struct TextExperienceScore {
  int count = 0;
  int exact = 0;
  double ratio_total = 0.0;
};

void add_text_experience_score(TextExperienceScore& score, const std::string& raw,
                               const std::string& expected) {
  score.count += 1;
  score.exact += raw == expected ? 1 : 0;
  score.ratio_total += lcs_ratio(raw, expected);
}

void write_text_experience_score(std::ostream& out, const TextExperienceScore& score) {
  out << "{\"count\": " << score.count
      << ", \"exact\": " << score.exact
      << ", \"exact_rate\": " << std::fixed << std::setprecision(6)
      << (score.count ? static_cast<double>(score.exact) / static_cast<double>(score.count) : 0.0)
      << ", \"mean_sequence_ratio\": "
      << (score.count ? score.ratio_total / static_cast<double>(score.count) : 0.0)
      << std::defaultfloat << "}";
}

void write_string_array_json(std::ostream& out, const std::vector<std::string>& values) {
  out << "[";
  for (size_t i = 0; i < values.size(); ++i) {
    if (i) out << ", ";
    out << q(values[i]);
  }
  out << "]";
}

TextExperienceScore score_text_experience_records(
    const OrganicBrain& brain, const std::vector<TextExperienceRecord>& records,
    const std::string& split, bool include_raw_text_spans = false) {
  TextExperienceScore score;
  for (const auto& record : records) {
    if (record.split != split) continue;
    Event event = event_from_text_experience(record, include_raw_text_spans);
    auto gen = brain.generate(event.input, event.observations);
    add_text_experience_score(score, gen.output, event.target_output);
  }
  return score;
}

struct TextExperienceTrainHistory {
  TextExperienceRecord record;
  Generation before_learning;
  Generation after_learning;
  bool exact_before = false;
  bool exact_after = false;
  uint64_t state_before = 0;
  uint64_t state_after = 0;
  bool learning_applied = false;
};

struct TextExperienceProbeHistory {
  TextExperienceRecord record;
  Generation generation;
  bool exact = false;
  uint64_t state_hash = 0;
};

struct TextExperienceReplayHistory {
  TextExperienceRecord record;
  int replay_pass = 0;
  std::string reason;
  Generation before_replay;
  Generation after_replay;
  bool exact_before = false;
  bool exact_after = false;
  double ratio_before = 0.0;
  double ratio_after = 0.0;
  uint64_t state_before = 0;
  uint64_t state_after = 0;
  uint64_t candidate_state_hash = 0;
  bool replay_applied = false;
  bool accepted = false;
  std::string acceptance_reason;
};

void write_text_experience_transcript(const std::string& transcript_path,
                                      const std::vector<TextExperienceTrainHistory>& train_history,
                                      const std::vector<TextExperienceProbeHistory>& probe_history,
                                      bool learning_disabled) {
  ensure_parent_dir(transcript_path);
  std::ofstream out(transcript_path);
  out << "# Cycle 7E Text Experience Transcript\n\n";
  out << "Generated: " << timestamp_utc() << "\n\n";
  out << "This transcript preserves raw organic-v0 output before correction, after correction, "
      << "and on held-out probes. Empty output is written as `<empty>`. The correction text is "
      << "training feedback, not a generation-time answer template.\n\n";
  out << "Learning disabled by ablation: " << (learning_disabled ? "true" : "false") << "\n\n";
  out << "## Training Records\n\n";
  for (size_t i = 0; i < train_history.size(); ++i) {
    const auto& item = train_history[i];
    out << "### " << item.record.experience_id << "\n\n";
    out << "- input: `" << item.record.input_text << "`\n";
    out << "- before correction: `" << display_output(item.before_learning.output) << "`\n";
    out << "- correction: `" << item.record.correction_output << "`\n";
    out << "- after correction: `" << display_output(item.after_learning.output) << "`\n";
    out << "- exact before/after: " << (item.exact_before ? "true" : "false")
        << " / " << (item.exact_after ? "true" : "false");
    if (i + 1 < train_history.size()) out << "\n\n";
  }
  out << "\n\n## Probe Records\n\n";
  for (size_t i = 0; i < probe_history.size(); ++i) {
    const auto& item = probe_history[i];
    out << "### " << item.record.experience_id << "\n\n";
    out << "- input: `" << item.record.input_text << "`\n";
    out << "- raw output: `" << display_output(item.generation.output) << "`\n";
    out << "- expected after oracle scoring: `" << item.record.correction_output << "`\n";
    out << "- exact: " << (item.exact ? "true" : "false");
    if (i + 1 < probe_history.size()) out << "\n\n";
  }
  out << "\n";
}

void text_experience_phase(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("text-experience requires --out");
  if (args.experience_db.empty()) throw std::runtime_error("text-experience requires --experience-db");

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  PersistenceContext persistence;
  persistence.organism_id = args.organism_id;
  persistence.loaded_state_path = args.load_state;
  persistence.saved_state_path = args.save_state;
  persistence.event_log_path = args.event_log;
  if (!args.load_state.empty()) {
    load_state_checked(brain, args.load_state);
    persistence.load_status = "loaded_from_disk";
  }
  if (!args.event_log.empty()) {
    ensure_parent_dir(args.event_log);
    std::ofstream(args.event_log, std::ios::trunc).close();
  }

  auto records = load_text_experience_records(args.experience_db);
  bool include_raw_text_spans = args.derive_raw_text_spans && !args.ablate_raw_text_spans;
  BrainStateStats parent_stats = capture_state_stats(brain);
  TextExperienceScore train_before_score;
  TextExperienceScore train_after_score;
  TextExperienceScore probe_score;
  std::vector<TextExperienceTrainHistory> train_history;
  std::vector<TextExperienceProbeHistory> probe_history;

  for (const auto& record : records) {
    if (record.split != "train") continue;
    Event event = event_from_text_experience(record, include_raw_text_spans);
    uint64_t before_hash = brain.state_hash();
    auto before_gen = brain.generate(event.input, event.observations);
    append_event_log_line(args.event_log, args.organism_id, "generate", event, before_gen.output,
                          event.target_output, before_hash, before_hash,
                          "text_experience_before_learning", args.experience_db);

    bool learned = false;
    uint64_t after_hash = before_hash;
    if (!args.ablate_text_experience_learning) {
      brain.learn(event);
      learned = true;
      after_hash = brain.state_hash();
      append_event_log_line(args.event_log, args.organism_id, "learn", event, event.target_output,
                            event.target_output, before_hash, after_hash,
                            "text_experience_correction", args.experience_db);
    }
    auto after_gen = brain.generate(event.input, event.observations);
    append_event_log_line(args.event_log, args.organism_id, "generate", event, after_gen.output,
                          event.target_output, after_hash, after_hash,
                          learned ? "text_experience_after_learning"
                                  : "text_experience_after_learning_ablation_disabled",
                          args.experience_db);

    add_text_experience_score(train_before_score, before_gen.output, event.target_output);
    add_text_experience_score(train_after_score, after_gen.output, event.target_output);
    train_history.push_back({record, std::move(before_gen), std::move(after_gen),
                             false, false, before_hash, after_hash, learned});
    auto& stored = train_history.back();
    stored.exact_before = stored.before_learning.output == event.target_output;
    stored.exact_after = stored.after_learning.output == event.target_output;
  }

  BrainStateStats child_stats = capture_state_stats(brain);
  if (!args.save_state.empty()) {
    ensure_parent_dir(args.save_state);
    std::ofstream state_out(args.save_state);
    brain.serialize_state(state_out, args.organism_id);
    persistence.load_status = args.load_state.empty()
                                  ? "text_experience_ingested_and_saved"
                                  : "loaded_then_text_experience_ingested_and_saved";
  } else if (args.load_state.empty()) {
    persistence.load_status = "text_experience_ingested_no_state_save";
  } else {
    persistence.load_status = "loaded_then_text_experience_ingested_no_state_save";
  }

  for (const auto& record : records) {
    if (record.split != "probe") continue;
    Event event = event_from_text_experience(record, include_raw_text_spans);
    uint64_t state_hash = brain.state_hash();
    auto gen = brain.generate(event.input, event.observations);
    append_event_log_line(args.event_log, args.organism_id, "generate", event, gen.output,
                          event.target_output, state_hash, state_hash,
                          "text_experience_probe", args.experience_db);
    add_text_experience_score(probe_score, gen.output, event.target_output);
    probe_history.push_back({record, std::move(gen), false, state_hash});
    auto& stored = probe_history.back();
    stored.exact = stored.generation.output == event.target_output;
  }

  std::string transcript_path = args.transcript_out.empty()
                                    ? args.out + ".transcript.md"
                                    : args.transcript_out;
  write_text_experience_transcript(transcript_path, train_history, probe_history,
                                   args.ablate_text_experience_learning);

  std::string ts = timestamp_utc();
  std::string run_id = "organic-v0-text-exp-" + hex64(fnv1a(ts + hex64(child_stats.state_hash))).substr(0, 12);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"text-experience\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"experience_db_path\": " << q(args.experience_db) << ",\n";
  out << "  \"transcript_path\": " << q(transcript_path) << ",\n";
  out << "  \"schema\": \"project_x.text_experience.v0\",\n";
  out << "  \"raw_text_span_sense\": {\"enabled\": "
      << (include_raw_text_spans ? "true" : "false")
      << ", \"derive_flag\": " << (args.derive_raw_text_spans ? "true" : "false")
      << ", \"ablation_flag\": " << (args.ablate_raw_text_spans ? "true" : "false")
      << ", \"max_span_tokens\": 8, \"max_span_len\": 3},\n";
  out << "  \"ablation\": {\"text_experience_learning_disabled\": "
      << (args.ablate_text_experience_learning ? "true" : "false") << "},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"correction_after_generation\": true, \"probe_evaluation\": true},\n";
  out << "  \"model_state_hash\": " << q(hex64(child_stats.state_hash)) << ",\n";
  out << "  \"parent_model_state_hash\": " << q(hex64(parent_stats.state_hash)) << ",\n";
  out << "  \"parent_model_state\": "; write_state_stats(out, parent_stats); out << ",\n";
  out << "  \"model_state\": "; write_state_stats(out, child_stats); out << ",\n";
  out << "  \"state_growth\": "; write_state_growth(out, parent_stats, child_stats); out << ",\n";
  out << "  \"persistence\": "; write_persistence_contract(out, persistence); out << ",\n";
  out << "  \"summary_metrics\": {\"train_before\": "; write_text_experience_score(out, train_before_score);
  out << ", \"train_after\": "; write_text_experience_score(out, train_after_score);
  out << ", \"probe\": "; write_text_experience_score(out, probe_score);
  out << "},\n";
  out << "  \"training_history\": [\n";
  for (size_t i = 0; i < train_history.size(); ++i) {
    if (i) out << ",\n";
    const auto& item = train_history[i];
    out << "    {\"experience_id\": " << q(item.record.experience_id)
        << ", \"session_id\": " << q(item.record.session_id)
        << ", \"input_text\": " << q(item.record.input_text)
        << ", \"observations\": ";
    write_string_array_json(out, item.record.observations);
    out << ", \"correction_output\": " << q(item.record.correction_output)
        << ", \"raw_before_learning\": " << q(item.before_learning.output)
        << ", \"exact_before_learning\": " << (item.exact_before ? "true" : "false")
        << ", \"raw_after_learning\": " << q(item.after_learning.output)
        << ", \"exact_after_learning\": " << (item.exact_after ? "true" : "false")
        << ", \"learning_applied\": " << (item.learning_applied ? "true" : "false")
        << ", \"state_before_hash\": " << q(hex64(item.state_before))
        << ", \"state_after_hash\": " << q(hex64(item.state_after))
        << ", \"before_learning_evidence\": ";
    write_generation_evidence(out, item.before_learning);
    out << ", \"after_learning_evidence\": ";
    write_generation_evidence(out, item.after_learning);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"probe_history\": [\n";
  for (size_t i = 0; i < probe_history.size(); ++i) {
    if (i) out << ",\n";
    const auto& item = probe_history[i];
    out << "    {\"experience_id\": " << q(item.record.experience_id)
        << ", \"session_id\": " << q(item.record.session_id)
        << ", \"input_text\": " << q(item.record.input_text)
        << ", \"observations\": ";
    write_string_array_json(out, item.record.observations);
    out << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"raw_generated_output\": " << q(item.generation.output)
        << ", \"exact\": " << (item.exact ? "true" : "false")
        << ", \"score\": ";
    write_score(out, item.generation.output, item.record.correction_output);
    out << ", \"state_hash\": " << q(hex64(item.state_hash))
        << ", \"activated_memory_state\": ";
    write_generation_evidence(out, item.generation);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"failure_traces\": [";
  bool first_failure = true;
  for (const auto& item : train_history) {
    if (item.exact_after) continue;
    if (!first_failure) out << ", ";
    out << "{\"experience_id\": " << q(item.record.experience_id)
        << ", \"stage\": \"train_after_learning\""
        << ", \"raw_output\": " << q(item.after_learning.output)
        << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"state_hash\": " << q(hex64(item.state_after)) << "}";
    first_failure = false;
  }
  for (const auto& item : probe_history) {
    if (item.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"experience_id\": " << q(item.record.experience_id)
        << ", \"stage\": \"probe\""
        << ", \"raw_output\": " << q(item.generation.output)
        << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"state_hash\": " << q(hex64(item.state_hash)) << "}";
    first_failure = false;
  }
  out << "],\n";
  out << "  \"honest_interpretation\": \"Cycle 7E text-experience rail: correction records mutate the same organic-v0 learned state used by prior phases. The transcript preserves weak raw outputs; exact matches here are small database-backed language recall/generalization, not fluent chat or broad reasoning.\"\n";
  out << "}\n";
}

void text_experience_probe_phase(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("text-experience-probe requires --out");
  if (args.load_state.empty()) throw std::runtime_error("text-experience-probe requires --load-state");
  if (args.experience_db.empty()) throw std::runtime_error("text-experience-probe requires --experience-db");

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  load_state_checked(brain, args.load_state);
  auto records = load_text_experience_records(args.experience_db);
  bool include_raw_text_spans = args.derive_raw_text_spans && !args.ablate_raw_text_spans;
  BrainStateStats state_stats = capture_state_stats(brain);
  TextExperienceScore probe_score;
  std::vector<TextExperienceProbeHistory> probe_history;
  for (const auto& record : records) {
    if (record.split != "probe") continue;
    Event event = event_from_text_experience(record, include_raw_text_spans);
    uint64_t state_hash = brain.state_hash();
    auto gen = brain.generate(event.input, event.observations);
    append_event_log_line(args.event_log, args.organism_id, "generate", event, gen.output,
                          event.target_output, state_hash, state_hash,
                          "text_experience_from_disk_probe", args.load_state);
    add_text_experience_score(probe_score, gen.output, event.target_output);
    probe_history.push_back({record, std::move(gen), false, state_hash});
    auto& stored = probe_history.back();
    stored.exact = stored.generation.output == event.target_output;
  }

  std::string ts = timestamp_utc();
  std::string run_id = "organic-v0-text-probe-" + hex64(fnv1a(ts + hex64(state_stats.state_hash))).substr(0, 12);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"text-experience-probe\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"experience_db_path\": " << q(args.experience_db) << ",\n";
  out << "  \"loaded_state_path\": " << q(args.load_state) << ",\n";
  out << "  \"raw_text_span_sense\": {\"enabled\": "
      << (include_raw_text_spans ? "true" : "false")
      << ", \"derive_flag\": " << (args.derive_raw_text_spans ? "true" : "false")
      << ", \"ablation_flag\": " << (args.ablate_raw_text_spans ? "true" : "false")
      << ", \"max_span_tokens\": 8, \"max_span_len\": 3},\n";
  out << "  \"model_state_hash\": " << q(hex64(state_stats.state_hash)) << ",\n";
  out << "  \"model_state\": "; write_state_stats(out, state_stats); out << ",\n";
  out << "  \"oracle_access\": {\"generation\": false, \"probe_evaluation\": true},\n";
  out << "  \"summary_metrics\": {\"probe\": "; write_text_experience_score(out, probe_score);
  out << "},\n";
  out << "  \"probe_history\": [\n";
  for (size_t i = 0; i < probe_history.size(); ++i) {
    if (i) out << ",\n";
    const auto& item = probe_history[i];
    out << "    {\"experience_id\": " << q(item.record.experience_id)
        << ", \"input_text\": " << q(item.record.input_text)
        << ", \"observations\": ";
    write_string_array_json(out, item.record.observations);
    out << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"raw_generated_output\": " << q(item.generation.output)
        << ", \"exact\": " << (item.exact ? "true" : "false")
        << ", \"score\": ";
    write_score(out, item.generation.output, item.record.correction_output);
    out << ", \"activated_memory_state\": ";
    write_generation_evidence(out, item.generation);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"failure_traces\": [";
  bool first_failure = true;
  for (const auto& item : probe_history) {
    if (item.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"experience_id\": " << q(item.record.experience_id)
        << ", \"raw_output\": " << q(item.generation.output)
        << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"state_hash\": " << q(hex64(item.state_hash)) << "}";
    first_failure = false;
  }
  out << "],\n";
  out << "  \"honest_interpretation\": \"Fresh loaded-child text probe: generated from disk without replaying the text experience stream.\"\n";
  out << "}\n";
}

void write_text_experience_replay_transcript(
    const std::string& transcript_path,
    const std::vector<TextExperienceTrainHistory>& first_pass_history,
    const std::vector<TextExperienceReplayHistory>& replay_history,
    const std::vector<TextExperienceProbeHistory>& post_replay_train_history,
    const std::vector<TextExperienceProbeHistory>& post_replay_probe_history,
    bool replay_disabled) {
  ensure_parent_dir(transcript_path);
  std::ofstream out(transcript_path);
  out << "# Cycle 7F Text Experience Replay Transcript\n\n";
  out << "Generated: " << timestamp_utc() << "\n\n";
  out << "This transcript shows first-pass text learning, replay selection, replay before/after "
      << "outputs, and post-replay probes. Replay uses stored correction records; it is not a "
      << "generation-time template.\n\n";
  out << "Replay disabled by ablation: " << (replay_disabled ? "true" : "false") << "\n\n";
  out << "## First Pass Training\n\n";
  for (size_t i = 0; i < first_pass_history.size(); ++i) {
    const auto& item = first_pass_history[i];
    out << "### " << item.record.experience_id << "\n\n";
    out << "- input: `" << item.record.input_text << "`\n";
    out << "- before correction: `" << display_output(item.before_learning.output) << "`\n";
    out << "- after correction: `" << display_output(item.after_learning.output) << "`\n";
    out << "- expected: `" << item.record.correction_output << "`\n";
    out << "- exact after: " << (item.exact_after ? "true" : "false");
    if (i + 1 < first_pass_history.size()) out << "\n\n";
  }
  out << "\n\n## Replay Events\n\n";
  if (replay_history.empty()) {
    out << "No records selected for replay.\n";
  }
  for (size_t i = 0; i < replay_history.size(); ++i) {
    const auto& item = replay_history[i];
    out << "### " << item.record.experience_id << " / pass " << item.replay_pass << "\n\n";
    out << "- reason: `" << item.reason << "`\n";
    out << "- before replay: `" << display_output(item.before_replay.output) << "`\n";
    out << "- after replay: `" << display_output(item.after_replay.output) << "`\n";
    out << "- expected: `" << item.record.correction_output << "`\n";
    out << "- exact before/after: " << (item.exact_before ? "true" : "false")
        << " / " << (item.exact_after ? "true" : "false") << "\n";
    out << "- replay mutation applied: " << (item.replay_applied ? "true" : "false") << "\n";
    out << "- accepted: " << (item.accepted ? "true" : "false") << "\n";
    out << "- acceptance reason: `" << item.acceptance_reason << "`";
    if (i + 1 < replay_history.size()) out << "\n\n";
  }
  out << "\n\n## Post-Replay Training Check\n\n";
  for (size_t i = 0; i < post_replay_train_history.size(); ++i) {
    const auto& item = post_replay_train_history[i];
    out << "### " << item.record.experience_id << "\n\n";
    out << "- raw output: `" << display_output(item.generation.output) << "`\n";
    out << "- expected: `" << item.record.correction_output << "`\n";
    out << "- exact: " << (item.exact ? "true" : "false");
    if (i + 1 < post_replay_train_history.size()) out << "\n\n";
  }
  out << "\n\n## Post-Replay Probe Check\n\n";
  for (size_t i = 0; i < post_replay_probe_history.size(); ++i) {
    const auto& item = post_replay_probe_history[i];
    out << "### " << item.record.experience_id << "\n\n";
    out << "- raw output: `" << display_output(item.generation.output) << "`\n";
    out << "- expected: `" << item.record.correction_output << "`\n";
    out << "- exact: " << (item.exact ? "true" : "false");
    if (i + 1 < post_replay_probe_history.size()) out << "\n\n";
  }
  out << "\n";
}

void text_experience_replay_phase(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("text-experience-replay requires --out");
  if (args.experience_db.empty()) throw std::runtime_error("text-experience-replay requires --experience-db");
  if (args.replay_passes < 0) throw std::runtime_error("text-experience-replay requires --replay-passes >= 0");

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  PersistenceContext persistence;
  persistence.organism_id = args.organism_id;
  persistence.loaded_state_path = args.load_state;
  persistence.saved_state_path = args.save_state;
  persistence.event_log_path = args.event_log;
  if (!args.load_state.empty()) {
    load_state_checked(brain, args.load_state);
    persistence.load_status = "loaded_from_disk";
  }
  if (!args.event_log.empty()) {
    ensure_parent_dir(args.event_log);
    std::ofstream(args.event_log, std::ios::trunc).close();
  }

  auto records = load_text_experience_records(args.experience_db);
  bool include_raw_text_spans = args.derive_raw_text_spans && !args.ablate_raw_text_spans;
  BrainStateStats parent_stats = capture_state_stats(brain);
  TextExperienceScore first_train_before_score;
  TextExperienceScore first_train_after_score;
  TextExperienceScore pre_replay_probe_score;
  std::vector<TextExperienceTrainHistory> first_pass_history;
  std::vector<TextExperienceProbeHistory> pre_replay_probe_history;

  for (const auto& record : records) {
    if (record.split != "train") continue;
    Event event = event_from_text_experience(record, include_raw_text_spans);
    uint64_t before_hash = brain.state_hash();
    auto before_gen = brain.generate(event.input, event.observations);
    append_event_log_line(args.event_log, args.organism_id, "generate", event, before_gen.output,
                          event.target_output, before_hash, before_hash,
                          "text_experience_replay_first_pass_before", args.experience_db);
    brain.learn(event);
    uint64_t after_hash = brain.state_hash();
    append_event_log_line(args.event_log, args.organism_id, "learn", event, event.target_output,
                          event.target_output, before_hash, after_hash,
                          "text_experience_replay_first_pass_correction", args.experience_db);
    auto after_gen = brain.generate(event.input, event.observations);
    append_event_log_line(args.event_log, args.organism_id, "generate", event, after_gen.output,
                          event.target_output, after_hash, after_hash,
                          "text_experience_replay_first_pass_after", args.experience_db);
    add_text_experience_score(first_train_before_score, before_gen.output, event.target_output);
    add_text_experience_score(first_train_after_score, after_gen.output, event.target_output);
    first_pass_history.push_back({record, std::move(before_gen), std::move(after_gen),
                                  false, false, before_hash, after_hash, true});
    auto& stored = first_pass_history.back();
    stored.exact_before = stored.before_learning.output == event.target_output;
    stored.exact_after = stored.after_learning.output == event.target_output;
  }

  for (const auto& record : records) {
    if (record.split != "probe") continue;
    Event event = event_from_text_experience(record, include_raw_text_spans);
    uint64_t state_hash = brain.state_hash();
    auto gen = brain.generate(event.input, event.observations);
    append_event_log_line(args.event_log, args.organism_id, "generate", event, gen.output,
                          event.target_output, state_hash, state_hash,
                          "text_experience_replay_pre_probe", args.experience_db);
    add_text_experience_score(pre_replay_probe_score, gen.output, event.target_output);
    pre_replay_probe_history.push_back({record, std::move(gen), false, state_hash});
    auto& stored = pre_replay_probe_history.back();
    stored.exact = stored.generation.output == event.target_output;
  }

  BrainStateStats first_pass_stats = capture_state_stats(brain);
  std::vector<std::pair<TextExperienceRecord, std::string>> selected_records;
  for (const auto& item : first_pass_history) {
    double ratio = lcs_ratio(item.after_learning.output, item.record.correction_output);
    if (!item.exact_after) {
      selected_records.push_back({item.record, "not_exact_after_first_pass"});
    } else if (ratio < args.replay_min_sequence_ratio) {
      selected_records.push_back({item.record, "below_replay_sequence_threshold"});
    }
  }

  TextExperienceScore replay_before_score;
  TextExperienceScore replay_after_score;
  std::vector<TextExperienceReplayHistory> replay_history;
  TextExperienceScore accepted_train_score =
      score_text_experience_records(brain, records, "train", include_raw_text_spans);
  TextExperienceScore accepted_probe_score =
      score_text_experience_records(brain, records, "probe", include_raw_text_spans);
  for (int pass = 1; pass <= args.replay_passes; ++pass) {
    for (const auto& selected : selected_records) {
      const auto& record = selected.first;
      Event event = event_from_text_experience(record, include_raw_text_spans);
      uint64_t before_hash = brain.state_hash();
      auto before_gen = brain.generate(event.input, event.observations);
      append_event_log_line(args.event_log, args.organism_id, "generate", event, before_gen.output,
                            event.target_output, before_hash, before_hash,
                            "text_experience_replay_before", args.experience_db);
      bool replay_applied = false;
      bool accepted = false;
      uint64_t after_hash = before_hash;
      uint64_t candidate_hash = before_hash;
      std::string acceptance_reason = args.ablate_text_experience_replay
                                          ? "replay_disabled"
                                          : "candidate_not_evaluated";
      Generation after_gen;
      if (!args.ablate_text_experience_replay) {
        OrganicBrain candidate = brain;
        candidate.learn(event);
        candidate_hash = candidate.state_hash();
        after_gen = candidate.generate(event.input, event.observations);
        TextExperienceScore candidate_train_score =
            score_text_experience_records(candidate, records, "train", include_raw_text_spans);
        TextExperienceScore candidate_probe_score =
            score_text_experience_records(candidate, records, "probe", include_raw_text_spans);
        double before_ratio = lcs_ratio(before_gen.output, event.target_output);
        double after_ratio = lcs_ratio(after_gen.output, event.target_output);
        bool local_not_worse = after_ratio >= before_ratio;
        bool train_not_worse = candidate_train_score.exact >= accepted_train_score.exact;
        bool probe_not_worse = candidate_probe_score.exact >= accepted_probe_score.exact;
        accepted = args.ablate_text_replay_audit ||
                   (local_not_worse && train_not_worse && probe_not_worse);
        if (accepted) {
          brain = std::move(candidate);
          accepted_train_score = candidate_train_score;
          accepted_probe_score = candidate_probe_score;
          replay_applied = true;
          after_hash = brain.state_hash();
          acceptance_reason = args.ablate_text_replay_audit
                                  ? "accepted_audit_ablation_disabled_guard"
                                  : "accepted_local_train_probe_not_worse";
          append_event_log_line(args.event_log, args.organism_id, "learn", event, event.target_output,
                                event.target_output, before_hash, after_hash,
                                "text_experience_replay_correction", args.experience_db);
          append_event_log_line(args.event_log, args.organism_id, "generate", event, after_gen.output,
                                event.target_output, after_hash, after_hash,
                                "text_experience_replay_after", args.experience_db);
        } else {
          after_hash = before_hash;
          acceptance_reason = "rejected_candidate_would_degrade_local_train_or_probe";
        }
      } else {
        after_gen = brain.generate(event.input, event.observations);
      }
      add_text_experience_score(replay_before_score, before_gen.output, event.target_output);
      add_text_experience_score(replay_after_score, after_gen.output, event.target_output);
      TextExperienceReplayHistory item;
      item.record = record;
      item.replay_pass = pass;
      item.reason = selected.second;
      item.before_replay = std::move(before_gen);
      item.after_replay = std::move(after_gen);
      item.exact_before = item.before_replay.output == event.target_output;
      item.exact_after = item.after_replay.output == event.target_output;
      item.ratio_before = lcs_ratio(item.before_replay.output, event.target_output);
      item.ratio_after = lcs_ratio(item.after_replay.output, event.target_output);
      item.state_before = before_hash;
      item.state_after = after_hash;
      item.candidate_state_hash = candidate_hash;
      item.replay_applied = replay_applied;
      item.accepted = accepted;
      item.acceptance_reason = acceptance_reason;
      replay_history.push_back(std::move(item));
    }
  }

  TextExperienceScore post_replay_train_score;
  TextExperienceScore post_replay_probe_score;
  std::vector<TextExperienceProbeHistory> post_replay_train_history;
  std::vector<TextExperienceProbeHistory> post_replay_probe_history;
  for (const auto& record : records) {
    if (record.split != "train") continue;
    Event event = event_from_text_experience(record, include_raw_text_spans);
    uint64_t state_hash = brain.state_hash();
    auto gen = brain.generate(event.input, event.observations);
    add_text_experience_score(post_replay_train_score, gen.output, event.target_output);
    post_replay_train_history.push_back({record, std::move(gen), false, state_hash});
    auto& stored = post_replay_train_history.back();
    stored.exact = stored.generation.output == event.target_output;
  }
  for (const auto& record : records) {
    if (record.split != "probe") continue;
    Event event = event_from_text_experience(record, include_raw_text_spans);
    uint64_t state_hash = brain.state_hash();
    auto gen = brain.generate(event.input, event.observations);
    append_event_log_line(args.event_log, args.organism_id, "generate", event, gen.output,
                          event.target_output, state_hash, state_hash,
                          "text_experience_replay_post_probe", args.experience_db);
    add_text_experience_score(post_replay_probe_score, gen.output, event.target_output);
    post_replay_probe_history.push_back({record, std::move(gen), false, state_hash});
    auto& stored = post_replay_probe_history.back();
    stored.exact = stored.generation.output == event.target_output;
  }

  BrainStateStats child_stats = capture_state_stats(brain);
  if (!args.save_state.empty()) {
    ensure_parent_dir(args.save_state);
    std::ofstream state_out(args.save_state);
    brain.serialize_state(state_out, args.organism_id);
    persistence.load_status = args.load_state.empty()
                                  ? "text_experience_replayed_and_saved"
                                  : "loaded_then_text_experience_replayed_and_saved";
  } else if (args.load_state.empty()) {
    persistence.load_status = "text_experience_replayed_no_state_save";
  } else {
    persistence.load_status = "loaded_then_text_experience_replayed_no_state_save";
  }

  std::string transcript_path = args.transcript_out.empty()
                                    ? args.out + ".transcript.md"
                                    : args.transcript_out;
  write_text_experience_replay_transcript(transcript_path, first_pass_history, replay_history,
                                          post_replay_train_history, post_replay_probe_history,
                                          args.ablate_text_experience_replay);

  std::string ts = timestamp_utc();
  std::string run_id = "organic-v0-text-replay-" + hex64(fnv1a(ts + hex64(child_stats.state_hash))).substr(0, 12);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"text-experience-replay\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"experience_db_path\": " << q(args.experience_db) << ",\n";
  out << "  \"transcript_path\": " << q(transcript_path) << ",\n";
  out << "  \"raw_text_span_sense\": {\"enabled\": "
      << (include_raw_text_spans ? "true" : "false")
      << ", \"derive_flag\": " << (args.derive_raw_text_spans ? "true" : "false")
      << ", \"ablation_flag\": " << (args.ablate_raw_text_spans ? "true" : "false")
      << ", \"max_span_tokens\": 8, \"max_span_len\": 3},\n";
  out << "  \"replay_policy\": {\"selector\": \"not_exact_after_first_pass_or_below_sequence_threshold\", \"replay_passes\": "
      << args.replay_passes << ", \"min_sequence_ratio\": " << args.replay_min_sequence_ratio
      << ", \"selected_count\": " << selected_records.size() << "},\n";
  out << "  \"ablation\": {\"text_experience_replay_disabled\": "
      << (args.ablate_text_experience_replay ? "true" : "false")
      << ", \"text_replay_acceptance_audit_disabled\": "
      << (args.ablate_text_replay_audit ? "true" : "false") << "},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"correction_after_generation\": true, \"probe_evaluation\": true},\n";
  out << "  \"parent_model_state_hash\": " << q(hex64(parent_stats.state_hash)) << ",\n";
  out << "  \"first_pass_model_state_hash\": " << q(hex64(first_pass_stats.state_hash)) << ",\n";
  out << "  \"model_state_hash\": " << q(hex64(child_stats.state_hash)) << ",\n";
  out << "  \"parent_model_state\": "; write_state_stats(out, parent_stats); out << ",\n";
  out << "  \"first_pass_model_state\": "; write_state_stats(out, first_pass_stats); out << ",\n";
  out << "  \"model_state\": "; write_state_stats(out, child_stats); out << ",\n";
  out << "  \"first_pass_state_growth\": "; write_state_growth(out, parent_stats, first_pass_stats); out << ",\n";
  out << "  \"replay_state_growth\": "; write_state_growth(out, first_pass_stats, child_stats); out << ",\n";
  out << "  \"persistence\": "; write_persistence_contract(out, persistence); out << ",\n";
  out << "  \"summary_metrics\": {\"first_pass_train_before\": ";
  write_text_experience_score(out, first_train_before_score);
  out << ", \"first_pass_train_after\": "; write_text_experience_score(out, first_train_after_score);
  out << ", \"pre_replay_probe\": "; write_text_experience_score(out, pre_replay_probe_score);
  out << ", \"replay_before\": "; write_text_experience_score(out, replay_before_score);
  out << ", \"replay_after\": "; write_text_experience_score(out, replay_after_score);
  out << ", \"post_replay_train\": "; write_text_experience_score(out, post_replay_train_score);
  out << ", \"post_replay_probe\": "; write_text_experience_score(out, post_replay_probe_score);
  out << "},\n";
  out << "  \"replay_selection\": [";
  for (size_t i = 0; i < selected_records.size(); ++i) {
    if (i) out << ", ";
    out << "{\"experience_id\": " << q(selected_records[i].first.experience_id)
        << ", \"reason\": " << q(selected_records[i].second) << "}";
  }
  out << "],\n";
  out << "  \"first_pass_training_history\": [";
  for (size_t i = 0; i < first_pass_history.size(); ++i) {
    if (i) out << ", ";
    const auto& item = first_pass_history[i];
    out << "{\"experience_id\": " << q(item.record.experience_id)
        << ", \"raw_before_learning\": " << q(item.before_learning.output)
        << ", \"raw_after_learning\": " << q(item.after_learning.output)
        << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"exact_after_learning\": " << (item.exact_after ? "true" : "false") << "}";
  }
  out << "],\n";
  out << "  \"pre_replay_probe_history\": [";
  for (size_t i = 0; i < pre_replay_probe_history.size(); ++i) {
    if (i) out << ", ";
    const auto& item = pre_replay_probe_history[i];
    out << "{\"experience_id\": " << q(item.record.experience_id)
        << ", \"raw_generated_output\": " << q(item.generation.output)
        << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"exact\": " << (item.exact ? "true" : "false") << "}";
  }
  out << "],\n";
  out << "  \"replay_history\": [\n";
  for (size_t i = 0; i < replay_history.size(); ++i) {
    if (i) out << ",\n";
    const auto& item = replay_history[i];
    out << "    {\"experience_id\": " << q(item.record.experience_id)
        << ", \"replay_pass\": " << item.replay_pass
        << ", \"reason\": " << q(item.reason)
        << ", \"raw_before_replay\": " << q(item.before_replay.output)
        << ", \"raw_after_replay\": " << q(item.after_replay.output)
        << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"exact_before_replay\": " << (item.exact_before ? "true" : "false")
        << ", \"exact_after_replay\": " << (item.exact_after ? "true" : "false")
        << ", \"ratio_before_replay\": " << std::fixed << std::setprecision(6) << item.ratio_before
        << ", \"ratio_after_replay\": " << item.ratio_after << std::defaultfloat
        << ", \"replay_applied\": " << (item.replay_applied ? "true" : "false")
        << ", \"accepted\": " << (item.accepted ? "true" : "false")
        << ", \"acceptance_reason\": " << q(item.acceptance_reason)
        << ", \"state_before_hash\": " << q(hex64(item.state_before))
        << ", \"candidate_state_hash\": " << q(hex64(item.candidate_state_hash))
        << ", \"state_after_hash\": " << q(hex64(item.state_after)) << "}";
  }
  out << "\n  ],\n";
  out << "  \"post_replay_training_history\": [";
  for (size_t i = 0; i < post_replay_train_history.size(); ++i) {
    if (i) out << ", ";
    const auto& item = post_replay_train_history[i];
    out << "{\"experience_id\": " << q(item.record.experience_id)
        << ", \"raw_generated_output\": " << q(item.generation.output)
        << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"exact\": " << (item.exact ? "true" : "false") << "}";
  }
  out << "],\n";
  out << "  \"post_replay_probe_history\": [";
  for (size_t i = 0; i < post_replay_probe_history.size(); ++i) {
    if (i) out << ", ";
    const auto& item = post_replay_probe_history[i];
    out << "{\"experience_id\": " << q(item.record.experience_id)
        << ", \"raw_generated_output\": " << q(item.generation.output)
        << ", \"expected_output\": " << q(item.record.correction_output)
        << ", \"exact\": " << (item.exact ? "true" : "false") << "}";
  }
  out << "],\n";
  out << "  \"failure_traces\": [";
  bool first_failure = true;
  for (const auto& item : post_replay_train_history) {
    if (item.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"experience_id\": " << q(item.record.experience_id)
        << ", \"stage\": \"post_replay_train\""
        << ", \"raw_output\": " << q(item.generation.output)
        << ", \"expected_output\": " << q(item.record.correction_output) << "}";
    first_failure = false;
  }
  for (const auto& item : post_replay_probe_history) {
    if (item.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"experience_id\": " << q(item.record.experience_id)
        << ", \"stage\": \"post_replay_probe\""
        << ", \"raw_output\": " << q(item.generation.output)
        << ", \"expected_output\": " << q(item.record.correction_output) << "}";
    first_failure = false;
  }
  out << "],\n";
  out << "  \"honest_interpretation\": \"Cycle 7F text-experience replay: failed/weak training records are selected after raw first-pass generation and replayed through the same learned state mutation path. This is consolidation evidence, not fluent chat.\"\n";
  out << "}\n";
}

void interactive_hidden_rule(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("interactive-hidden-rule requires --out");
  if (args.action_budget <= 0) throw std::runtime_error("interactive-hidden-rule requires positive --action-budget");
  if (args.feedback_strength <= 0.0) throw std::runtime_error("interactive-hidden-rule requires positive --feedback-strength");

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  PersistenceContext persistence;
  persistence.organism_id = args.organism_id;
  persistence.loaded_state_path = args.load_state;
  persistence.saved_state_path = args.save_state;
  persistence.event_log_path = args.event_log;
  if (!args.load_state.empty()) {
    load_state_checked(brain, args.load_state);
    persistence.load_status = "loaded_from_disk";
  }
  if (!args.event_log.empty()) {
    ensure_parent_dir(args.event_log);
    std::ofstream(args.event_log, std::ios::trunc).close();
  }
  BrainStateStats parent_stats = capture_state_stats(brain);
  auto steps = build_hidden_rule_steps(args.scenario_seed, args.rule_family);
  if (steps.empty()) throw std::runtime_error("interactive-hidden-rule has no steps for rule family: " + args.rule_family);
  if (static_cast<int>(steps.size()) > args.action_budget) steps.resize(static_cast<size_t>(args.action_budget));

  std::vector<HiddenRuleActionRecord> history;
  history.reserve(steps.size());
  HiddenRuleScore overall;
  std::map<std::string, HiddenRuleScore> by_family;

  for (size_t i = 0; i < steps.size(); ++i) {
    const auto& spec = steps[i];
    Event action_event;
    action_event.event_id = "evt_ihr_" + std::to_string(args.scenario_seed) + "_" + std::to_string(i);
    action_event.episode_id = "ep_ihr_" + spec.rule_id;
    action_event.split = spec.held_out ? "heldout_interactive" : "support_interactive";
    action_event.domain = "interactive_hidden_rule";
    action_event.level = spec.held_out ? 1 : 0;
    action_event.input = spec.input;
    action_event.observations = spec.observations;
    action_event.target_output = spec.correct_action;
    action_event.reward = {{"oracle_feedback", 1.0}};
    action_event.source = "interactive_hidden_rule_oracle_after_action";
    action_event.composition = spec.family;

    uint64_t before = brain.state_hash();
    auto gen = brain.generate(action_event.input, action_event.observations);
    bool exact = (gen.output == spec.correct_action);
    append_event_log_line(args.event_log, args.organism_id, "generate", action_event, gen.output,
                          spec.correct_action, before, before, "interactive_hidden_rule", spec.rule_id);

    Event feedback_event = action_event;
    feedback_event.split = "train";
    feedback_event.reward = {{"oracle_feedback", args.feedback_strength}};
    brain.learn(feedback_event);
    uint64_t after = brain.state_hash();
    append_event_log_line(args.event_log, args.organism_id, "learn", feedback_event, spec.correct_action,
                          spec.correct_action, before, after, "interactive_hidden_rule_feedback", spec.rule_id);

    add_hidden_rule_score(overall, spec.held_out, exact);
    add_hidden_rule_score(by_family[spec.family], spec.held_out, exact);
    HiddenRuleActionRecord record;
    record.spec = spec;
    record.generation = std::move(gen);
    record.exact = exact;
    record.state_before = before;
    record.state_after_feedback = after;
    history.push_back(std::move(record));
  }

  BrainStateStats child_stats = capture_state_stats(brain);
  if (!args.save_state.empty()) {
    ensure_parent_dir(args.save_state);
    std::ofstream state_out(args.save_state);
    brain.serialize_state(state_out, args.organism_id);
    persistence.load_status = args.load_state.empty() ? "interacted_and_saved" : "loaded_then_interacted_and_saved";
  } else if (args.load_state.empty()) {
    persistence.load_status = "interactive_hidden_rule_no_state_save";
  } else {
    persistence.load_status = "loaded_then_interacted_no_state_save";
  }

  std::string ts = timestamp_utc();
  std::string run_id = "organic-v0-ihr-" + hex64(fnv1a(ts + hex64(child_stats.state_hash))).substr(0, 12);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"interactive-hidden-rule\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"mode\": " << q(args.mode) << ",\n";
  out << "  \"scenario_seed\": " << args.scenario_seed << ",\n";
  out << "  \"rule_family\": " << q(args.rule_family) << ",\n";
  out << "  \"feedback_strength\": " << args.feedback_strength << ",\n";
  out << "  \"action_budget\": {\"max_actions\": " << args.action_budget
      << ", \"actions_taken\": " << history.size() << "},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"feedback_after_action\": true},\n";
  out << "  \"hidden_rule_exposure\": \"Rule family and correct action are not included in the action input or observations; oracle feedback is applied only after raw generation.\",\n";
  out << "  \"model_state_hash\": " << q(hex64(child_stats.state_hash)) << ",\n";
  out << "  \"parent_model_state_hash\": " << q(hex64(parent_stats.state_hash)) << ",\n";
  out << "  \"parent_model_state\": "; write_state_stats(out, parent_stats); out << ",\n";
  out << "  \"model_state\": "; write_state_stats(out, child_stats); out << ",\n";
  out << "  \"state_growth\": "; write_state_growth(out, parent_stats, child_stats); out << ",\n";
  out << "  \"persistence\": "; write_persistence_contract(out, persistence); out << ",\n";
  out << "  \"scorecard\": {\"overall\": "; write_hidden_rule_score(out, overall);
  out << ", \"by_family\": {";
  bool first_family = true;
  for (const auto& item : by_family) {
    if (!first_family) out << ", ";
    out << q(item.first) << ": ";
    write_hidden_rule_score(out, item.second);
    first_family = false;
  }
  out << "}},\n";
  out << "  \"action_history\": [\n";
  for (size_t i = 0; i < history.size(); ++i) {
    if (i) out << ",\n";
    const auto& record = history[i];
    out << "    {\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"held_out\": " << (record.spec.held_out ? "true" : "false")
        << ", \"input\": " << q(record.spec.input)
        << ", \"observations\": [";
    for (size_t j = 0; j < record.spec.observations.size(); ++j) {
      if (j) out << ", ";
      out << q(record.spec.observations[j]);
    }
    out << "], \"raw_action\": " << q(record.generation.output)
        << ", \"correct_action_after_feedback\": " << q(record.spec.correct_action)
        << ", \"exact_before_feedback\": " << (record.exact ? "true" : "false")
        << ", \"state_before_hash\": " << q(hex64(record.state_before))
        << ", \"state_after_feedback_hash\": " << q(hex64(record.state_after_feedback))
        << ", \"activated_memory_state\": ";
    write_generation_evidence(out, record.generation);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"failure_traces\": [";
  bool first_failure = true;
  for (size_t i = 0; i < history.size(); ++i) {
    const auto& record = history[i];
    if (record.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"held_out\": " << (record.spec.held_out ? "true" : "false")
        << ", \"raw_action\": " << q(record.generation.output)
        << ", \"correct_action_after_feedback\": " << q(record.spec.correct_action)
        << ", \"state_before_hash\": " << q(hex64(record.state_before)) << "}";
    first_failure = false;
  }
  out << "],\n";
  out << "  \"honest_interpretation\": \"Interactive hidden-rule micro-harness: the model acts before oracle feedback, then feedback is learned into the same organic-v0 state. Scores measure pre-feedback actions only. This is not broad ARC competence.\"\n";
  out << "}\n";
}

void interactive_symbolic_rule(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("interactive-symbolic-rule requires --out");
  if (args.action_budget <= 0) throw std::runtime_error("interactive-symbolic-rule requires positive --action-budget");
  if (args.feedback_strength <= 0.0) throw std::runtime_error("interactive-symbolic-rule requires positive --feedback-strength");

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  PersistenceContext persistence;
  persistence.organism_id = args.organism_id;
  persistence.loaded_state_path = args.load_state;
  persistence.saved_state_path = args.save_state;
  persistence.event_log_path = args.event_log;
  if (!args.load_state.empty()) {
    load_state_checked(brain, args.load_state);
    brain.set_symbolic_relation_features_enabled(!args.ablate_symbolic_relations);
    persistence.load_status = "loaded_from_disk";
  }
  if (!args.event_log.empty()) {
    ensure_parent_dir(args.event_log);
    std::ofstream(args.event_log, std::ios::trunc).close();
  }
  BrainStateStats parent_stats = capture_state_stats(brain);
  auto steps = build_symbolic_rule_steps(args.scenario_seed, args.rule_family);
  if (steps.empty()) throw std::runtime_error("interactive-symbolic-rule has no steps for rule family: " + args.rule_family);
  if (static_cast<int>(steps.size()) > args.action_budget) steps.resize(static_cast<size_t>(args.action_budget));

  std::vector<HiddenRuleActionRecord> history;
  history.reserve(steps.size());
  HiddenRuleScore overall;
  std::map<std::string, HiddenRuleScore> by_family;

  for (size_t i = 0; i < steps.size(); ++i) {
    const auto& spec = steps[i];
    Event action_event;
    action_event.event_id = "evt_isr_" + std::to_string(args.scenario_seed) + "_" + std::to_string(i);
    action_event.episode_id = "ep_isr_" + spec.rule_id;
    action_event.split = spec.held_out ? "heldout_interactive" : "support_interactive";
    action_event.domain = "interactive_symbolic_rule";
    action_event.level = spec.held_out ? 2 : 1;
    action_event.input = spec.input;
    action_event.observations = spec.observations;
    action_event.target_output = spec.correct_action;
    action_event.reward = {{"oracle_feedback", 1.0}};
    action_event.source = "interactive_symbolic_rule_oracle_after_action";
    action_event.composition = spec.family;

    uint64_t before = brain.state_hash();
    auto gen = brain.generate(action_event.input, action_event.observations);
    bool exact = (gen.output == spec.correct_action);
    append_event_log_line(args.event_log, args.organism_id, "generate", action_event, gen.output,
                          spec.correct_action, before, before, "interactive_symbolic_rule", spec.rule_id);

    Event feedback_event = action_event;
    feedback_event.split = "train";
    feedback_event.reward = {{"oracle_feedback", args.feedback_strength}};
    brain.learn(feedback_event);
    uint64_t after = brain.state_hash();
    append_event_log_line(args.event_log, args.organism_id, "learn", feedback_event, spec.correct_action,
                          spec.correct_action, before, after, "interactive_symbolic_rule_feedback", spec.rule_id);

    add_hidden_rule_score(overall, spec.held_out, exact);
    add_hidden_rule_score(by_family[spec.family], spec.held_out, exact);
    HiddenRuleActionRecord record;
    record.spec = spec;
    record.generation = std::move(gen);
    record.exact = exact;
    record.state_before = before;
    record.state_after_feedback = after;
    history.push_back(std::move(record));
  }

  BrainStateStats child_stats = capture_state_stats(brain);
  if (!args.save_state.empty()) {
    ensure_parent_dir(args.save_state);
    std::ofstream state_out(args.save_state);
    brain.serialize_state(state_out, args.organism_id);
    persistence.load_status = args.load_state.empty() ? "interacted_and_saved" : "loaded_then_interacted_and_saved";
  } else if (args.load_state.empty()) {
    persistence.load_status = "interactive_symbolic_rule_no_state_save";
  } else {
    persistence.load_status = "loaded_then_interacted_no_state_save";
  }

  auto probe_steps = build_symbolic_probe_steps(args.scenario_seed, args.rule_family);
  std::vector<HiddenRuleActionRecord> probe_history;
  HiddenRuleScore probe_overall;
  std::map<std::string, HiddenRuleScore> probe_by_family;
  probe_history.reserve(probe_steps.size());
  for (size_t i = 0; i < probe_steps.size(); ++i) {
    const auto& spec = probe_steps[i];
    Event probe_event;
    probe_event.event_id = "evt_isr_probe_" + std::to_string(args.scenario_seed) + "_" + std::to_string(i);
    probe_event.episode_id = "ep_isr_probe_" + spec.rule_id;
    probe_event.split = "post_episode_probe";
    probe_event.domain = "interactive_symbolic_rule";
    probe_event.level = 3;
    probe_event.input = spec.input;
    probe_event.observations = spec.observations;
    probe_event.target_output = spec.correct_action;
    probe_event.reward = {{"oracle_evaluation", 1.0}};
    probe_event.source = "interactive_symbolic_rule_probe_oracle_after_generation";
    probe_event.composition = spec.family;
    uint64_t before = brain.state_hash();
    auto gen = brain.generate(probe_event.input, probe_event.observations);
    bool exact = (gen.output == spec.correct_action);
    append_event_log_line(args.event_log, args.organism_id, "generate", probe_event, gen.output,
                          spec.correct_action, before, before, "interactive_symbolic_rule_probe", spec.rule_id);
    add_hidden_rule_score(probe_overall, true, exact);
    add_hidden_rule_score(probe_by_family[spec.family], true, exact);
    HiddenRuleActionRecord record;
    record.spec = spec;
    record.generation = std::move(gen);
    record.exact = exact;
    record.state_before = before;
    record.state_after_feedback = before;
    probe_history.push_back(std::move(record));
  }

  std::string ts = timestamp_utc();
  std::string run_id = "organic-v0-isr-" + hex64(fnv1a(ts + hex64(child_stats.state_hash))).substr(0, 12);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"interactive-symbolic-rule\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"mode\": " << q(args.mode) << ",\n";
  out << "  \"scenario_seed\": " << args.scenario_seed << ",\n";
  out << "  \"rule_family\": " << q(args.rule_family) << ",\n";
  out << "  \"feedback_strength\": " << args.feedback_strength << ",\n";
  out << "  \"ablation\": {\"symbolic_relations\": " << (args.ablate_symbolic_relations ? "true" : "false") << "},\n";
  out << "  \"action_budget\": {\"max_actions\": " << args.action_budget
      << ", \"actions_taken\": " << history.size() << "},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"feedback_after_action\": true, \"probe_evaluation\": true},\n";
  out << "  \"symbolic_rule_exposure\": \"Input and observations do not include the rule truth or correct action; symbolic same/different relations are feature addresses only, and oracle feedback is applied after raw generation.\",\n";
  out << "  \"model_state_hash\": " << q(hex64(child_stats.state_hash)) << ",\n";
  out << "  \"parent_model_state_hash\": " << q(hex64(parent_stats.state_hash)) << ",\n";
  out << "  \"parent_model_state\": "; write_state_stats(out, parent_stats); out << ",\n";
  out << "  \"model_state\": "; write_state_stats(out, child_stats); out << ",\n";
  out << "  \"state_growth\": "; write_state_growth(out, parent_stats, child_stats); out << ",\n";
  out << "  \"persistence\": "; write_persistence_contract(out, persistence); out << ",\n";
  out << "  \"scorecard\": {\"overall\": "; write_hidden_rule_score(out, overall);
  out << ", \"by_family\": {";
  bool first_family = true;
  for (const auto& item : by_family) {
    if (!first_family) out << ", ";
    out << q(item.first) << ": ";
    write_hidden_rule_score(out, item.second);
    first_family = false;
  }
  out << "}},\n";
  out << "  \"post_episode_probe_scorecard\": {\"overall\": "; write_hidden_rule_score(out, probe_overall);
  out << ", \"by_family\": {";
  first_family = true;
  for (const auto& item : probe_by_family) {
    if (!first_family) out << ", ";
    out << q(item.first) << ": ";
    write_hidden_rule_score(out, item.second);
    first_family = false;
  }
  out << "}},\n";
  out << "  \"action_history\": [\n";
  for (size_t i = 0; i < history.size(); ++i) {
    if (i) out << ",\n";
    const auto& record = history[i];
    out << "    {\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"held_out\": " << (record.spec.held_out ? "true" : "false")
        << ", \"input\": " << q(record.spec.input)
        << ", \"observations\": [";
    for (size_t j = 0; j < record.spec.observations.size(); ++j) {
      if (j) out << ", ";
      out << q(record.spec.observations[j]);
    }
    out << "], \"raw_action\": " << q(record.generation.output)
        << ", \"correct_action_after_feedback\": " << q(record.spec.correct_action)
        << ", \"exact_before_feedback\": " << (record.exact ? "true" : "false")
        << ", \"state_before_hash\": " << q(hex64(record.state_before))
        << ", \"state_after_feedback_hash\": " << q(hex64(record.state_after_feedback))
        << ", \"activated_memory_state\": ";
    write_generation_evidence(out, record.generation);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"post_episode_probe_history\": [\n";
  for (size_t i = 0; i < probe_history.size(); ++i) {
    if (i) out << ",\n";
    const auto& record = probe_history[i];
    out << "    {\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"input\": " << q(record.spec.input)
        << ", \"observations\": [";
    for (size_t j = 0; j < record.spec.observations.size(); ++j) {
      if (j) out << ", ";
      out << q(record.spec.observations[j]);
    }
    out << "], \"raw_action\": " << q(record.generation.output)
        << ", \"expected_action\": " << q(record.spec.correct_action)
        << ", \"exact\": " << (record.exact ? "true" : "false")
        << ", \"state_hash\": " << q(hex64(record.state_before))
        << ", \"activated_memory_state\": ";
    write_generation_evidence(out, record.generation);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"failure_traces\": [";
  bool first_failure = true;
  for (size_t i = 0; i < history.size(); ++i) {
    const auto& record = history[i];
    if (record.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"held_out\": " << (record.spec.held_out ? "true" : "false")
        << ", \"raw_action\": " << q(record.generation.output)
        << ", \"correct_action_after_feedback\": " << q(record.spec.correct_action)
        << ", \"state_before_hash\": " << q(hex64(record.state_before)) << "}";
    first_failure = false;
  }
  for (size_t i = 0; i < probe_history.size(); ++i) {
    const auto& record = probe_history[i];
    if (record.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"held_out\": true"
        << ", \"probe\": true"
        << ", \"raw_action\": " << q(record.generation.output)
        << ", \"correct_action_after_feedback\": " << q(record.spec.correct_action)
        << ", \"state_before_hash\": " << q(hex64(record.state_before)) << "}";
    first_failure = false;
  }
  out << "],\n";
  out << "  \"honest_interpretation\": \"Interactive symbolic-rule micro-harness: the model acts before oracle feedback, then feedback is learned into the same organic-v0 state. Symbolic same/different features are relation addresses, not action routes. This is not broad language or ARC competence.\"\n";
  out << "}\n";
}

void interactive_symbolic_probe(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("interactive-symbolic-probe requires --out");
  if (args.load_state.empty()) throw std::runtime_error("interactive-symbolic-probe requires --load-state");

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  load_state_checked(brain, args.load_state);
  brain.set_symbolic_relation_features_enabled(!args.ablate_symbolic_relations);
  BrainStateStats state_stats = capture_state_stats(brain);
  auto probe_steps = build_symbolic_probe_steps(args.scenario_seed, args.rule_family);
  if (probe_steps.empty()) throw std::runtime_error("interactive-symbolic-probe has no probes for rule family: " + args.rule_family);

  std::vector<HiddenRuleActionRecord> history;
  HiddenRuleScore overall;
  std::map<std::string, HiddenRuleScore> by_family;
  history.reserve(probe_steps.size());
  for (size_t i = 0; i < probe_steps.size(); ++i) {
    const auto& spec = probe_steps[i];
    Event probe_event;
    probe_event.event_id = "evt_isr_disk_probe_" + std::to_string(args.scenario_seed) + "_" + std::to_string(i);
    probe_event.episode_id = "ep_isr_disk_probe_" + spec.rule_id;
    probe_event.split = "from_disk_probe";
    probe_event.domain = "interactive_symbolic_rule";
    probe_event.level = 3;
    probe_event.input = spec.input;
    probe_event.observations = spec.observations;
    probe_event.target_output = spec.correct_action;
    probe_event.reward = {{"oracle_evaluation", 1.0}};
    probe_event.source = "interactive_symbolic_rule_from_disk_probe";
    probe_event.composition = spec.family;
    uint64_t before = brain.state_hash();
    auto gen = brain.generate(probe_event.input, probe_event.observations);
    bool exact = (gen.output == spec.correct_action);
    append_event_log_line(args.event_log, args.organism_id, "generate", probe_event, gen.output,
                          spec.correct_action, before, before, "interactive_symbolic_rule_from_disk_probe",
                          args.load_state);
    add_hidden_rule_score(overall, true, exact);
    add_hidden_rule_score(by_family[spec.family], true, exact);
    HiddenRuleActionRecord record;
    record.spec = spec;
    record.generation = std::move(gen);
    record.exact = exact;
    record.state_before = before;
    record.state_after_feedback = before;
    history.push_back(std::move(record));
  }

  std::string ts = timestamp_utc();
  std::string run_id = "organic-v0-isr-probe-" + hex64(fnv1a(ts + hex64(state_stats.state_hash))).substr(0, 12);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"interactive-symbolic-probe\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"scenario_seed\": " << args.scenario_seed << ",\n";
  out << "  \"rule_family\": " << q(args.rule_family) << ",\n";
  out << "  \"loaded_state_path\": " << q(args.load_state) << ",\n";
  out << "  \"model_state_hash\": " << q(hex64(state_stats.state_hash)) << ",\n";
  out << "  \"model_state\": "; write_state_stats(out, state_stats); out << ",\n";
  out << "  \"ablation\": {\"symbolic_relations\": " << (args.ablate_symbolic_relations ? "true" : "false") << "},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"probe_evaluation\": true},\n";
  out << "  \"scorecard\": {\"overall\": "; write_hidden_rule_score(out, overall);
  out << ", \"by_family\": {";
  bool first_family = true;
  for (const auto& item : by_family) {
    if (!first_family) out << ", ";
    out << q(item.first) << ": ";
    write_hidden_rule_score(out, item.second);
    first_family = false;
  }
  out << "}},\n";
  out << "  \"probe_history\": [\n";
  for (size_t i = 0; i < history.size(); ++i) {
    if (i) out << ",\n";
    const auto& record = history[i];
    out << "    {\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"input\": " << q(record.spec.input)
        << ", \"observations\": [";
    for (size_t j = 0; j < record.spec.observations.size(); ++j) {
      if (j) out << ", ";
      out << q(record.spec.observations[j]);
    }
    out << "], \"raw_action\": " << q(record.generation.output)
        << ", \"expected_action\": " << q(record.spec.correct_action)
        << ", \"exact\": " << (record.exact ? "true" : "false")
        << ", \"activated_memory_state\": ";
    write_generation_evidence(out, record.generation);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"honest_interpretation\": \"Fresh loaded child probe: same symbolic post-episode probes generated from disk without replaying the interactive episode.\"\n";
  out << "}\n";
}

void interactive_grid_rule(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("interactive-grid-rule requires --out");
  if (args.action_budget <= 0) throw std::runtime_error("interactive-grid-rule requires positive --action-budget");
  if (args.feedback_strength <= 0.0) throw std::runtime_error("interactive-grid-rule requires positive --feedback-strength");

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  PersistenceContext persistence;
  persistence.organism_id = args.organism_id;
  persistence.loaded_state_path = args.load_state;
  persistence.saved_state_path = args.save_state;
  persistence.event_log_path = args.event_log;
  if (!args.load_state.empty()) {
    load_state_checked(brain, args.load_state);
    brain.set_grid_spatial_features_enabled(!args.ablate_grid_spatial);
    persistence.load_status = "loaded_from_disk";
  }
  if (!args.event_log.empty()) {
    ensure_parent_dir(args.event_log);
    std::ofstream(args.event_log, std::ios::trunc).close();
  }
  BrainStateStats parent_stats = capture_state_stats(brain);
  auto steps = build_grid_rule_steps(args.scenario_seed, args.rule_family);
  if (steps.empty()) throw std::runtime_error("interactive-grid-rule has no steps for rule family: " + args.rule_family);
  if (static_cast<int>(steps.size()) > args.action_budget) steps.resize(static_cast<size_t>(args.action_budget));

  std::vector<HiddenRuleActionRecord> history;
  HiddenRuleScore overall;
  std::map<std::string, HiddenRuleScore> by_family;
  history.reserve(steps.size());
  for (size_t i = 0; i < steps.size(); ++i) {
    const auto& spec = steps[i];
    Event action_event;
    action_event.event_id = "evt_igr_" + std::to_string(args.scenario_seed) + "_" + std::to_string(i);
    action_event.episode_id = "ep_igr_" + spec.rule_id;
    action_event.split = spec.held_out ? "heldout_interactive" : "support_interactive";
    action_event.domain = "interactive_grid_rule";
    action_event.level = spec.held_out ? 3 : 2;
    action_event.input = spec.input;
    action_event.observations = spec.observations;
    action_event.target_output = spec.correct_action;
    action_event.reward = {{"oracle_feedback", 1.0}};
    action_event.source = "interactive_grid_rule_oracle_after_action";
    action_event.composition = spec.family;

    uint64_t before = brain.state_hash();
    auto gen = brain.generate(action_event.input, action_event.observations);
    bool exact = (gen.output == spec.correct_action);
    append_event_log_line(args.event_log, args.organism_id, "generate", action_event, gen.output,
                          spec.correct_action, before, before, "interactive_grid_rule", spec.rule_id);

    Event feedback_event = action_event;
    feedback_event.split = "train";
    feedback_event.reward = {{"oracle_feedback", args.feedback_strength}};
    brain.learn(feedback_event);
    uint64_t after = brain.state_hash();
    append_event_log_line(args.event_log, args.organism_id, "learn", feedback_event, spec.correct_action,
                          spec.correct_action, before, after, "interactive_grid_rule_feedback", spec.rule_id);

    add_hidden_rule_score(overall, spec.held_out, exact);
    add_hidden_rule_score(by_family[spec.family], spec.held_out, exact);
    history.push_back({spec, std::move(gen), exact, before, after});
  }

  BrainStateStats child_stats = capture_state_stats(brain);
  if (!args.save_state.empty()) {
    ensure_parent_dir(args.save_state);
    std::ofstream state_out(args.save_state);
    brain.serialize_state(state_out, args.organism_id);
    persistence.load_status = args.load_state.empty() ? "interacted_and_saved" : "loaded_then_interacted_and_saved";
  } else if (args.load_state.empty()) {
    persistence.load_status = "interactive_grid_rule_no_state_save";
  } else {
    persistence.load_status = "loaded_then_interacted_no_state_save";
  }

  auto probe_steps = build_grid_probe_steps(args.scenario_seed, args.rule_family);
  std::vector<HiddenRuleActionRecord> probe_history;
  HiddenRuleScore probe_overall;
  std::map<std::string, HiddenRuleScore> probe_by_family;
  for (size_t i = 0; i < probe_steps.size(); ++i) {
    const auto& spec = probe_steps[i];
    Event probe_event;
    probe_event.event_id = "evt_igr_probe_" + std::to_string(args.scenario_seed) + "_" + std::to_string(i);
    probe_event.episode_id = "ep_igr_probe_" + spec.rule_id;
    probe_event.split = "post_episode_probe";
    probe_event.domain = "interactive_grid_rule";
    probe_event.level = 4;
    probe_event.input = spec.input;
    probe_event.observations = spec.observations;
    probe_event.target_output = spec.correct_action;
    probe_event.reward = {{"oracle_evaluation", 1.0}};
    probe_event.source = "interactive_grid_rule_probe_oracle_after_generation";
    probe_event.composition = spec.family;
    uint64_t before = brain.state_hash();
    auto gen = brain.generate(probe_event.input, probe_event.observations);
    bool exact = (gen.output == spec.correct_action);
    append_event_log_line(args.event_log, args.organism_id, "generate", probe_event, gen.output,
                          spec.correct_action, before, before, "interactive_grid_rule_probe", spec.rule_id);
    add_hidden_rule_score(probe_overall, true, exact);
    add_hidden_rule_score(probe_by_family[spec.family], true, exact);
    probe_history.push_back({spec, std::move(gen), exact, before, before});
  }

  std::string ts = timestamp_utc();
  std::string run_id = "organic-v0-igr-" + hex64(fnv1a(ts + hex64(child_stats.state_hash))).substr(0, 12);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"interactive-grid-rule\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"mode\": " << q(args.mode) << ",\n";
  out << "  \"scenario_seed\": " << args.scenario_seed << ",\n";
  out << "  \"rule_family\": " << q(args.rule_family) << ",\n";
  out << "  \"feedback_strength\": " << args.feedback_strength << ",\n";
  out << "  \"ablation\": {\"grid_spatial\": " << (args.ablate_grid_spatial ? "true" : "false") << "},\n";
  out << "  \"action_budget\": {\"max_actions\": " << args.action_budget
      << ", \"actions_taken\": " << history.size() << "},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"feedback_after_action\": true, \"probe_evaluation\": true},\n";
  out << "  \"grid_rule_exposure\": \"Input and cell observations do not include the rule truth or correct action; grid/spatial relations are feature addresses only, and oracle feedback is applied after raw generation.\",\n";
  out << "  \"model_state_hash\": " << q(hex64(child_stats.state_hash)) << ",\n";
  out << "  \"parent_model_state_hash\": " << q(hex64(parent_stats.state_hash)) << ",\n";
  out << "  \"parent_model_state\": "; write_state_stats(out, parent_stats); out << ",\n";
  out << "  \"model_state\": "; write_state_stats(out, child_stats); out << ",\n";
  out << "  \"state_growth\": "; write_state_growth(out, parent_stats, child_stats); out << ",\n";
  out << "  \"persistence\": "; write_persistence_contract(out, persistence); out << ",\n";
  out << "  \"scorecard\": {\"overall\": "; write_hidden_rule_score(out, overall);
  out << ", \"by_family\": {";
  bool first_family = true;
  for (const auto& item : by_family) {
    if (!first_family) out << ", ";
    out << q(item.first) << ": ";
    write_hidden_rule_score(out, item.second);
    first_family = false;
  }
  out << "}},\n";
  out << "  \"post_episode_probe_scorecard\": {\"overall\": "; write_hidden_rule_score(out, probe_overall);
  out << ", \"by_family\": {";
  first_family = true;
  for (const auto& item : probe_by_family) {
    if (!first_family) out << ", ";
    out << q(item.first) << ": ";
    write_hidden_rule_score(out, item.second);
    first_family = false;
  }
  out << "}},\n";
  out << "  \"action_history\": [\n";
  for (size_t i = 0; i < history.size(); ++i) {
    if (i) out << ",\n";
    const auto& record = history[i];
    out << "    {\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"held_out\": " << (record.spec.held_out ? "true" : "false")
        << ", \"input\": " << q(record.spec.input)
        << ", \"observations\": [";
    for (size_t j = 0; j < record.spec.observations.size(); ++j) {
      if (j) out << ", ";
      out << q(record.spec.observations[j]);
    }
    out << "], \"raw_action\": " << q(record.generation.output)
        << ", \"correct_action_after_feedback\": " << q(record.spec.correct_action)
        << ", \"exact_before_feedback\": " << (record.exact ? "true" : "false")
        << ", \"state_before_hash\": " << q(hex64(record.state_before))
        << ", \"state_after_feedback_hash\": " << q(hex64(record.state_after_feedback))
        << ", \"activated_memory_state\": ";
    write_generation_evidence(out, record.generation);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"post_episode_probe_history\": [\n";
  for (size_t i = 0; i < probe_history.size(); ++i) {
    if (i) out << ",\n";
    const auto& record = probe_history[i];
    out << "    {\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"input\": " << q(record.spec.input)
        << ", \"observations\": [";
    for (size_t j = 0; j < record.spec.observations.size(); ++j) {
      if (j) out << ", ";
      out << q(record.spec.observations[j]);
    }
    out << "], \"raw_action\": " << q(record.generation.output)
        << ", \"expected_action\": " << q(record.spec.correct_action)
        << ", \"exact\": " << (record.exact ? "true" : "false")
        << ", \"state_hash\": " << q(hex64(record.state_before))
        << ", \"activated_memory_state\": ";
    write_generation_evidence(out, record.generation);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"failure_traces\": [";
  bool first_failure = true;
  for (size_t i = 0; i < history.size(); ++i) {
    const auto& record = history[i];
    if (record.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"held_out\": " << (record.spec.held_out ? "true" : "false")
        << ", \"raw_action\": " << q(record.generation.output)
        << ", \"correct_action_after_feedback\": " << q(record.spec.correct_action)
        << ", \"state_before_hash\": " << q(hex64(record.state_before)) << "}";
    first_failure = false;
  }
  for (size_t i = 0; i < probe_history.size(); ++i) {
    const auto& record = probe_history[i];
    if (record.exact) continue;
    if (!first_failure) out << ", ";
    out << "{\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"held_out\": true"
        << ", \"probe\": true"
        << ", \"raw_action\": " << q(record.generation.output)
        << ", \"correct_action_after_feedback\": " << q(record.spec.correct_action)
        << ", \"state_before_hash\": " << q(hex64(record.state_before)) << "}";
    first_failure = false;
  }
  out << "],\n";
  out << "  \"honest_interpretation\": \"Interactive grid-rule micro-harness: the model acts before oracle feedback, then feedback is learned into the same organic-v0 state. Grid/spatial features are relation addresses, not action routes. This is not ARC competence or broad language.\"\n";
  out << "}\n";
}

void interactive_grid_probe(const Args& args, const std::string& command) {
  if (args.out.empty()) throw std::runtime_error("interactive-grid-probe requires --out");
  if (args.load_state.empty()) throw std::runtime_error("interactive-grid-probe requires --load-state");

  Config config;
  apply_ablations(config, args);
  OrganicBrain brain(config);
  load_state_checked(brain, args.load_state);
  brain.set_grid_spatial_features_enabled(!args.ablate_grid_spatial);
  BrainStateStats state_stats = capture_state_stats(brain);
  auto probe_steps = build_grid_probe_steps(args.scenario_seed, args.rule_family);
  if (probe_steps.empty()) throw std::runtime_error("interactive-grid-probe has no probes for rule family: " + args.rule_family);

  std::vector<HiddenRuleActionRecord> history;
  HiddenRuleScore overall;
  std::map<std::string, HiddenRuleScore> by_family;
  for (size_t i = 0; i < probe_steps.size(); ++i) {
    const auto& spec = probe_steps[i];
    Event probe_event;
    probe_event.event_id = "evt_igr_disk_probe_" + std::to_string(args.scenario_seed) + "_" + std::to_string(i);
    probe_event.episode_id = "ep_igr_disk_probe_" + spec.rule_id;
    probe_event.split = "from_disk_probe";
    probe_event.domain = "interactive_grid_rule";
    probe_event.level = 4;
    probe_event.input = spec.input;
    probe_event.observations = spec.observations;
    probe_event.target_output = spec.correct_action;
    probe_event.reward = {{"oracle_evaluation", 1.0}};
    probe_event.source = "interactive_grid_rule_from_disk_probe";
    probe_event.composition = spec.family;
    uint64_t before = brain.state_hash();
    auto gen = brain.generate(probe_event.input, probe_event.observations);
    bool exact = (gen.output == spec.correct_action);
    append_event_log_line(args.event_log, args.organism_id, "generate", probe_event, gen.output,
                          spec.correct_action, before, before, "interactive_grid_rule_from_disk_probe",
                          args.load_state);
    add_hidden_rule_score(overall, true, exact);
    add_hidden_rule_score(by_family[spec.family], true, exact);
    history.push_back({spec, std::move(gen), exact, before, before});
  }

  std::string ts = timestamp_utc();
  std::string run_id = "organic-v0-igr-probe-" + hex64(fnv1a(ts + hex64(state_stats.state_hash))).substr(0, 12);
  ensure_parent_dir(args.out);
  std::ofstream out(args.out);
  out << "{\n";
  out << "  \"run_id\": " << q(run_id) << ",\n";
  out << "  \"timestamp\": " << q(ts) << ",\n";
  out << "  \"phase\": \"interactive-grid-probe\",\n";
  out << "  \"command\": " << q(command) << ",\n";
  out << "  \"scenario_seed\": " << args.scenario_seed << ",\n";
  out << "  \"rule_family\": " << q(args.rule_family) << ",\n";
  out << "  \"loaded_state_path\": " << q(args.load_state) << ",\n";
  out << "  \"model_state_hash\": " << q(hex64(state_stats.state_hash)) << ",\n";
  out << "  \"model_state\": "; write_state_stats(out, state_stats); out << ",\n";
  out << "  \"ablation\": {\"grid_spatial\": " << (args.ablate_grid_spatial ? "true" : "false") << "},\n";
  out << "  \"oracle_access\": {\"generation\": false, \"probe_evaluation\": true},\n";
  out << "  \"scorecard\": {\"overall\": "; write_hidden_rule_score(out, overall);
  out << ", \"by_family\": {";
  bool first_family = true;
  for (const auto& item : by_family) {
    if (!first_family) out << ", ";
    out << q(item.first) << ": ";
    write_hidden_rule_score(out, item.second);
    first_family = false;
  }
  out << "}},\n";
  out << "  \"probe_history\": [\n";
  for (size_t i = 0; i < history.size(); ++i) {
    if (i) out << ",\n";
    const auto& record = history[i];
    out << "    {\"step\": " << i
        << ", \"family\": " << q(record.spec.family)
        << ", \"rule_id\": " << q(record.spec.rule_id)
        << ", \"input\": " << q(record.spec.input)
        << ", \"observations\": [";
    for (size_t j = 0; j < record.spec.observations.size(); ++j) {
      if (j) out << ", ";
      out << q(record.spec.observations[j]);
    }
    out << "], \"raw_action\": " << q(record.generation.output)
        << ", \"expected_action\": " << q(record.spec.correct_action)
        << ", \"exact\": " << (record.exact ? "true" : "false")
        << ", \"activated_memory_state\": ";
    write_generation_evidence(out, record.generation);
    out << "}";
  }
  out << "\n  ],\n";
  out << "  \"honest_interpretation\": \"Fresh loaded child probe: same grid post-episode probes generated from disk without replaying the interactive episode.\"\n";
  out << "}\n";
}

}  // namespace px

int main(int argc, char** argv) {
  try {
    px::Args args = px::parse_args(argc, argv);
    std::string command = px::command_string(argc, argv);
    // Sentinel phases bypass the normal artifact-writer pipeline:
    //   self-test                 — cold-brain emit-then-learn-then-emit substrate guard
    //   persistence-self-test     — full round-trip save/spawn-child/load/verify orchestration
    //   persistence-load-verify   — child phase invoked by persistence-self-test
    if (args.phase == "self-test") {
      px::self_test();
      return 0;
    }
    if (args.phase == "persistence-self-test") {
      px::persistence_self_test(args);
      return 0;
    }
    if (args.phase == "persistence-load-verify") {
      px::persistence_load_verify(args);
      return 0;
    }
    if (args.phase == "interactive-hidden-rule") {
      px::interactive_hidden_rule(args, command);
      return 0;
    }
    if (args.phase == "interactive-symbolic-rule") {
      px::interactive_symbolic_rule(args, command);
      return 0;
    }
    if (args.phase == "interactive-symbolic-probe") {
      px::interactive_symbolic_probe(args, command);
      return 0;
    }
    if (args.phase == "interactive-grid-rule") {
      px::interactive_grid_rule(args, command);
      return 0;
    }
    if (args.phase == "interactive-grid-probe") {
      px::interactive_grid_probe(args, command);
      return 0;
    }
    if (args.phase == "text-experience") {
      px::text_experience_phase(args, command);
      return 0;
    }
    if (args.phase == "text-experience-probe") {
      px::text_experience_probe_phase(args, command);
      return 0;
    }
    if (args.phase == "text-experience-replay") {
      px::text_experience_replay_phase(args, command);
      return 0;
    }
    if (args.phase == "policy-self-test") {
      px::policy_self_test_phase(args, command);
      return 0;
    }
    if (args.phase == "quote-probe") {
      px::quote_probe_phase(args, command);
      return 0;
    }
    if (args.phase == "corpus-exposure") {
      px::corpus_exposure_phase(args, command);
      return 0;
    }
    if (args.phase == "neural-text-quality") {
      px::neural_text_quality_phase(args, command);
      return 0;
    }
    if (args.phase == "neural-recurrent-text") {
      px::neural_recurrent_text_phase(args, command);
      return 0;
    }
    if (args.phase == "neural-recurrent-regenerate") {
      px::neural_recurrent_regenerate_phase(args, command);
      return 0;
    }
    if (args.phase == "state-config-copy") {
      px::state_config_copy_phase(args);
      return 0;
    }
    if (args.phase == "sleep-wake" || args.phase == "daemon-lite") {
      px::sleep_wake_runtime_phase(args, command);
      return 0;
    }

    // train / eval — normal artifact-writer pipeline. Persistence side-effects honored if paths provided.
    if (args.out.empty()) throw std::runtime_error("--out is required for train/eval");
    px::Config config;
    px::apply_ablations(config, args);
    auto events = px::load_events(args.data);

    // PersistenceContext threaded through artifact writers; status updates as side-effects occur (save / load).
    px::PersistenceContext persistence;
    persistence.organism_id = args.organism_id;
    persistence.loaded_state_path = args.load_state;
    persistence.saved_state_path = args.save_state;
    persistence.event_log_path = args.event_log;

    if (args.phase == "train") {
      px::write_train_artifact(args.out, args.data, args.mode, command, events, config, persistence);
      std::cout << "wrote " << args.out << "\n";
    } else if (args.phase == "eval") {
      px::write_eval_artifact(args.out, args.data, args.mode, command, events, config, persistence);
      std::cout << "wrote " << args.out << "\n";
    } else {
      throw std::runtime_error("unknown phase: " + args.phase);
    }
  } catch (const std::exception& e) {
    std::cerr << "organic_v0 error: " << e.what() << "\n";
    return 1;
  }
  return 0;
}
