# x

Project workspace repository, versioned with git and governed by a written rule set.

## Status

Initialized. Version `1.0.1`. No application stack has been selected yet
(see `OPEN-2` in `rules.md`).

## Repository layout

| Path | Purpose |
| ---------- | ---------------------------------------------------------------------------- |
| `rules.md` | Project rule set. Single source of truth for conventions and decisions. |
| `VERSION` | Single source of truth for the project version (`VER-3`). |
| `CHANGELOG.md` | Release history in Keep a Changelog format (`VER-6`, `VER-7`). |
| `.gitignore` | Ignored files and folders (`GIT-6`). |

## Version

The version is stored in the `VERSION` file and is bumped only after the user
decides the new number (`VER-2`, `VER-3`). Released versions are tagged in git
as `vX.Y.Z` and documented in `CHANGELOG.md` (`VER-6`).

Current version:

```sh
cat VERSION
```

## Getting started

No build tooling exists yet. Tooling, dependencies, and folder structure are
introduced only after the user approves the stack (`FLOW-3`, `CODE-6`).

## Contributing

Read `rules.md` before writing any code. All files, comments, commit messages,
and branch names are in English; conversation is in Turkish (`LANG-1`, `LANG-2`).
