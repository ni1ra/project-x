#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
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
  bool use_trace_id_feature = true;
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
};

struct Generation {
  std::string output;
  std::vector<Activation> activations;
  std::vector<GenerationStep> steps;
  uint64_t state_hash = 0;
  size_t connection_feature_count = 0;
  size_t connection_nonzero_count = 0;
};

struct Weights {
  std::array<double, kAscii> value{};
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
  return event;
}

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
  std::vector<std::string> duplicates;
};

SplitAudit validate_splits(const std::vector<Event>& events) {
  SplitAudit audit;
  std::set<std::string> train_inputs;
  for (const auto& event : events) {
    audit.splits[event.split] += 1;
    audit.levels_by_domain[event.domain].insert(event.level);
    if (event.split == "train") train_inputs.insert(event.input);
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
      for (size_t i = 0; i < std::min<size_t>(5, ranked.size()); ++i) step.top_chars.push_back(ranked[i]);
      gen.steps.push_back(step);

      if (step.chosen == kEnd) break;
      gen.output.push_back(static_cast<char>(step.chosen));
      previous = step.chosen;
    }
    gen.state_hash = state_hash();
    gen.connection_feature_count = connections_.size();
    gen.connection_nonzero_count = connection_nonzero_count();
    return gen;
  }

  uint64_t state_hash() const {
    uint64_t h = fnv1a("organic-v0-state");
    h = combine(h, static_cast<uint64_t>(traces_.size()));
    h = combine(h, static_cast<uint64_t>(connections_.size()));
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

 private:
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
  std::set<unsigned char> learned_chars_;
  std::vector<size_t> mutation_connection_deltas_;
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
      << ", \"use_trace_id_feature\": " << (config.use_trace_id_feature ? "true" : "false") << "}";
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
                          const std::string& command, const std::vector<Event>& events, const Config& config) {
  auto audit = validate_splits(events);
  if (!audit.duplicates.empty()) throw std::runtime_error("held-out prompt duplicates training prompt");
  auto brain = train_brain(events, config);
  std::string ts = timestamp_utc();
  uint64_t state = brain.state_hash();
  std::string run_id = "organic-v0-train-" + hex64(fnv1a(ts + hex64(state))).substr(0, 12);

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
                         const std::string& command, const std::vector<Event>& events, const Config& config) {
  auto audit = validate_splits(events);
  if (!audit.duplicates.empty()) throw std::runtime_error("held-out prompt duplicates training prompt");
  auto brain = train_brain(events, config);
  auto alphabet = collect_alphabet(events);

  struct Result {
    const Event* event = nullptr;
    Generation gen;
    std::string random;
    bool exact = false;
    double ratio = 0.0;
  };

  std::vector<Result> results;
  std::map<std::string, EvalSummary> by_split;
  std::map<std::string, EvalSummary> by_domain;
  std::map<std::string, EvalSummary> by_level;
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
    else if (key == "--ablate-trace-id") args.ablate_trace_id = true;
    else throw std::runtime_error("unknown argument: " + key);
  }
  if (args.phase.empty()) throw std::runtime_error("--phase is required");
  return args;
}

}  // namespace px

int main(int argc, char** argv) {
  try {
    px::Args args = px::parse_args(argc, argv);
    if (args.phase == "self-test") {
      px::self_test();
      return 0;
    }
    if (args.out.empty()) throw std::runtime_error("--out is required for train/eval");
    px::Config config;
    if (args.ablate_trace_id) config.use_trace_id_feature = false;
    auto events = px::load_events(args.data);
    std::string command = px::command_string(argc, argv);
    if (args.phase == "train") {
      px::write_train_artifact(args.out, args.data, args.mode, command, events, config);
      std::cout << "wrote " << args.out << "\n";
    } else if (args.phase == "eval") {
      px::write_eval_artifact(args.out, args.data, args.mode, command, events, config);
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
