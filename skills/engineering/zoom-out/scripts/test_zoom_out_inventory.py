import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "zoom_out_inventory.py"


def write_repo(repo: Path) -> None:
    files = {
        "package.json": '{"name":"probe","type":"module"}\n',
        "src/auth/session.ts": (
            "import { saveSession } from '../data/session-store';\n"
            "export class SessionService {\n"
            "  createSession(userId: string) { return saveSession(userId); }\n"
            "}\n"
        ),
        "src/routes/login.ts": (
            "import { SessionService } from '../auth/session';\n"
            "export function loginRoute(req) {\n"
            "  return new SessionService().createSession(req.user.id);\n"
            "}\n"
        ),
        "src/data/session-store.ts": (
            "export function saveSession(userId: string) { return { userId }; }\n"
        ),
    }
    for name, body in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")


class InventoryTests(unittest.TestCase):
    def test_inventory_finds_owner_caller_and_import_edge(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            write_repo(repo)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo", str(repo),
                 "--target", "SessionService", "--json"],
                text=True, capture_output=True, check=True,
            )
        data = json.loads(result.stdout)
        centers = {item["path"] for item in data["center_candidates"]}
        callers = {item["path"] for item in data["caller_candidates"]}
        import_sources = {item["from"] for item in data["import_edges"]}
        self.assertIn("src/auth/session.ts", centers)
        self.assertIn("src/routes/login.ts", callers | centers)
        self.assertTrue(import_sources & {"src/auth/session.ts", "src/routes/login.ts"})
        self.assertTrue(data["suggested_reads"])


if __name__ == "__main__":
    unittest.main()
