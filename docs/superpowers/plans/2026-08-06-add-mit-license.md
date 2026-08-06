# Add MIT License Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** License the public repository under the standard MIT License and make that status explicit in the README and on GitHub.

**Architecture:** Add one authoritative root-level `LICENSE` file and link to it from the README. Keep all Skill/plugin implementation files and release artifacts unchanged, then publish through a dedicated PR because `main` is protected.

**Tech Stack:** Markdown/plain text, Git, GitHub CLI (`gh`), Python `unittest`.

## Global Constraints

- License identifier: `MIT`.
- Copyright notice: `Copyright (c) 2026 GGBond`.
- License wording must match the Open Source Initiative MIT text apart from filling the copyright line.
- Modify only `LICENSE`, `README.md`, this plan, and the already committed design specification.
- Do not add SPDX headers, a `NOTICE` file, or nested license copies.
- Preserve `skill/preparing-ui-replica-handoffs.zip` as an unrelated untracked file.
- Do not modify the Skill/plugin source, tests, examples, existing release asset, or tag `v1.0.0`.
- Publish through `agent/add-mit-license` and a ready-for-review PR against protected `main`; never force-push.

---

### Task 1: Add the MIT license and README declaration

**Files:**
- Create: `LICENSE`
- Modify: `README.md`
- Create: `docs/superpowers/plans/2026-08-06-add-mit-license.md`
- Preserve: `docs/superpowers/specs/2026-08-06-mit-license-design.md`

**Interfaces:**
- Consumes: standard OSI MIT wording and the approved copyright holder.
- Produces: GitHub-detectable root license metadata and a human-readable README link.

- [ ] **Step 1: Create the root LICENSE**

Create `LICENSE` with this exact text:

```text
MIT License

Copyright (c) 2026 GGBond

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Replace the README no-license warning**

Replace:

```markdown
本仓库暂未附带开源许可证；在许可证明确前，请不要默认获得复制、修改或再分发授权。
```

with:

```markdown
## 开源许可证 / License

本项目采用 [MIT License](LICENSE) 开源。允许使用、复制、修改和再分发，但必须保留原始版权与许可声明。

This project is licensed under the [MIT License](LICENSE).
```

- [ ] **Step 3: Verify the files and intended diff**

Run:

```powershell
Test-Path LICENSE
Select-String -Path LICENSE -Pattern '^MIT License$','^Copyright \(c\) 2026 GGBond$','Permission is hereby granted','THE SOFTWARE IS PROVIDED "AS IS"'
Select-String -Path README.md -Pattern 'MIT License','LICENSE'
git diff --check
git status --short
git diff --stat main...HEAD
git diff --stat
```

Expected: the root license exists and contains all standard clauses; README links to it; no whitespace errors exist; the unrelated ZIP remains untracked; only the approved documentation files are in scope.

- [ ] **Step 4: Run the full test suite**

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest discover -s tests -v
```

Expected: `Ran 192 tests` and `OK`.

- [ ] **Step 5: Commit only the licensing files**

```powershell
git add -- LICENSE README.md docs/superpowers/plans/2026-08-06-add-mit-license.md
git diff --cached --check
git commit -m "docs: add MIT license"
```

Expected: the implementation commit contains exactly `LICENSE`, `README.md`, and the plan; the prior design-spec commit remains in branch history.

### Task 2: Publish and verify the license on GitHub

**Files:**
- Push: branch `agent/add-mit-license`
- Create remotely: ready-for-review PR against `main`
- Modify remotely: protected branch `main` through PR merge

**Interfaces:**
- Consumes: verified licensing commit from Task 1.
- Produces: merged MIT-licensed public repository recognized by GitHub.

- [ ] **Step 1: Push the dedicated branch**

```powershell
git push -u origin agent/add-mit-license
```

Expected: the remote branch contains the design and implementation commits.

- [ ] **Step 2: Open a ready-for-review PR**

Create a PR titled `docs: add MIT license` with a body that states:

```markdown
## Summary

- add the standard MIT License at the repository root
- set the copyright holder to GGBond for 2026
- replace the README no-license warning with a linked bilingual license section

## Validation

- 192/192 tests pass
- license wording and README link verified
- Skill/plugin source and release artifacts unchanged
```

Expected: PR targets `main`, uses head `agent/add-mit-license`, and is not a draft.

- [ ] **Step 3: Merge through branch protection**

```powershell
gh pr merge <PR_NUMBER> --repo GGBond2424648901/preparing-ui-replica-handoffs --merge
```

Expected: PR state becomes `MERGED`; no branch is deleted.

- [ ] **Step 4: Synchronize local main and verify GitHub recognition**

```powershell
git fetch --no-tags origin main
git branch -f main origin/main
gh repo view GGBond2424648901/preparing-ui-replica-handoffs --json licenseInfo,defaultBranchRef,url
gh api --method GET repos/GGBond2424648901/preparing-ui-replica-handoffs/contents/LICENSE -f ref=main --jq '.html_url'
gh api --method GET repos/GGBond2424648901/preparing-ui-replica-handoffs/contents/README.md -f ref=main --jq '.html_url'
git status --short
```

Expected: GitHub reports `licenseInfo.spdxId` as `MIT`, both files exist on `main`, local `main` matches `origin/main`, and only `skill/preparing-ui-replica-handoffs.zip` remains untracked.
