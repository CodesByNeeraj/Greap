# Claude Code Agent / Codex Agent Guidelines

This file defines the coding standards, naming conventions, file organisation,
and contribution workflow for this project. Follow these guidelines for every change,whether you are a human contributor or an AI agent (Claude Code/Codex/Anything else).

## Code Quality

Write code that is easy to read before it is clever. If a piece of logic
requires a comment to explain what it does, consider rewriting it so the code
explains itself. Comments should explain why something is done, not what is
being done.

Keep functions small and focused. A function should do one thing and do it
well. If a function is growing long, it is doing too many things and should be
split up.

No file should contain a large block of unrelated logic. If a file is getting
long, that is a signal to separate concerns into smaller modules.

Avoid magic numbers and hardcoded strings. Define them as named constants at
the top of the file or in a dedicated constants file.

Write comments for every piece of code. The comments should explain why that code was written.

---

## Naming Conventions

**Files and directories:** use kebab-case.

**Functions:** use camelCase. Do not prefix functions with an underscore. There are no private functions in this codebase by naming convention.

**Classes:** use PascalCase.

**Variables:** use camelCase.

**Constants:** use UPPER_SNAKE_CASE.

File names and function names must convey their meaning immediately. A new
contributor reading the file tree or a function signature should understand
what it does without opening the file.

## File Organisation and Separation of Concerns

Each file & folder should have a single clear responsibility. 

If a file is growing beyond 200 lines, question whether it is doing too much
and split it.

---

## Python Coding Standards

Follow PEP 8 for all Python code. Use a formatter such as Black and a linter
such as Flake8. Do not hand-format code against these tools.

Use 4 spaces for indentation in Python files. Use 2 spaces for JSON and YAML.

Type hints are required for all function signatures.

```python
def extractData(frame: np.ndarray, threshold: float) -> str:
    ...
```
Do not use bare except clauses. Always catch specific exceptions.

```python
# wrong
try:
    loadConfig()
except:
    pass

# right
try:
    loadConfig()
except FileNotFoundError:
    createDefaultConfig()
```
---

## Commit Practices

Use conventional commits for every commit message. The format is:

```
type(scope): short description in imperative present tense
```

Types:

- `feat` for a new feature
- `fix` for a bug fix
- `refactor` for code changes that neither fix a bug nor add a feature
- `test` for adding or updating tests
- `docs` for documentation changes
- `chore` for maintenance tasks like dependency updates

Keep the subject line under 72 characters. Use the body of the commit to
explain why the change was made if it is not obvious from the subject.

Do not mix unrelated changes in a single commit. One commit should represent
one logical change.

Never commit gallery to repo unless mentioned by human. Never put co-authored by claude. Never mention your name (Claude).
---

## Branching and Pull Request Workflow

Never commit directly to `main`. Every change goes through a branch and a pull
request.

Name branches using the format `type/short-description`. Examples:

One feature or fix per branch. Do not bundle unrelated changes into the same
branch.

When opening a pull request:

- Write a clear title using the same conventional commit format
- Describe what the change does and why it was made
- Link any related issues

A pull request should be small enough to review in one sitting. If a pull
request is getting large, break it into smaller ones.

---