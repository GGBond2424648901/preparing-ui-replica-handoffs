# Preparing UI Replica Handoffs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, validate, install, and package an independent bilingual Codex Skill that converts UI design images into deterministic, evidence-bounded handoff packages for high-fidelity implementation agents.

**Architecture:** Keep the repository wrapper separate from the distributable skill at `skill/preparing-ui-replica-handoffs/`. The skill combines concise bilingual operating instructions, mirrored Chinese/English references, schemas and templates, and four deterministic Python utilities. The utilities create only an initial evidence skeleton; visual interpretation and enrichment remain an explicit Agent workflow with unknowns recorded as gaps.

**Tech Stack:** Python 3.10+, Python standard library, Pillow, JSON, CSV, Markdown, `unittest`, Git, Codex Skill metadata.

## Global constraints

- The skill is self-contained and must not call, reference as a prerequisite, or require `design-image-to-web-replica`.
- Original design directories are read-only. Generated assets are byte-for-byte copies whose hashes are verified.
- Human-readable output is Chinese and English. Machine contracts use one stable English-keyed representation with localized display values where needed.
- Unknown content, states, routes, interactions, components, assets, and responsive behavior remain `unknown`, `candidate`, or `proposed` and must be linked to a gap record.
- Original-canvas geometry is the baseline. Narrow viewports preserve geometry with horizontal scrolling unless a responsive variant is directly evidenced or approved.
- All links and stored paths in the handoff are relative to the handoff root. Absolute-path leakage is a validation failure.
- Validation fails closed for source drift, hash mismatch, duplicate identities, missing bilingual coverage, unresolved blocker/major gaps, or out-of-scope staged Git files.
- The scripts never initialize repositories, create worktrees, stage, commit, push, or modify user Git state.

---

## Task 1: Scaffold the repository-owned skill

**Files:**

- Create: `skill/preparing-ui-replica-handoffs/SKILL.md`
- Create: `skill/preparing-ui-replica-handoffs/agents/openai.yaml`
- Create: `skill/preparing-ui-replica-handoffs/scripts/`
- Create: `skill/preparing-ui-replica-handoffs/references/{zh,en}/`
- Create: `skill/preparing-ui-replica-handoffs/assets/{schemas,templates}/`
- Create: `tests/`

- [ ] Run the official `skill-creator/scripts/init_skill.py` with the exact skill name `preparing-ui-replica-handoffs` and resources `scripts,references,assets`.
- [ ] Set bilingual UI metadata and ensure `default_prompt` explicitly invokes `$preparing-ui-replica-handoffs`.
- [ ] Remove only generated placeholder/example files that are not part of the approved structure.
- [ ] Add a structural test asserting the exact required directories, `SKILL.md` frontmatter keys, and agent metadata fields.
- [ ] Run the structural test and confirm it fails before replacing scaffold placeholders.
- [ ] Make the minimum metadata edits and confirm the test passes.
- [ ] Commit as `chore: scaffold bilingual UI handoff skill`.

## Task 2: Define the machine contract schemas and bilingual templates

**Files:**

- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/handoff-config.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/asset-manifest.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/page-inventory.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/ui-style-contract.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/component-registry.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/implementation-map.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/capture-profile.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/diff-regions.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/schemas/design-lock.schema.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/templates/handoff-config.template.json`
- Create: `skill/preparing-ui-replica-handoffs/assets/templates/{requirement-ledger,gap-register,visual-qa-matrix}.template.csv`
- Create: paired Markdown templates under `skill/preparing-ui-replica-handoffs/assets/templates/docs/{zh,en}/`
- Create: `tests/test_contract_assets.py`

- [ ] Write failing tests for valid JSON, required stable keys, allowed evidence/status enums, paired bilingual template IDs, and forbidden absolute path examples.
- [ ] Run `python -m unittest tests.test_contract_assets -v` and confirm failure.
- [ ] Implement the smallest complete schemas and templates covering assets, page/state/variant identity, shell/regions, layout relationships, copy, icons, components, data classification, interactions, responsive variants, capture environment, diff regions, QA, Git scope, and gaps.
- [ ] Re-run the test and confirm it passes.
- [ ] Commit as `feat: define UI handoff contracts and templates`.

## Task 3: Implement source scanning and deterministic handoff preparation with TDD

**Files:**

- Create: `skill/preparing-ui-replica-handoffs/scripts/prepare_handoff.py`
- Create: `tests/test_prepare_handoff.py`

**Required interfaces:**

```python
def collect_images(source_root: Path) -> list[dict]: ...
def sha256_file(path: Path) -> str: ...
def prepare_handoff(
    source_root: Path,
    output_root: Path,
    design_version: str,
    languages: tuple[str, ...] = ("zh-CN", "en-US"),
    dry_run: bool = False,
    force: bool = False,
) -> dict: ...
```

- [ ] Write tests that generate tiny PNG/JPEG fixtures and assert deterministic ordering, dimensions, SHA-256, duplicate grouping, source-set hash, stable `P###-S##-V##` identities, normalized English copy names, and dry-run behavior.
- [ ] Add failure tests for a missing source, no supported images, corrupt images, output nested under source, collision with unmanaged output, and source mutation during processing.
- [ ] Run `python -m unittest tests.test_prepare_handoff -v` and confirm failure.
- [ ] Implement read-only scanning and byte-copy generation. Use `unclassified` when semantics are not known; never infer a page name from visual content in the utility.
- [ ] Generate the complete standard handoff tree, initial bilingual documents, machine contracts, requirement/gap ledgers, and validation command.
- [ ] Recompute source and copy hashes after write; fail before producing a design lock if they differ.
- [ ] Re-run tests and confirm they pass.
- [ ] Commit as `feat: generate deterministic bilingual handoff skeletons`.

## Task 4: Implement bilingual parity validation with TDD

**Files:**

- Create: `skill/preparing-ui-replica-handoffs/scripts/check_bilingual_parity.py`
- Create: `tests/test_bilingual_parity.py`

**Required interface:**

```python
def check_bilingual_parity(root: Path) -> dict: ...
```

- [ ] Write failing tests for a valid pair and for missing mirrored files, mismatched rule/section IDs, mismatched placeholders, missing page documents, and one-sided image references.
- [ ] Run `python -m unittest tests.test_bilingual_parity -v` and confirm failure.
- [ ] Implement parity checking without requiring literal translation equality.
- [ ] Emit stable issue codes and non-zero CLI exit status on failure.
- [ ] Re-run tests and confirm they pass.
- [ ] Commit as `feat: enforce Chinese English handoff parity`.

## Task 5: Implement contact sheets and fail-closed package validation with TDD

**Files:**

- Create: `skill/preparing-ui-replica-handoffs/scripts/build_contact_sheet.py`
- Create: `skill/preparing-ui-replica-handoffs/scripts/validate_handoff.py`
- Create: `tests/test_contact_sheet.py`
- Create: `tests/test_validate_handoff.py`

**Required interfaces:**

```python
def build_contact_sheet(handoff_root: Path, output_path: Path) -> dict: ...
def validate_handoff(
    handoff_root: Path,
    source_root: Path | None = None,
    repo_root: Path | None = None,
    allowed_git_prefix: str | None = None,
) -> dict: ...
```

- [ ] Write failing tests for contact-sheet creation from the asset manifest, stable labels, and no source writes.
- [ ] Write failing validation tests for missing files, malformed JSON/CSV, source/copy hash drift, duplicate target identity, absolute paths, broken relative links, missing page docs, unknown state without gap ID, bilingual mismatch, incomplete capture profile, missing diff/QA coverage, blocker/major gaps, and a staged file outside an optional Git allowlist.
- [ ] Run both test modules and confirm failure.
- [ ] Implement the contact sheet using Pillow and package-relative manifest paths.
- [ ] Implement validation with stable error/warning codes, computed design-lock material, JSON reporting, and non-zero CLI exit status on errors.
- [ ] Treat absence of a Git repository as `skipped`, never as permission to initialize one.
- [ ] Re-run tests and confirm they pass.
- [ ] Commit as `feat: validate and visually index UI handoff packages`.

## Task 6: Write the bilingual operating skill and mirrored references

**Files:**

- Modify: `skill/preparing-ui-replica-handoffs/SKILL.md`
- Create: `skill/preparing-ui-replica-handoffs/references/zh/intake-and-authority.md`
- Create: `skill/preparing-ui-replica-handoffs/references/en/intake-and-authority.md`
- Create: paired `{page-and-state-contract,component-and-style-contract,visual-qa-and-git-safety,delivery-package-spec}.md`
- Create: `tests/test_skill_content.py`

- [ ] Write failing content tests for the independent-skill statement, original-source immutability, authority order, evidence levels, inferred-copy policy, sample-data policy, original-width/scroll behavior, unknown-state handling, visual/structural/interaction QA, fail-closed completion, bilingual output, relative paths, Git safety, and required reference routing.
- [ ] Run `python -m unittest tests.test_skill_content -v` and confirm failure.
- [ ] Replace the scaffold SKILL body with a concise bilingual workflow and decision tree. Keep detailed material in the mirrored references.
- [ ] Give every mirrored section and rule a stable ID, and ensure both languages describe equivalent requirements.
- [ ] Explicitly prohibit dependency on the existing UI-replica skill while allowing ordinary image, document, browser, and filesystem tools when available.
- [ ] Run content and parity tests and confirm they pass.
- [ ] Commit as `docs: complete bilingual UI handoff operating guide`.

## Task 7: Validate the distributable skill and forward-test agent behavior

**Files:**

- Create: `tests/fixtures/` only for minimal synthetic fixtures
- Modify tests or skill files only when a forward test exposes a specification gap

- [ ] Run the complete `unittest` suite.
- [ ] Run `skill-creator/scripts/quick_validate.py` against `skill/preparing-ui-replica-handoffs`.
- [ ] Run `check_bilingual_parity.py` against both the skill references/templates and a generated handoff.
- [ ] Ask fresh agents to solve the same preparation scenario with the new skill loaded; verify the outputs converge on the standard tree, preserve unknowns, avoid invented breakpoints/worktrees, and remain self-contained.
- [ ] Apply only evidence-backed refinements and re-run the entire suite.
- [ ] Commit as `test: verify bilingual skill behavior and structure`.

## Task 8: Run a real read-only forward test, install, and package

**Files:**

- Create outside the repo: a temporary generated handoff under a safe test directory
- Install: `C:/Users/PC/.codex/skills/preparing-ui-replica-handoffs/`
- Package: `D:/AI_Demo/Result/preparing-ui-replica-handoffs.zip`

- [ ] Resolve the real 16-image design source and compute pre-run hashes for source images and the existing handoff package.
- [ ] Generate a fresh handoff in a temporary output directory; do not modify the current production handoff.
- [ ] Run preparation, contact-sheet generation, bilingual parity checking, and full validation.
- [ ] Confirm expected unresolved gaps are reported and that no script falsely declares an implementation-complete handoff.
- [ ] Recompute hashes and prove the original design images and existing handoff are unchanged.
- [ ] Copy the validated skill directory to the personal skill install location, preserving only distributable files.
- [ ] Create the ZIP from the installed content and compare file lists and SHA-256 values.
- [ ] Run `quick_validate.py` on both repository and installed copies.
- [ ] Run `git status --short`, inspect the diff, and commit only repository-owned implementation files as `feat: deliver preparing UI replica handoffs skill` if any remain.

## Final acceptance commands

```powershell
python -m unittest discover -s tests -v
python C:\Users\PC\.codex\skills\.system\skill-creator\scripts\quick_validate.py skill\preparing-ui-replica-handoffs
python skill\preparing-ui-replica-handoffs\scripts\check_bilingual_parity.py --skill-root skill\preparing-ui-replica-handoffs
git status --short --branch
```

## Task 9: Convert the verified skill into a personal Codex plugin

**Files:**

- Create: `plugin/preparing-ui-replica-handoffs/.codex-plugin/plugin.json`
- Create: `plugin/preparing-ui-replica-handoffs/skills/preparing-ui-replica-handoffs/`
- Create: `tests/test_plugin_package.py`
- Install: `C:/Users/PC/plugins/preparing-ui-replica-handoffs/`
- Update through official scaffold flow: `C:/Users/PC/.agents/plugins/marketplace.json`
- Package: `D:/AI_Demo/Result/preparing-ui-replica-handoffs-plugin.zip`

- [ ] Write failing tests for plugin manifest identity, semver, bilingual metadata, `skills: "./skills/"`, absence of undeclared MCP/App/Hook fields, and byte parity between repository Skill and plugin-contained Skill.
- [ ] Scaffold with the official `plugin-creator/scripts/create_basic_plugin.py` using `--with-skills --with-marketplace`; do not hand-edit marketplace JSON.
- [ ] Replace only the generated placeholder skill directory with the verified repository Skill.
- [ ] Validate the plugin and its contained Skill using the official validators in UTF-8 mode.
- [ ] Install/reinstall with `codex plugin add preparing-ui-replica-handoffs@personal` and verify with `codex plugin list`.
- [ ] Build the ZIP from the installed plugin and compare every relative file path and SHA-256 with the repository plugin package.
- [ ] Confirm the existing `design-image-to-web-replica` marketplace entry and source remain unchanged.

The task is complete only when all commands pass, the real read-only forward test leaves source hashes unchanged, the plugin is discoverable through the personal marketplace, and the ZIP content matches the installed plugin.
