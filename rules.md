# Project Rules

Single source of truth for how this project is written, versioned, and maintained.

- Every rule is mandatory unless it is explicitly marked as a suggestion.
- Rules carry stable IDs (for example `VER-2`) so they can be referenced in commits,
  reviews, and task descriptions.
- Changing a rule requires the user's explicit approval (see `META-2`).

## Table of Contents

1. [Language Policy](#1-language-policy)
2. [Versioning](#2-versioning)
3. [Git & Commit Rules](#3-git--commit-rules)
4. [Modularity & File Size](#4-modularity--file-size)
5. [Coding Conventions](#5-coding-conventions)
6. [Agent Workflow](#6-agent-workflow)
7. [Rule Changes](#7-rule-changes)
8. [Open Decisions](#8-open-decisions)

---

## 1. Language Policy

| ID | Rule |
| ------ | -------------------------------------------------------------------------------------------------------------- |
| LANG-1 | All conversation with the user is in Turkish. |
| LANG-2 | Every file in the repository is written in English: source code, identifiers, comments, docstrings, documentation, commit messages, branch names, test names, fixtures, config keys, and log output. |
| LANG-3 | Turkish-specific letters (Unicode `U+00E7`, `U+011F`, `U+0131`, `U+0130`, `U+00F6`, `U+015F`, `U+00FC`) must never appear in file names, folder names, identifiers, or file contents. This file itself stays pure ASCII so the check can be automated. |
| LANG-4 | User-facing text is never hardcoded in source files. It lives in dedicated localization resources with English as the default locale. |
| LANG-5 | Third-party, vendored, or generated files keep their upstream language. They are exempt from `LANG-2` but are never translated. |
| LANG-6 | When a Turkish term has no exact English equivalent, pick one short English term and record it in `docs/glossary.md`. |
| LANG-7 | Text that is only meant for the user (task summaries, explanations in chat, review notes) is Turkish and stays outside the repository. |

## 2. Versioning

| ID | Rule |
| ------ | -------------------------------------------------------------------------------------------------------------- |
| VER-1 | The project follows Semantic Versioning: `MAJOR.MINOR.PATCH`, for example `1.2.2`. |
| VER-2 | The version number is the user's decision. The agent never bumps, invents, or assumes a version; it proposes candidate numbers and waits for confirmation. |
| VER-3 | The version has exactly one source of truth, stored in the `VERSION` file at the repository root. Any manifest that also carries a version must be synchronized by the release script, never edited by hand. |
| VER-4 | Bump mapping used for proposals: `MAJOR` for breaking changes, `MINOR` for backward-compatible features, `PATCH` for backward-compatible fixes. |
| VER-5 | While a release is in progress the version may carry a suffix such as `1.3.0-dev.2`. A version without a suffix always means "released". |
| VER-6 | Every released version gets an entry in `CHANGELOG.md` (Keep a Changelog format) and an annotated git tag named `vX.Y.Z`. |
| VER-7 | `CHANGELOG.md` lists changes under `Added`, `Changed`, `Fixed`, `Removed`, all in English and phrased from the user's point of view. |
| VER-8 | The version must be visible at runtime once an application entry point exists, and print the same value as the `VERSION` file. |

## 3. Git & Commit Rules

| ID | Rule |
| ------ | -------------------------------------------------------------------------------------------------------------- |
| GIT-1 | The project is always version-controlled. Work on an untracked project starts by running `git init` before any file is written. |
| GIT-2 | Commit messages follow Conventional Commits: `<type>(<scope>): <summary>`, where `<type>` is one of `feat`, `fix`, `docs`, `refactor`, `test`, `build`, `ci`, `chore`, `perf`, `style`, `revert`. |
| GIT-3 | A commit message is English, imperative mood, no emoji, no trailing period, first line at most 72 characters. The body (optional) is wrapped at 72 characters and explains *why*, not *what*. |
| GIT-4 | One commit carries one logical change. Unrelated edits are never bundled into the same commit. |
| GIT-5 | Branch naming: `feature/<slug>`, `fix/<slug>`, `chore/<slug>`, `docs/<slug>`, `release/<version>`. Slugs are lowercase English with hyphens. |
| GIT-6 | Secrets, tokens, credentials, local environment files, build output, dependency folders, and editor state are never committed; they are covered by `.gitignore`. |
| GIT-7 | Published history is never rewritten (no `push --force` on shared branches, no `commit --amend` on pushed commits) without explicit user approval. |
| GIT-8 | `README.md`, `CHANGELOG.md`, `VERSION`, and `.gitignore` are created during project initialization, together with the first commit `chore: initialize project`. |
| GIT-9 | Before finishing any task the agent reports `git status`-level facts: which files changed and a proposed commit message. It creates the commit only when the user asks for it. |
| GIT-10 | Large binaries, generated assets, and datasets stay out of git; they are referenced through a script or a download step documented in `README.md`. |

## 4. Modularity & File Size

| ID | Rule |
| ------ | -------------------------------------------------------------------------------------------------------------- |
| MOD-1 | The codebase is modular: every module has one responsibility, a narrow public interface, and no hidden side effects. |
| MOD-2 | File size limits: soft limit **200 lines**, hard limit **300 lines** per source file. Hitting the soft limit triggers a split *in the same change*, unless the user accepts a documented exception. |
| MOD-3 | Split files by responsibility, not by line count: extract helpers, types, constants, fixtures, or sub-modules into their own files. |
| MOD-4 | Prefer many small files over few large ones. One exported component, class, or service per file; a barrel `index` file only re-exports. |
| MOD-5 | Function limits: at most **40 lines** and **4 parameters**; deeper nesting than 3 levels is refactored. |
| MOD-6 | Dependency direction is one-way: shared/core code never imports from feature, UI, or adapter layers. Circular imports are forbidden. |
| MOD-7 | Constants, types, schemas, and configuration live in their own files, never at the top of a large module. |
| MOD-8 | Folder layout mirrors responsibilities, for example `src/core`, `src/features/<name>`, `src/shared`, `docs`, `scripts`, `tests`. New top-level folders require user approval. |
| MOD-9 | Tests mirror the source tree (`tests/<path-of-module>`), one test file per module, so a module and its test stay small together. |

## 5. Coding Conventions

| ID | Rule |
| ------ | -------------------------------------------------------------------------------------------------------------- |
| CODE-1 | Names are descriptive English words. Abbreviations are only allowed for universally known ones (`id`, `url`, `api`, `http`). |
| CODE-2 | The repository linter and formatter are authoritative. Inline rule disabling is allowed only with a comment explaining the reason. |
| CODE-3 | Errors are handled explicitly. Silent catches, empty catch blocks, and leftover debug printing are forbidden. |
| CODE-4 | No commented-out code. A `TODO` must include an owner and a tracked issue reference. |
| CODE-5 | Public modules document their interface; internal helpers stay private. |
| CODE-6 | Dependencies are added only with user approval, one dependency per purpose, and are recorded together with the reason in the pull request or commit body. |
| CODE-7 | Configuration is read from one place, never duplicated across modules. |
| CODE-8 | The code must be readable without the original author: no magic numbers, no implicit behavior, no clever one-liners that need explanation. |

## 6. Agent Workflow

| ID | Rule |
| ------ | -------------------------------------------------------------------------------------------------------------- |
| FLOW-1 | Read the relevant code and this `rules.md` before editing. Follow existing patterns instead of inventing new ones. |
| FLOW-2 | Present a short plan before any multi-file change, and keep it updated if the approach changes. |
| FLOW-3 | Never change folder structure, build tooling, or dependencies without user approval. |
| FLOW-4 | Validate the work: run the available linter, type checks, and tests. Report failures and skipped checks honestly. |
| FLOW-5 | Deliver complete, working code. Placeholders, stubs, and "fill in later" comments are not acceptable. |
| FLOW-6 | Ask when a requirement is ambiguous; never fill the gap with an assumption. |
| FLOW-7 | Close every task with a Turkish summary: what changed, which files, which rules were exercised, and the proposed next version. |
| FLOW-8 | Never delete user work, rewrite files outside the scope of the task, or perform destructive git operations without approval. |
| FLOW-9 | Keep generated artifacts, temporary scripts, and scratch files out of the repository. |
| FLOW-10 | Adding a data type is one change that also updates its inventory: the registry in `src/shared/config.py`, `docs/data.md` plus the matching guide (`docs/cot.md`, `docs/macro.md`, `docs/web.md`), `README.md`, and a fresh `python data_report.py` run. The dashboard and the report must show the new type without further code changes, and the tests that compare the guides with the registry must pass. |

## 7. Rule Changes

| ID | Rule |
| ------ | -------------------------------------------------------------------------------------------------------------- |
| META-1 | This file is the single source of truth. When a rule conflicts with a habit, this file wins. |
| META-2 | Adding, removing, or relaxing a rule requires explicit user approval and a `docs:` commit that updates this file. |
| META-3 | Rule IDs are stable. A retired rule is marked `Deprecated` instead of being renumbered, so older references stay resolvable. |
| META-4 | Decisions that extend this file are recorded under `Open Decisions` until the user resolves them, then folded into the relevant section. |

## 8. Open Decisions

Items below are intentionally unanswered and require the user's decision.
Resolved items keep their ID for reference (`META-3`).

| ID | Question | Impact |
| ------ | -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| OPEN-1 | **Resolved by the user:** the project starts at version `1.0.1`. | `VER-1`, `VER-3` |
| OPEN-2 | **Resolved by the user:** Python 3 with the standard library only; no package manager and no third-party dependency. | `MOD-8`, `CODE-6` |
| OPEN-3 | Is Turkish user-facing text required? If yes, the `tr` locale file becomes the only place where Turkish is permitted. | `LANG-4` |
| OPEN-4 | Should releases be automated by a `scripts/release` step that bumps `VERSION`, updates `CHANGELOG.md`, and tags the commit? | `VER-3`, `VER-5`, `VER-6` |
| OPEN-5 | Which license applies to the project? | `GIT-8` |

---

## Quick Checklist

Use this list before reporting any task as finished.

- [ ] All files, comments, commits, and names are in English with no Turkish characters (`LANG-2`, `LANG-3`).
- [ ] No new or changed file exceeds 200 lines, or the split is explained (`MOD-2`).
- [ ] Each changed file still has one responsibility (`MOD-1`, `MOD-3`).
- [ ] `VERSION` file and `CHANGELOG.md` are consistent with the changes (`VER-3`, `VER-6`).
- [ ] The proposed version bump was confirmed by the user (`VER-2`).
- [ ] Linter, type checks, and tests passed, or the gap is reported (`FLOW-4`).
- [ ] A new data type is registered, documented, and present in a fresh `python data_report.py` run (`FLOW-10`).
- [ ] The change is a single logical unit with a Conventional Commit message (`GIT-2`, `GIT-4`).

