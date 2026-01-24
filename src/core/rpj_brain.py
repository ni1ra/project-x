"""
RPJ Brain - The Complete Integrated System

This combines:
1. LN-GRU Substrate (the neural core)
2. Bits-Back VAE (compression/representation)
3. Byte Interface (content-free I/O)
4. RND/Intrinsic rewards (exploration)
5. Local Plasticity (fast weights within episodes)
6. Sleep/Offline Consolidation (replay + imagination)

This is the "agent" that will be trained on CCB and other environments.

Reference: BLUEPRINT.md Sections 2.2-2.8
"""

from __future__ import annotations

from typing import Tuple, NamedTuple, Optional, Dict, Any, List
from dataclasses import dataclass

import math
import torch
import torch.nn as nn
import torch.nn.functional as F

from src.core.substrate import RPJSubstrate, SubstrateOutput, HIDDEN_DIM, LATENT_DIM, K_MAX
from src.core.vae import BitsBackVAE, VAEOutput
from src.core.byte_interface import phi, AutoregressiveActionDecoder, ByteInterface
from src.core.plasticity import LocalPlasticity, PlasticityConfig
from src.core.sleep import SleepModule, SleepConfig
from src.core.goal_encoder import GoalEncoder, GoalEncoderConfig


def amplify_step_signal(phi_obs: torch.Tensor, meta_offset: int = 448) -> torch.Tensor:
    """
    JARVIS 420 FIX: Amplify step signal in observations.

    The step byte (at meta_offset + 6) after phi() normalization produces
    nearly identical values: step 0 = -1.0, step 1 = -0.988, step 2 = -0.976, step 3 = -0.965.
    These 0.012 differences are too small for the model to distinguish.

    This function amplifies the step signal by adding a sinusoidal encoding
    of the step position to the last 8 bytes, making step differences salient.

    Args:
        phi_obs: Normalized observation [batch, obs_dim] with values in [-1, 1]
        meta_offset: Offset to metadata section (default 448)

    Returns:
        Modified phi_obs with amplified step signal
    """
    # Extract step byte (at meta_offset + 6, which is byte 454)
    # In normalized space: step_val = (step_byte - 127.5) / 127.5
    # To recover step_byte: step_byte = step_val * 127.5 + 127.5
    step_byte_idx = meta_offset + 6
    step_normalized = phi_obs[:, step_byte_idx]  # [batch]
    step_raw = (step_normalized * 127.5 + 127.5).round().long().clamp(0, 255)  # [batch]

    # Create amplified step encoding using sinusoidal pattern (like positional encoding)
    batch_size = phi_obs.size(0)
    device = phi_obs.device

    step_float = step_raw.float()
    freqs = torch.tensor([1.0, 0.5, 0.25, 0.125], device=device)
    angles = step_float.unsqueeze(1) * freqs.unsqueeze(0) * 3.14159  # [batch, 4]
    sin_enc = torch.sin(angles)  # [batch, 4]
    cos_enc = torch.cos(angles)  # [batch, 4]

    # Interleave sin/cos for 8-dim encoding
    step_encoding = torch.stack([sin_enc, cos_enc], dim=2).view(batch_size, 8)  # [batch, 8]

    # Replace last 8 bytes with step encoding
    phi_obs_amplified = phi_obs.clone()
    phi_obs_amplified[:, -8:] = step_encoding

    return phi_obs_amplified


@dataclass
class RPJConfig:
    """Configuration for RPJ Brain."""
    obs_dim: int = 64
    action_bytes: int = 1
    hidden_dim: int = HIDDEN_DIM
    latent_dim: int = LATENT_DIM
    k_max: int = K_MAX

    # Reward coefficients (BLUEPRINT Section 2.7)
    lambda_E: float = 1.0       # Energy penalty
    lambda_mdl: float = 1.0     # Codelength penalty
    lambda_rnd: float = 0.1     # RND intrinsic (warmup)
    lambda_int: float = 0.1     # Info gain intrinsic (post-warmup)
    lambda_dyn: float = 1.0     # Dynamics model loss
    lambda_g: float = 0.01      # Global scalar sparsity penalty - further reduced for K_eff in [2-6]

    # Warmup
    T_warm: int = 50_000        # RND warmup steps

    # RND network dims
    rnd_hidden: int = 256
    rnd_output: int = 128

    # Plasticity
    enable_plasticity: bool = True
    adapter_rank: int = 16      # Fast weight adapter rank
    num_envs: int = 1           # BATCHED: Number of parallel environments for per-env plasticity

    # Sleep
    enable_sleep: bool = True
    buffer_capacity: int = 100_000
    e_sleep_max: float = 0.1
    b_sleep: float = 100.0

    # Discount (BLUEPRINT: γ ≥ 0.999 for sleep credit assignment)
    gamma: float = 0.999

    # Vocab head size (Phase 9 fix: must match training difficulty)
    # TRIVIAL: 5 (TRIVIAL_VOCAB), HARD/EASY/MEDIUM: 21 (COMBINED_VOCAB)
    vocab_size: int = 5

    # Phase 10: Natural Language Interface (goal encoder)
    enable_goal_encoder: bool = False
    goal_embed_dim: int = 64          # Goal embedding dimension
    max_goal_len: int = 512           # Max goal length in UTF-8 bytes

    # Step signal amplification (JARVIS 420 fix from Phase 8)
    # Without this, steps 0-3 have nearly identical phi() values (~0.012 apart)
    # and the model can't distinguish them, causing RUN_TESTS spam
    enable_step_amplification: bool = True


class RPJBrainOutput(NamedTuple):
    """Output from a single brain step."""
    # Actions
    action: torch.Tensor           # Action bytes [batch, action_bytes]
    action_log_prob: torch.Tensor  # Log prob [batch, action_bytes]
    action_mu: torch.Tensor        # Continuous action prediction [batch] - DIFFERENTIABLE for supervised learning

    # States for next step
    h_next: torch.Tensor           # Hidden state [batch, hidden_dim]
    g_t: torch.Tensor              # Global scalars [batch, k_max]

    # VAE outputs
    z_t: torch.Tensor              # Latent [batch, latent_dim]
    mu: torch.Tensor               # Posterior mean [batch, latent_dim]
    sigma: torch.Tensor            # Posterior std [batch, latent_dim]

    # Values and metrics
    value: torch.Tensor            # V(h_t) [batch]
    code_len: torch.Tensor         # CodeLen_t [batch]

    # Emergence metrics
    c_t: torch.Tensor              # Compute allocation [batch, 1]
    k_r: torch.Tensor              # Routed blocks count [batch] - for energy scaling
    n_t: torch.Tensor              # Rollout step count [batch] - for PPO stored decisions
    cbr_t: torch.Tensor            # Compute burst ratio [batch]
    bi_t: torch.Tensor             # Broadcast index [batch]

    # Compute decision log probs (for PPO)
    compute_log_prob: torch.Tensor # Log prob of (k_r, N) [batch]

    # Sleep
    omega_t: torch.Tensor          # Sleep probability [batch]
    is_sleeping: torch.Tensor      # Binary sleep indicator [batch]

    # Plasticity gate
    P_t: torch.Tensor              # Plasticity gate [batch]

    # RND metrics (for curriculum signals)
    rnd_error: torch.Tensor        # RND prediction error [batch] - novelty metric


class RNDNetwork(nn.Module):
    """
    Random Network Distillation for exploration.

    From BLUEPRINT Section 2.7:
    - 2-layer MLP 256→256→128 (ReLU)
    - Fixed random target, trained predictor
    - r^rnd_t = ||f_pred(φ(o_t)) - f_target(φ(o_t))||²
    """

    def __init__(self, obs_dim: int, hidden_dim: int = 256, output_dim: int = 128):
        super().__init__()

        # Fixed random target network
        self.target = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )
        # Freeze target
        for param in self.target.parameters():
            param.requires_grad = False

        # Trained predictor network
        self.predictor = nn.Sequential(
            nn.Linear(obs_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, phi_obs: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Compute RND intrinsic reward.

        Args:
            phi_obs: Normalized observation [batch, obs_dim]

        Returns:
            reward: RND intrinsic reward [batch]
            loss: Predictor loss for training [batch]
        """
        with torch.no_grad():
            target_feat = self.target(phi_obs)

        pred_feat = self.predictor(phi_obs)

        # MSE per sample (intrinsic reward = prediction error)
        error = ((pred_feat - target_feat.detach()) ** 2).mean(dim=-1)

        return error, error  # reward and loss are the same


class RPJBrain(nn.Module):
    """
    The Complete RPJ Brain.

    Combines all components into a single agent that:
    1. Observes bytes, emits bytes (content-free)
    2. Compresses observations via bits-back VAE
    3. Processes via sparse recurrent substrate
    4. Explores via RND (warmup) or info gain (post-warmup)
    5. Adapts within episodes via local plasticity
    6. Consolidates via sleep/offline replay
    7. Outputs value estimates for RL
    """

    def __init__(self, config: RPJConfig):
        super().__init__()

        self.config = config

        # Core substrate
        self.substrate = RPJSubstrate(
            obs_dim=config.obs_dim,
            latent_dim=config.latent_dim,
            hidden_dim=config.hidden_dim,
            action_bytes=config.action_bytes,
            k_max=config.k_max,
        )

        # VAE for compression
        self.vae = BitsBackVAE(
            obs_dim=config.obs_dim,
            hidden_dim=config.hidden_dim,
            latent_dim=config.latent_dim,
        )

        # Action decoder (with g_t conditioning for K_eff gradient flow)
        # JARVIS 420 FIX: Pass obs_dim for direct observation input path
        # Phase 9 FIX: Pass vocab_size to match training difficulty
        self.action_decoder = AutoregressiveActionDecoder(
            hidden_dim=config.hidden_dim,
            num_action_bytes=config.action_bytes,
            k_max=config.k_max,
            obs_dim=config.obs_dim,  # Enable direct gradient path from input to output
            vocab_size=config.vocab_size,  # Must match training vocab
        )

        # RND for exploration warmup
        self.rnd = RNDNetwork(
            obs_dim=config.obs_dim,
            hidden_dim=config.rnd_hidden,
            output_dim=config.rnd_output,
        )

        # Local plasticity (fast weights) - BATCHED for per-env learning
        if config.enable_plasticity:
            self.plasticity = LocalPlasticity(PlasticityConfig(
                hidden_dim=config.hidden_dim,
                obs_dim=config.obs_dim,
                k_max=config.k_max,
                adapter_rank=config.adapter_rank,
                num_envs=config.num_envs,  # JARVIS 360→420: Per-env plasticity
            ))
        else:
            self.plasticity = None

        # Sleep/offline consolidation
        if config.enable_sleep:
            self.sleep = SleepModule(SleepConfig(
                hidden_dim=config.hidden_dim,
                latent_dim=config.latent_dim,
                obs_dim=config.obs_dim,
                action_bytes=config.action_bytes,
                buffer_capacity=config.buffer_capacity,
                e_sleep_max=config.e_sleep_max,
                b_sleep=config.b_sleep,
            ))
        else:
            self.sleep = None

        # Byte interface for OD-NDT harness compatibility
        self.byte_interface = ByteInterface(
            hidden_dim=config.hidden_dim,
            num_action_bytes=config.action_bytes,
        )

        # Phase 10: Goal encoder for natural language interface
        if config.enable_goal_encoder:
            self.goal_encoder = GoalEncoder(GoalEncoderConfig(
                max_goal_len=config.max_goal_len,
                goal_embed_dim=config.goal_embed_dim,
                hidden_dim=256,  # Internal GRU hidden dim
            ))
            # Projection to combine goal embedding with observation
            self.goal_projection = nn.Linear(
                config.goal_embed_dim,
                config.obs_dim,  # Project to observation dimension
            )
        else:
            self.goal_encoder = None
            self.goal_projection = None

        # Step counter for warmup
        self.register_buffer('step_count', torch.tensor(0))

        # Cache for KL intrinsic computation
        self._prev_mu: Optional[torch.Tensor] = None
        self._prev_sigma: Optional[torch.Tensor] = None

        # Cache previous values for TD error computation
        self._prev_value: Optional[torch.Tensor] = None

    def init_state(
        self,
        batch_size: int,
        device: torch.device
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Initialize hidden state and global scalars for new episode.

        Returns:
            h: Initial hidden state [batch, hidden_dim]
            g: Initial global scalars [batch, k_max]
        """
        h = self.substrate.init_hidden(batch_size, device)
        g = self.substrate.init_global_scalars(batch_size, device)

        # Reset KL cache
        self._prev_mu = None
        self._prev_sigma = None
        self._prev_value = None

        # Reset fast weights at episode start
        if self.plasticity is not None:
            self.plasticity.reset_fast_weights()

        # Reset sleep energy tracking
        if self.sleep is not None:
            self.sleep.reset_episode()

        return h, g

    def forward(
        self,
        obs_bytes: torch.Tensor,
        h_t: torch.Tensor,
        g_prev: torch.Tensor,
        a_prev: torch.Tensor,
        training: bool = True,
        goal_bytes: Optional[torch.Tensor] = None,
        goal_lengths: Optional[torch.Tensor] = None,
    ) -> RPJBrainOutput:
        """
        Single brain step.

        Args:
            obs_bytes: Raw observation bytes [batch, obs_dim]
            h_t: Current hidden state [batch, hidden_dim]
            g_prev: Previous global scalars [batch, k_max]
            a_prev: Previous action bytes [batch] or [batch, action_bytes]
            training: Whether in training mode
            goal_bytes: Optional goal text as UTF-8 bytes [batch, max_goal_len] (Phase 10)
            goal_lengths: Optional lengths of goal texts [batch] (Phase 10)

        Returns:
            RPJBrainOutput with all outputs
        """
        batch_size = obs_bytes.size(0)
        device = obs_bytes.device

        # Normalize observation
        phi_obs = phi(obs_bytes)

        # JARVIS 420 FIX: Amplify step signal to make steps distinguishable
        # Without this, steps 0-3 have nearly identical phi() values
        if self.config.enable_step_amplification:
            phi_obs = amplify_step_signal(phi_obs)

        # Phase 10: Add goal conditioning if goal encoder is enabled and goal provided
        if self.goal_encoder is not None and goal_bytes is not None:
            goal_embed = self.goal_encoder(goal_bytes, goal_lengths)  # [B, goal_embed_dim]
            goal_features = self.goal_projection(goal_embed)  # [B, obs_dim]
            phi_obs = phi_obs + goal_features  # Additive conditioning

        # Encode observation to latent
        vae_output = self.vae(h_t, phi_obs, obs_bytes)
        z_t = vae_output.z_t
        mu = vae_output.mu
        sigma = vae_output.sigma
        code_len = vae_output.code_len

        # Get fast-weight adapter factors if plasticity enabled
        recurrent_A = None
        recurrent_B = None
        if self.plasticity is not None:
            recurrent_A = self.plasticity.recurrent_adapter.A
            recurrent_B = self.plasticity.recurrent_adapter.B

        # Substrate forward pass (with optional fast-weight adaptation)
        substrate_out = self.substrate(
            phi_obs=phi_obs,
            z_t=z_t,
            a_prev=a_prev,
            h_t=h_t,
            g_prev=g_prev,
            training=training,
            recurrent_A=recurrent_A,
            recurrent_B=recurrent_B,
        )

        # Get value estimate (conditions on g_t for K_eff gradient flow)
        value = self.substrate.get_value(substrate_out.h_next, substrate_out.g_t)

        # Generate action (conditions on g_t for K_eff gradient flow)
        # JARVIS 420 FIX: Pass phi_obs for direct observation→action gradient path
        action, action_log_prob, action_mu = self.action_decoder(
            substrate_out.h_next,
            g_t=substrate_out.g_t,
            num_bytes=self.config.action_bytes,
            greedy=not training,
            phi_obs=phi_obs,  # Direct input for identity tasks
        )

        # Use compute_log_prob from substrate (NOT recomputed - same sample)
        compute_log_prob = substrate_out.compute_log_prob

        # Sleep probability
        if self.sleep is not None:
            omega_t = self.sleep.get_sleep_probability(substrate_out.h_next)
            is_sleeping = self.sleep.is_sleeping(omega_t)
        else:
            omega_t = torch.zeros(batch_size, device=device)
            is_sleeping = torch.zeros(batch_size, dtype=torch.bool, device=device)

        # Plasticity gate
        if self.plasticity is not None:
            P_t = self.plasticity.plasticity_gate(substrate_out.g_t)
        else:
            P_t = torch.zeros(batch_size, device=device)

        # RND error for curriculum signals (computed once, reused)
        rnd_error, _ = self.rnd(phi_obs)

        # Update step counter
        if training:
            self.step_count += batch_size

        return RPJBrainOutput(
            action=action,
            action_log_prob=action_log_prob,
            action_mu=action_mu,  # DIFFERENTIABLE for supervised learning
            h_next=substrate_out.h_next,
            g_t=substrate_out.g_t,
            z_t=z_t,
            mu=mu,
            sigma=sigma,
            value=value,
            code_len=code_len,
            c_t=substrate_out.c_t,
            k_r=substrate_out.k_r,
            n_t=substrate_out.n_t,
            cbr_t=substrate_out.cbr_t,
            bi_t=substrate_out.bi_t,
            compute_log_prob=compute_log_prob,
            omega_t=omega_t,
            is_sleeping=is_sleeping,
            P_t=P_t,
            rnd_error=rnd_error,
        )

    def compute_intrinsic_reward(
        self,
        phi_obs: torch.Tensor,
        mu: torch.Tensor,
        sigma: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute intrinsic reward (RND during warmup, info gain after).

        Args:
            phi_obs: Normalized observation [batch, obs_dim]
            mu: Current posterior mean [batch, latent_dim]
            sigma: Current posterior std [batch, latent_dim]

        Returns:
            intrinsic_reward: [batch]
        """
        in_warmup = self.step_count < self.config.T_warm

        if in_warmup:
            # RND intrinsic reward
            r_int, _ = self.rnd(phi_obs)
            return self.config.lambda_rnd * r_int
        else:
            # Information gain KL intrinsic reward
            if self._prev_mu is None:
                # First step after warmup, no KL
                r_int = torch.zeros(mu.size(0), device=mu.device)
            else:
                r_int = self.vae.compute_kl_intrinsic(
                    mu, sigma, self._prev_mu, self._prev_sigma
                )

            # Cache for next step
            self._prev_mu = mu.detach()
            self._prev_sigma = sigma.detach()

            return self.config.lambda_int * r_int

    def compute_reward_per_joule(
        self,
        extrinsic_reward: torch.Tensor,
        intrinsic_reward: torch.Tensor,
        energy_t: torch.Tensor,
        code_len_t: torch.Tensor,
        g_t: torch.Tensor = None,
        omega_t: Optional[torch.Tensor] = None,
        e_cap_step: float = 0.1,  # From BLUEPRINT: 200J / 2000 steps
    ) -> torch.Tensor:
        """
        Compute the full RPJ reward.

        From BLUEPRINT Section 2.7:
        r̃_t = r_t + λ_int * r^int_t
        J = Σ γ^t (r̃_t - λ_E * Ê_t - λ_mdl * Ĉ_t - λ_g * ||g_t||_1)

        K_eff Fix: Added λ_g sparsity penalty on g_t to encourage compression.
        This creates gradient pressure to push unused scalars toward 0.

        Args:
            extrinsic_reward: Environment reward [batch]
            intrinsic_reward: RND or info gain reward [batch]
            energy_t: Energy used this step [batch]
            code_len_t: Codelength this step [batch]
            g_t: Global scalars [batch, k_max] (for sparsity penalty)
            e_cap_step: Per-step energy cap (for normalization)

        Returns:
            rpj_reward: Full reward for RL [batch]
        """
        # Combined extrinsic + intrinsic
        r_tilde = extrinsic_reward + intrinsic_reward

        # Normalized energy penalty (includes sleep allocation if provided)
        sleep_energy_t = torch.zeros_like(energy_t)
        if omega_t is not None and self.sleep is not None:
            sleep_energy_t = self.sleep.compute_sleep_energy(omega_t)
        E_hat = (energy_t + sleep_energy_t) / e_cap_step

        # Normalized codelength penalty
        # CodeLen_t is in nats; convert to bits by dividing by ln(2),
        # then normalize by raw observation bits (8 * obs_dim).
        C_hat = code_len_t / (8 * self.config.obs_dim * math.log(2))

        # G_t sparsity penalty (L1 norm normalized by k_max)
        # This encourages unused scalars to go to 0, compressing K_eff
        if g_t is not None:
            G_hat = g_t.abs().mean(dim=-1)  # Mean L1 per sample, range [0, 1]
        else:
            G_hat = torch.zeros_like(extrinsic_reward)

        # Full objective with sparsity penalty
        rpj_reward = (r_tilde
                      - self.config.lambda_E * E_hat
                      - self.config.lambda_mdl * C_hat
                      - self.config.lambda_g * G_hat)

        return rpj_reward

    def get_action_log_prob(
        self,
        h_t: torch.Tensor,
        actions: torch.Tensor,
        g_t: torch.Tensor = None,
    ) -> torch.Tensor:
        """Get log probability of given actions (for PPO)."""
        return self.action_decoder.get_log_prob(h_t, actions, g_t)

    def get_action_entropy(self, h_t: torch.Tensor, g_t: torch.Tensor = None) -> torch.Tensor:
        """Get action distribution entropy (for PPO entropy bonus)."""
        return self.action_decoder.get_entropy(h_t, self.config.action_bytes, g_t)

    def evaluate_actions(
        self,
        obs_bytes: torch.Tensor,
        prev_h: torch.Tensor,
        prev_g: torch.Tensor,
        prev_a: torch.Tensor,
        actions: torch.Tensor,
        z_t: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, Optional[torch.Tensor]]:
        """
        Evaluate actions by re-running forward pass with gradients.

        TRUNCATED BPTT(1): This is the critical method that restores gradient flow
        from observations through substrate to actions. Without this, the substrate
        never learns and outputs random noise, causing policy collapse.

        JARVIS 420 FIX #1: The original implementation used detached hidden states
        during PPO update, breaking the obs→substrate→action gradient chain.

        JARVIS 420 FIX #2: Accept pre-computed z_t from rollout buffer to ensure
        the substrate sees the SAME context during update as during execution.
        Re-sampling z_t injects massive noise that washes out the input signal.

        Args:
            obs_bytes: Observation bytes [batch, obs_dim]
            prev_h: Hidden state before forward pass [batch, hidden_dim]
            prev_g: Global scalars before forward pass [batch, k_max]
            prev_a: Previous action [batch] or [batch, action_bytes]
            actions: Actions taken (to evaluate log_prob) [batch, action_bytes]
            z_t: Optional pre-computed latent from rollout [batch, latent_dim]

        Returns:
            action_log_probs: Log prob of actions [batch, action_bytes]
            entropy: Action distribution entropy [batch]
            values: Value estimates [batch]
            g_t: Global scalars (for compute allocation importance sampling) [batch, k_max]
            h_next: New hidden state [batch, hidden_dim]
            action_mu: Continuous action prediction [batch] - DIFFERENTIABLE for supervised learning
        """
        # Normalize observation
        phi_obs = phi(obs_bytes)

        # JARVIS 420 FIX: Amplify step signal to make steps distinguishable
        if self.config.enable_step_amplification:
            phi_obs = amplify_step_signal(phi_obs)

        # JARVIS 420 FIX: Use stored z_t if provided to ensure consistent state
        # Re-sampling z_t introduces noise that washes out the obs→action signal
        if z_t is None:
            vae_output = self.vae(prev_h, phi_obs, obs_bytes)
            z_t = vae_output.z_t

        # Substrate forward pass WITH GRADIENTS
        # This is the key: we re-run the forward pass so gradients can flow
        # from policy loss back through substrate to learn input→output mapping
        substrate_out = self.substrate(
            phi_obs=phi_obs,
            z_t=z_t,
            a_prev=prev_a,
            h_t=prev_h,
            g_prev=prev_g,
            training=True,  # Always training mode for PPO update
        )

        # Get value estimate (conditioned on g_t for K_eff)
        values = self.substrate.get_value(substrate_out.h_next, substrate_out.g_t)

        # Get log probs for the actions taken (conditioned on g_t)
        # JARVIS 420 FIX: Pass phi_obs for direct observation→action gradient path
        action_log_probs = self.action_decoder.get_log_prob(
            substrate_out.h_next, actions, substrate_out.g_t, phi_obs
        )

        # Get entropy (conditioned on g_t)
        # JARVIS 420 FIX: Pass phi_obs for direct observation→action gradient path
        entropy = self.action_decoder.get_entropy(
            substrate_out.h_next, self.config.action_bytes, substrate_out.g_t, phi_obs
        )

        # Get action_mu for supervised auxiliary loss
        # HYBRID TRAINING FIX: Return differentiable action_mu for supervised DoErr loss
        action_mu = None
        if self.action_decoder.gaussian_head is not None:
            _, action_mu, _ = self.action_decoder.gaussian_head.forward(
                substrate_out.h_next, substrate_out.g_t, phi_obs
            )

        return action_log_probs, entropy, values, substrate_out.g_t, substrate_out.h_next, action_mu

    def get_vocab_logits(
        self,
        obs_bytes: torch.Tensor,
        prev_h: torch.Tensor,
        prev_g: torch.Tensor,
        prev_a: torch.Tensor,
        z_t: Optional[torch.Tensor] = None,
    ) -> Optional[torch.Tensor]:
        """
        Get vocab classification logits for direct BC training.

        JARVIS VOCAB FIX: The VocabClassificationHead needs direct supervision
        during BC training to learn the correct vocab token for each bug type.
        This bypasses the autoregressive collapse.

        Args:
            obs_bytes: Observation bytes [batch, obs_dim]
            prev_h: Hidden state before forward pass [batch, hidden_dim]
            prev_g: Global scalars before forward pass [batch, k_max]
            prev_a: Previous action [batch] or [batch, action_bytes]
            z_t: Optional pre-computed latent from rollout [batch, latent_dim]

        Returns:
            vocab_logits: Logits over TRIVIAL_VOCAB [batch, 5] or None if no vocab head
        """
        vocab_head = getattr(self.action_decoder, 'vocab_head', None)
        if vocab_head is None:
            return None

        # Normalize observation
        phi_obs = phi(obs_bytes)

        # JARVIS 420 FIX: Amplify step signal to make steps distinguishable
        if self.config.enable_step_amplification:
            phi_obs = amplify_step_signal(phi_obs)

        # Get z_t if not provided
        if z_t is None:
            vae_output = self.vae(prev_h, phi_obs, obs_bytes)
            z_t = vae_output.z_t

        # Run substrate forward pass
        substrate_out = self.substrate(
            phi_obs=phi_obs,
            z_t=z_t,
            a_prev=prev_a,
            h_t=prev_h,
            g_prev=prev_g,
            training=True,
        )

        # Extract goal_bytes and focus_text from phi_obs
        goal_start = self.action_decoder.goal_start
        goal_dim = self.action_decoder.goal_dim
        focus_text_start = self.action_decoder.focus_text_start
        focus_text_dim = self.action_decoder.focus_text_dim

        goal_bytes = phi_obs[:, goal_start:goal_start + goal_dim]
        focus_text = phi_obs[:, focus_text_start:focus_text_start + focus_text_dim]

        # Get vocab logits from the dedicated head
        vocab_logits = vocab_head(substrate_out.h_next, goal_bytes, focus_text)
        return vocab_logits

    def update_vae_target(self):
        """Update VAE target encoder via Polyak averaging."""
        self.vae.update_target()

    def get_vae_loss(
        self,
        h_t: torch.Tensor,
        phi_obs: torch.Tensor,
        obs_bytes: torch.Tensor
    ) -> torch.Tensor:
        """Get VAE training loss for direct SGD."""
        return self.vae.get_vae_loss(h_t, phi_obs, obs_bytes)

    def get_rnd_loss(self, phi_obs: torch.Tensor) -> torch.Tensor:
        """Get RND predictor loss for training."""
        _, loss = self.rnd(phi_obs)
        return loss.mean()

    def count_parameters(self) -> Dict[str, int]:
        """Count parameters by component."""
        result = {
            'substrate': sum(p.numel() for p in self.substrate.parameters()),
            'vae': sum(p.numel() for p in self.vae.parameters() if p.requires_grad),
            'action_decoder': sum(p.numel() for p in self.action_decoder.parameters()),
            'rnd': sum(p.numel() for p in self.rnd.predictor.parameters()),
        }

        if self.plasticity is not None:
            result['plasticity_slow'] = self.plasticity.count_slow_parameters()
            result['plasticity_fast'] = self.plasticity.count_fast_parameters()

        if self.sleep is not None:
            result['sleep'] = sum(p.numel() for p in self.sleep.parameters())

        result['total'] = sum(p.numel() for p in self.parameters() if p.requires_grad)

        return result

    def update_plasticity(
        self,
        h_t: torch.Tensor,
        phi_o_next: torch.Tensor,
        reward: torch.Tensor,
        value: torch.Tensor,
        value_next: torch.Tensor,
        g_t: torch.Tensor,
    ):
        """
        Update fast weights via local plasticity rule.

        Args:
            h_t: Hidden state [batch, hidden_dim]
            phi_o_next: Normalized next observation [batch, obs_dim]
            reward: Reward [batch]
            value: V(h_t) [batch]
            value_next: V(h_{t+1}) [batch]
            g_t: Global scalars [batch, k_max]
        """
        if self.plasticity is None:
            return

        # Compute TD error
        td_error = reward + self.config.gamma * value_next - value

        # Compute local error
        e_t = self.plasticity.compute_local_error(h_t, phi_o_next, td_error)

        # Update fast weights (using h_t as pre-activation for both)
        self.plasticity.update_fast_weights(e_t, h_t, h_t, g_t)

    def add_experience_to_replay(
        self,
        obs: torch.Tensor,
        action: torch.Tensor,
        reward: float,
        next_obs: torch.Tensor,
        done: bool,
        energy: float,
        code_len: float,
        z_t: torch.Tensor,
        h_t: Optional[torch.Tensor] = None,
        td_error: Optional[float] = None,
    ):
        """Add experience to sleep replay buffer."""
        if self.sleep is not None:
            self.sleep.add_experience(
                obs=obs,
                action=action,
                reward=reward,
                next_obs=next_obs,
                done=done,
                energy=energy,
                code_len=code_len,
                z_t=z_t,
                h_t=h_t,
                td_error=td_error,
            )

    def do_sleep_step(
        self,
        batch_size: int = 32,
    ) -> Optional[torch.Tensor]:
        """
        Perform one sleep/consolidation step.

        This implements the imagination loop from BLUEPRINT Section 2.5:
        - Sample from replay buffer
        - Re-encode next_obs to get z_next target (using target encoder)
        - Train dynamics model via 1-step consistency

        Returns:
            dynamics_loss: Loss from imagination (if any)
        """
        if self.sleep is None or len(self.sleep.replay_buffer) < 1:
            return None

        device = next(self.parameters()).device

        # Multi-step dynamics training (uses real transition sequences when available).
        # Try the longest horizon first, fall back to shorter sequences.
        max_n_steps = min(self.sleep.config.n_max, len(self.sleep.replay_buffer))
        sequences = []
        weights = None
        n_steps = 0
        for candidate_n in range(max_n_steps, 0, -1):
            sequences, weights, _ = self.sleep.replay_buffer.sample_sequences(
                sequence_length=candidate_n,
                batch_size=batch_size,
                beta=self.sleep.beta,
            )
            if sequences:
                n_steps = candidate_n
                break

        if not sequences or weights is None or n_steps <= 0:
            return None

        batch_size_eff = len(sequences)

        # z_t start state (from first transition in each sequence)
        z_t = torch.stack([seq[0].z_t for seq in sequences]).to(device)

        # Actions over the sequence: [B, n_steps, action_dim]
        actions_steps = [torch.stack([seq[i].action for seq in sequences]) for i in range(n_steps)]
        actions = torch.stack(actions_steps, dim=1).to(device)

        # Targets: encode each step's next_obs using the corresponding stored hidden state.
        # Each seq[i] provides (a_{t+i}, o_{t+i+1}, h_{t+i+1}).
        z_targets = []
        for i in range(n_steps):
            next_obs_i = torch.stack([seq[i].next_obs for seq in sequences]).to(device)
            h_i = torch.stack([seq[i].h_t for seq in sequences]).to(device)
            phi_o_next_i = phi(next_obs_i)
            z_next_target_i, _, _ = self.vae.encode(h_i, phi_o_next_i, use_target=True)
            z_targets.append(z_next_target_i)

        dyn_loss = self.sleep.compute_multistep_dynamics_loss(
            z_t=z_t,
            actions=actions,
            z_targets=z_targets,
            n_steps=n_steps,
        )

        weighted_loss = dyn_loss * weights.mean().to(device)
        return weighted_loss

    def apply_synaptic_renormalization(self):
        """Apply synaptic renormalization after sleep."""
        if self.sleep is not None:
            self.sleep.synaptic_renormalization(self.substrate)
            self.sleep.synaptic_renormalization(self.action_decoder)


def create_brain(obs_dim: int, action_bytes: int = 1, **kwargs) -> RPJBrain:
    """Factory function to create RPJ Brain."""
    config = RPJConfig(obs_dim=obs_dim, action_bytes=action_bytes, **kwargs)
    return RPJBrain(config)


if __name__ == "__main__":
    # Quick sanity check
    print("Testing RPJ Brain v5 (with Plasticity + Sleep)...")

    obs_dim = 64
    batch_size = 4

    brain = create_brain(obs_dim=obs_dim, action_bytes=1)

    # Initialize state
    device = torch.device('cpu')
    h, g = brain.init_state(batch_size, device)

    # Dummy inputs
    obs = torch.randint(0, 256, (batch_size, obs_dim))
    a_prev = torch.randint(0, 256, (batch_size, brain.config.action_bytes))

    # Forward pass
    output = brain(obs, h, g, a_prev, training=True)

    print(f"\n=== Shapes ===")
    print(f"Action: {output.action.shape}")
    print(f"Hidden: {output.h_next.shape}")
    print(f"Latent: {output.z_t.shape}")
    print(f"Value: {output.value.shape}")

    print(f"\n=== Core Values ===")
    print(f"Action: {output.action.tolist()}")
    print(f"Value: {output.value.tolist()}")
    print(f"CodeLen: {output.code_len.tolist()}")
    print(f"CBR: {output.cbr_t.tolist()}")
    print(f"BI: {output.bi_t.tolist()}")

    print(f"\n=== Sleep & Plasticity ===")
    print(f"ω_t (sleep prob): {output.omega_t.tolist()}")
    print(f"Is sleeping: {output.is_sleeping.tolist()}")
    print(f"P_t (plasticity gate): {output.P_t.tolist()}")

    # Test intrinsic reward
    phi_obs = phi(obs)
    r_int = brain.compute_intrinsic_reward(phi_obs, output.mu, output.sigma)
    print(f"\nIntrinsic reward (RND): {r_int.tolist()}")

    # Test RPJ reward
    extrinsic = torch.randn(batch_size)
    energy = torch.rand(batch_size) * 0.05
    rpj = brain.compute_reward_per_joule(extrinsic, r_int, energy, output.code_len)
    print(f"RPJ reward: {rpj.tolist()}")

    # Test plasticity update
    obs_next = torch.randint(0, 256, (batch_size, obs_dim))
    phi_o_next = phi(obs_next)
    reward = torch.randn(batch_size)
    value_next = brain.substrate.get_value(output.h_next)

    brain.update_plasticity(
        h, phi_o_next, reward, output.value, value_next, output.g_t
    )
    print(f"\n✓ Plasticity update OK")
    print(f"Fast weight A norm: {brain.plasticity.recurrent_adapter.A.norm().item():.4f}")

    # Test replay buffer
    for i in range(10):
        brain.add_experience_to_replay(
            obs=obs[0],
            action=output.action[0],
            reward=float(reward[0].item()),
            next_obs=obs_next[0],
            done=False,
            energy=energy[0].item(),
            code_len=output.code_len[0].item(),
            z_t=output.z_t[0],
        )
    print(f"Replay buffer size: {len(brain.sleep.replay_buffer)}")

    # Parameter counts
    print(f"\n=== Parameters ===")
    params = brain.count_parameters()
    for name, count in params.items():
        print(f"{name}: {count:,}")

    # Verify fast param budget
    if brain.plasticity is not None:
        fast = brain.plasticity.count_fast_parameters()
        total = params['total']
        budget = min(500_000, int(0.05 * total))
        print(f"\nFast param budget: {fast:,} / {budget:,} ({'OK' if fast <= budget else 'EXCEEDED!'})")

    # Gradient test
    loss = output.value.sum() + output.code_len.mean() + output.action_log_prob.sum()
    loss.backward()
    print(f"\n✓ Backward pass OK")

    # K_eff fix verification: Check that W_g receives gradient
    W_g_param = brain.substrate.global_broadcast.W_g.weight
    if W_g_param.grad is not None:
        grad_norm = W_g_param.grad.norm().item()
        print(f"✓ K_eff Fix: W_g.grad.norm = {grad_norm:.6f} (gradient flows to g_t!)")
    else:
        print("✗ K_eff Fix FAILED: W_g.grad is None!")

    print("\n✓ RPJ Brain v5 works!")
