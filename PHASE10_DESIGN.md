# Phase 10: Natural Language Interface Design

**Goal:** Accept full natural language task descriptions instead of truncated 64-byte goals.

**Constraint:** No external LLMs, no pretrained embeddings (intelligence ceiling violation).

---

## 1. Current Limitation

Current observation structure allocates 64 bytes for goal:
```
GOAL_BYTES = 64  # Truncated UTF-8 of task description
```

This means "Fix the off-by-one error in the calculate_average function where the loop iterates one too many times, causing an IndexError when processing empty lists" becomes "Fix the off-by-one error in the calculate_average fun".

---

## 2. Proposed Architecture

### 2.1 GoalEncoder Module

```python
class GoalEncoder(nn.Module):
    """Byte-level encoder for natural language goals.

    No pretrained embeddings - learns byte-level representations from scratch.
    This maintains the 'no intelligence ceiling' constraint.
    """

    def __init__(
        self,
        max_goal_len: int = 512,      # Max UTF-8 bytes in goal
        byte_embed_dim: int = 64,      # Byte embedding dimension
        hidden_dim: int = 256,         # GRU hidden dimension
        goal_embed_dim: int = 64,      # Output goal embedding dimension
        num_layers: int = 2,           # GRU layers
        dropout: float = 0.1,
    ):
        super().__init__()
        self.max_goal_len = max_goal_len

        # Byte embedding: 256 possible byte values
        self.byte_embed = nn.Embedding(256, byte_embed_dim, padding_idx=0)

        # Bidirectional GRU to process variable-length text
        self.gru = nn.GRU(
            byte_embed_dim,
            hidden_dim // 2,
            num_layers=num_layers,
            bidirectional=True,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
        )

        # Project final hidden state to goal embedding
        self.project = nn.Linear(hidden_dim, goal_embed_dim)

    def forward(self, goal_bytes: torch.Tensor, lengths: Optional[torch.Tensor] = None):
        """
        Args:
            goal_bytes: [B, max_len] - UTF-8 bytes of goal text (0-padded)
            lengths: [B] - actual lengths (optional, for packed sequences)

        Returns:
            goal_embed: [B, goal_embed_dim] - goal embedding
        """
        # Embed bytes
        x = self.byte_embed(goal_bytes)  # [B, L, byte_embed_dim]

        # Pack if lengths provided (more efficient)
        if lengths is not None:
            x = nn.utils.rnn.pack_padded_sequence(
                x, lengths.cpu(), batch_first=True, enforce_sorted=False
            )

        # Process with GRU
        _, h = self.gru(x)  # h: [num_layers*2, B, hidden_dim//2]

        # Take final layer's bidirectional hidden state
        h = torch.cat([h[-2], h[-1]], dim=-1)  # [B, hidden_dim]

        # Project to goal embedding
        return self.project(h)  # [B, goal_embed_dim]
```

### 2.2 Integration Options

**Option A: Concatenate with Observation Encoding**
```python
# In RPJBrain.forward()
obs_embed = self.obs_encoder(obs_bytes)       # [B, obs_embed_dim]
goal_embed = self.goal_encoder(goal_bytes)    # [B, goal_embed_dim]
combined = torch.cat([obs_embed, goal_embed], dim=-1)  # [B, obs_embed_dim + goal_embed_dim]
```

**Option B: Add to Global Broadcast (g_t)**
```python
# Goal embedding influences global scalar computation
g_t = self.global_encoder(h_t, goal_embed)  # Goal-conditioned global scalar
```

**Option C: Initialize Hidden State**
```python
# Goal embedding initializes h_0
h_0 = self.goal_to_hidden(goal_embed).view(B, hidden_dim)
```

**Recommended: Option B** - Matches the RPJ Brain's global broadcast mechanism.

### 2.3 Observation Modification

Extend observation to include variable-length goal:
```python
@dataclass
class JarvisObservationV2:
    # ... existing fields ...
    goal_text: str = ""  # Full text (not truncated)
    goal_bytes: Optional[torch.Tensor] = None  # Pre-encoded goal bytes
```

New layout:
```
OLD: [terminal:256][goal:64][focus:128][meta:64] = 512 bytes
NEW: [terminal:256][focus:128][meta:64][reserved:64] = 512 bytes
     + [goal_bytes:512] = separate tensor
```

---

## 3. Training Strategy

### 3.1 Dataset Creation

Create BC dataset with (goal_text, expert_trajectory) pairs:

```python
@dataclass
class Phase10Demo:
    goal_text: str                    # Full natural language goal
    observations: List[torch.Tensor]  # Sequence of observations
    actions: List[torch.Tensor]       # Sequence of expert actions
    repo_state: str                   # Initial repo state

def create_phase10_demos():
    templates = [
        "Fix the {bug_type} in {function_name} that causes {symptom}",
        "The {function_name} function has a bug: {description}. Make the tests pass.",
        "There's an issue with {file_name}: {description}",
        # ... many more templates
    ]
```

### 3.2 Training Loop

1. **Stage 1 (BC):** Pre-train goal encoder + brain on expert demos
2. **Stage 2 (RL):** Fine-tune with PPO on harness tasks

```python
# BC loss with goal conditioning
obs_embed = brain.obs_encoder(obs)
goal_embed = brain.goal_encoder(goal_bytes)
action_logits = brain.policy(obs_embed, goal_embed, h, g)
bc_loss = cross_entropy(action_logits, expert_actions)
```

---

## 4. Evaluation

### 4.1 Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Goal understanding | >80% | Model extracts correct information from goal |
| Task completion | >50% | Complete tasks given natural language goal |
| Robustness | >70% | Handle paraphrased/noisy goals |

### 4.2 Test Suite

```python
test_goals = [
    # Direct
    ("Fix the bug in calculator.py", "calculator.py"),

    # Indirect
    ("The add function returns wrong results", "calculator.py"),

    # Complex
    ("There's an off-by-one error causing IndexError", "utils.py"),

    # Noisy
    ("plz fix the bug its broken", "main.py"),
]
```

---

## 5. Implementation Plan

1. **Create GoalEncoder module** (`src/core/goal_encoder.py`)
2. **Modify RPJBrain** to accept and use goal embeddings
3. **Update observation encoding** to separate goal bytes
4. **Create Phase 10 demo dataset** with varied goal texts
5. **Train BC** with goal-conditioned policy
6. **Evaluate** on diverse natural language goals
7. **Fine-tune with RL** on harness tasks

---

## 6. Parameter Budget

| Component | Parameters | Notes |
|-----------|------------|-------|
| Byte embedding | 256 × 64 = 16K | 256 byte values |
| GRU (2 layers) | 2 × (3 × 64 × 128) × 2 = 98K | Bidirectional |
| Projection | 256 × 64 = 16K | Hidden → goal_embed |
| **Total** | **~130K** | 4% overhead on 3.2M brain |

---

## 7. Success Criteria

- [ ] GoalEncoder trained from scratch (no pretrained weights)
- [ ] HARD solve rate maintained (>70%) with natural language goals
- [ ] Can handle goal descriptions up to 512 bytes
- [ ] Robust to paraphrasing and varied phrasing
- [ ] Energy overhead <5% (130K params / 3.2M params)
