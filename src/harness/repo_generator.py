"""
Jarvis Harness Repo Generator

Generates synthetic repositories with configurable bugs for training.
Each generated repo is a self-contained project with:
1. Source code (potentially multiple files with dependencies)
2. Tests that fail due to injected bugs
3. A ground truth fix

This is the key to feeding the model REAL challenges, not toy single-file bugs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import os
import random
import tempfile
import shutil

from src.harness.bug_templates import (
    BugTemplate, BugInstance, BugCategory, BugDifficulty,
    sample_template, get_multi_file_templates,
)


@dataclass
class RepoFile:
    """A file in the generated repository."""
    path: str           # Relative path within repo
    content: str        # File content
    is_test: bool = False
    dependencies: List[str] = field(default_factory=list)  # Other files this imports


@dataclass
class GeneratedRepo:
    """A complete generated repository with bugs."""
    name: str
    files: Dict[str, RepoFile]  # path -> RepoFile
    bugs: List[BugInstance]     # Injected bugs
    difficulty: BugDifficulty
    multi_file: bool
    original_files: Dict[str, str]  # path -> original content (ground truth)
    fix_description: str = ""


# =============================================================================
# Code Templates for Repo Generation
# =============================================================================

# Template: Simple data processing pipeline (multi-file)
DATA_PIPELINE_TEMPLATE = {
    "models.py": '''"""Data models for the pipeline."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Record:
    """A single data record."""
    id: int
    name: str
    value: float
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def is_valid(self) -> bool:
        """Check if record is valid."""
        return self.id > 0 and len(self.name) > 0 and self.value >= 0


@dataclass
class Batch:
    """A batch of records."""
    records: List[Record]
    batch_id: str

    def __len__(self) -> int:
        return len(self.records)

    def filter_valid(self) -> 'Batch':
        """Return new batch with only valid records."""
        valid = [r for r in self.records if r.is_valid()]
        return Batch(records=valid, batch_id=self.batch_id)

    def total_value(self) -> float:
        """Sum of all record values."""
        return sum(r.value for r in self.records)
''',

    "processor.py": '''"""Data processing logic."""

from typing import List, Dict, Optional
from models import Record, Batch


class DataProcessor:
    """Processes batches of records."""

    def __init__(self, multiplier: float = 1.0):
        self.multiplier = multiplier
        self.processed_count = 0

    def transform_record(self, record: Record) -> Record:
        """Apply transformation to a single record."""
        new_value = record.value * self.multiplier
        return Record(
            id=record.id,
            name=record.name.upper(),
            value=new_value,
            tags=record.tags + ["processed"],
        )

    def process_batch(self, batch: Batch) -> Batch:
        """Process entire batch."""
        transformed = [self.transform_record(r) for r in batch.records]
        self.processed_count += len(transformed)
        return Batch(records=transformed, batch_id=f"{batch.batch_id}_processed")

    def get_stats(self) -> Dict[str, float]:
        """Return processing statistics."""
        return {
            "processed_count": self.processed_count,
            "multiplier": self.multiplier,
        }


def aggregate_batches(batches: List[Batch]) -> float:
    """Aggregate total value across all batches."""
    total = 0.0
    for batch in batches:
        total += batch.total_value()
    return total
''',

    "pipeline.py": '''"""Main pipeline orchestration."""

from typing import List, Optional
from models import Record, Batch
from processor import DataProcessor, aggregate_batches


class Pipeline:
    """End-to-end data pipeline."""

    def __init__(self, multiplier: float = 1.0, filter_invalid: bool = True):
        self.processor = DataProcessor(multiplier=multiplier)
        self.filter_invalid = filter_invalid
        self.results: List[Batch] = []

    def ingest(self, raw_data: List[dict]) -> Batch:
        """Ingest raw data into a batch."""
        records = []
        for i, item in enumerate(raw_data):
            record = Record(
                id=item.get("id", i),
                name=item.get("name", ""),
                value=float(item.get("value", 0)),
                tags=item.get("tags", []),
            )
            records.append(record)
        return Batch(records=records, batch_id=f"batch_{len(self.results)}")

    def run(self, batch: Batch) -> Batch:
        """Run pipeline on a batch."""
        if self.filter_invalid:
            batch = batch.filter_valid()

        result = self.processor.process_batch(batch)
        self.results.append(result)
        return result

    def get_total_value(self) -> float:
        """Get total value of all processed batches."""
        return aggregate_batches(self.results)

    def get_processed_count(self) -> int:
        """Get total records processed."""
        return self.processor.processed_count
''',

    "test_pipeline.py": '''"""Tests for the data pipeline."""

import pytest
from models import Record, Batch
from processor import DataProcessor, aggregate_batches
from pipeline import Pipeline


class TestRecord:
    def test_valid_record(self):
        r = Record(id=1, name="test", value=10.0)
        assert r.is_valid() == True

    def test_invalid_id(self):
        r = Record(id=0, name="test", value=10.0)
        assert r.is_valid() == False

    def test_invalid_name(self):
        r = Record(id=1, name="", value=10.0)
        assert r.is_valid() == False


class TestBatch:
    def test_filter_valid(self):
        records = [
            Record(id=1, name="a", value=10.0),
            Record(id=0, name="b", value=20.0),  # Invalid
            Record(id=2, name="c", value=30.0),
        ]
        batch = Batch(records=records, batch_id="test")
        filtered = batch.filter_valid()
        assert len(filtered) == 2

    def test_total_value(self):
        records = [
            Record(id=1, name="a", value=10.0),
            Record(id=2, name="b", value=20.0),
        ]
        batch = Batch(records=records, batch_id="test")
        assert batch.total_value() == 30.0


class TestProcessor:
    def test_transform_record(self):
        proc = DataProcessor(multiplier=2.0)
        r = Record(id=1, name="test", value=10.0, tags=["original"])
        transformed = proc.transform_record(r)
        assert transformed.value == 20.0
        assert transformed.name == "TEST"
        assert "processed" in transformed.tags

    def test_process_batch(self):
        proc = DataProcessor(multiplier=1.0)
        records = [Record(id=1, name="a", value=10.0)]
        batch = Batch(records=records, batch_id="test")
        result = proc.process_batch(batch)
        assert result.batch_id == "test_processed"
        assert proc.processed_count == 1


class TestPipeline:
    def test_ingest(self):
        pipe = Pipeline()
        raw = [{"id": 1, "name": "test", "value": 10}]
        batch = pipe.ingest(raw)
        assert len(batch) == 1

    def test_run(self):
        pipe = Pipeline(multiplier=2.0)
        raw = [{"id": 1, "name": "test", "value": 10}]
        batch = pipe.ingest(raw)
        result = pipe.run(batch)
        assert result.records[0].value == 20.0

    def test_get_total_value(self):
        pipe = Pipeline(multiplier=1.0)
        raw1 = [{"id": 1, "name": "a", "value": 10}]
        raw2 = [{"id": 2, "name": "b", "value": 20}]
        pipe.run(pipe.ingest(raw1))
        pipe.run(pipe.ingest(raw2))
        assert pipe.get_total_value() == 30.0

    def test_filter_invalid(self):
        pipe = Pipeline(filter_invalid=True)
        raw = [
            {"id": 1, "name": "valid", "value": 10},
            {"id": 0, "name": "invalid", "value": 20},
        ]
        batch = pipe.ingest(raw)
        result = pipe.run(batch)
        assert len(result) == 1
''',

    "conftest.py": '''"""Pytest configuration."""
import sys
import os

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
''',
}


# Template: Simple REST API (multi-file)
REST_API_TEMPLATE = {
    "config.py": '''"""Configuration for the API."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """API configuration."""
    host: str = "localhost"
    port: int = 8000
    debug: bool = False
    db_path: str = ":memory:"
    max_connections: int = 100

    def validate(self) -> bool:
        """Validate configuration."""
        if self.port < 1 or self.port > 65535:
            return False
        if self.max_connections < 1:
            return False
        return True
''',

    "database.py": '''"""Database layer."""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class User:
    """User model."""
    id: int
    username: str
    email: str
    active: bool = True


class Database:
    """Simple in-memory database."""

    def __init__(self):
        self._users: Dict[int, User] = {}
        self._next_id: int = 1

    def create_user(self, username: str, email: str) -> User:
        """Create a new user."""
        user = User(
            id=self._next_id,
            username=username,
            email=email,
        )
        self._users[user.id] = user
        self._next_id += 1
        return user

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self._users.get(user_id)

    def list_users(self, active_only: bool = False) -> List[User]:
        """List all users."""
        users = list(self._users.values())
        if active_only:
            users = [u for u in users if u.active]
        return users

    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user fields."""
        user = self._users.get(user_id)
        if user is None:
            return None
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        return user

    def delete_user(self, user_id: int) -> bool:
        """Delete user by ID."""
        if user_id in self._users:
            del self._users[user_id]
            return True
        return False
''',

    "handlers.py": '''"""Request handlers."""

from typing import Dict, Any, Optional, Tuple
from database import Database, User


class UserHandler:
    """Handle user-related requests."""

    def __init__(self, db: Database):
        self.db = db

    def create(self, data: Dict[str, Any]) -> Tuple[Dict, int]:
        """Create user handler."""
        username = data.get("username")
        email = data.get("email")

        if not username or not email:
            return {"error": "username and email required"}, 400

        user = self.db.create_user(username, email)
        return self._user_to_dict(user), 201

    def get(self, user_id: int) -> Tuple[Dict, int]:
        """Get user handler."""
        user = self.db.get_user(user_id)
        if user is None:
            return {"error": "user not found"}, 404
        return self._user_to_dict(user), 200

    def list_all(self, active_only: bool = False) -> Tuple[Dict, int]:
        """List users handler."""
        users = self.db.list_users(active_only=active_only)
        return {"users": [self._user_to_dict(u) for u in users]}, 200

    def update(self, user_id: int, data: Dict[str, Any]) -> Tuple[Dict, int]:
        """Update user handler."""
        user = self.db.update_user(user_id, **data)
        if user is None:
            return {"error": "user not found"}, 404
        return self._user_to_dict(user), 200

    def delete(self, user_id: int) -> Tuple[Dict, int]:
        """Delete user handler."""
        if self.db.delete_user(user_id):
            return {"status": "deleted"}, 200
        return {"error": "user not found"}, 404

    def _user_to_dict(self, user: User) -> Dict:
        """Convert user to dict."""
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "active": user.active,
        }
''',

    "app.py": '''"""Main application."""

from typing import Dict, Any, Tuple
from config import Config
from database import Database
from handlers import UserHandler


class App:
    """Main application class."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.db = Database()
        self.user_handler = UserHandler(self.db)
        self._initialized = False

    def initialize(self) -> bool:
        """Initialize the application."""
        if not self.config.validate():
            return False
        self._initialized = True
        return True

    def route(self, method: str, path: str, data: Dict = None) -> Tuple[Dict, int]:
        """Route request to appropriate handler."""
        if not self._initialized:
            return {"error": "app not initialized"}, 500

        data = data or {}

        # Users endpoints
        if path == "/users" and method == "GET":
            return self.user_handler.list_all()
        elif path == "/users" and method == "POST":
            return self.user_handler.create(data)
        elif path.startswith("/users/") and method == "GET":
            user_id = int(path.split("/")[-1])
            return self.user_handler.get(user_id)
        elif path.startswith("/users/") and method == "PUT":
            user_id = int(path.split("/")[-1])
            return self.user_handler.update(user_id, data)
        elif path.startswith("/users/") and method == "DELETE":
            user_id = int(path.split("/")[-1])
            return self.user_handler.delete(user_id)

        return {"error": "not found"}, 404
''',

    "test_app.py": '''"""Tests for the application."""

import pytest
from config import Config
from database import Database, User
from handlers import UserHandler
from app import App


class TestConfig:
    def test_valid_config(self):
        c = Config(port=8080, max_connections=10)
        assert c.validate() == True

    def test_invalid_port(self):
        c = Config(port=0)
        assert c.validate() == False

    def test_invalid_connections(self):
        c = Config(max_connections=0)
        assert c.validate() == False


class TestDatabase:
    def test_create_user(self):
        db = Database()
        user = db.create_user("test", "test@test.com")
        assert user.id == 1
        assert user.username == "test"

    def test_get_user(self):
        db = Database()
        created = db.create_user("test", "test@test.com")
        fetched = db.get_user(created.id)
        assert fetched.username == "test"

    def test_list_users(self):
        db = Database()
        db.create_user("a", "a@test.com")
        db.create_user("b", "b@test.com")
        users = db.list_users()
        assert len(users) == 2

    def test_update_user(self):
        db = Database()
        user = db.create_user("test", "test@test.com")
        updated = db.update_user(user.id, username="updated")
        assert updated.username == "updated"

    def test_delete_user(self):
        db = Database()
        user = db.create_user("test", "test@test.com")
        result = db.delete_user(user.id)
        assert result == True
        assert db.get_user(user.id) is None


class TestApp:
    def test_init(self):
        app = App()
        assert app.initialize() == True

    def test_create_user_route(self):
        app = App()
        app.initialize()
        resp, code = app.route("POST", "/users", {"username": "test", "email": "t@t.com"})
        assert code == 201
        assert resp["username"] == "test"

    def test_get_user_route(self):
        app = App()
        app.initialize()
        app.route("POST", "/users", {"username": "test", "email": "t@t.com"})
        resp, code = app.route("GET", "/users/1")
        assert code == 200
        assert resp["username"] == "test"

    def test_list_users_route(self):
        app = App()
        app.initialize()
        app.route("POST", "/users", {"username": "a", "email": "a@t.com"})
        app.route("POST", "/users", {"username": "b", "email": "b@t.com"})
        resp, code = app.route("GET", "/users")
        assert code == 200
        assert len(resp["users"]) == 2

    def test_not_initialized(self):
        app = App()
        resp, code = app.route("GET", "/users")
        assert code == 500
''',

    "conftest.py": '''"""Pytest configuration."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
''',
}


# =============================================================================
# Bug Injection Functions
# =============================================================================

def inject_off_by_one(code: str) -> Tuple[str, str, str]:
    """Inject off-by-one error. Returns (buggy, hint, fix_description)."""
    # Find range() calls and modify bounds
    import re
    pattern = r'range\((\d+),\s*(\w+)\s*\+\s*1\)'
    match = re.search(pattern, code)
    if match:
        buggy = re.sub(pattern, r'range(\1, \2)', code, count=1)
        return buggy, "Check loop bounds", "Add +1 to range end"

    pattern2 = r'range\((\d+),\s*len\((\w+)\)\)'
    match2 = re.search(pattern2, code)
    if match2:
        buggy = re.sub(pattern2, r'range(\1, len(\2) - 1)', code, count=1)
        return buggy, "Check loop bounds", "Remove -1 from range end"

    return code, "", ""


def inject_wrong_operator(code: str) -> Tuple[str, str, str]:
    """Inject wrong comparison operator."""
    operators = [
        (r'==', '!='),
        (r'>=', '>'),
        (r'<=', '<'),
        (r' > ', ' >= '),
        (r' < ', ' <= '),
    ]
    for orig, wrong in operators:
        if orig in code:
            # Only replace first occurrence
            buggy = code.replace(orig, wrong, 1)
            return buggy, "Check comparison operators", f"Change {wrong} to {orig}"
    return code, "", ""


def inject_wrong_return(code: str) -> Tuple[str, str, str]:
    """Inject wrong return value."""
    import re
    # Find return statements with variables
    pattern = r'return (\w+)\s*$'
    matches = list(re.finditer(pattern, code, re.MULTILINE))
    if matches:
        match = random.choice(matches)
        var = match.group(1)
        # Replace with wrong variable
        wrong_vars = ['None', '0', 'False', '""', '[]']
        wrong = random.choice(wrong_vars)
        buggy = code[:match.start()] + f'return {wrong}' + code[match.end():]
        return buggy, "Check return values", f"Should return {var}, not {wrong}"
    return code, "", ""


def inject_case_transform(code: str) -> Tuple[str, str, str]:
    """Inject a bug by swapping upper/lower casing transformation."""
    if ".upper()" in code:
        buggy = code.replace(".upper()", ".lower()", 1)
        return buggy, "Check string case transforms", "Use .upper() (not .lower())"
    if ".lower()" in code:
        buggy = code.replace(".lower()", ".upper()", 1)
        return buggy, "Check string case transforms", "Use .lower() (not .upper())"
    return code, "", ""


def inject_missing_arg(code: str) -> Tuple[str, str, str]:
    """Inject missing function argument (signature mismatch)."""
    import re
    # Find function definitions with 2+ args
    pattern = r'def (\w+)\(self,\s*(\w+),\s*(\w+)'
    match = re.search(pattern, code)
    if match:
        func_name = match.group(1)
        arg1 = match.group(2)
        arg2 = match.group(3)
        # Remove the second argument
        buggy = re.sub(
            rf'def {func_name}\(self,\s*{arg1},\s*{arg2}',
            f'def {func_name}(self, {arg1}',
            code, count=1
        )
        return buggy, f"Check {func_name} signature", f"Missing argument: {arg2}"
    return code, "", ""


def inject_wrong_import(files: Dict[str, str]) -> Dict[str, str]:
    """Inject wrong import path."""
    import re
    result = dict(files)

    for path, content in files.items():
        if 'from ' in content:
            # Find an import and corrupt it
            pattern = r'from (\w+) import'
            match = re.search(pattern, content)
            if match:
                module = match.group(1)
                wrong_module = module + "_wrong"
                result[path] = re.sub(
                    rf'from {module} import',
                    f'from {wrong_module} import',
                    content, count=1
                )
                return result
    return result


def inject_two_file_bug_combo(
    files: Dict[str, str],
    difficulty: BugDifficulty,
) -> Optional[BugInstance]:
    """
    Inject a true multi-file bug: two distinct files get different bugs.

    This forces the agent to read/modify multiple files to pass all tests,
    which is necessary for exercising v2 (64-byte) multi-file editing.
    """
    candidates = [
        (p, c) for p, c in files.items()
        if not p.startswith("test_") and p != "conftest.py"
    ]
    if len(candidates) < 2:
        return None

    # Choose injectors that tend to succeed on typical Python code.
    primary_injectors = [
        inject_wrong_operator,
        inject_case_transform,
        inject_off_by_one,
        inject_wrong_return,
    ]
    secondary_injectors = [
        inject_case_transform,
        inject_wrong_operator,
        inject_wrong_return,
        inject_off_by_one,
    ]

    def try_inject(code: str, injectors: List) -> Tuple[str, str]:
        for injector in injectors:
            buggy, hint, _ = injector(code)
            if buggy != code:
                return buggy, hint
        return code, ""

    # Find two distinct files that both admit an injection.
    random.shuffle(candidates)
    chosen = None
    for path_a, code_a in candidates:
        buggy_a, hint_a = try_inject(code_a, primary_injectors)
        if buggy_a == code_a:
            continue
        for path_b, code_b in candidates:
            if path_b == path_a:
                continue
            buggy_b, hint_b = try_inject(code_b, secondary_injectors)
            if buggy_b == code_b:
                continue
            chosen = (path_a, code_a, buggy_a, hint_a, path_b, code_b, buggy_b, hint_b)
            break
        if chosen is not None:
            break

    if chosen is None:
        return None

    path_a, code_a, buggy_a, hint_a, path_b, code_b, buggy_b, hint_b = chosen

    files[path_a] = buggy_a
    files[path_b] = buggy_b

    template = BugTemplate(
        name="multi_file_combo",
        category=BugCategory.LOGIC,
        difficulty=difficulty,
        description="Two-file bug combo (requires multi-file fix)",
        files_affected=[path_a, path_b],
        multi_file_fix=True,
    )

    return BugInstance(
        template=template,
        file_path=path_a,
        original_code=code_a,
        buggy_code=buggy_a,
        fix_code=code_a,
        line_number=0,
        hint=f"Multiple failures: inspect {path_a} and {path_b}. {hint_a}; {hint_b}".strip(),
        secondary_files={
            path_b: (code_b, buggy_b, code_b),
        },
    )


# =============================================================================
# Repository Generator
# =============================================================================

class RepoGenerator:
    """Generates synthetic repositories with bugs."""

    TEMPLATES = {
        "data_pipeline": DATA_PIPELINE_TEMPLATE,
        "rest_api": REST_API_TEMPLATE,
    }

    def __init__(self, seed: Optional[int] = None):
        self.seed = seed
        if seed is not None:
            random.seed(seed)

    def generate(
        self,
        template_name: str = None,
        difficulty: BugDifficulty = BugDifficulty.MEDIUM,
        num_bugs: int = 1,
        multi_file: bool = True,
    ) -> GeneratedRepo:
        """
        Generate a repository with injected bugs.

        Args:
            template_name: Which template to use (or random)
            difficulty: Target difficulty level
            num_bugs: Number of bugs to inject
            multi_file: If True, prefer multi-file bugs

        Returns:
            GeneratedRepo with bugs injected
        """
        # Select template
        if template_name is None:
            template_name = random.choice(list(self.TEMPLATES.keys()))

        template = self.TEMPLATES.get(template_name)
        if template is None:
            raise ValueError(f"Unknown template: {template_name}")

        # Create file objects
        original_files = dict(template)  # Copy of clean files
        files = {}
        for path, content in template.items():
            files[path] = RepoFile(
                path=path,
                content=content,
                is_test=path.startswith("test_") or "conftest" in path,
            )

        # Inject bugs
        bugs = []
        buggy_files = dict(template)

        for _ in range(num_bugs):
            bug = self._inject_bug(buggy_files, difficulty, multi_file)
            if bug:
                bugs.append(bug)

        # Update file contents with buggy versions
        for path, content in buggy_files.items():
            if path in files:
                files[path].content = content

        return GeneratedRepo(
            name=f"{template_name}_{random.randint(1000, 9999)}",
            files=files,
            bugs=bugs,
            difficulty=difficulty,
            multi_file=multi_file and any(b.template.multi_file_fix for b in bugs),
            original_files=original_files,
            fix_description="; ".join(b.hint for b in bugs if b.hint),
        )

    def _inject_bug(
        self,
        files: Dict[str, str],
        difficulty: BugDifficulty,
        multi_file: bool,
    ) -> Optional[BugInstance]:
        """Inject a single bug into the files."""
        # For HARD+ tasks, optionally inject a true multi-file bug combo.
        if multi_file and difficulty.value >= BugDifficulty.HARD.value:
            multi_bug = inject_two_file_bug_combo(files, difficulty=difficulty)
            if multi_bug is not None:
                return multi_bug

        # Select non-test, non-config file
        candidates = [
            (p, c) for p, c in files.items()
            if not p.startswith("test_") and p != "conftest.py"
        ]
        if not candidates:
            return None

        path, content = random.choice(candidates)

        # Select injection type based on difficulty
        if difficulty.value <= BugDifficulty.EASY.value:
            injectors = [inject_wrong_operator, inject_off_by_one]
        elif difficulty.value <= BugDifficulty.MEDIUM.value:
            injectors = [inject_wrong_operator, inject_off_by_one, inject_wrong_return]
        else:
            injectors = [inject_wrong_return, inject_missing_arg]

        # Try injectors until one works
        for injector in injectors:
            buggy, hint, fix_desc = injector(content)
            if buggy != content:
                files[path] = buggy

                # Create template for this bug
                template = BugTemplate(
                    name=injector.__name__,
                    category=BugCategory.LOGIC,
                    difficulty=difficulty,
                    description=hint,
                    files_affected=[path],
                )

                return BugInstance(
                    template=template,
                    file_path=path,
                    original_code=content,
                    buggy_code=buggy,
                    fix_code=content,
                    line_number=0,
                    hint=hint,
                )

        return None

    def write_to_disk(self, repo: GeneratedRepo, base_path: str) -> str:
        """Write generated repo to disk. Returns path."""
        repo_path = os.path.join(base_path, repo.name)
        os.makedirs(repo_path, exist_ok=True)

        for path, file_obj in repo.files.items():
            full_path = os.path.join(repo_path, path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(file_obj.content)

        return repo_path


def generate_task_batch(
    num_tasks: int,
    difficulty_range: Tuple[BugDifficulty, BugDifficulty] = (
        BugDifficulty.EASY, BugDifficulty.HARD
    ),
    seed: Optional[int] = None,
) -> List[GeneratedRepo]:
    """Generate a batch of tasks for training."""
    if seed is not None:
        random.seed(seed)

    generator = RepoGenerator(seed=seed)
    tasks = []

    difficulties = list(BugDifficulty)
    valid_difficulties = [
        d for d in difficulties
        if difficulty_range[0].value <= d.value <= difficulty_range[1].value
    ]

    for i in range(num_tasks):
        difficulty = random.choice(valid_difficulties)
        repo = generator.generate(
            difficulty=difficulty,
            num_bugs=random.randint(1, 2),
            multi_file=difficulty.value >= BugDifficulty.MEDIUM.value,
        )
        tasks.append(repo)

    return tasks
