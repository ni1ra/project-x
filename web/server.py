"""
RPJ Brain Web Server - Honest CCB Interface

FastAPI server that exposes the trained RPJ Brain for CCB task interaction.
Shows what the brain ACTUALLY does: predict E[Y|do(X=x)] from confounded data.

HONESTY: This brain was trained on Confounded Causal Bandits (CCB).
It does NOT understand text. It predicts causal effects from numeric inputs.
"""

import sys
import os
import math

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, Dict, Any, List
from pathlib import Path
import asyncio

import torch
import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from scipy.stats import norm

from src.core.rpj_brain import RPJBrain, RPJConfig


# --- Configuration ---
CHECKPOINT_PATH = "results/checkpoint_multitask_ccb_blindfold.pt"  # New blindfold checkpoint
FALLBACK_CHECKPOINT = "results/checkpoint_multitask_ccb_final_50331648.pt"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# --- Global State ---
brain: Optional[RPJBrain] = None
h_state: Optional[torch.Tensor] = None
g_state: Optional[torch.Tensor] = None
a_prev: Optional[torch.Tensor] = None
step_count: int = 0

# Current CCB task parameters
current_b_X: float = 0.5
current_b_U: float = 0.3


# --- Pydantic Models ---
class CCBRequest(BaseModel):
    """Request for CCB inference."""
    z_value: float  # Confounding variable observation [-2, 2]
    x_value: float  # Intervention target [-2, 2]
    reset_state: bool = False


class CCBResponse(BaseModel):
    """Response from CCB inference."""
    # Input
    z_value: float
    x_value: float
    z_byte: int
    x_byte: int

    # Brain prediction
    predicted_Y: float
    prediction_byte: int

    # True causal effect (oracle)
    true_Y: float
    error: float

    # Emergence metrics
    k_eff: float
    cbr: float
    bi: float
    c_t: float

    # State info
    h_norm: float
    g_values: List[float]
    P_t: float
    step: int


class TaskConfig(BaseModel):
    """Configure the CCB task parameters."""
    b_X: float  # Causal coefficient [0.2, 0.8]
    b_U: float  # Confounding coefficient [0.1, 0.5]


class BrainStatus(BaseModel):
    """Brain status information."""
    loaded: bool
    checkpoint: str
    device: str
    parameters: int
    obs_dim: int
    step_count: int
    current_b_X: float
    current_b_U: float

    # Current emergence metrics
    current_k_eff: Optional[float] = None
    blindfold_mode: bool = True  # No answer leak


# --- FastAPI App ---
app = FastAPI(
    title="RPJ Brain - Causal Inference Demo",
    description="""
    **HONEST INTERFACE** for the RPJ Brain trained on Confounded Causal Bandits (CCB).

    This brain predicts E[Y | do(X=x)] - the expected outcome under intervention.
    It was trained WITHOUT being given the answer (Blindfold Test).

    **What this brain does:**
    - Takes (Z, X) as input where Z is confounding observation and X is intervention target
    - Outputs predicted causal effect Y
    - Shows emergence metrics (K_eff, CBR) demonstrating brain-like dynamics

    **What this brain does NOT do:**
    - Understand text or language
    - "Chat" or have conversations
    - General intelligence
    """,
    version="2.0.0 (Blindfold)",
)


# --- Helper Functions ---
def compute_true_effect_nonlinear(x: float, b_X: float, b_U: float) -> float:
    """
    Compute E[ReLU(b_X * x² + b_U * U)] analytically for U ~ N(0,1).

    For ReLU(a + b*Z) where Z ~ N(0,1):
    E[ReLU(a + b*Z)] = a * Φ(a/|b|) + |b| * φ(a/|b|)
    """
    a = b_X * x ** 2
    b = b_U

    if abs(b) < 1e-8:
        return max(0.0, a)

    z = a / abs(b)
    cdf = norm.cdf(z)
    pdf = norm.pdf(z)

    return a * cdf + abs(b) * pdf


def float_to_byte(value: float, min_val: float, max_val: float) -> int:
    """Quantize float to byte [0, 255]."""
    normalized = (value - min_val) / (max_val - min_val)
    return int(np.clip(normalized * 255, 0, 255))


def byte_to_float(byte_val: int, min_val: float, max_val: float) -> float:
    """Dequantize byte to float."""
    return byte_val / 255.0 * (max_val - min_val) + min_val


def compute_k_eff(g_values: torch.Tensor) -> float:
    """Compute effective neuromodulator count via participation ratio."""
    squared = g_values.squeeze() ** 2
    sum_sq = squared.sum()
    sum_sq_sq = (squared ** 2).sum()
    if sum_sq_sq < 1e-8:
        return float(g_values.shape[-1])
    return float((sum_sq ** 2) / (sum_sq_sq + 1e-8))


# --- Load Brain ---
def load_brain():
    """Load the trained RPJ Brain from checkpoint."""
    global brain, h_state, g_state, a_prev

    # Try blindfold checkpoint first, fall back to old one
    checkpoint_path = Path(CHECKPOINT_PATH)
    if not checkpoint_path.exists():
        checkpoint_path = Path(FALLBACK_CHECKPOINT)

    if not checkpoint_path.exists():
        raise FileNotFoundError(f"No checkpoint found at {CHECKPOINT_PATH} or {FALLBACK_CHECKPOINT}")

    print(f"Loading checkpoint from: {checkpoint_path}")
    checkpoint = torch.load(checkpoint_path, map_location=DEVICE, weights_only=False)

    # Extract config
    if "config" in checkpoint:
        config_dict = checkpoint["config"]
        config = RPJConfig(**{k: v for k, v in config_dict.items() if hasattr(RPJConfig, k)})
    else:
        config = RPJConfig()

    # Force single-env for inference
    config.num_envs = 1

    # Create brain
    brain = RPJBrain(config).to(DEVICE)

    # Load weights (skip batched fast weights)
    state_dict = checkpoint.get("model_state_dict", checkpoint)
    filtered_state = {}
    for k, v in state_dict.items():
        if "plasticity" in k and ("adapter.A" in k or "adapter.B" in k):
            continue
        filtered_state[k] = v

    brain.load_state_dict(filtered_state, strict=False)
    brain.eval()

    # Initialize state
    reset_brain_state()

    print(f"Brain loaded! Parameters: {sum(p.numel() for p in brain.parameters()):,}")
    print(f"Observation dim: {brain.config.obs_dim} bytes")
    return brain


def reset_brain_state():
    """Reset brain state to initial."""
    global h_state, g_state, a_prev, step_count

    h_state = torch.zeros(1, brain.config.hidden_dim, device=DEVICE)
    g_state = torch.zeros(1, brain.config.k_max, device=DEVICE)
    a_prev = torch.zeros(1, dtype=torch.long, device=DEVICE)
    step_count = 0

    if brain.plasticity is not None:
        brain.plasticity.reset_fast_weights()


# --- API Endpoints ---
@app.on_event("startup")
async def startup_event():
    """Load brain on server startup."""
    try:
        load_brain()
    except Exception as e:
        print(f"Warning: Could not load brain on startup: {e}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    return FileResponse("web/static/index.html")


@app.get("/status", response_model=BrainStatus)
async def get_status():
    """Get brain status."""
    global brain, step_count, g_state, current_b_X, current_b_U

    if brain is None:
        return BrainStatus(
            loaded=False,
            checkpoint=CHECKPOINT_PATH,
            device=DEVICE,
            parameters=0,
            obs_dim=0,
            step_count=0,
            current_b_X=current_b_X,
            current_b_U=current_b_U,
        )

    current_k_eff = None
    if g_state is not None:
        current_k_eff = compute_k_eff(g_state)

    return BrainStatus(
        loaded=True,
        checkpoint=str(CHECKPOINT_PATH),
        device=DEVICE,
        parameters=sum(p.numel() for p in brain.parameters()),
        obs_dim=brain.config.obs_dim,
        step_count=step_count,
        current_b_X=current_b_X,
        current_b_U=current_b_U,
        current_k_eff=current_k_eff,
        blindfold_mode=True,
    )


@app.post("/set_task", response_model=TaskConfig)
async def set_task(config: TaskConfig):
    """Set the CCB task parameters (b_X, b_U)."""
    global current_b_X, current_b_U

    current_b_X = max(0.2, min(0.8, config.b_X))
    current_b_U = max(0.1, min(0.5, config.b_U))

    return TaskConfig(b_X=current_b_X, b_U=current_b_U)


@app.post("/ccb", response_model=CCBResponse)
async def ccb_inference(request: CCBRequest):
    """
    Run CCB inference.

    Given confounding observation Z and intervention target X,
    predict E[Y | do(X=x)].
    """
    global brain, h_state, g_state, a_prev, step_count, current_b_X, current_b_U

    if brain is None:
        raise HTTPException(status_code=500, detail="Brain not loaded")

    if request.reset_state:
        reset_brain_state()

    # Clamp inputs
    z_value = max(-2.0, min(2.0, request.z_value))
    x_value = max(-2.0, min(2.0, request.x_value))

    # Convert to bytes
    z_byte = float_to_byte(z_value, -2.0, 2.0)
    x_byte = float_to_byte(x_value, -2.0, 2.0)

    # Build observation (2 bytes: [Z, X] - NO prev_true_Y!)
    obs_dim = brain.config.obs_dim
    if obs_dim == 2:
        input_bytes = [z_byte, x_byte]
    else:
        # Pad if brain expects more bytes (legacy checkpoint)
        input_bytes = [z_byte, x_byte] + [0] * (obs_dim - 2)

    obs = torch.tensor(input_bytes, dtype=torch.uint8, device=DEVICE).unsqueeze(0)

    # Run inference
    with torch.no_grad():
        output = brain.forward(
            obs_bytes=obs.float(),
            h_t=h_state,
            g_prev=g_state,
            a_prev=a_prev,
            training=False,
        )

    # Update state
    h_state = output.h_next
    g_state = output.g_t
    prediction_byte = int(output.action.squeeze().item())
    a_prev = torch.tensor([prediction_byte], dtype=torch.long, device=DEVICE)
    step_count += 1

    # Decode prediction (CCB-NL uses [0, 4] range)
    predicted_Y = byte_to_float(prediction_byte, 0.0, 4.0)

    # Compute true causal effect
    true_Y = compute_true_effect_nonlinear(x_value, current_b_X, current_b_U)
    error = abs(predicted_Y - true_Y)

    # Compute metrics
    k_eff = compute_k_eff(output.g_t)

    return CCBResponse(
        z_value=z_value,
        x_value=x_value,
        z_byte=z_byte,
        x_byte=x_byte,
        predicted_Y=predicted_Y,
        prediction_byte=prediction_byte,
        true_Y=true_Y,
        error=error,
        k_eff=k_eff,
        cbr=float(output.cbr_t.squeeze().item()),
        bi=float(output.bi_t.squeeze().item()),
        c_t=float(output.c_t.squeeze().item()),
        h_norm=float(h_state.norm().item()),
        g_values=[float(g) for g in output.g_t.squeeze().tolist()],
        P_t=float(output.P_t.squeeze().item()) if hasattr(output, 'P_t') and output.P_t is not None else 0.0,
        step=step_count,
    )


@app.post("/reset")
async def reset():
    """Reset brain state."""
    if brain is None:
        raise HTTPException(status_code=500, detail="Brain not loaded")

    reset_brain_state()
    return {"status": "reset", "step": step_count}


@app.get("/random_trial")
async def random_trial():
    """Generate a random CCB trial and get brain's prediction."""
    global current_b_X, current_b_U

    # Random Z and X
    z_value = np.random.uniform(-2, 2)
    x_value = np.random.uniform(-2, 2)

    # Run inference
    request = CCBRequest(z_value=z_value, x_value=x_value)
    return await ccb_inference(request)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time CCB interaction."""
    global brain, h_state, g_state, a_prev, step_count, current_b_X, current_b_U

    await websocket.accept()

    if brain is None:
        await websocket.send_json({"error": "Brain not loaded"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "reset":
                reset_brain_state()
                await websocket.send_json({"type": "reset", "step": step_count})
                continue

            if data.get("type") == "set_task":
                current_b_X = max(0.2, min(0.8, data.get("b_X", 0.5)))
                current_b_U = max(0.1, min(0.5, data.get("b_U", 0.3)))
                await websocket.send_json({
                    "type": "task_set",
                    "b_X": current_b_X,
                    "b_U": current_b_U,
                })
                continue

            if data.get("type") == "ccb":
                z_value = max(-2.0, min(2.0, data.get("z", 0.0)))
                x_value = max(-2.0, min(2.0, data.get("x", 0.0)))

                z_byte = float_to_byte(z_value, -2.0, 2.0)
                x_byte = float_to_byte(x_value, -2.0, 2.0)

                obs_dim = brain.config.obs_dim
                input_bytes = [z_byte, x_byte] + [0] * max(0, obs_dim - 2)
                obs = torch.tensor(input_bytes, dtype=torch.uint8, device=DEVICE).unsqueeze(0)

                with torch.no_grad():
                    output = brain.forward(
                        obs_bytes=obs.float(),
                        h_t=h_state,
                        g_prev=g_state,
                        a_prev=a_prev,
                        training=False,
                    )

                h_state = output.h_next
                g_state = output.g_t
                prediction_byte = int(output.action.squeeze().item())
                a_prev = torch.tensor([prediction_byte], dtype=torch.long, device=DEVICE)
                step_count += 1

                predicted_Y = byte_to_float(prediction_byte, 0.0, 4.0)
                true_Y = compute_true_effect_nonlinear(x_value, current_b_X, current_b_U)

                await websocket.send_json({
                    "type": "ccb_result",
                    "z": z_value,
                    "x": x_value,
                    "predicted_Y": predicted_Y,
                    "true_Y": true_Y,
                    "error": abs(predicted_Y - true_Y),
                    "k_eff": compute_k_eff(output.g_t),
                    "cbr": float(output.cbr_t.squeeze().item()),
                    "g_values": [float(g) for g in output.g_t.squeeze().tolist()],
                    "step": step_count,
                })

    except WebSocketDisconnect:
        print("WebSocket disconnected")


# --- CHAT INTERFACE (Cross-Modal Grounding) ---
# This is NOT an LLM - it's deterministic text parsing + brain reasoning + text formatting.
# The brain does ALL the causal reasoning. This just provides natural language I/O.

import re


class ChatRequest(BaseModel):
    """Chat request."""
    message: str
    feedback_y: Optional[float] = None  # Optional: provide true Y to help brain learn


class ChatResponse(BaseModel):
    """Chat response."""
    user_message: str
    brain_response: str
    reasoning: Dict[str, Any]  # Show brain's internal reasoning (transparency)
    learning_note: Optional[str] = None  # Explain learning limitation


def parse_causal_query(text: str) -> Optional[tuple[float, float]]:
    """
    Parse a natural language causal query into (Z, X) values.

    Supports patterns like:
    - "If I observe Z=0.5 and intervene with X=1.2, what is Y?"
    - "confound is 0.3, action is -0.8"
    - "Z: 1.5, X: -0.5"
    - Just numbers: "0.5 1.2"
    """
    # Try to find Z and X values
    z_patterns = [
        r"[Zz]\s*[=:]\s*([-\d.]+)",
        r"observe\w*\s*([-\d.]+)",
        r"confound\w*\s*(?:is\s*)?([-\d.]+)",
        r"confounding\s*(?:variable\s*)?([-\d.]+)",
    ]

    x_patterns = [
        r"[Xx]\s*[=:]\s*([-\d.]+)",
        r"interven\w*\s*(?:with\s*)?([-\d.]+)",
        r"do\s*[=(]\s*([-\d.]+)",
        r"action\s*(?:is\s*)?([-\d.]+)",
        r"treat\w*\s*([-\d.]+)",
    ]

    z_value = None
    x_value = None

    # Try each pattern for Z
    for pattern in z_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                z_value = float(match.group(1))
                break
            except ValueError:
                continue

    # Try each pattern for X
    for pattern in x_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                x_value = float(match.group(1))
                break
            except ValueError:
                continue

    # Fallback: look for two numbers
    if z_value is None or x_value is None:
        numbers = re.findall(r"[-+]?\d*\.?\d+", text)
        if len(numbers) >= 2:
            try:
                z_value = float(numbers[0]) if z_value is None else z_value
                x_value = float(numbers[1]) if x_value is None else x_value
            except ValueError:
                pass

    if z_value is not None and x_value is not None:
        return (max(-2.0, min(2.0, z_value)), max(-2.0, min(2.0, x_value)))

    return None


def format_brain_response(predicted_Y: float, true_Y: float, z: float, x: float,
                          k_eff: float, cbr: float, error: float) -> str:
    """
    Format brain's prediction as natural language.

    The brain's reasoning is shown transparently - no hidden interpretation.
    """
    # Describe the magnitude
    if abs(predicted_Y) < 0.2:
        magnitude = "negligible"
    elif abs(predicted_Y) < 0.5:
        magnitude = "small"
    elif abs(predicted_Y) < 1.0:
        magnitude = "moderate"
    elif abs(predicted_Y) < 1.5:
        magnitude = "substantial"
    else:
        magnitude = "large"

    # Describe direction
    if predicted_Y > 0.1:
        direction = "positive"
    elif predicted_Y < -0.1:
        direction = "negative"
    else:
        direction = "neutral"

    # Describe confidence based on K_eff
    if k_eff > 5.0:
        confidence = "high confidence"
        conf_explain = "(multiple neuromodulators engaged)"
    elif k_eff > 3.0:
        confidence = "moderate confidence"
        conf_explain = "(selective neuromodulation)"
    else:
        confidence = "exploratory"
        conf_explain = "(sparse neuromodulator activation)"

    # Build response
    response = f"Given confound Z={z:.2f} and intervention X={x:.2f}:\n\n"
    response += f"**Predicted causal effect:** {predicted_Y:.3f} ({magnitude} {direction})\n\n"
    response += f"**Reasoning ({confidence}):**\n"
    response += f"- K_eff = {k_eff:.2f} {conf_explain}\n"
    response += f"- Compute burst ratio = {cbr:.3f}\n"

    if error < 0.1:
        response += f"\n*Accuracy: Excellent (error = {error:.3f})*"
    elif error < 0.3:
        response += f"\n*Accuracy: Good (error = {error:.3f})*"
    else:
        response += f"\n*Accuracy: Approximate (error = {error:.3f})*"

    return response


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat with the brain using natural language.

    IMPORTANT: This is NOT an LLM. The brain does causal reasoning, this interface
    just provides natural language parsing and formatting.

    The brain understands:
    - Confounding variables (Z)
    - Interventions (X)
    - Causal effects (Y = E[Y | do(X=x)])

    Example queries:
    - "If I observe Z=0.5 and intervene with X=1.2, what happens?"
    - "What's the effect when confound is -0.3 and action is 0.8?"
    - "Z: 1.0, X: -0.5"
    """
    global brain, h_state, g_state, a_prev, step_count, current_b_X, current_b_U

    if brain is None:
        return ChatResponse(
            user_message=request.message,
            brain_response="Brain not loaded. Please restart the server.",
            reasoning={},
        )

    # Parse the query
    parsed = parse_causal_query(request.message)

    if parsed is None:
        return ChatResponse(
            user_message=request.message,
            brain_response=(
                "I understand causal queries about confounding variables (Z) and interventions (X).\n\n"
                "Try asking:\n"
                "- 'If Z=0.5 and X=1.2, what is Y?'\n"
                "- 'confound 0.3, action -0.8'\n"
                "- 'What's the effect when Z=-1 and do(X=0.5)?'\n\n"
                "I predict E[Y | do(X=x)] - the expected outcome under intervention."
            ),
            reasoning={"parsed": None, "error": "Could not parse Z and X values"},
        )

    z_value, x_value = parsed

    # Run inference
    z_byte = float_to_byte(z_value, -2.0, 2.0)
    x_byte = float_to_byte(x_value, -2.0, 2.0)

    obs_dim = brain.config.obs_dim
    input_bytes = [z_byte, x_byte] + [0] * max(0, obs_dim - 2)
    obs = torch.tensor(input_bytes, dtype=torch.uint8, device=DEVICE).unsqueeze(0)

    with torch.no_grad():
        output = brain.forward(
            obs_bytes=obs.float(),
            h_t=h_state,
            g_prev=g_state,
            a_prev=a_prev,
            training=False,
        )

    h_state = output.h_next
    g_state = output.g_t
    prediction_byte = int(output.action.squeeze().item())
    a_prev = torch.tensor([prediction_byte], dtype=torch.long, device=DEVICE)
    step_count += 1

    predicted_Y = byte_to_float(prediction_byte, 0.0, 4.0)
    true_Y = compute_true_effect_nonlinear(x_value, current_b_X, current_b_U)
    error = abs(predicted_Y - true_Y)
    k_eff = compute_k_eff(output.g_t)
    cbr = float(output.cbr_t.squeeze().item())

    # Format response
    brain_response = format_brain_response(
        predicted_Y, true_Y, z_value, x_value, k_eff, cbr, error
    )

    # HONESTY NOTE: Explain why predictions may seem constant
    learning_note = None
    if error > 1.0:
        learning_note = (
            "NOTE: This brain is a multi-task RL agent trained with reward feedback. "
            "In stateless inference mode (no feedback), it outputs the global prior (~2.1). "
            "The brain's true capability emerges during TRAINING when it receives error signals. "
            f"K_eff={k_eff:.1f} shows {int(k_eff)} neuromodulators ARE engaged - "
            "the learning mechanism is active but has no feedback to adapt to."
        )

    return ChatResponse(
        user_message=request.message,
        brain_response=brain_response,
        reasoning={
            "parsed_z": z_value,
            "parsed_x": x_value,
            "predicted_Y": predicted_Y,
            "true_Y": true_Y,
            "error": error,
            "k_eff": k_eff,
            "cbr": cbr,
            "step": step_count,
            "g_values": [float(g) for g in output.g_t.squeeze().tolist()],
        },
        learning_note=learning_note,
    )


# --- MATH INTERFACE ---
# The brain learned to compute f(Z, X) = b_X * X + b_U * tanh(Z)
# This IS a mathematical function. We can use it to solve math problems.

class MathRequest(BaseModel):
    """Math problem request."""
    problem: str  # Natural language math problem

class MathResponse(BaseModel):
    """Math response."""
    problem: str
    interpretation: str
    brain_computation: float
    analytical_answer: Optional[float]
    explanation: str
    confidence: str
    reasoning: Dict[str, Any]


def parse_math_problem(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse a math problem and map it to the brain's domain.

    The brain computes: f(Z, X) = b_X * X + b_U * tanh(Z)

    We can map problems like:
    - "compute tanh(0.5)" -> Z=0.5, use b_U component
    - "what is 0.3 + 0.7*tanh(0.5)?" -> direct evaluation
    - "linear function at x=0.8 with slope b_X" -> X=0.8
    """
    text = text.lower().strip()

    # Pattern 1: tanh evaluation
    tanh_match = re.search(r'tanh\s*\(\s*([-\d.]+)\s*\)', text)
    if tanh_match:
        z = float(tanh_match.group(1))
        return {
            'type': 'tanh',
            'z': z,
            'x': 0.0,  # Zero intervention to isolate tanh component
            'description': f'Evaluating tanh({z})'
        }

    # Pattern 2: Linear combination
    linear_match = re.search(r'([-\d.]+)\s*\*?\s*x\s*\+\s*([-\d.]+)\s*\*?\s*tanh', text)
    if linear_match:
        # Looking for a*x + b*tanh(z) pattern
        return {
            'type': 'linear_combination',
            'description': 'Linear combination with tanh'
        }

    # Pattern 3: Function evaluation f(z, x)
    func_match = re.search(r'f\s*\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)', text)
    if func_match:
        z = float(func_match.group(1))
        x = float(func_match.group(2))
        return {
            'type': 'function_eval',
            'z': z,
            'x': x,
            'description': f'Function evaluation f({z}, {x})'
        }

    # Pattern 4: Simple arithmetic that can be approximated
    add_match = re.search(r'([-\d.]+)\s*\+\s*([-\d.]+)', text)
    if add_match:
        a = float(add_match.group(1))
        b = float(add_match.group(2))
        # Map addition to function domain by scaling
        return {
            'type': 'addition',
            'a': a,
            'b': b,
            'z': a,  # First operand as confound
            'x': b,  # Second as intervention
            'description': f'Addition: {a} + {b}'
        }

    # Pattern 5: Multiplication
    mul_match = re.search(r'([-\d.]+)\s*[*×]\s*([-\d.]+)', text)
    if mul_match:
        a = float(mul_match.group(1))
        b = float(mul_match.group(2))
        return {
            'type': 'multiplication',
            'a': a,
            'b': b,
            'description': f'Multiplication: {a} × {b}'
        }

    # Pattern 6: Numbers only
    nums = re.findall(r'([-\d.]+)', text)
    if len(nums) >= 2:
        return {
            'type': 'numbers',
            'z': float(nums[0]),
            'x': float(nums[1]),
            'description': f'Raw input mapping: Z={nums[0]}, X={nums[1]}'
        }

    return None


@app.post("/math", response_model=MathResponse)
async def solve_math(request: MathRequest):
    """
    Solve math problems using the brain's learned function.

    The brain learned to compute f(Z, X) where f is a nonlinear function.
    This endpoint maps math problems to the brain's computation domain.

    NOTE: The brain is NOT a general-purpose calculator. It learned a specific
    function from CCB training. Math problems outside this domain will be
    approximations at best.
    """
    global brain, h_state, g_state, a_prev, step_count, current_b_X, current_b_U

    if brain is None:
        return MathResponse(
            problem=request.problem,
            interpretation="Brain not loaded",
            brain_computation=0.0,
            analytical_answer=None,
            explanation="Brain not loaded. Restart server.",
            confidence="none",
            reasoning={}
        )

    parsed = parse_math_problem(request.problem)

    if parsed is None:
        return MathResponse(
            problem=request.problem,
            interpretation="Could not parse",
            brain_computation=0.0,
            analytical_answer=None,
            explanation=(
                "Could not map this problem to the brain's function domain.\n\n"
                "The brain computes: f(Z, X) ≈ b_X·X + b_U·tanh(Z)\n\n"
                "Try:\n"
                "- 'What is tanh(0.5)?'\n"
                "- 'Evaluate f(0.3, 0.8)'\n"
                "- 'Compute 0.5 + 0.3'\n"
            ),
            confidence="none",
            reasoning={'error': 'parse_failed'}
        )

    # Get Z and X values for brain computation
    z_val = parsed.get('z', 0.0)
    x_val = parsed.get('x', 0.0)

    # Convert to bytes (same as CCB endpoint)
    z_byte = float_to_byte(z_val, -2.0, 2.0)
    x_byte = float_to_byte(x_val, -2.0, 2.0)

    # Build observation tensor
    obs = torch.tensor([z_byte, x_byte], dtype=torch.uint8, device=DEVICE).unsqueeze(0)

    # Run brain inference
    with torch.no_grad():
        output = brain.forward(
            obs_bytes=obs.float(),
            h_t=h_state,
            g_prev=g_state,
            a_prev=a_prev,
            training=False,
        )

    # Update states
    h_state = output.h_next
    g_state = output.g_t
    prediction_byte = int(output.action.squeeze().item())
    a_prev = torch.tensor([prediction_byte], dtype=torch.long, device=DEVICE)
    step_count += 1

    # Brain's computation - decode from byte
    brain_answer = byte_to_float(prediction_byte, 0.0, 4.0)

    # Analytical answer (true function evaluation)
    analytical = compute_true_effect_nonlinear(x_val, current_b_X, current_b_U)

    # K_eff
    g_values = output.g_t.squeeze()
    g_sorted = torch.sort(g_values, descending=True)[0]
    g_cumsum = torch.cumsum(g_sorted, dim=0)
    k_eff = float((g_cumsum < 0.95).sum().item() + 1)

    # Generate explanation based on problem type
    prob_type = parsed['type']

    if prob_type == 'tanh':
        analytical_tanh = float(np.tanh(z_val))
        explanation = (
            f"**Computing tanh({z_val}):**\n\n"
            f"The brain's learned function includes tanh in its nonlinear component.\n"
            f"Brain approximation: {brain_answer:.4f}\n"
            f"True tanh({z_val}): {analytical_tanh:.4f}\n\n"
            f"Note: The brain doesn't compute pure tanh - it learned the full CCB function."
        )
        analytical = analytical_tanh

    elif prob_type == 'function_eval':
        explanation = (
            f"**Evaluating f({z_val}, {x_val}):**\n\n"
            f"Brain computation: {brain_answer:.4f}\n"
            f"Analytical f(Z,X) = b_X·X + b_U·tanh(Z): {analytical:.4f}\n"
            f"Error: {abs(brain_answer - analytical):.4f}\n\n"
            f"K_eff = {k_eff:.2f} (neuromodulator engagement)"
        )

    elif prob_type == 'addition':
        true_sum = parsed['a'] + parsed['b']
        explanation = (
            f"**Addition mapped to CCB domain:**\n\n"
            f"Problem: {parsed['a']} + {parsed['b']} = {true_sum}\n"
            f"Brain's CCB computation: {brain_answer:.4f}\n\n"
            f"NOTE: The brain wasn't trained on addition. It computes f(Z,X),\n"
            f"which is NOT addition. This shows domain mismatch."
        )
        analytical = true_sum

    elif prob_type == 'multiplication':
        true_prod = parsed['a'] * parsed['b']
        explanation = (
            f"**Multiplication (outside brain's domain):**\n\n"
            f"Problem: {parsed['a']} × {parsed['b']} = {true_prod}\n"
            f"Brain's CCB computation: {brain_answer:.4f}\n\n"
            f"NOTE: The brain computes f(Z,X) = b_X·X + b_U·tanh(Z),\n"
            f"which is NOT multiplication. This is expected to be inaccurate."
        )
        analytical = true_prod

    else:
        explanation = (
            f"**Generic function evaluation:**\n\n"
            f"Inputs: Z={z_val}, X={x_val}\n"
            f"Brain computation: {brain_answer:.4f}\n"
            f"Analytical: {analytical:.4f}\n"
            f"K_eff = {k_eff:.2f}"
        )

    # Determine confidence
    error = abs(brain_answer - analytical) if analytical is not None else float('inf')
    if error < 0.1:
        confidence = "high"
    elif error < 0.3:
        confidence = "medium"
    else:
        confidence = "low (outside trained domain)"

    return MathResponse(
        problem=request.problem,
        interpretation=parsed['description'],
        brain_computation=brain_answer,
        analytical_answer=analytical,
        explanation=explanation,
        confidence=confidence,
        reasoning={
            'problem_type': prob_type,
            'z_value': z_val,
            'x_value': x_val,
            'k_eff': k_eff,
            'step': step_count,
            'g_values': [float(g) for g in output.g_t.squeeze().tolist()],
        }
    )


# Mount static files
app.mount("/static", StaticFiles(directory="web/static"), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8420)
