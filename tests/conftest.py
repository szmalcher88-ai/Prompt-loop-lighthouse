# -*- coding: utf-8 -*-
"""Helpery testów pętli: tymczasowe repo git + mockowany agent.

Każdy test buduje świeże repo w tmp_path/repo. Mock agenta to skrypt
Pythona w tmp_path (POZA repo), sterowany treścią zadania z PLAN.md:
  good:NAME  -> tworzy plik NAME (praca poprawna)
  bad        -> tworzy bad.txt (weryfikator VERIFY_NO_BAD wtedy pada)
  protected  -> tworzy tests/hack.txt (chroniona ścieżka)
  big        -> tworzy big.txt z 700 liniami (scope guard)
  noop       -> nic nie robi
Zero sieci, zero prawdziwego `claude`.
"""
import json
import subprocess
import sys
from pathlib import Path

LOOP_PY = Path(__file__).resolve().parents[1] / "loop.py"

PROMPT_END = "=====PROMPT-END====="

AGENT_SRC = r'''# -*- coding: utf-8 -*-
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if len(sys.argv) > 1:
    prompt = Path(sys.argv[1]).read_text(encoding="utf-8")
else:
    prompt = sys.stdin.read()
with (HERE / "prompts.log").open("a", encoding="utf-8") as f:
    f.write(prompt)
    f.write("\n=====PROMPT-END=====\n")

first = prompt.splitlines()[0]
assert first.startswith("TASK: "), first
task = first[len("TASK: "):].strip()
cwd = Path.cwd()
for op in task.split():
    if op.startswith("good:"):
        (cwd / op[len("good:"):]).write_text("ok\n", encoding="utf-8")
    elif op == "bad":
        (cwd / "bad.txt").write_text("zle\n", encoding="utf-8")
    elif op == "protected":
        d = cwd / "tests"
        d.mkdir(exist_ok=True)
        (d / "hack.txt").write_text("hack\n", encoding="utf-8")
    elif op == "big":
        (cwd / "big.txt").write_text(
            "\n".join("linia %d tresci" % i for i in range(700)) + "\n",
            encoding="utf-8",
        )
    elif op == "bad-vary":
        # za kazda proba INNA tresc porazki (litery, nie cyfry — sygnatura
        # porazki maskuje cyfry, wiec roznice musza byc niecyfrowe)
        cnt = HERE / "vary_counter.txt"
        n = int(cnt.read_text(encoding="utf-8")) if cnt.exists() else 0
        cnt.write_text(str(n + 1), encoding="utf-8")
        (cwd / "bad.txt").write_text(
            "wariant-" + "abcdefgh"[n] + "\n", encoding="utf-8"
        )
    elif op == "noop":
        pass
'''

TEMPLATE = (
    "TASK: {{TASK}}\n"
    "\n"
    "VERIFY:\n"
    "{{VERIFY_COMMANDS}}\n"
    "\n"
    "FEEDBACK:\n"
    "{{FEEDBACK}}\n"
)

# Każda stała to LISTA komend (verify_commands w configu to lista list argv).
VERIFY_GREEN = [[sys.executable, "-c", "pass"]]
# Zielony na nietkniętym repo (baseline), czerwony gdy agent stworzył bad.txt.
VERIFY_NO_BAD = [[
    sys.executable,
    "-c",
    "import os,sys; sys.exit(1 if os.path.exists('bad.txt') else 0)",
]]
VERIFY_ALWAYS_RED = [[sys.executable, "-c", "import sys; sys.exit(1)"]]
# Jak VERIFY_NO_BAD, ale wypisuje treść bad.txt — ogon porażki niesie wtedy
# treść pliku, więc różne treści dają różne sygnatury porażki.
VERIFY_NO_BAD_VERBOSE = [[
    sys.executable,
    "-c",
    "import os,sys\n"
    "if os.path.exists('bad.txt'):\n"
    "    print(open('bad.txt', encoding='utf-8').read())\n"
    "    sys.exit(1)\n"
    "sys.exit(0)",
]]


class LoopEnv:
    """Tymczasowe repo + config + mock agenta, gotowe do `python loop.py`."""

    def __init__(
        self,
        tmp_path: Path,
        tasks,
        verify_commands,
        prompt_mode="stdin",          # "stdin" | "file"
        config_overrides=None,
        gitignore=".loop/\n",
        template=TEMPLATE,
    ):
        self.root = tmp_path
        self.root.mkdir(parents=True, exist_ok=True)
        self.repo = tmp_path / "repo"
        self.repo.mkdir(parents=True)
        self.agent_py = tmp_path / "mock_agent.py"
        self.agent_py.write_text(AGENT_SRC, encoding="utf-8")
        self.prompts_log = tmp_path / "prompts.log"

        (self.repo / "PLAN.md").write_text(
            "# Plan\n\n" + "".join(f"- [ ] {t}\n" for t in tasks),
            encoding="utf-8",
        )
        (self.repo / "PROMPT.template.md").write_text(template, encoding="utf-8")
        if gitignore is not None:
            (self.repo / ".gitignore").write_text(gitignore, encoding="utf-8")

        self.git("init", "-q")
        self.git("config", "user.email", "loop-test@example.com")
        self.git("config", "user.name", "Loop Test")
        self.git("config", "commit.gpgsign", "false")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")

        agent_command = [sys.executable, str(self.agent_py)]
        if prompt_mode == "file":
            agent_command.append("{prompt_file}")
        cfg = {
            "repo_dir": str(self.repo),
            "agent_command": agent_command,
            "verify_commands": verify_commands,
            "max_iterations": 10,
            "max_retries_per_task": 3,
            "agent_timeout_seconds": 120,
            "verify_timeout_seconds": 120,
        }
        cfg.update(config_overrides or {})
        self.config_path = tmp_path / "loop.config.json"
        self.config_path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # -- uruchamianie ---------------------------------------------------

    def run_loop(self, *extra_args):
        import os
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        p = subprocess.run(
            [sys.executable, str(LOOP_PY), "--config", str(self.config_path),
             *extra_args],
            cwd=str(self.repo),
            capture_output=True,
            timeout=300,
            env=env,
        )
        out = p.stdout.decode("utf-8", "replace")
        err = p.stderr.decode("utf-8", "replace")
        return p.returncode, out, err

    # -- introspekcja ---------------------------------------------------

    def git(self, *args):
        p = subprocess.run(
            ["git", *args], cwd=str(self.repo), capture_output=True, timeout=60
        )
        return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")

    def plan_text(self) -> str:
        return (self.repo / "PLAN.md").read_text(encoding="utf-8")

    def commit_subjects(self):
        _, out = self.git("log", "--format=%s")
        return out.strip().splitlines()

    def status_porcelain(self) -> str:
        _, out = self.git("status", "--porcelain")
        return out.strip()

    def stash_list(self) -> str:
        _, out = self.git("stash", "list")
        return out.strip()

    def prompts(self):
        if not self.prompts_log.exists():
            return []
        raw = self.prompts_log.read_text(encoding="utf-8")
        return [p for p in raw.split(PROMPT_END + "\n") if p.strip()]

    def escalation_reports(self):
        loop_dir = self.repo / ".loop"
        if not loop_dir.exists():
            return []
        return sorted(loop_dir.glob("ESKALACJA-*.md"))
