"""why_engine.py - Sensei 5-Whys engine.

Caller: SKILL.md (onboarding trigger), or the CLI:
        python why_engine.py [start | next <depth> <question> <answer> | summary | status]
Schema:
  Writes: <SENSEI_HOME>/projects/<hash>/why_chain.md  (YAML frontmatter + markdown)
  Writes: <SENSEI_HOME>/projects/<hash>/profile.yml   (project profile)
  Writes: $OBSIDIAN_VAULT/projects/sensei/<name>/why_chain.md (when the env var is set)
  Dates: ISO 8601 UTC, %Y-%m-%dT%H:%M:%SZ

Environment:
  SENSEI_HOME     override for the runtime directory (default: ~/.claude/sensei)
  OBSIDIAN_VAULT  optional vault path for the markdown mirror
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SENSEI_HOME = Path(
    os.environ.get("SENSEI_HOME") or (Path.home() / ".claude" / "sensei")
)
PROJECTS_DIR = SENSEI_HOME / "projects"
SENSEI_LOG = SENSEI_HOME / "state" / "why_engine.log"
OBSIDIAN_VAULT = os.environ.get("OBSIDIAN_VAULT", "")

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
SENSEI_LOG.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    filename=str(SENSEI_LOG),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger("why_engine")

# ---------------------------------------------------------------------------
# Why questions (depth 1-5 plus a closing question)
# ---------------------------------------------------------------------------
WHY_QUESTIONS: dict[int, str] = {
    1: "What are you building here - in one sentence, what is this project?",
    2: "Why are you building it? What would be worse without this project?",
    3: "Why does that matter - what sits behind it, deeper?",
    4: "Why did you choose this goal and not a different one?",
    5: "If this project becomes a full success - what comes after it?",
}
CLOSING_QUESTION = "What is the one thing you have to move forward this week?"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _repo_hash(project_path: str) -> str:
    """SHA-256 of the absolute cwd, first 16 characters - an idempotent project key."""
    return hashlib.sha256(project_path.encode()).hexdigest()[:16]


def _repo_name(project_path: str) -> str:
    """Last path segment, used as the repository name."""
    return Path(project_path).name or "unknown"


# ---------------------------------------------------------------------------
# WhyEngine
# ---------------------------------------------------------------------------


class WhyEngine:
    """5-Whys onboarding for one project.

    Dual storage:
    - local: <SENSEI_HOME>/projects/<hash>/why_chain.md
    - vault: $OBSIDIAN_VAULT/projects/sensei/<name>/why_chain.md (when the env var is set)
    - memory MCP: stub - the caller performs the memory tool call itself
    """

    def __init__(self, project_path: str) -> None:
        self.project_path = project_path
        self.hash = _repo_hash(project_path)
        self.name = _repo_name(project_path)
        self.project_dir = PROJECTS_DIR / self.hash
        self.chain_file = self.project_dir / "why_chain.md"
        self.profile_file = self.project_dir / "profile.yml"
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def is_known(self) -> bool:
        """True when a why chain already exists for this project."""
        return self.chain_file.exists()

    def start_chain(self) -> dict:
        """Initialises the why chain and returns the first question.

        Returns:
            {"depth": 1, "question": str}
        """
        now = _now_iso()
        frontmatter = (
            f"---\n"
            f"project: {self.name}\n"
            f"project_path: {self.project_path}\n"
            f"repo_hash: {self.hash}\n"
            f"created: {now}\n"
            f"depth: 0\n"
            f"complete: false\n"
            f"---\n\n"
            f"# Why chain - {self.name}\n\n"
            f"*Started: {now}*\n\n"
        )
        self.chain_file.write_text(frontmatter, encoding="utf-8")
        self._write_profile(complete=False)
        log.info("start_chain project=%s hash=%s", self.name, self.hash)
        return {"depth": 1, "question": WHY_QUESTIONS[1]}

    def record_answer(self, depth: int, question: str, answer: str) -> None:
        """Appends a question/answer pair to why_chain.md and syncs the mirrors.

        Args:
            depth:    1-5 (depth), 6 for the closing question
            question: question text
            answer:   the user's answer
        """
        entry = f"## Depth {depth}: {question}\n\n> {answer}\n\n"
        with self.chain_file.open("a", encoding="utf-8") as f:
            f.write(entry)

        self._update_frontmatter_depth(depth)
        self._sync_vault()
        self._stub_memory(depth, question, answer)

        log.info("record_answer depth=%d project=%s", depth, self.name)

    def next_question(self, depth: int, last_answer: str) -> str:  # noqa: ARG002
        """Returns the next question.

        Args:
            depth:       the depth that was just answered
            last_answer: the last answer (reserved for future contextual tailoring)

        Returns:
            Question string for depth + 1.
        """
        next_depth = depth + 1
        if next_depth <= 5:
            return WHY_QUESTIONS[next_depth]
        if next_depth == 6:
            return CLOSING_QUESTION
        return "Complete already the why chain is, hmm."

    def summarize(self) -> str:
        """Yoda-compatible summary string after all 5 + 1 questions.

        Returns:
            Multi-line string suitable for render_mini.
        """
        if not self.chain_file.exists():
            return "Begun the why chain has not. Start the onboarding you must."

        content = self.chain_file.read_text(encoding="utf-8")
        answer_lines = [l for l in content.splitlines() if l.startswith(">")]
        answers = [l.lstrip("> ").strip() for l in answer_lines[:5]]

        lines = [f"Why chain - {self.name}:"]
        for i, ans in enumerate(answers, 1):
            short = ans[:60] + "..." if len(ans) > 60 else ans
            lines.append(f"  D{i}: {short}")

        self._write_profile(complete=True)
        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _write_profile(self, complete: bool) -> None:
        """Writes (or overwrites) profile.yml."""
        content = (
            f"project: {self.name}\n"
            f"project_path: {self.project_path}\n"
            f"repo_hash: {self.hash}\n"
            f"created: {_now_iso()}\n"
            f"why_depth_complete: {str(complete).lower()}\n"
        )
        self.profile_file.write_text(content, encoding="utf-8")

    def _update_frontmatter_depth(self, depth: int) -> None:
        """Updates the depth: and complete: fields in the YAML frontmatter."""
        try:
            text = self.chain_file.read_text(encoding="utf-8")
            is_done = depth >= 6
            text = text.replace(
                f"depth: {depth - 1}\n",
                f"depth: {depth}\n",
                1,
            )
            if is_done:
                text = text.replace("complete: false\n", "complete: true\n", 1)
            self.chain_file.write_text(text, encoding="utf-8")
        except Exception as exc:
            log.warning("frontmatter update failed: %s", exc)

    def _sync_vault(self) -> None:
        """Mirrors why_chain.md into $OBSIDIAN_VAULT/projects/sensei/<name>/."""
        if not OBSIDIAN_VAULT:
            log.debug("OBSIDIAN_VAULT not set - no sync")
            return
        try:
            target_dir = Path(OBSIDIAN_VAULT) / "projects" / "sensei" / self.name
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / "why_chain.md"
            target.write_text(
                self.chain_file.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            log.info("vault sync -> %s", target)
        except Exception as exc:
            log.warning("vault sync failed: %s", exc)

    def _stub_memory(self, depth: int, question: str, answer: str) -> None:
        """Stub for an external memory MCP server.

        A memory MCP runs as its own server and is reached through its own tool
        calls - no direct Python import is possible. This only leaves a log hint
        so the caller knows to make that tool call itself.
        """
        log.info(
            "memory STUB depth=%d q=%r ans_len=%d "
            "(the caller performs the memory tool call itself)",
            depth,
            question[:40],
            len(answer),
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _usage() -> None:
    script = sys.argv[0]
    print(
        f"Usage: python {script} <cmd>\n"
        "  start                              - start the onboarding, print the first question\n"
        "  next <depth> <question> <answer>   - store an answer and print the next question\n"
        "  summary                            - print the why-chain summary\n"
        "  status                             - is the project known? current depth?\n"
    )


def main() -> None:
    cwd = os.getcwd()
    engine = WhyEngine(project_path=cwd)
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "start":
        result = engine.start_chain()
        print(json.dumps(result, ensure_ascii=False, indent=2))

    elif cmd == "next":
        if len(sys.argv) < 5:
            print("Error: next needs <depth> <question> <answer>", file=sys.stderr)
            sys.exit(1)
        depth = int(sys.argv[2])
        question = sys.argv[3]
        answer = sys.argv[4]
        engine.record_answer(depth, question, answer)
        next_q = engine.next_question(depth, answer)
        print(
            json.dumps(
                {"depth": depth + 1, "question": next_q},
                ensure_ascii=False,
                indent=2,
            )
        )

    elif cmd == "summary":
        print(engine.summarize())

    elif cmd == "status":
        known = engine.is_known()
        depth = 0
        if known:
            try:
                for line in engine.chain_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("depth:"):
                        depth = int(line.split(":", 1)[1].strip())
                        break
            except Exception:
                pass
        print(
            json.dumps(
                {
                    "project": engine.name,
                    "hash": engine.hash,
                    "known": known,
                    "depth": depth,
                    "complete": depth >= 6,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    else:
        _usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
