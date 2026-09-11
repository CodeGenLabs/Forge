---
name: forge
phase: understand
description: >
  Start here for any request that will change this repository. Restates the
  intent, picks the track, and hands off to the phase skills.
requires-kernel: ["forge status", "forge change new", "forge change show", "forge change track"]
reads: from-dag
writes: ["changes/${change}/.forge.yaml"]
---

# forge - the router

## Announce

> Running the `forge` router: restating intent and choosing a track.

## What this does

Every request that will change the repository starts here. Three things happen
and nothing else: the intent is restated in your words, a track is chosen, and
the change directory is opened. Implementation does not start in this skill.

## 1. Restate the intent

One paragraph, in the user's terms, covering:

- what they want to be true afterwards, as an outcome rather than an edit;
- what you are assuming, each assumption on its own line;
- what you do not know yet.

Getting this wrong is cheap here and expensive everywhere downstream, which is
why it is written before anything is chosen.

## 2. Choose the track

Run `forge status` first, so the choice is made against the repository as it
is rather than as remembered.

| Track | When |
|---|---|
| A - probe | A question, not a deliverable. "Can we", "is it possible", a spike. The output is an answer and the code is thrown away |
| B - bounded | A scoped change to a flow that already exists here, touching no `ARC-`, `API-` or `DAT-` claim |
| C - structural | A new subsystem or capability; a component boundary, public interface, data model or invariant changes; anything security- or migration-sensitive |

Four signals force track C regardless of how small it feels. Check each:

- the blast radius intersects an `ARC-`, `API-` or `DAT-` claim;
- the change adds a public export, a route, or a migration;
- more than about fifteen files are in scope;
- the change touches authentication, authorisation, or stored credentials.

**"It is too simple to need a spec" is a signal to take the heavier track, not
the lighter one.** What scales down with simplicity is the size of each
artifact, never whether it exists. A one-line spec delta is a normal thing; a
missing one is how a change arrives with nobody able to say what it promised.

## 3. Gate G1 - intent and track

Show the user: the restated intent, the chosen track, the signals that forced
it if any, and what is still unknown. Wait for their answer before opening the
change.

This gate is never skipped and never automated. Product intent is not in the
repository, and the track sets every obligation that follows.

## 4. Open the change

```bash
forge change new "<title>" --track <A|B|C>
forge change show <n>
```

`forge change show` prints what the track requires and what is blocked on
what. Follow it rather than a remembered order; the workflow is data and it
may have been edited.

## 5. The ratchet

If the work turns out to be bigger than the track:

```bash
forge change track <n> --to C --reason "<what you found>"
```

Upgrading is normal and costs a sentence. Downgrading is refused by the
kernel, and the reason is worth knowing: a change that turns out to touch an
`ARC-` claim would otherwise be able to shed the artifacts that account for
it, one reasonable-looking step at a time. If the scope genuinely shrank,
close the change and open a smaller one.

## Handing off

| Next | Skill |
|---|---|
| Understand the code before changing it | `investigate` |
| Write the delta requirements | `specify` |
| Turn the spec into ordered work | `plan-tasks` |
| Do one task | `implement` |
| Write what was learned into the store | `curate-knowledge` |

On track A, stop after `investigate`. A probe has no artifacts, and the code
it produces is labelled throwaway and deleted - keeping it is how an
experiment becomes a dependency nobody chose.
