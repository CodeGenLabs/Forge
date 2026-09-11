# Drift detection

## Purpose

Drift detection tells a maintainer which recorded claims describe code that has changed
since a human last confirmed them, so that stale knowledge is found by a command rather
than by being wrong in front of somebody.

## ADDED Requirements

### Requirement: REQ-drift-store-scan - Drift can be asked of the whole claim store

The system SHALL classify every anchor of every claim in the store when asked, without
the caller naming any anchor, and SHALL report the result grouped by claim rather than
by anchor.

#### Scenario: Every claim is fresh

- Given a store whose every anchor records the SHA of the code it points at
- When a store-wide drift scan runs
- Then no claim is reported as needing attention and the command exits 0

#### Scenario: One claim's code has moved

- Given a claim anchored to a symbol whose body has since changed
- When a store-wide drift scan runs
- Then that claim is reported once, with the anchor and the status that caused it
- And the command exits 1

#### Scenario: A claim has several anchors and one is stale

- Given a claim with three anchors, of which one is stale and two are fresh
- When a store-wide drift scan runs
- Then the claim is reported once, at the worst status among its anchors
- And the fresh anchors are not reported as separate findings

#### Scenario: A candidate claim is stale

- Given a proposed claim in the candidate tier whose anchor is stale
- When a store-wide drift scan runs
- Then the candidate is reported separately from the ratified claims
- And a stale candidate alone does not make the command exit 1

### Requirement: REQ-drift-changed-only - Drift can be narrowed to the current diff

The system SHALL support narrowing a store-wide scan to those claims with at least one
anchor whose path appears in the working diff, so that the scan is cheap enough to run
on every commit.

#### Scenario: The diff touches no anchored file

- Given a working diff that touches only files no claim anchors to
- When a diff-narrowed drift scan runs
- Then no claim is examined and the command exits 0

#### Scenario: The diff touches an anchored file

- Given a working diff that modifies a file some claim anchors to
- When a diff-narrowed drift scan runs
- Then that claim is classified and reported like any other
- And claims anchored only to untouched files are not classified

### Requirement: REQ-drift-never-rewrites - A drift scan never edits a claim

The system SHALL NOT modify any claim, anchor or recorded SHA as part of reporting
drift. Reporting and resolving are separate acts, and only a human performs the second.

#### Scenario: A scan over a store with stale claims

- Given a store containing at least one stale claim
- When a store-wide drift scan runs to completion
- Then no file under the store has changed on disk
