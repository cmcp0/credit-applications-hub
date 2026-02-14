#!/usr/bin/env python3
"""Scaffold a bounded context structure under src/."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChangeCounter:
    created: int = 0
    overwritten: int = 0
    skipped: int = 0


def parse_modules(raw_modules: list[str]) -> list[str]:
    modules: list[str] = []
    for item in raw_modules:
        for part in item.split(","):
            name = part.strip()
            if name and name not in modules:
                modules.append(name)
    return modules


def safe_name(name: str, kind: str) -> str:
    if not name:
        raise ValueError(f"{kind} cannot be empty")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_")
    lowered = name.lower()
    if any(ch not in allowed for ch in lowered):
        raise ValueError(
            f"{kind} '{name}' contains unsupported characters. "
            "Use lowercase letters, digits, or underscores."
        )
    return lowered


def write_text_file(
    path: Path,
    content: str,
    *,
    force: bool,
    dry_run: bool,
    counter: ChangeCounter,
) -> None:
    exists = path.exists()
    action = "OVERWRITE" if exists else "CREATE"

    if exists and not force:
        print(f"SKIP {path}")
        counter.skipped += 1
        return

    print(f"{action} {path}")
    if dry_run:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if exists:
        counter.overwritten += 1
    else:
        counter.created += 1


def module_files(context: str, module: str) -> list[tuple[Path, str]]:
    base = Path("src") / context / module
    capitalized = module.replace("_", " ").title()
    return [
        (
            base / "domain" / "__init__.py",
            f'"""Domain layer for the {module} module."""\n',
        ),
        (
            base / "domain" / "entities.py",
            f'"""Domain entities for the {module} module."""\n\n'
            f"# Define {capitalized} entities here.\n",
        ),
        (
            base / "domain" / "events.py",
            f'"""Domain events for the {module} module."""\n\n'
            f"# Define {capitalized} domain events here.\n",
        ),
        (
            base / "domain" / "value_objects.py",
            f'"""Value objects for the {module} module."""\n\n'
            f"# Define {capitalized} value objects here.\n",
        ),
        (
            base / "domain" / "ports" / "__init__.py",
            f'"""Domain ports for the {module} module."""\n',
        ),
        (
            base / "application" / "__init__.py",
            f'"""Application layer for the {module} module."""\n',
        ),
        (
            base / "application" / "ports" / "__init__.py",
            f'"""Application ports for the {module} module."""\n',
        ),
        (
            base / "application" / "services" / "__init__.py",
            f'"""Application services for the {module} module."""\n',
        ),
        (
            base / "infrastructure" / "__init__.py",
            f'"""Infrastructure layer for the {module} module."""\n',
        ),
        (
            base / "infrastructure" / "adapters" / "__init__.py",
            f'"""Infrastructure adapters for the {module} module."""\n',
        ),
        (
            base / "infrastructure" / "subscribers" / "__init__.py",
            f'"""Domain event subscribers for the {module} module."""\n',
        ),
    ]


def context_files(context: str) -> list[tuple[Path, str]]:
    base = Path("src") / context
    return [
        (
            base / "__init__.py",
            f'"""Bounded context package for {context}."""\n',
        ),
        (
            base / "shared" / "domain" / "__init__.py",
            f'"""Context-level shared domain code for {context}."""\n',
        ),
        (
            base / "shared" / "application" / "__init__.py",
            f'"""Context-level shared application code for {context}."""\n',
        ),
        (
            base / "shared" / "infrastructure" / "__init__.py",
            f'"""Context-level shared infrastructure code for {context}."""\n',
        ),
        (
            base / "persistence" / "__init__.py",
            f'"""Persistence package for the {context} bounded context."""\n',
        ),
        (
            base / "persistence" / "models.py",
            f'"""Persistence models for the {context} bounded context."""\n\n'
            "# Add ORM/document models shared by modules in this context.\n",
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold bounded-context module folders/files under src/<context>/ "
            "following docs/bounded-context-structure.md."
        )
    )
    parser.add_argument(
        "--context",
        required=True,
        help="Bounded context name (lowercase letters, digits, underscores).",
    )
    parser.add_argument(
        "--modules",
        nargs="+",
        required=True,
        help=(
            "Module names separated by spaces or commas "
            "(example: --modules intake validation routing)."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without writing files.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    context = safe_name(args.context, "context")
    raw_modules = parse_modules(args.modules)
    if not raw_modules:
        raise ValueError("At least one module must be provided.")
    modules = [safe_name(module, "module") for module in raw_modules]

    counter = ChangeCounter()
    planned: list[tuple[Path, str]] = []
    planned.extend(context_files(context))
    for module in modules:
        planned.extend(module_files(context, module))

    for path, content in planned:
        write_text_file(
            path,
            content,
            force=args.force,
            dry_run=args.dry_run,
            counter=counter,
        )

    if args.dry_run:
        print(f"\nPlanned {len(planned)} files. No filesystem changes were made.")
        return 0

    print(
        "\nDone. "
        f"Created: {counter.created}, Overwritten: {counter.overwritten}, "
        f"Skipped: {counter.skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
