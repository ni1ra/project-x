"""
Byte Interface Implementation

The universal "Socket" for content-free I/O:
- φ(o): bytes → normalized floats (observation encoder)
- Action decoder: autoregressive GRU → 256-way categorical per byte

This ensures ALL domains use the same interface with no domain-specific processing.
"""

from __future__ import annotations

from typing import Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


def phi(observation: torch.Tensor) -> torch.Tensor:
    """
    Universal observation encoder: bytes → normalized floats.

    Converts byte values [0, 255] to float range [-1, 1].
    This is the ONLY allowed preprocessing - no domain-specific tokenizers.

    Args:
        observation: Tensor of byte values, shape [..., n]
                    dtype can be uint8, int, or float

    Returns:
        Normalized floats, shape [..., n], range [-1, 1]
    """
    # Ensure float dtype for computation
    obs_float = observation.float()

    # Normalize: [0, 255] → [-1, 1]
    normalized = (obs_float - 127.5) / 127.5

    return normalized


def phi_inverse(normalized: torch.Tensor) -> torch.Tensor:
    """
    Inverse of phi: normalized floats → bytes.

    Args:
        normalized: Tensor of floats in range [-1, 1]

    Returns:
        Byte values [0, 255] as uint8
    """
    # Denormalize: [-1, 1] → [0, 255]
    bytes_float = (normalized * 127.5) + 127.5

    # Clamp and convert to uint8
    bytes_clamped = torch.clamp(bytes_float, 0, 255)
    return bytes_clamped.to(torch.uint8)


class GaussianActionHead(nn.Module):
    """
    Gaussian Action Head for ordinal byte outputs.

    JARVIS 420 FIX: The standard 256-way categorical head lacks ordinal topology -
    class 16 and class 17 are as distinct as class 16 and class 200. This creates
    a jagged optimization surface where the agent falls into 'safe' local clusters
    that minimize average error but lack gradient slope to slide to exact values.

    This architecture forces the network to predict continuous mu and sigma, then
    projects that distribution onto the 256 discrete bins. This restores gradient
    flow between adjacent integers - if target is 48 and output is 22, the gradient
    on mu will smoothly push probability mass from 22 → 48.

    The logits are computed as: -0.5 * ((bin - mu) / sigma)^2
    This is equivalent to a discretized Gaussian distribution.

    CRITICAL FIX: Also accepts phi_obs (normalized observation) as direct input.
    For simple tasks like CCB (identity mapping), this provides a direct path
    from input byte to output mu, bypassing the complex substrate→h_t path.
    """

    def __init__(
        self,
        hidden_dim: int,
        decoder_hidden: int = 128,
        num_bins: int = 256,
        k_max: int = 16,
        obs_dim: int = 2,  # Direct observation input dimension
    ):
        super().__init__()
        self.num_bins = num_bins
        self.decoder_hidden = decoder_hidden
        self.k_max = k_max
        self.obs_dim = obs_dim

        # Project [h_t || g_t || phi_obs] to decoder hidden
        # Adding phi_obs provides direct gradient path from input to output
        self.h_proj = nn.Linear(hidden_dim + k_max + obs_dim, decoder_hidden)

        # Predict mu (0-255) and log_sigma from decoder hidden
        # Two separate heads for cleaner gradient flow
        self.mu_head = nn.Sequential(
            nn.Linear(decoder_hidden, decoder_hidden),
            nn.ReLU(),
            nn.Linear(decoder_hidden, 1),
        )
        self.sigma_head = nn.Sequential(
            nn.Linear(decoder_hidden, decoder_hidden),
            nn.ReLU(),
            nn.Linear(decoder_hidden, 1),
        )

        # JARVIS 420 FIX #3: Contextual Reflex Path
        # Previous obs_skip only saw phi_obs -> learned AVERAGE function across tasks
        # DoErr plateaued at 0.12 because reflex couldn't specialize to task
        # FIX: Feed [phi_obs || g_t] to obs_skip for task-specific precision
        # This creates a Context-Aware Reflex that is both stable (no dropout) and task-specific
        self.obs_skip = nn.Sequential(
            nn.Linear(obs_dim + k_max, 64),  # CHANGED: Added k_max for context
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, 1)
        )

        # Initialize last layer to small values
        # Action space now aligns with target range, no bias needed
        with torch.no_grad():
            self.obs_skip[-1].weight.data.fill_(0.0)
            self.obs_skip[-1].bias.data.fill_(0.0)

        # Fixed grid [0, 1, ..., 255] for computing Gaussian logits
        self.register_buffer('grid', torch.arange(num_bins).float())

        # JARVIS 420 FIX: Information Bottleneck
        # Apply dropout to h_t (local state) while leaving g_t (global broadcast) clean
        # This forces the network to use neuromodulators for precision
        self.h_dropout = nn.Dropout(p=0.5)

    def forward(
        self,
        h_t: torch.Tensor,
        g_t: torch.Tensor = None,
        phi_obs: torch.Tensor = None,
    ) -> torch.Tensor:
        """
        Compute Gaussian logits over byte values.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            g_t: Global scalars [batch, k_max]
            phi_obs: Normalized observation [batch, obs_dim] - CRITICAL for direct gradient path

        Returns:
            logits: Gaussian logits over [0, 255], shape [batch, 256]
        """
        batch_size = h_t.size(0)

        # JARVIS 420 FIX: Information Bottleneck
        # Apply dropout to h_t during training to degrade local path
        # Forces network to rely on g_t (neuromodulators) for stable prediction
        h_t_dropped = self.h_dropout(h_t)

        # Concatenate [h_t_dropped || g_t || phi_obs] for direct gradient flow
        # Note: g_t is NOT dropped - it's the "conscious" channel
        if g_t is None:
            g_t = torch.zeros(batch_size, self.k_max, device=h_t.device)
        if phi_obs is None:
            phi_obs = torch.zeros(batch_size, self.obs_dim, device=h_t.device)

        context = torch.cat([h_t_dropped, g_t, phi_obs], dim=-1)

        # Project to decoder hidden
        decoder_h = self.h_proj(context)  # [batch, decoder_hidden]

        # Predict mu in [0, 255]
        mu_raw = self.mu_head(decoder_h).squeeze(-1)  # [batch]
        # JARVIS 420 FIX #3: Contextual Reflex
        # Feed [phi_obs || g_t] for task-specific precision (no dropout on this path)
        reflex_input = torch.cat([phi_obs, g_t], dim=-1)  # [batch, obs_dim + k_max]
        obs_skip_out = self.obs_skip(reflex_input).squeeze(-1)  # [batch]
        mu_combined = mu_raw + obs_skip_out * 2.0
        mu = torch.sigmoid(mu_combined) * (self.num_bins - 1)  # [0, 255]

        # Predict sigma with floor AND cap
        # JARVIS 420 FIX: Old sigma=20 floor prevented precise actions
        # JARVIS 420 FIX #2: Must CAP sigma to prevent "Sigma Trap"
        # JARVIS 420 FIX #3: Lower sigma floor from 3.0→0.5 to reduce noise floor
        # At sigma=3.0 bins, MAE floor ≈ 0.037 (too high for DoErr≤0.05)
        # At sigma=0.5 bins, MAE floor ≈ 0.006 (allows DoErr≤0.05)
        # Supervised loss on mu makes low sigma safe (no entropy collapse)
        sigma_raw = self.sigma_head(decoder_h).squeeze(-1)  # [batch]
        sigma_unbounded = F.softplus(sigma_raw) + 0.5  # [0.5, inf)
        sigma = torch.clamp(sigma_unbounded, min=0.5, max=8.0)  # [0.5, 8] - JARVIS 420

        # Compute Gaussian logits: -0.5 * ((x - mu) / sigma)^2
        # This gives unnormalized log-probabilities of a Gaussian
        # Shape: [batch, 256]
        dist = (self.grid.unsqueeze(0) - mu.unsqueeze(1)) / sigma.unsqueeze(1)
        logits = -0.5 * dist.pow(2)

        return logits, mu, sigma

    def sample(
        self,
        h_t: torch.Tensor,
        g_t: torch.Tensor = None,
        phi_obs: torch.Tensor = None,
        greedy: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Sample action bytes from Gaussian distribution.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            g_t: Global scalars [batch, k_max]
            phi_obs: Normalized observation [batch, obs_dim]
            greedy: If True, return argmax (mode)

        Returns:
            action: Sampled byte [batch]
            log_prob: Log probability [batch]
            mu: Continuous action prediction [batch] - DIFFERENTIABLE for supervised learning
        """
        logits, mu, sigma = self.forward(h_t, g_t, phi_obs)

        probs = F.softmax(logits, dim=-1)
        log_probs = F.log_softmax(logits, dim=-1)

        if greedy:
            # Return the mode (rounded mu)
            action = torch.round(mu).long().clamp(0, self.num_bins - 1)
        else:
            action = torch.multinomial(probs, 1).squeeze(-1)

        action_log_prob = log_probs.gather(1, action.unsqueeze(-1)).squeeze(-1)

        # Clone to avoid CUDAGraphs tensor overwrite error
        # Return mu for supervised learning (differentiable path)
        return action.clone(), action_log_prob.clone(), mu

    def get_log_prob(
        self,
        h_t: torch.Tensor,
        actions: torch.Tensor,
        g_t: torch.Tensor = None,
        phi_obs: torch.Tensor = None,
    ) -> torch.Tensor:
        """
        Compute log probability of given actions.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            actions: Action bytes [batch] or [batch, 1]
            g_t: Global scalars [batch, k_max]
            phi_obs: Normalized observation [batch, obs_dim]

        Returns:
            log_prob: Log probability [batch]
        """
        logits, _, _ = self.forward(h_t, g_t, phi_obs)
        log_probs = F.log_softmax(logits, dim=-1)

        if actions.dim() == 2:
            actions = actions[:, 0]

        # Clone to avoid CUDAGraphs tensor overwrite error
        return log_probs.gather(1, actions.unsqueeze(-1)).squeeze(-1).clone()

    def get_entropy(
        self,
        h_t: torch.Tensor,
        g_t: torch.Tensor = None,
        phi_obs: torch.Tensor = None,
    ) -> torch.Tensor:
        """
        Compute entropy of action distribution.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            g_t: Global scalars [batch, k_max]
            phi_obs: Normalized observation [batch, obs_dim]

        Returns:
            entropy: Entropy [batch]
        """
        logits, _, _ = self.forward(h_t, g_t, phi_obs)
        probs = F.softmax(logits, dim=-1)
        log_probs = F.log_softmax(logits, dim=-1)

        # Entropy: -sum(p * log(p))
        entropy = -(probs * log_probs).sum(dim=-1)

        # Clone to avoid CUDAGraphs tensor overwrite error
        return entropy.clone()


class VocabClassificationHead(nn.Module):
    """
    Vocab Classification Head for TRIVIAL bug fixes.

    JARVIS VOCAB FIX: The autoregressive decoder collapses to always predicting
    vocab_idx=0 (':\\n') regardless of bug type. This is because byte 25 is
    generated at step 25 of the GRU loop, losing gradient signal.

    This head directly classifies which vocab token to use based on:
    - Goal bytes (256-320): Contains "Missing colon", "Missing paren", etc.
    - Focus text (320-448): Contains the actual buggy code
    - Hidden state h_t: Accumulated context

    The output is a 5-class softmax over TRIVIAL_VOCAB:
    - 0: ':\\n' (missing colon)
    - 1: ')' (missing paren)
    - 2: ',' (missing comma)
    - 3: "'" (wrong single quote)
    - 4: '"' (wrong double quote)
    """

    def __init__(
        self,
        hidden_dim: int = 512,
        decoder_hidden: int = 128,
        vocab_size: int = 5,  # TRIVIAL_VOCAB size
        goal_dim: int = 64,  # Goal bytes (256-320)
        focus_text_dim: int = 128,  # Focus text (320-448)
    ):
        super().__init__()
        self.vocab_size = vocab_size
        self.goal_dim = goal_dim
        self.focus_text_dim = focus_text_dim

        # Project context to vocab logits
        # Input: [h_t || goal_bytes || focus_text]
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim + goal_dim + focus_text_dim, decoder_hidden),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(decoder_hidden, decoder_hidden),
            nn.ReLU(),
            nn.Linear(decoder_hidden, vocab_size),
        )

    def forward(
        self,
        h_t: torch.Tensor,
        goal_bytes: torch.Tensor,
        focus_text: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute vocab classification logits.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            goal_bytes: Goal bytes [batch, goal_dim] (normalized)
            focus_text: Focus text [batch, focus_text_dim] (normalized)

        Returns:
            logits: Vocab logits [batch, vocab_size]
        """
        context = torch.cat([h_t, goal_bytes, focus_text], dim=-1)
        return self.classifier(context)

    def sample(
        self,
        h_t: torch.Tensor,
        goal_bytes: torch.Tensor,
        focus_text: torch.Tensor,
        greedy: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Sample vocab index from distribution.

        Returns:
            vocab_idx: Selected vocab index [batch]
            log_prob: Log probability [batch]
        """
        logits = self.forward(h_t, goal_bytes, focus_text)
        probs = F.softmax(logits, dim=-1)
        log_probs = F.log_softmax(logits, dim=-1)

        if greedy:
            vocab_idx = logits.argmax(dim=-1)
        else:
            vocab_idx = torch.multinomial(probs, 1).squeeze(-1)

        action_log_prob = log_probs.gather(1, vocab_idx.unsqueeze(-1)).squeeze(-1)
        return vocab_idx, action_log_prob

    def get_log_prob(
        self,
        h_t: torch.Tensor,
        goal_bytes: torch.Tensor,
        focus_text: torch.Tensor,
        vocab_idx: torch.Tensor,
    ) -> torch.Tensor:
        """Compute log probability of given vocab index."""
        logits = self.forward(h_t, goal_bytes, focus_text)
        log_probs = F.log_softmax(logits, dim=-1)
        if vocab_idx.dim() == 2:
            vocab_idx = vocab_idx[:, 0]
        return log_probs.gather(1, vocab_idx.unsqueeze(-1)).squeeze(-1)

    def get_entropy(
        self,
        h_t: torch.Tensor,
        goal_bytes: torch.Tensor,
        focus_text: torch.Tensor,
    ) -> torch.Tensor:
        """Compute entropy of vocab distribution."""
        logits = self.forward(h_t, goal_bytes, focus_text)
        probs = F.softmax(logits, dim=-1)
        log_probs = F.log_softmax(logits, dim=-1)
        return -(probs * log_probs).sum(dim=-1)


class AutoregressiveActionDecoder(nn.Module):
    """
    Autoregressive action decoder using GRU(128).

    Generates action bytes one at a time, each conditioned on:
    - Hidden state h_t from the substrate
    - Global scalars g_t (for K_eff gradient flow)
    - Previously generated bytes in the action sequence

    Architecture from BLUEPRINT.md Section 2.7:
    - GRU(128) decoder
    - 16-d byte embeddings
    - 256-way categorical per byte (or Gaussian head)

    K_eff Fix: Policy conditions on [h_t || g_t] so RL gradients flow to W_g.

    JARVIS 420 FIX (DoErr): When use_gaussian=True, replaces the flat categorical
    head with a Gaussian head that provides ordinal gradient flow.

    JARVIS VOCAB FIX: Adds parallel VocabClassificationHead for byte 25 (vocab_idx)
    to prevent collapse to single token during autoregressive decoding.
    """

    def __init__(
        self,
        hidden_dim: int = 512,  # Substrate hidden dim
        decoder_hidden: int = 128,  # GRU decoder hidden
        byte_embed_dim: int = 16,  # Byte embedding dimension
        num_action_bytes: int = 1,  # Default action length
        k_max: int = 16,  # Global scalar dimension (for g_t conditioning)
        use_gaussian: bool = True,  # JARVIS 420 FIX: Use Gaussian head for ordinal outputs
        obs_dim: int = 2,  # Observation dimension for direct input path
        use_vocab_head: bool = True,  # JARVIS VOCAB FIX: Use parallel vocab classification
        vocab_size: int = 5,  # Phase 9 FIX: Vocab head size (5=TRIVIAL, 21=COMBINED)
    ):
        super().__init__()

        self.hidden_dim = hidden_dim
        self.decoder_hidden = decoder_hidden
        self.byte_embed_dim = byte_embed_dim
        self.num_action_bytes = num_action_bytes
        self.k_max = k_max
        self.use_gaussian = use_gaussian
        self.obs_dim = obs_dim
        self.use_vocab_head = use_vocab_head
        self.vocab_size = vocab_size

        # JARVIS 420 FIX: Use Gaussian head for single-byte ordinal outputs (like CCB)
        # This provides smooth gradients between adjacent byte values
        if use_gaussian and num_action_bytes == 1:
            self.gaussian_head = GaussianActionHead(
                hidden_dim=hidden_dim,
                decoder_hidden=decoder_hidden,
                num_bins=256,
                k_max=k_max,
                obs_dim=obs_dim,  # Pass observation for direct gradient path
            )
            # Dummy params for compatibility
            self.byte_embedding = None
            self.h_proj = None
            self.gru = None
            self.output_head = None
            self.start_embed = None
            self.vocab_head = None  # Not needed for single-byte
        else:
            # Original categorical decoder for multi-byte actions
            self.gaussian_head = None

            # Byte embeddings for conditioning on previous bytes
            self.byte_embedding = nn.Embedding(256, byte_embed_dim)

            # JARVIS FIX: Include goal bytes, focus_text, and focus_preview for full context
            # Goal bytes (256-320) contain bug type info: "Missing colon", "Missing paren", etc.
            # Focus text (320-448) contains the actual code where the bug is
            # Focus preview (480-512) contains a small preview (redundant but kept for compatibility)
            # Handle smaller obs_dim for test compatibility
            self.focus_preview_dim = min(32, obs_dim)  # Last N bytes of observation
            self.goal_dim = min(64, obs_dim)  # Goal bytes (256-320)
            self.focus_text_dim = min(128, max(0, obs_dim - 320))  # Focus text (320-448)
            self.goal_start = 256 if obs_dim >= 320 else 0  # Start of goal section
            self.focus_text_start = 320 if obs_dim >= 448 else 0  # Start of focus text

            # DEEP-DEBUG FIX: Add metadata skip connection
            # The model ignores metadata bytes (step, tests_passing, tests_total) buried in text.
            # Adding them directly to context forces the decoder to attend to them.
            # Metadata layout at bytes 448-480:
            #   [448-449]: energy (float16)
            #   [450-451]: time (float16)
            #   [452-453]: actions_remaining (uint16)
            #   [454-455]: step (uint16)  <-- KEY for action selection
            #   [456-457]: last_reward (float16)
            #   [458]:     tests_passing (uint8)  <-- KEY for action selection
            #   [459]:     tests_total (uint8)    <-- KEY for action selection
            self.metadata_dim = 12 if obs_dim >= 460 else 0  # Bytes 448-459
            self.metadata_start = 448 if obs_dim >= 460 else 0

            # Project [h_t || g_t || goal_bytes || focus_text || focus_preview || metadata] to decoder initial state
            self.h_proj = nn.Linear(hidden_dim + k_max + self.goal_dim + self.focus_text_dim + self.focus_preview_dim + self.metadata_dim, decoder_hidden)

            # GRU decoder
            self.gru = nn.GRU(
                input_size=byte_embed_dim,
                hidden_size=decoder_hidden,
                num_layers=1,
                batch_first=True,
            )

            # Output head: decoder hidden → 256-way categorical
            self.output_head = nn.Linear(decoder_hidden, 256)

            # Start token embedding (for first byte)
            self.start_embed = nn.Parameter(torch.randn(byte_embed_dim))

            # JARVIS VOCAB FIX: Parallel vocab classification head for byte 25
            # This directly classifies which TRIVIAL_VOCAB token to use
            # instead of relying on autoregressive generation which collapses
            # Phase 9 FIX: vocab_size is configurable (5=TRIVIAL, 21=COMBINED)
            if use_vocab_head and obs_dim >= 448:
                self.vocab_head = VocabClassificationHead(
                    hidden_dim=hidden_dim,
                    decoder_hidden=decoder_hidden,
                    vocab_size=vocab_size,  # Phase 9: Configurable vocab size
                    goal_dim=self.goal_dim,
                    focus_text_dim=self.focus_text_dim,
                )
            else:
                self.vocab_head = None

    def forward(
        self,
        h_t: torch.Tensor,
        g_t: Optional[torch.Tensor] = None,
        num_bytes: Optional[int] = None,
        temperature: float = 1.0,
        greedy: bool = False,
        phi_obs: Optional[torch.Tensor] = None,  # Direct observation input
    ) -> Tuple[torch.Tensor, torch.Tensor, Optional[torch.Tensor]]:
        """
        Generate action bytes autoregressively.

        Args:
            h_t: Substrate hidden state, shape [batch, hidden_dim]
            g_t: Global scalars, shape [batch, k_max] (for K_eff gradient flow)
            num_bytes: Number of bytes to generate (default: self.num_action_bytes)
            temperature: Sampling temperature (1.0 = normal, <1 = sharper)
            greedy: If True, use argmax instead of sampling
            phi_obs: Normalized observation, shape [batch, obs_dim] (for direct gradient path)

        Returns:
            actions: Generated bytes, shape [batch, num_bytes], dtype=long
            log_probs: Log probabilities, shape [batch, num_bytes]
            action_mu: Continuous prediction [batch] (only for Gaussian head, None otherwise)
        """
        # JARVIS 420 FIX: Use Gaussian head for single-byte outputs
        if self.gaussian_head is not None:
            action, log_prob, action_mu = self.gaussian_head.sample(h_t, g_t, phi_obs, greedy=greedy)
            # Return in expected shape [batch, 1]
            # Clone to avoid CUDAGraphs tensor overwrite error with torch.compile
            return action.unsqueeze(1).clone(), log_prob.unsqueeze(1).clone(), action_mu

        # Original categorical decoder for multi-byte actions
        batch_size = h_t.size(0)
        num_bytes = num_bytes or self.num_action_bytes

        # JARVIS FIX: Extract goal bytes, focus_text, AND focus_preview from phi_obs
        # Goal bytes (256-320) contain bug type info for vocabulary selection
        # Focus text (320-448) contains actual code for offset selection
        # Focus preview (480-512) contains small code preview
        # DEEP-DEBUG FIX: Also extract metadata bytes (448-459) for action type selection
        if g_t is None:
            g_t = torch.zeros(batch_size, self.k_max, device=h_t.device)
        if phi_obs is None:
            goal_bytes = torch.zeros(batch_size, self.goal_dim, device=h_t.device)
            focus_text = torch.zeros(batch_size, self.focus_text_dim, device=h_t.device)
            focus_preview = torch.zeros(batch_size, self.focus_preview_dim, device=h_t.device)
            metadata = torch.zeros(batch_size, self.metadata_dim, device=h_t.device)
        else:
            # Extract goal bytes (256-320) for bug type discrimination
            goal_bytes = phi_obs[:, self.goal_start:self.goal_start + self.goal_dim]
            # Extract focus text (320-448) for offset selection - this is where the bug is!
            focus_text = phi_obs[:, self.focus_text_start:self.focus_text_start + self.focus_text_dim]
            # Extract last 32 bytes (focus_preview region)
            focus_preview = phi_obs[:, -self.focus_preview_dim:]
            # DEEP-DEBUG FIX: Extract metadata bytes (448-459) for action type selection
            # These contain step, tests_passing, tests_total - critical for RUN_TESTS decision
            if self.metadata_dim > 0:
                metadata = phi_obs[:, self.metadata_start:self.metadata_start + self.metadata_dim]
            else:
                metadata = torch.zeros(batch_size, 0, device=h_t.device)
        context = torch.cat([h_t, g_t, goal_bytes, focus_text, focus_preview, metadata], dim=-1)

        # Initialize decoder hidden state from [h_t || g_t || focus_preview]
        decoder_h = self.h_proj(context).unsqueeze(0)  # [1, batch, decoder_hidden]

        # Start with start token
        current_embed = self.start_embed.unsqueeze(0).expand(batch_size, -1)  # [batch, embed]

        actions = []
        log_probs = []

        # JARVIS VOCAB FIX: Pre-compute vocab_idx using parallel head if available
        # This will be used to override byte 25 (content_raw[0] in decode_action_v2)
        vocab_idx = None
        vocab_log_prob = None
        if self.vocab_head is not None:
            vocab_idx, vocab_log_prob = self.vocab_head.sample(
                h_t, goal_bytes, focus_text, greedy=greedy
            )

        for byte_idx in range(num_bytes):
            # GRU step
            current_embed = current_embed.unsqueeze(1)  # [batch, 1, embed]
            gru_out, decoder_h = self.gru(current_embed, decoder_h)

            # Get logits
            logits = self.output_head(gru_out.squeeze(1))  # [batch, 256]

            # Apply temperature
            if temperature != 1.0:
                logits = logits / temperature

            # Sample or greedy
            probs = F.softmax(logits, dim=-1)
            if greedy:
                action = logits.argmax(dim=-1)
            else:
                action = torch.multinomial(probs, 1).squeeze(-1)

            # Compute log probability
            log_prob = F.log_softmax(logits, dim=-1)
            action_log_prob = log_prob.gather(1, action.unsqueeze(-1)).squeeze(-1)

            # JARVIS VOCAB FIX: Override byte 25 with vocab_head output
            # Byte 25 is the vocab index in action encoding (content_raw[0])
            if byte_idx == 25 and vocab_idx is not None:
                action = vocab_idx
                action_log_prob = vocab_log_prob

            actions.append(action)
            log_probs.append(action_log_prob)

            # Embed this action for next step
            current_embed = self.byte_embedding(action)  # [batch, embed]

        # Stack results
        actions = torch.stack(actions, dim=1)  # [batch, num_bytes]
        log_probs = torch.stack(log_probs, dim=1)  # [batch, num_bytes]

        # Clone to avoid CUDAGraphs tensor overwrite error with torch.compile
        # Return None for action_mu (categorical decoder doesn't have differentiable mu)
        return actions.clone(), log_probs.clone(), None

    def get_log_prob(
        self,
        h_t: torch.Tensor,
        actions: torch.Tensor,
        g_t: Optional[torch.Tensor] = None,
        phi_obs: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Compute log probabilities for given actions (for PPO).

        Args:
            h_t: Substrate hidden state, shape [batch, hidden_dim]
            actions: Action bytes, shape [batch, num_bytes]
            g_t: Global scalars, shape [batch, k_max] (for K_eff gradient flow)
            phi_obs: Normalized observation, shape [batch, obs_dim] (for direct gradient path)

        Returns:
            log_probs: Log probabilities, shape [batch, num_bytes]
        """
        # JARVIS 420 FIX: Use Gaussian head for single-byte outputs
        if self.gaussian_head is not None:
            log_prob = self.gaussian_head.get_log_prob(h_t, actions, g_t, phi_obs)
            # Return in expected shape [batch, 1]
            # Clone to avoid CUDAGraphs tensor overwrite error
            return log_prob.unsqueeze(1).clone()

        # Original categorical decoder for multi-byte actions
        batch_size = h_t.size(0)
        num_bytes = actions.size(1)

        # JARVIS FIX: Extract goal bytes, focus_text, AND focus_preview from phi_obs
        # DEEP-DEBUG FIX: Also extract metadata bytes (448-459) for action type selection
        if g_t is None:
            g_t = torch.zeros(batch_size, self.k_max, device=h_t.device)
        if phi_obs is None:
            goal_bytes = torch.zeros(batch_size, self.goal_dim, device=h_t.device)
            focus_text = torch.zeros(batch_size, self.focus_text_dim, device=h_t.device)
            focus_preview = torch.zeros(batch_size, self.focus_preview_dim, device=h_t.device)
            metadata = torch.zeros(batch_size, self.metadata_dim, device=h_t.device)
        else:
            goal_bytes = phi_obs[:, self.goal_start:self.goal_start + self.goal_dim]
            focus_text = phi_obs[:, self.focus_text_start:self.focus_text_start + self.focus_text_dim]
            focus_preview = phi_obs[:, -self.focus_preview_dim:]
            # DEEP-DEBUG FIX: Extract metadata bytes
            if self.metadata_dim > 0:
                metadata = phi_obs[:, self.metadata_start:self.metadata_start + self.metadata_dim]
            else:
                metadata = torch.zeros(batch_size, 0, device=h_t.device)
        context = torch.cat([h_t, g_t, goal_bytes, focus_text, focus_preview, metadata], dim=-1)

        # Initialize decoder hidden state
        decoder_h = self.h_proj(context).unsqueeze(0)

        # Start with start token
        current_embed = self.start_embed.unsqueeze(0).expand(batch_size, -1)

        log_probs = []

        # JARVIS VOCAB FIX: Pre-compute vocab log prob for byte 25
        vocab_log_prob_byte25 = None
        if self.vocab_head is not None and num_bytes > 25:
            # Phase 9 FIX: Clamp vocab_idx to valid range for vocab_head
            # Actions[:, 25] can be 0-255 from model output, but vocab_head has vocab_size classes
            vocab_idx_actual = actions[:, 25].clamp(0, self.vocab_size - 1)
            vocab_log_prob_byte25 = self.vocab_head.get_log_prob(
                h_t, goal_bytes, focus_text, vocab_idx_actual
            )

        for i in range(num_bytes):
            # GRU step
            current_embed = current_embed.unsqueeze(1)
            gru_out, decoder_h = self.gru(current_embed, decoder_h)

            # Get logits and log probs
            logits = self.output_head(gru_out.squeeze(1))
            log_prob = F.log_softmax(logits, dim=-1)

            # Get log prob for actual action
            action = actions[:, i]
            action_log_prob = log_prob.gather(1, action.unsqueeze(-1)).squeeze(-1)

            # JARVIS VOCAB FIX: Use vocab_head log prob for byte 25
            if i == 25 and vocab_log_prob_byte25 is not None:
                action_log_prob = vocab_log_prob_byte25

            log_probs.append(action_log_prob)

            # Embed actual action for next step (teacher forcing)
            current_embed = self.byte_embedding(action)

        # Clone to avoid CUDAGraphs tensor overwrite error
        return torch.stack(log_probs, dim=1).clone()

    def get_entropy(
        self,
        h_t: torch.Tensor,
        num_bytes: Optional[int] = None,
        g_t: Optional[torch.Tensor] = None,
        phi_obs: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Compute entropy of action distribution (for PPO entropy bonus).

        Args:
            h_t: Substrate hidden state, shape [batch, hidden_dim]
            num_bytes: Number of bytes
            g_t: Global scalars, shape [batch, k_max] (for K_eff gradient flow)
            phi_obs: Normalized observation, shape [batch, obs_dim] (for direct gradient path)

        Returns:
            entropy: Mean entropy, shape [batch]
        """
        # JARVIS 420 FIX: Use Gaussian head for single-byte outputs
        if self.gaussian_head is not None:
            # Clone to avoid CUDAGraphs tensor overwrite error
            return self.gaussian_head.get_entropy(h_t, g_t, phi_obs).clone()

        # Original categorical decoder for multi-byte actions
        batch_size = h_t.size(0)
        num_bytes = num_bytes or self.num_action_bytes

        # JARVIS FIX: Extract goal bytes, focus_text, AND focus_preview from phi_obs
        # DEEP-DEBUG FIX: Also extract metadata bytes (448-459) for action type selection
        if g_t is None:
            g_t = torch.zeros(batch_size, self.k_max, device=h_t.device)
        if phi_obs is None:
            goal_bytes = torch.zeros(batch_size, self.goal_dim, device=h_t.device)
            focus_text = torch.zeros(batch_size, self.focus_text_dim, device=h_t.device)
            focus_preview = torch.zeros(batch_size, self.focus_preview_dim, device=h_t.device)
            metadata = torch.zeros(batch_size, self.metadata_dim, device=h_t.device)
        else:
            goal_bytes = phi_obs[:, self.goal_start:self.goal_start + self.goal_dim]
            focus_text = phi_obs[:, self.focus_text_start:self.focus_text_start + self.focus_text_dim]
            focus_preview = phi_obs[:, -self.focus_preview_dim:]
            # DEEP-DEBUG FIX: Extract metadata bytes
            if self.metadata_dim > 0:
                metadata = phi_obs[:, self.metadata_start:self.metadata_start + self.metadata_dim]
            else:
                metadata = torch.zeros(batch_size, 0, device=h_t.device)
        context = torch.cat([h_t, g_t, goal_bytes, focus_text, focus_preview, metadata], dim=-1)

        # Initialize decoder hidden state
        decoder_h = self.h_proj(context).unsqueeze(0)
        current_embed = self.start_embed.unsqueeze(0).expand(batch_size, -1)

        entropies = []

        # JARVIS VOCAB FIX: Pre-compute vocab entropy for byte 25
        vocab_entropy_byte25 = None
        if self.vocab_head is not None and num_bytes > 25:
            vocab_entropy_byte25 = self.vocab_head.get_entropy(h_t, goal_bytes, focus_text)

        for byte_idx in range(num_bytes):
            current_embed = current_embed.unsqueeze(1)
            gru_out, decoder_h = self.gru(current_embed, decoder_h)

            logits = self.output_head(gru_out.squeeze(1))
            probs = F.softmax(logits, dim=-1)
            log_probs = F.log_softmax(logits, dim=-1)

            # Entropy: -sum(p * log(p))
            entropy = -(probs * log_probs).sum(dim=-1)

            # JARVIS VOCAB FIX: Use vocab_head entropy for byte 25
            if byte_idx == 25 and vocab_entropy_byte25 is not None:
                entropy = vocab_entropy_byte25

            entropies.append(entropy)

            # Sample for next step (need some action to continue)
            action = torch.multinomial(probs, 1).squeeze(-1)
            current_embed = self.byte_embedding(action)

        # Clone to avoid CUDAGraphs tensor overwrite error
        return torch.stack(entropies, dim=1).mean(dim=1).clone()


class ByteInterface(nn.Module):
    """
    Complete byte interface wrapper.

    Combines observation encoding and action decoding
    into a single module for clean integration.
    """

    def __init__(
        self,
        hidden_dim: int = 512,
        decoder_hidden: int = 128,
        byte_embed_dim: int = 16,
        num_action_bytes: int = 1,
    ):
        super().__init__()

        self.action_decoder = AutoregressiveActionDecoder(
            hidden_dim=hidden_dim,
            decoder_hidden=decoder_hidden,
            byte_embed_dim=byte_embed_dim,
            num_action_bytes=num_action_bytes,
        )

    def encode_observation(self, observation: torch.Tensor) -> torch.Tensor:
        """Encode observation bytes to normalized floats."""
        return phi(observation)

    def decode_action(
        self,
        h_t: torch.Tensor,
        num_bytes: Optional[int] = None,
        temperature: float = 1.0,
        greedy: bool = False,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Generate action bytes from hidden state."""
        actions, log_probs, _ = self.action_decoder(
            h_t,
            num_bytes=num_bytes,
            temperature=temperature,
            greedy=greedy,
        )
        return actions, log_probs

    def get_action_log_prob(
        self,
        h_t: torch.Tensor,
        actions: torch.Tensor,
    ) -> torch.Tensor:
        """Get log probabilities for given actions."""
        return self.action_decoder.get_log_prob(h_t, actions)

    def get_action_entropy(
        self,
        h_t: torch.Tensor,
        num_bytes: Optional[int] = None,
    ) -> torch.Tensor:
        """Get action distribution entropy."""
        return self.action_decoder.get_entropy(h_t, num_bytes)
