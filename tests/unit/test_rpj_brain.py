"""
Unit tests for RPJBrain integration points.

Focus:
- Reward-per-joule normalization correctness (bits vs nats)
- Sleep energy wiring (ω_t must affect the energy penalty)
- Sleep replay uses stored hidden state (no h_dummy zeros)
"""

import math

import pytest
import torch

from src.core.rpj_brain import RPJBrain, RPJConfig


class TestRewardPerJoule:
    """Tests for compute_reward_per_joule()."""

    def test_codelen_nats_converted_to_bits(self):
        """
        Regression: CodeLen_t is computed in nats, but Ĉ_t is normalized in bits.

        If CodeLen_t == 8*obs_dim bits, then Ĉ_t should equal 1.0.
        """
        config = RPJConfig(
            obs_dim=10,
            action_bytes=1,
            enable_plasticity=False,
            enable_sleep=False,
            lambda_E=0.0,
            lambda_mdl=1.0,
            lambda_g=0.0,
        )
        brain = RPJBrain(config)

        extrinsic = torch.zeros(1)
        intrinsic = torch.zeros(1)
        energy_t = torch.zeros(1)

        # 8*obs_dim bits == 8*obs_dim*ln(2) nats
        code_len_nats = torch.tensor([8.0 * config.obs_dim * math.log(2)])

        rpj = brain.compute_reward_per_joule(
            extrinsic_reward=extrinsic,
            intrinsic_reward=intrinsic,
            energy_t=energy_t,
            code_len_t=code_len_nats,
            e_cap_step=1.0,
        )

        assert rpj.item() == pytest.approx(-1.0)

    def test_sleep_energy_wires_into_energy_penalty(self):
        """
        Regression: ω_t must affect the energy penalty via compute_sleep_energy().
        """
        config = RPJConfig(
            obs_dim=8,
            action_bytes=1,
            enable_plasticity=False,
            enable_sleep=True,
            lambda_E=1.0,
            lambda_mdl=0.0,
            lambda_g=0.0,
        )
        brain = RPJBrain(config)

        called = {"count": 0}
        orig_compute_sleep_energy = brain.sleep.compute_sleep_energy

        def wrapped_compute_sleep_energy(omega_t: torch.Tensor) -> torch.Tensor:
            called["count"] += 1
            return orig_compute_sleep_energy(omega_t)

        brain.sleep.compute_sleep_energy = wrapped_compute_sleep_energy  # type: ignore[method-assign]

        extrinsic = torch.zeros(1)
        intrinsic = torch.zeros(1)
        energy_t = torch.zeros(1)
        code_len_t = torch.zeros(1)
        omega_t = torch.ones(1)

        # Default e_cap_step=0.1 and e_sleep_max=0.1 => E_hat should be 1.0.
        rpj = brain.compute_reward_per_joule(
            extrinsic_reward=extrinsic,
            intrinsic_reward=intrinsic,
            energy_t=energy_t,
            code_len_t=code_len_t,
            omega_t=omega_t,
            e_cap_step=0.1,
        )

        assert called["count"] == 1
        assert rpj.item() == pytest.approx(-1.0)


class TestSleepReplay:
    """Tests for sleep replay mechanics in RPJBrain.do_sleep_step()."""

    def test_do_sleep_step_uses_stored_hidden_state(self):
        """
        Regression: do_sleep_step must encode next_obs using stored hidden states,
        not an all-zeros dummy tensor.
        """
        config = RPJConfig(
            obs_dim=4,
            action_bytes=1,
            enable_plasticity=False,
            enable_sleep=True,
        )
        brain = RPJBrain(config)

        # Two-step sequence so multi-step loss can run with n_steps=2.
        obs0 = torch.randint(0, 256, (config.obs_dim,), dtype=torch.long)
        obs1 = torch.randint(0, 256, (config.obs_dim,), dtype=torch.long)
        obs2 = torch.randint(0, 256, (config.obs_dim,), dtype=torch.long)

        action0 = torch.tensor([10], dtype=torch.long)
        action1 = torch.tensor([20], dtype=torch.long)

        z0 = torch.randn(config.latent_dim)
        z1 = torch.randn(config.latent_dim)

        h1 = torch.full((config.hidden_dim,), 1.0)
        h2 = torch.full((config.hidden_dim,), 2.0)

        brain.sleep.add_experience(
            obs=obs0,
            action=action0,
            reward=0.0,
            next_obs=obs1,
            done=False,
            energy=0.0,
            code_len=0.0,
            z_t=z0,
            h_t=h1,
            td_error=1.0,
        )
        brain.sleep.add_experience(
            obs=obs1,
            action=action1,
            reward=0.0,
            next_obs=obs2,
            done=False,
            energy=0.0,
            code_len=0.0,
            z_t=z1,
            h_t=h2,
            td_error=1.0,
        )

        captured_h = []
        orig_encode = brain.vae.encode

        def fake_encode(h_t: torch.Tensor, phi_obs: torch.Tensor, use_target: bool = True):
            captured_h.append(h_t.detach().cpu().clone())
            batch = phi_obs.size(0)
            z = torch.zeros(batch, config.latent_dim, device=phi_obs.device)
            mu = torch.zeros_like(z)
            sigma = torch.ones_like(z)
            return z, mu, sigma

        brain.vae.encode = fake_encode  # type: ignore[method-assign]

        called = {"n_steps": None}
        orig_multistep = brain.sleep.compute_multistep_dynamics_loss

        def wrapped_multistep(**kwargs):
            called["n_steps"] = kwargs.get("n_steps")
            return orig_multistep(**kwargs)

        brain.sleep.compute_multistep_dynamics_loss = wrapped_multistep  # type: ignore[method-assign]

        loss = brain.do_sleep_step(batch_size=1)

        # Restore to avoid side effects if this file is imported elsewhere.
        brain.vae.encode = orig_encode  # type: ignore[method-assign]
        brain.sleep.compute_multistep_dynamics_loss = orig_multistep  # type: ignore[method-assign]

        assert loss is not None
        assert loss.shape == ()
        assert called["n_steps"] == 2

        assert len(captured_h) == 2
        assert torch.allclose(captured_h[0].squeeze(0), h1)
        assert torch.allclose(captured_h[1].squeeze(0), h2)

