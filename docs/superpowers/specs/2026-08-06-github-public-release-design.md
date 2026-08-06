# GitHub Public Release Design

## Goal

Publish `preparing-ui-replica-handoffs` as a complete public Codex Skill repository whose default `main` branch immediately shows the final source, README, two example images, and a downloadable release artifact.

## Current State

- The public repository is `GGBond2424648901/preparing-ui-replica-handoffs`.
- `main` contains only the original baseline and therefore has no README.
- Pull request `#1` contains the final Skill, plugin, README, and two example images, but is still a draft.
- The current PR is mergeable and targets `main`.
- `main` has no branch protection.
- The validated distribution archive exists outside the repository at `D:\AI_Demo\Result\preparing-ui-replica-handoffs-plugin.zip`.
- The unrelated untracked file `skill/preparing-ui-replica-handoffs.zip` remains excluded.

## Public Repository Experience

The repository homepage on `main` will show:

1. A concise Chinese-first introduction with an English summary.
2. Core capabilities and the generated handoff package.
3. A quick-start section explaining which plugin directory to install or package.
4. A direct GitHub Release download link for the plugin ZIP.
5. The two user-approved example images.
6. A clear note that the example predates the current improved Skill and that SoI models are expected to improve replica quality.
7. Version and validation status without claiming that an un-enriched generated skeleton is implementation-ready.

No license will be invented in this release because license choice is a separate legal decision.

## Release Flow

1. Improve `README.md` on `feat/preparing-ui-replica-handoffs`.
2. Verify the complete test suite, plugin metadata, image paths, distribution ZIP hash, Git diff, and Git scope.
3. Commit and push only the README/spec changes; keep the unrelated ZIP untracked.
4. Mark PR `#1` ready for review.
5. Merge PR `#1` into `main` using a merge commit so the implementation history remains visible.
6. Synchronize the local `main` branch to the merged remote state without deleting the feature branch or unrelated local files.
7. Create annotated public release `v1.0.0` at the merged `main` commit.
8. Attach `preparing-ui-replica-handoffs-plugin.zip` as the release artifact and publish release notes summarizing scope, validation, and early-example context.

## Main Branch Protection

Apply protection only after the initial merge and release:

- Require changes to arrive through pull requests.
- Require zero approving reviews so a solo maintainer is not blocked.
- Require all review conversations to be resolved.
- Enforce protection for administrators.
- Require linear history for future changes.
- Block force pushes.
- Block branch deletion.
- Do not require status checks until a GitHub Actions workflow exists.
- Do not lock the branch or block branch creation.

This configuration protects the public default branch without inventing a CI check that the repository does not currently run.

## Failure Handling

- If validation fails, do not merge or publish the release.
- If the PR cannot be marked ready or merged, leave it open and report the exact GitHub state.
- If release upload fails, keep `main` merged but do not claim the downloadable release exists.
- If branch protection fails, preserve the merged release and report the protection error separately.
- Never force-push, delete branches, edit hashes manually, or include the unrelated local ZIP.

## Acceptance Criteria

- The repository is public and its default branch is `main`.
- `main` contains `README.md`, the final Skill/plugin source, and both example images.
- PR `#1` is merged and no longer a draft.
- Release `v1.0.0` is published with the verified ZIP asset.
- The release asset SHA-256 is recorded in the release notes or final handoff.
- `main` branch protection reports pull-request enforcement, conversation resolution, admin enforcement, no force pushes, and no deletions.
- The full local test suite passes immediately before merge.
- The only remaining local untracked item is the pre-existing `skill/preparing-ui-replica-handoffs.zip`.
