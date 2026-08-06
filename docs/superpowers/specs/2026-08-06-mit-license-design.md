# MIT License Design

## Goal

Publish the repository under the standard MIT License so users have explicit permission to use, copy, modify, merge, publish, distribute, sublicense, and sell copies while preserving the required copyright and license notice.

## Authority and Copyright

- License identifier: `MIT`.
- License text authority: Open Source Initiative, `https://opensource.org/license/mit`.
- Copyright notice: `Copyright (c) 2026 GGBond`.
- The standard MIT warranty disclaimer remains unchanged.

## Repository Changes

1. Add a root-level `LICENSE` containing the standard MIT License text with the approved year and copyright holder.
2. Replace the final README warning that no license exists with a clear statement linking to `LICENSE`.
3. Do not add per-file SPDX headers, a `NOTICE` file, or duplicate license files inside the Skill and plugin trees.
4. Do not modify the validated Skill/plugin source, generated release ZIP, examples, tests, or existing `v1.0.0` release artifact.

## Publication Flow

1. Work on `agent/add-mit-license`, forked from the merged `main` commit.
2. Stage only `LICENSE`, `README.md`, this specification, and the implementation plan created after approval.
3. Preserve the unrelated untracked `skill/preparing-ui-replica-handoffs.zip`.
4. Run license-text, README-link, Git-diff, and full test-suite checks.
5. Push the branch, open a ready-for-review pull request against `main`, and merge through the existing branch protection.
6. Verify GitHub reports the repository license as MIT and that `main` contains the new files.

## Acceptance Criteria

- Root `LICENSE` exactly follows the standard MIT License wording apart from the filled copyright line.
- README links to `LICENSE` and states that the project is MIT licensed.
- GitHub recognizes the repository license as MIT after merge.
- The full 192-test suite passes before merge.
- No Skill/plugin implementation file or unrelated ZIP is committed.
