#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <numeric>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
#include <vector>

namespace px {

constexpr int kDim = 256;
constexpr int kAscii = 128;
// kMaxRoles caps the segment-mode action-space expansion (cycle-3 mechanism).
// WHAT: extra action ids past kAscii reserved for "start copy span from role-token R".
// WHY: per docs/artifacts/CYCLE3_MECHANISM.md, the generator's softmax now ranges over
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

struct GenerationStep {
  int position = 0;
  unsigned char chosen = 0;
  double score = 0.0;
  std::vector<std::pair<unsigned char, double>> top_chars;
  size_t active_state_feature_count = 0;
  size_t active_slot_copy_count = 0;
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

Event event_from_text_experience(const TextExperienceRecord& record) {
  Event event;
  event.event_id = record.experience_id;
  event.episode_id = record.session_id;
  event.split = record.split == "train" ? "train" : "probe";
  event.domain = "text_experience";
  event.level = record.split == "train" ? 0 : 1;
  event.input = record.input_text;
  event.observations = record.observations;
  event.target_output = record.correction_output;
  event.reward = record.reward;
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
          pos += span;
          previous = (last_in_span < kAscii) ? last_in_span : previous;
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
        }
        continue;
      }

      auto active = state_features(features, previous, pos);
      add_trace_span_position_features(active, gen.activations, pos);
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
        }
        // else: single-char filler; never enter copy_mode; remaining emissions resume in
        // literal mode at the next iteration.
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
    config_.use_trace_span_position_features = false;
    config_.use_numeric_derived_features = false;
    config_.use_threshold_derived_features = false;
    config_.use_modular_derived_features = false;
    config_.use_relation_projection = false;
    config_.use_symbolic_relation_features = false;
    config_.use_grid_spatial_features = false;
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
  //   See docs/artifacts/CYCLE3_MECHANISM.md §"Builder-Law boundary call".
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
  uint64_t state_hash = 0;
};

BrainStateStats capture_state_stats(const OrganicBrain& brain) {
  BrainStateStats stats;
  stats.trace_count = brain.trace_count();
  stats.connection_feature_count = brain.connection_feature_count();
  stats.connection_nonzero_count = brain.connection_nonzero_count();
  stats.slot_copy_link_count = brain.slot_copy_link_count();
  stats.learned_char_count = brain.learned_char_count();
  stats.state_hash = brain.state_hash();
  return stats;
}

void write_state_stats(std::ostream& out, const BrainStateStats& stats) {
  out << "{\"trace_count\": " << stats.trace_count
      << ", \"connection_feature_count\": " << stats.connection_feature_count
      << ", \"connection_nonzero_count\": " << stats.connection_nonzero_count
      << ", \"slot_copy_link_count\": " << stats.slot_copy_link_count
      << ", \"learned_char_count\": " << stats.learned_char_count
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
      << delta(child.learned_char_count, parent.learned_char_count) << "}";
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
  std::string verify_event_id;
  std::string organism_id = "raphael-local-0001";
  std::string rule_family = "all";
  std::string experience_db = "experience/organic-v0/text_experience_seed_v0.jsonl";
  std::string transcript_out;
  uint64_t scenario_seed = 7001;
  int action_budget = 64;
  double feedback_strength = 2.0;
  bool ablate_trace_id = false;
  bool ablate_numeric_derived = false;
  bool ablate_threshold_derived = false;
  bool ablate_modular_derived = false;
  bool ablate_relation_projection = false;
  bool ablate_symbolic_relations = false;
  bool ablate_grid_spatial = false;
  bool ablate_text_experience_learning = false;
};

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
    else if (key == "--verify-event") args.verify_event_id = need_value(key);
    else if (key == "--organism-id") args.organism_id = need_value(key);
    else if (key == "--rule-family") args.rule_family = need_value(key);
    else if (key == "--experience-db") args.experience_db = need_value(key);
    else if (key == "--transcript-out") args.transcript_out = need_value(key);
    else if (key == "--scenario-seed") args.scenario_seed = std::stoull(need_value(key));
    else if (key == "--action-budget") args.action_budget = std::stoi(need_value(key));
    else if (key == "--feedback-strength") args.feedback_strength = std::stod(need_value(key));
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
  BrainStateStats parent_stats = capture_state_stats(brain);
  TextExperienceScore train_before_score;
  TextExperienceScore train_after_score;
  TextExperienceScore probe_score;
  std::vector<TextExperienceTrainHistory> train_history;
  std::vector<TextExperienceProbeHistory> probe_history;

  for (const auto& record : records) {
    if (record.split != "train") continue;
    Event event = event_from_text_experience(record);
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
    Event event = event_from_text_experience(record);
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
  BrainStateStats state_stats = capture_state_stats(brain);
  TextExperienceScore probe_score;
  std::vector<TextExperienceProbeHistory> probe_history;
  for (const auto& record : records) {
    if (record.split != "probe") continue;
    Event event = event_from_text_experience(record);
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
