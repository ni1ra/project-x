# Jarvis Harness - Tool-using Agent Environment
#
# v2: Extended with multi-file debugging, git operations, and repo generation.

from src.harness.env import JarvisHarnessEnv, Task, VectorizedJarvisEnv, HarnessConfig
from src.harness.actions import (
    ActionType, JarvisAction, encode_action, decode_action,
    encode_action_v2, decode_action_v2, ACTION_BYTES, ACTION_BYTES_V2,
    is_git_action, is_multi_file_action,
)
from src.harness.observations import encode_observation, decode_observation
from src.harness.verifiers import run_pytest, compute_reward, VerifierResult, RewardComponents
from src.harness.bug_templates import (
    BugTemplate, BugInstance, BugCategory, BugDifficulty,
    sample_template, get_multi_file_templates,
)
from src.harness.repo_generator import (
    RepoGenerator, GeneratedRepo, RepoFile,
    generate_task_batch,
)

__all__ = [
    # Environment
    'JarvisHarnessEnv',
    'VectorizedJarvisEnv',
    'HarnessConfig',
    'Task',
    # Actions
    'ActionType',
    'JarvisAction',
    'encode_action',
    'decode_action',
    'encode_action_v2',
    'decode_action_v2',
    'ACTION_BYTES',
    'ACTION_BYTES_V2',
    'is_git_action',
    'is_multi_file_action',
    # Observations
    'encode_observation',
    'decode_observation',
    # Verifiers
    'run_pytest',
    'compute_reward',
    'VerifierResult',
    'RewardComponents',
    # Bug generation (v2)
    'BugTemplate',
    'BugInstance',
    'BugCategory',
    'BugDifficulty',
    'sample_template',
    'get_multi_file_templates',
    # Repo generation (v2)
    'RepoGenerator',
    'GeneratedRepo',
    'RepoFile',
    'generate_task_batch',
]
