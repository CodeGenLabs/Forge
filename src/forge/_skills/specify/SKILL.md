---
name: specify
phase: spec
description: >
  Write the delta requirements and scenarios for a change, and on track C the
  design section and any ADR. Behaviour only, never implementation.
requires-kernel: ["forge instructions", "forge gate", "forge impact", "forge check"]
reads: from-dag
writes: ["changes/${change}/spec/**", "changes/${change}/design.md"]
---

# specify

## Announce

> Running `specify`: writing the delta requirements for this change.

## What this does

States what the system must do afterwards, as a delta against the permanent
capability specs. Behaviour only. How it will be built is `design`, below, and
even there it is an approach rather than code.

## 1. Load the contract

```bash
forge instructions spec --change <n>
```

That resolves what this phase may read, including the project's `rules.spec`
list from `.forge/config.yaml`. Those rules are house style with teeth - a
project that says "money is integer minor units" means every requirement you
write about an amount.

## 2. Write the delta

`changes/<n>/spec/<capability-path>/spec.md`, in four verbs and no others:

```markdown
## ADDED Requirements

### Requirement: REQ-refunds-1 - An operator can refund a settled payment
The system SHALL allow a refund against any settled payment up to its
remaining refundable balance.

#### Scenario: Partial refund within balance
- **WHEN** an operator refunds 30 against a payment of 100 with no prior refunds
- **THEN** the refund settles and the remaining refundable balance is 70

#### Scenario: Refund exceeding remaining balance
- **WHEN** an operator refunds 80 against a payment of 100 with 30 refunded
- **THEN** the request is rejected with `refund_exceeds_balance`

## MODIFIED Requirements
(the requirement's full new text, never a diff fragment)

## REMOVED Requirements
### Requirement: REQ-old-4 - ...
**Reason**: ...
**Migration**: ...
```

`MODIFIED` carries full content because a reviewer has to read what the system
will do, not a patch against what it did. `REMOVED` carries a reason and a
migration because deleting a promise should cost as much to write as making
one.

The capability path is an existing directory under `docs/system/specs/` where
one exists. Inventing a parallel path for the same capability splits it in
two, and nothing ever merges them back.

## 3. Make each requirement testable

Read each one and ask: could a test fail this, as written?

- **Observable behaviour, not implementation.** "The system SHALL use a
  mutex" is not a requirement; "concurrent captures against one authorisation
  SHALL settle at most once" is.
- **Say what happens at the boundary** - rejected, clamped, queued, retried.
  That detail is the one most often left out and most often implemented
  wrong.
- **Say what it is quantified over.** "A refund never exceeds the capture" is
  ambiguous between each refund and their sum, and the two are different
  systems.

Each requirement needs at least one scenario, and the scenarios should cover
the boundary as well as the happy path. A requirement with one cheerful
scenario is a requirement nobody has thought about.

## 4. Check it

```bash
forge gate spec:post --change <n>
```

The grammar is checked mechanically: headings, scenario depth, SHALL or MUST,
unique ids, no unresolved clarifications, full content in MODIFIED, reason and
migration in REMOVED. Fix what it reports before showing anyone.

If the change genuinely alters no observable behaviour, record that decision
rather than leaving the delta absent:

```yaml
# changes/<n>/.forge.yaml
skip_spec: log format only; no caller can observe the difference
```

A bare `skip_spec: true` is rejected. The reason nobody writes is the one
nobody can argue with later.

## 5. Gate G2 - the spec

Show the user the delta requirements and scenarios. This is the contract;
everything downstream argues from it, and a wrong requirement wastes the rest
of the lifecycle. Track C always; track B when the change introduces a new
capability.

## 6. Design, on track C

`changes/<n>/design.md` after the spec is agreed:

- the approach, in a paragraph;
- **the alternatives rejected, each with the reason it lost** - a design with
  no rejected alternative records a preference rather than a decision;
- the risks, and what would tell you early that one is happening;
- which claims the approach changes. `forge impact --change <n>` computes the
  set; the design says what it intends to do to each.

Write an ADR when the change decides something that outlives it: a dependency
direction, a boundary, a data-model rule, anything a future reader would
otherwise have to reverse-engineer. ADRs are never edited once accepted - a
later decision supersedes them.

## Exit

`forge check --scope change --change <n>` clean for the grammar, G2 recorded,
and every scenario is something a test could assert.
