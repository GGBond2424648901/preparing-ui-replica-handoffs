# GitHub Public Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish `preparing-ui-replica-handoffs` as a complete public Codex Skill repository with a polished bilingual README, merged final source, downloadable `v1.0.0` artifact, and protected `main` branch.

**Architecture:** Keep the validated Skill and plugin source unchanged; improve only the public documentation and release surface, then promote the existing feature branch through PR #1. Perform local validation before mutation, publish the verified external ZIP as a GitHub Release asset, and apply branch protection only after the initial merge so the solo maintainer is not locked out.

**Tech Stack:** Markdown, Git, GitHub CLI (`gh`), GitHub REST API, Python `unittest`, PowerShell.

## Global Constraints

- Public repository: `GGBond2424648901/preparing-ui-replica-handoffs`.
- Default branch: `main`; source branch: `feat/preparing-ui-replica-handoffs`; pull request: `#1`.
- Release tag: `v1.0.0`; plugin version: `1.0.0+codex.20260806040539`.
- Release asset: `D:\AI_Demo\Result\preparing-ui-replica-handoffs-plugin.zip`.
- Expected SHA-256: `6D65D790ED4325AE916CA91E4A828217D17136F751EC6620BB96262BD9AAC96E`.
- Preserve `skill/preparing-ui-replica-handoffs.zip` as an unrelated untracked file; never add, modify, delete, or publish it.
- Do not invent a software license or claim that an un-enriched generated handoff skeleton is implementation-ready.
- The example images predate the final Skill; the README and release notes must say the current version is more complete and SoI models are expected to improve replica quality.
- Do not force-push or delete any branch.

---

### Task 1: Complete the public README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: repository directory structure, release tag `v1.0.0`, and the two tracked files under `examples/`.
- Produces: the public homepage documentation rendered from `main` and stable links to the release and source directories.

- [ ] **Step 1: Add a bilingual project summary and public quick start**

Add an English summary beneath the Chinese introduction. Add installation instructions for both the release ZIP and the source plugin directory, including the exact release URL:

```text
https://github.com/GGBond2424648901/preparing-ui-replica-handoffs/releases/tag/v1.0.0
```

- [ ] **Step 2: Clarify the generated package and readiness boundary**

Keep the existing output list, state that multimodal evidence enrichment plus validation is required before implementation, and explain that all page replicas belong to one router, one dev server, and one software system.

- [ ] **Step 3: Preserve and clarify the examples**

Retain these exact image links:

```markdown
![设计稿参考图](examples/reference-design.png)
![实际 UI 复刻图](examples/gpt5.6-luna-max-replica.png)
```

State that they are early, pre-improvement examples produced with GPT-5.6 Luna Max and that the current Skill plus SoI models is expected to perform better.

- [ ] **Step 4: Verify README links and scope**

Run:

```powershell
Test-Path README.md
Test-Path examples/reference-design.png
Test-Path examples/gpt5.6-luna-max-replica.png
Select-String -Path README.md -Pattern 'v1.0.0','examples/reference-design.png','examples/gpt5.6-luna-max-replica.png','SoI'
git diff --check
git status --short
```

Expected: all paths are `True`, all required strings are found, `git diff --check` is empty, and the only unrelated untracked file is `skill/preparing-ui-replica-handoffs.zip`.

- [ ] **Step 5: Commit and push the README and plan**

```powershell
git add -- README.md docs/superpowers/plans/2026-08-06-github-public-release.md
git diff --cached --check
git commit -m "docs: complete public release guide"
git push origin feat/preparing-ui-replica-handoffs
```

Expected: the commit is pushed to the existing PR branch and the unrelated ZIP remains untracked.

### Task 2: Run the final pre-merge verification

**Files:**
- Test: `tests/test_bilingual_parity.py`
- Test: `tests/test_contact_sheet.py`
- Test: `tests/test_contract_assets.py`
- Test: `tests/test_evidence_graph_contracts.py`
- Test: `tests/test_plugin_package.py`
- Test: `tests/test_prepare_handoff.py`
- Test: `tests/test_skill_content.py`
- Test: `tests/test_skill_scaffold.py`
- Test: `tests/test_validate_handoff.py`

**Interfaces:**
- Consumes: the complete feature-branch repository and external release ZIP.
- Produces: fresh proof that source, plugin package, bilingual contracts, and release artifact are ready to publish.

- [ ] **Step 1: Run the full test suite without writing bytecode**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest discover -s tests -v
```

Expected: `Ran 192 tests` and `OK`.

- [ ] **Step 2: Verify the release artifact hash and plugin manifest**

```powershell
Get-FileHash 'D:\AI_Demo\Result\preparing-ui-replica-handoffs-plugin.zip' -Algorithm SHA256
Get-Content -Raw -Encoding UTF8 'plugin\preparing-ui-replica-handoffs\.codex-plugin\plugin.json'
```

Expected: SHA-256 equals `6D65D790ED4325AE916CA91E4A828217D17136F751EC6620BB96262BD9AAC96E`, and the manifest identifies the published plugin.

- [ ] **Step 3: Verify Git scope and PR mergeability**

```powershell
git status --short
git log -1 --oneline
gh pr view 1 --repo GGBond2424648901/preparing-ui-replica-handoffs --json isDraft,state,mergeable,headRefName,baseRefName,url
```

Expected: only the unrelated ZIP is untracked; PR #1 is open from `feat/preparing-ui-replica-handoffs` to `main` and is mergeable or reports `UNKNOWN` only while GitHub recalculates.

### Task 3: Promote PR #1 to the public main branch

**Files:**
- Modify remotely: GitHub pull request `#1`
- Modify remotely: branch `main`
- Update locally: Git ref `main`

**Interfaces:**
- Consumes: the pushed and freshly verified feature branch.
- Produces: non-draft merged PR #1 and a synchronized local `main` ref.

- [ ] **Step 1: Mark the pull request ready for review**

```powershell
gh pr ready 1 --repo GGBond2424648901/preparing-ui-replica-handoffs
```

Expected: PR #1 is no longer a draft.

- [ ] **Step 2: Merge with a merge commit and preserve branches**

```powershell
gh pr merge 1 --repo GGBond2424648901/preparing-ui-replica-handoffs --merge
```

Expected: PR #1 becomes `MERGED`; neither local nor remote feature branch is deleted.

- [ ] **Step 3: Synchronize the local main ref without switching worktrees**

```powershell
git fetch origin
git branch -f main origin/main
```

Expected: local `main` points to the merged `origin/main`; the working tree stays on the feature branch and the unrelated ZIP is untouched.

- [ ] **Step 4: Verify the merged public files**

```powershell
gh pr view 1 --repo GGBond2424648901/preparing-ui-replica-handoffs --json isDraft,state,mergedAt,mergeCommit,url
gh api repos/GGBond2424648901/preparing-ui-replica-handoffs/contents/README.md -f ref=main --jq '.html_url'
gh api repos/GGBond2424648901/preparing-ui-replica-handoffs/contents/examples/reference-design.png -f ref=main --jq '.html_url'
gh api repos/GGBond2424648901/preparing-ui-replica-handoffs/contents/examples/gpt5.6-luna-max-replica.png -f ref=main --jq '.html_url'
```

Expected: PR state is `MERGED`, `isDraft` is `false`, and all three content requests return GitHub URLs.

### Task 4: Publish v1.0.0 and protect main

**Files:**
- Create remotely: GitHub release `v1.0.0`
- Upload remotely: `preparing-ui-replica-handoffs-plugin.zip`
- Modify remotely: `main` branch protection

**Interfaces:**
- Consumes: merged `main`, verified ZIP, expected SHA-256, and release notes.
- Produces: downloadable public release and protected default branch.

- [ ] **Step 1: Confirm the release tag does not already exist**

```powershell
gh release view v1.0.0 --repo GGBond2424648901/preparing-ui-replica-handoffs
```

Expected: command reports that the release does not exist. If it exists, inspect it and do not overwrite it blindly.

- [ ] **Step 2: Create the public release with the verified ZIP**

```powershell
gh release create v1.0.0 'D:\AI_Demo\Result\preparing-ui-replica-handoffs-plugin.zip#preparing-ui-replica-handoffs-plugin.zip' --repo GGBond2424648901/preparing-ui-replica-handoffs --target main --title 'preparing-ui-replica-handoffs v1.0.0' --notes 'First complete public release of the bilingual, evidence-driven Codex Skill for preparing high-fidelity UI replica handoffs from design images. Includes the Codex plugin package, multi-board design-language authority, navigation reconciliation, page/state/component/motion/micro-visual contracts, and Diff acceptance contracts. The README examples were produced before the current improvements with GPT-5.6 Luna Max; the current Skill is more complete, and SoI models are expected to improve results. SHA-256: 6D65D790ED4325AE916CA91E4A828217D17136F751EC6620BB96262BD9AAC96E'
```

Expected: release `v1.0.0` is published from merged `main` with one ZIP asset.

- [ ] **Step 3: Apply solo-maintainer-safe branch protection**

Send this exact JSON to `PUT /repos/GGBond2424648901/preparing-ui-replica-handoffs/branches/main/protection`:

```json
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": false,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 0,
    "require_last_push_approval": false
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false,
  "allow_fork_syncing": true
}
```

Expected: future changes require a pull request and resolved conversations; admins are included; force pushes and deletion are disabled; no approval or status check blocks the solo maintainer.

- [ ] **Step 4: Verify the final public state**

```powershell
gh repo view GGBond2424648901/preparing-ui-replica-handoffs --json url,isPrivate,defaultBranchRef
gh release view v1.0.0 --repo GGBond2424648901/preparing-ui-replica-handoffs --json url,tagName,isDraft,isPrerelease,targetCommitish,assets
gh api repos/GGBond2424648901/preparing-ui-replica-handoffs/branches/main/protection
git status --short
```

Expected: repository is public with default `main`; release is public, final, targets `main`, and includes the ZIP; protection matches the policy; only `skill/preparing-ui-replica-handoffs.zip` remains untracked.

