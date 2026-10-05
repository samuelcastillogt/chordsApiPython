import os
import sys
import tempfile
from pathlib import Path

# Isolated database and settings for the whole test session (set before app import).
_db_dir = tempfile.mkdtemp(prefix="chordweaver-tests-")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db_dir}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ.pop("VERCEL", None)

sys.path.insert(0, str(Path(__file__).parent.parent))
