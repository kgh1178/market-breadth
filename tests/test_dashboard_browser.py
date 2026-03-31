import os
import shutil
import socket
import subprocess
import time
from pathlib import Path
from urllib.request import urlopen

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
PWCLI = Path.home() / ".codex" / "skills" / "playwright" / "scripts" / "playwright_cli.sh"


def _free_port() -> int:
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", 0))
        except PermissionError as exc:
            raise RuntimeError("local_port_bind_unavailable") from exc
        return int(sock.getsockname()[1])


def _wait_for_server(url: str, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1):
                return
        except Exception:
            time.sleep(0.2)
    raise TimeoutError(f"Timed out waiting for {url}")


@pytest.mark.skipif(not shutil.which("npx"), reason="npx is required for Playwright CLI")
@pytest.mark.skipif(not PWCLI.exists(), reason="Playwright CLI wrapper is unavailable")
def test_full_dashboard_browser_smoke(tmp_path: Path):
    try:
        port = _free_port()
    except RuntimeError:
        pytest.skip("Local port binding is unavailable in this environment")
    server = subprocess.Popen(
        ["python3", "-m", "http.server", str(port), "--directory", str(DOCS_DIR)],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server(f"http://127.0.0.1:{port}/")

        env = os.environ.copy()
        env["CODEX_HOME"] = env.get("CODEX_HOME", str(Path.home() / ".codex"))
        env["PLAYWRIGHT_CLI_SESSION"] = "mbdashsmoke"
        url = f"http://127.0.0.1:{port}/?lang=en"

        subprocess.run(
            [str(PWCLI), "open", url],
            cwd=tmp_path,
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )

        rendered = ""
        deadline = time.time() + 30
        while time.time() < deadline:
            result = subprocess.run(
                [str(PWCLI), "eval", "document.body.innerText"],
                cwd=tmp_path,
                env=env,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            rendered = result.stdout
            if all(token in rendered for token in ["Market Breadth Dashboard", "Global Breadth", "Signals", "Widget View"]):
                break
            time.sleep(1)

        assert "Market Breadth Dashboard" in rendered
        assert "Global Breadth" in rendered
        assert "Signals" in rendered
        assert "Widget View" in rendered
        assert "S&P 500" in rendered
        assert "Nikkei 225" in rendered or "NIKKEI 225" in rendered
        assert "KOSPI 200" in rendered
    finally:
        server.terminate()
        server.wait(timeout=10)
