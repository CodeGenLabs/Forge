---
skill: specify
id: implementation-as-requirement
fails-without: >
  A requirement reads "The system SHALL use a database transaction around the
  refund write". It passes the grammar, and it locks in an implementation
  nobody agreed to while saying nothing a user could observe.
with-skill: >
  The requirement states the observable property - concurrent refunds settle
  at most once against a balance - and the transaction is a design choice.
caught-by: none
---

The user describes a race condition they hit, in terms of the fix they have
in mind.

What to look for: whether the requirement survives changing the storage
engine. The grammar cannot tell an implementation from a behaviour, so this
one rests entirely on the skill - which is why the skill gives the test
("could a test fail this, as written, without knowing how it is built") rather
than the rule.
