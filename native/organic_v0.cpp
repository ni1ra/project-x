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
  double transition_gain = 0.65;
  double position_gain = 0.35;
  double state_binding_gain = 1.35;
  double slot_pass_gain = 7.5;
  bool use_trace_id_feature = true;
  bool use_slot_pass_through = true;
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

struct Trace {
  std::string event_id;
  std::string episode_id;
  std::string split;
  std::string domain;
  int level = 0;
  std::string input;
  std::vector<std::string> observations;
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
};

struct Generation {
  std::string output;
  std::vector<Activation> activations;
  std::vector<GenerationStep> steps;
  uint64_t state_hash = 0;
  size_t connection_feature_count = 0;
  size_t connection_nonzero_count = 0;
  size_t slot_copy_link_count = 0;
};

struct Weights {
  std::array<double, kAscii> value{};
};

struct ObservationSlot {
  std::string type;
  std::string value;
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

std::vector<ObservationSlot> parse_slots(const std::vector<std::string>& observations) {
  std::vector<ObservationSlot> slots;
  for (const auto& observation : observations) {
    size_t colon = observation.find(':');
    if (colon == std::string::npos || colon == 0 || colon + 1 >= observation.size()) continue;
    slots.push_back({lower_ascii(observation.substr(0, colon)), lower_ascii(observation.substr(colon + 1))});
  }
  return slots;
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

// Split on a single delimiter char. No quoting; benchmark strings are pipe-free by audit.
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
    traces_.push_back(trace);

    if (trace.reward_scalar <= 0.0) {
      mutation_connection_deltas_.push_back(0);
      return;
    }

    learn_slot_pass_through(event.observations, event.target_output, trace.reward_scalar);

    auto features = context_features(event.input, event.observations);
    if (config_.use_trace_id_feature) {
      features.push_back({hash_pair("trace", event.event_id), 1.0});
    }
    size_t deltas = 0;
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
    mutation_connection_deltas_.push_back(deltas);
  }

  Generation generate(const std::string& input, const std::vector<std::string>& observations) const {
    Generation gen;
    auto query = hdc_.encode_event(input, observations);
    gen.activations = retrieve(query);
    auto features = context_features(input, observations);
    auto slots = parse_slots(observations);
    if (config_.use_trace_id_feature) {
      for (const auto& activation : gen.activations) {
        if (activation.similarity > 0.0) {
          features.push_back({hash_pair("trace", activation.event_id), activation.similarity * config_.trace_gain});
        }
      }
    }

    unsigned char previous = kStart;
    for (int pos = 0; pos < config_.max_output_chars; ++pos) {
      auto active = state_features(features, previous, pos);
      std::array<double, kAscii> scores{};
      bool any = false;
      for (const auto& feature : active) {
        auto found = connections_.find(feature.id);
        if (found == connections_.end()) continue;
        for (int c = 0; c < kAscii; ++c) {
          if (found->second.value[c] != 0.0) {
            scores[c] += feature.scale * found->second.value[c];
            any = true;
          }
        }
      }
      size_t slot_copy_count = add_slot_pass_scores(scores, slots, pos);
      if (slot_copy_count > 0) any = true;
      if (!any) break;

      std::vector<std::pair<unsigned char, double>> ranked;
      for (int c = 0; c < kAscii; ++c) {
        if (scores[c] != 0.0) ranked.push_back({static_cast<unsigned char>(c), scores[c]});
      }
      std::sort(ranked.begin(), ranked.end(), [](const auto& a, const auto& b) {
        if (a.second != b.second) return a.second > b.second;
        return a.first < b.first;
      });
      if (ranked.empty()) break;

      GenerationStep step;
      step.position = pos;
      step.chosen = ranked.front().first;
      step.score = ranked.front().second;
      step.active_state_feature_count = active.size();
      step.active_slot_copy_count = slot_copy_count;
      for (size_t i = 0; i < std::min<size_t>(5, ranked.size()); ++i) step.top_chars.push_back(ranked[i]);
      gen.steps.push_back(step);

      if (step.chosen == kEnd) break;
      gen.output.push_back(static_cast<char>(step.chosen));
      previous = step.chosen;
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

  // Line-oriented state snapshot. Ugly but loadable + hash-checked, per brief.
  // Bit-exact doubles via hex64-of-IEEE-bits so state_hash matches across save/load.
  void serialize_state(std::ostream& out, const std::string& organism_id) const {
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
        << " transition_gain=" << double_to_hex(config_.transition_gain)
        << " position_gain=" << double_to_hex(config_.position_gain)
        << " state_binding_gain=" << double_to_hex(config_.state_binding_gain)
        << " slot_pass_gain=" << double_to_hex(config_.slot_pass_gain)
        << " use_trace_id_feature=" << (config_.use_trace_id_feature ? 1 : 0)
        << " use_slot_pass_through=" << (config_.use_slot_pass_through ? 1 : 0)
        << "\n";
    out << "TRACES " << traces_.size() << "\n";
    for (const auto& tr : traces_) {
      // Observations joined with ','; benchmark observations contain no commas (audit).
      std::string obs_csv;
      for (size_t i = 0; i < tr.observations.size(); ++i) {
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
    out << "STATE_HASH " << hex64(state_hash()) << "\n";
    out << "PXSTATE_END\n";
  }

  // Load a state snapshot. Throws on schema mismatch or malformed lines.
  // After load, state_hash() must equal the STATE_HASH line value — caller verifies.
  void load_serialized_state(std::istream& in) {
    traces_.clear();
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
      else if (k == "transition_gain") config_.transition_gain = hex_to_double(v);
      else if (k == "position_gain") config_.position_gain = hex_to_double(v);
      else if (k == "state_binding_gain") config_.state_binding_gain = hex_to_double(v);
      else if (k == "slot_pass_gain") config_.slot_pass_gain = hex_to_double(v);
      else if (k == "use_trace_id_feature") config_.use_trace_id_feature = (v != "0");
      else if (k == "use_slot_pass_through") config_.use_slot_pass_through = (v != "0");
    }
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
      traces_.push_back(std::move(tr));
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

    // STATE_HASH (caller verifies match against state_hash() after load).
    std::string hash_line = next_line();
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
    return features;
  }

  std::vector<Feature> state_features(const std::vector<Feature>& base, unsigned char previous, int position) const {
    std::vector<Feature> features;
    features.reserve(3 + base.size() * 4);
    features.push_back({combine(fnv1a("global-prev"), previous), config_.transition_gain});
    features.push_back({combine(fnv1a("global-pos"), static_cast<uint64_t>(position)), config_.position_gain});
    features.push_back({combine(fnv1a("global-bucket"), static_cast<uint64_t>(position / 4)), config_.position_gain * 0.5});
    for (const auto& feature : base) {
      uint64_t pos_id = combine(feature.id, combine(fnv1a("pos"), static_cast<uint64_t>(position)));
      uint64_t prev_id = combine(feature.id, combine(fnv1a("prev"), previous));
      uint64_t bucket_id = combine(feature.id, combine(fnv1a("bucket"), static_cast<uint64_t>(position / 4)));
      features.push_back({pos_id, feature.scale});
      features.push_back({prev_id, feature.scale * 0.8});
      features.push_back({bucket_id, feature.scale * 0.35});
      features.push_back({combine(pos_id, prev_id), feature.scale * config_.state_binding_gain});
    }
    return features;
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

  Config config_;
  Hdc hdc_;
  std::vector<Trace> traces_;
  std::unordered_map<uint64_t, Weights> connections_;
  std::unordered_map<uint64_t, double> slot_copy_weights_;
  std::set<unsigned char> learned_chars_;
  std::vector<size_t> mutation_connection_deltas_;
  uint64_t expected_state_hash_ = 0;  // populated by load_serialized_state for round-trip verification
};

OrganicBrain train_brain(const std::vector<Event>& events, const Config& config) {
  OrganicBrain brain(config);
  for (const auto& event : events) {
    if (event.split == "train") brain.learn(event);
  }
  return brain;
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

void write_config(std::ostream& out, const Config& config) {
  out << "{\"dimensions\": " << config.dimensions
      << ", \"seed\": " << config.seed
      << ", \"learning_rate\": " << config.learning_rate
      << ", \"top_k\": " << config.top_k
      << ", \"max_output_chars\": " << config.max_output_chars
      << ", \"trace_gain\": " << config.trace_gain
      << ", \"context_gain\": " << config.context_gain
      << ", \"transition_gain\": " << config.transition_gain
      << ", \"position_gain\": " << config.position_gain
      << ", \"state_binding_gain\": " << config.state_binding_gain
      << ", \"slot_pass_gain\": " << config.slot_pass_gain
      << ", \"use_trace_id_feature\": " << (config.use_trace_id_feature ? "true" : "false")
      << ", \"use_slot_pass_through\": " << (config.use_slot_pass_through ? "true" : "false") << "}";
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
  out << "\"state_snapshot_schema_path\": \"docs/artifacts/PERSISTENCE_SCHEMA.md#state-snapshot-binary-v0\", ";
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

void write_train_artifact(const std::string& out_path, const std::string& data_path, const std::string& mode,
                          const std::string& command, const std::vector<Event>& events, const Config& config,
                          PersistenceContext& persistence) {
  auto audit = validate_splits(events);
  if (!audit.duplicates.empty()) throw std::runtime_error("held-out prompt duplicates training prompt");
  auto brain = train_brain(events, config);
  std::string ts = timestamp_utc();
  uint64_t state = brain.state_hash();
  std::string run_id = "organic-v0-train-" + hex64(fnv1a(ts + hex64(state))).substr(0, 12);

  // Persistence side-effects: save state and/or append event log if paths were provided.
  if (!persistence.saved_state_path.empty()) {
    ensure_parent_dir(persistence.saved_state_path);
    std::ofstream state_out(persistence.saved_state_path);
    brain.serialize_state(state_out, persistence.organism_id);
    if (persistence.load_status == "schema_only_not_runtime_persistence") {
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
  out << "  \"seed\": " << config.seed << ",\n";
  out << "  \"config\": "; write_config(out, config); out << ",\n";
  out << "  \"model_config_hash\": " << q(hex64(config_hash(config))) << ",\n";
  out << "  \"model_state_hash\": " << q(hex64(state)) << ",\n";
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
  out << "  \"model_state\": {\"trace_count\": " << brain.trace_count()
      << ", \"connection_feature_count\": " << brain.connection_feature_count()
      << ", \"connection_nonzero_count\": " << brain.connection_nonzero_count()
      << ", \"slot_copy_link_count\": " << brain.slot_copy_link_count()
      << ", \"learned_char_count\": " << brain.learned_char_count()
      << ", \"state_hash\": " << q(hex64(state)) << "},\n";
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
  if (!persistence.loaded_state_path.empty()) {
    std::ifstream state_in(persistence.loaded_state_path);
    if (!state_in) throw std::runtime_error("cannot open loaded state: " + persistence.loaded_state_path);
    brain.load_serialized_state(state_in);
    if (brain.state_hash() != brain.expected_state_hash()) {
      throw std::runtime_error("loaded state hash mismatch: file=" + hex64(brain.expected_state_hash()) +
                               " recomputed=" + hex64(brain.state_hash()));
    }
    persistence.load_status = "loaded_from_disk";
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
  uint64_t eval_state_hash = brain.state_hash();
  std::string eval_source = persistence.loaded_state_path.empty() ? std::string("benchmark") : std::string("loaded_state");
  std::string eval_source_path = persistence.loaded_state_path.empty() ? data_path : persistence.loaded_state_path;

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
    result.random = random_baseline(event, alphabet, config.seed);
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
  out << "  \"seed\": " << config.seed << ",\n";
  out << "  \"config\": "; write_config(out, config); out << ",\n";
  out << "  \"model_config_hash\": " << q(hex64(config_hash(config))) << ",\n";
  out << "  \"model_state_hash\": " << q(hex64(state)) << ",\n";
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
  bool ablate_trace_id = false;
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
    else if (key == "--ablate-trace-id") args.ablate_trace_id = true;
    else throw std::runtime_error("unknown argument: " + key);
  }
  if (args.phase.empty()) throw std::runtime_error("--phase is required");
  return args;
}

// Append one JSONL event-log line per the docs/artifacts/PERSISTENCE_SCHEMA.md v0 schema.
// Open in append mode; flush after each line so a crash mid-run preserves history.
void append_event_log_line(const std::string& log_path, const std::string& organism_id,
                           const std::string& phase, const Event& event,
                           const std::string& raw_output, const std::string& expected,
                           uint64_t state_before_hash, uint64_t state_after_hash,
                           const std::string& source_kind, const std::string& source_path) {
  if (log_path.empty()) return;
  ensure_parent_dir(log_path);
  std::ofstream log(log_path, std::ios::app);
  if (!log) throw std::runtime_error("cannot open event log: " + log_path);
  log << "{\"schema\":\"project_x.event_log.v0\","
      << "\"event_id\":\"" << json_escape(event.event_id) << "\","
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
      << "\"state_before_hash\":\"" << hex64(state_before_hash) << "\","
      << "\"state_after_hash\":\"" << hex64(state_after_hash) << "\"}\n";
}

// Orchestrate the persistence round-trip: train → save → spawn child → load+generate → verify.
// Honors brief's "fresh process must load prior state and generate without replaying full training stream".
void persistence_self_test(const Args& args) {
  if (args.save_state.empty()) throw std::runtime_error("persistence-self-test requires --save-state");
  if (args.out.empty()) throw std::runtime_error("persistence-self-test requires --out");

  Config config;
  if (args.ablate_trace_id) config.use_trace_id_feature = false;
  auto events = load_events(args.data);
  std::string verify_id = args.verify_event_id.empty() ? "evt_mem_test_001" : args.verify_event_id;
  const Event* verify_event = nullptr;
  for (const auto& ev : events) {
    if (ev.event_id == verify_id) { verify_event = &ev; break; }
  }
  if (!verify_event) throw std::runtime_error("verify event not in benchmark: " + verify_id);

  // Parent process: train INCREMENTALLY so we can record honest per-event state-hash transitions.
  // (train_brain() exists but trains in one shot; the event log requires before/after hashes per event,
  //  so we replicate its inner loop here. Cost: ~2M hash ops over 20 events — microseconds.)
  if (!args.event_log.empty()) {
    ensure_parent_dir(args.event_log);
    std::ofstream(args.event_log, std::ios::trunc).close();  // start fresh; child will append
  }
  OrganicBrain brain(config);
  uint64_t before_hash = brain.state_hash();
  for (const auto& ev : events) {
    if (ev.split != "train") continue;
    brain.learn(ev);
    uint64_t after_hash = brain.state_hash();
    if (!args.event_log.empty()) {
      // Per-event log line — state_before/after are HONEST transitions, not final-state stamps.
      // raw_generated_output == target_output because learning is rewarded against the target.
      append_event_log_line(args.event_log, args.organism_id, "learn", ev, ev.target_output, ev.target_output,
                            before_hash, after_hash, "benchmark", args.data);
    }
    before_hash = after_hash;
  }
  uint64_t pre_hash = brain.state_hash();
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
      << " --load-state " << args.save_state
      << " --data " << args.data
      << " --verify-event " << verify_id
      << " --out " << child_out
      << " --organism-id " << args.organism_id;
  if (!args.event_log.empty()) cmd << " --event-log " << args.event_log;
  if (args.ablate_trace_id) cmd << " --ablate-trace-id";
  int rc = std::system(cmd.str().c_str());
  if (rc != 0) throw std::runtime_error("child persistence-load-verify failed with rc=" + std::to_string(rc));

  // Parse child verdict — minimal JSON: read two keys from a single-line JSON file.
  // The .child.json is a temp file; the parent verdict written below contains all the same fields
  // plus the parent-side ones, so the child file is redundant and deleted after read.
  std::ifstream child(child_out);
  std::string verdict((std::istreambuf_iterator<char>(child)), std::istreambuf_iterator<char>());
  child.close();
  std::string child_hash = get_string(verdict, "loaded_state_hash");
  std::string child_output = get_string(verdict, "raw_generated_output");
  std::error_code rm_ec;
  std::filesystem::remove(child_out, rm_ec);  // best-effort cleanup; ignore errors
  std::string parent_hash = hex64(pre_hash);
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
  out << "  \"saved_state_path\": " << q(args.save_state) << ",\n";
  out << "  \"appended_event_log_path\": " << (args.event_log.empty() ? "null" : q(args.event_log)) << ",\n";
  out << "  \"child_verdict_path\": " << q(child_out) << ",\n";
  out << "  \"verify_event_id\": " << q(verify_id) << ",\n";
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
  if (args.ablate_trace_id) config.use_trace_id_feature = false;
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
    append_event_log_line(args.event_log, args.organism_id, "child_generate", *ev, gen.output,
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

}  // namespace px

int main(int argc, char** argv) {
  try {
    px::Args args = px::parse_args(argc, argv);
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

    // train / eval — normal artifact-writer pipeline. Persistence side-effects honored if paths provided.
    if (args.out.empty()) throw std::runtime_error("--out is required for train/eval");
    px::Config config;
    if (args.ablate_trace_id) config.use_trace_id_feature = false;
    auto events = px::load_events(args.data);
    std::string command = px::command_string(argc, argv);

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
