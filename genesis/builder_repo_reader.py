from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


ALLOWED_SUFFIXES = {
    ".py",
    ".qml",
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
}

IGNORED_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
}

IGNORED_PREFIXES = (
    "genesis/builder_",
)


@dataclass
class Match:
    score: int
    path: Path
    line_index: int
    keyword: str


class RepoReader:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def _safe_path(self, path: Path) -> Path:
        path = Path(path).resolve()

        if self.root not in path.parents and path != self.root:
            raise ValueError("Refusing to read outside GENESIS worktree")

        return path

    def list_files(self) -> list[Path]:
        files = []

        for path in self.root.rglob("*"):
            if not path.is_file():
                continue

            relative = path.relative_to(self.root).as_posix()

            if any(part in IGNORED_PARTS for part in path.parts):
                continue

            if relative.startswith(IGNORED_PREFIXES):
                continue

            if path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue

            files.append(path)

        return sorted(files)

    def read_file(self, path: Path, max_chars: int = 12000) -> str:
        path = self._safe_path(path)
        text = path.read_text(encoding="utf-8", errors="replace")

        if len(text) > max_chars:
            return text[:max_chars] + "\n[TRUNCATED]\n"

        return text

    def _match_score(
        self,
        path: Path,
        line: str,
        keyword: str,
    ) -> int:
        relative = path.relative_to(self.root).as_posix()
        lower_line = line.lower()
        lower_keyword = keyword.lower()

        score = 0

        # Source code is more useful than prose documentation
        # for repository-architecture questions.
        if path.suffix in {".py", ".qml"}:
            score += 100
        elif path.suffix == ".json":
            score += 50
        else:
            score += 10

        # Main application and real GENESIS modules get priority.
        if relative == "main.py":
            score += 80
        elif relative.startswith("genesis/"):
            score += 60
        elif relative.startswith("tests/"):
            score += 30

        # Exact symbol/string match gets a substantial boost.
        if lower_keyword in lower_line:
            score += 100

        stripped = line.strip()

        if stripped.startswith("def ") and lower_keyword in stripped.lower():
            score += 150

        if stripped.startswith("class ") and lower_keyword in stripped.lower():
            score += 150

        if "=" in stripped and lower_keyword in stripped.lower():
            score += 50

        return score

    def search_context(
        self,
        keywords: list[str],
        *,
        lines_before: int = 10,
        lines_after: int = 22,
        max_chunks: int = 16,
        max_total_chars: int = 24000,
    ) -> str:

        matches: list[Match] = []

        for path in self.list_files():
            try:
                lines = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).splitlines()
            except OSError:
                continue

            for i, line in enumerate(lines):
                lower_line = line.lower()

                for keyword in keywords:
                    if keyword.lower() not in lower_line:
                        continue

                    matches.append(
                        Match(
                            score=self._match_score(path, line, keyword),
                            path=path,
                            line_index=i,
                            keyword=keyword,
                        )
                    )

        matches.sort(
            key=lambda m: (
                -m.score,
                m.path.relative_to(self.root).as_posix(),
                m.line_index,
            )
        )

        chunks = []
        seen_regions = []
        total = 0

        for match in matches:
            path = match.path

            try:
                lines = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).splitlines()
            except OSError:
                continue

            start = max(0, match.line_index - lines_before)
            end = min(len(lines), match.line_index + lines_after + 1)

            # Avoid feeding nearly identical overlapping excerpts.
            overlapping = False
            for seen_path, seen_start, seen_end in seen_regions:
                if seen_path != path:
                    continue

                if not (end < seen_start or start > seen_end):
                    overlapping = True
                    break

            if overlapping:
                continue

            relative = path.relative_to(self.root)

            body = "\n".join(
                f"{n + 1:05d}: {lines[n]}"
                for n in range(start, end)
            )

            chunk = (
                f"\n===== FILE: {relative} "
                f"LINES {start + 1}-{end} "
                f"MATCH={match.keyword!r} SCORE={match.score} =====\n"
                f"{body}\n"
            )

            if total + len(chunk) > max_total_chars:
                break

            chunks.append(chunk)
            seen_regions.append((path, start, end))
            total += len(chunk)

            if len(chunks) >= max_chunks:
                break

        return "".join(chunks)
