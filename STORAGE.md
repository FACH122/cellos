# Where the bytes go

**A design decision, recorded. No implementation.**

CellOS can already attach evidence — a link, a note, a reference — to a
decision, a task or a cell. What it cannot do is hold a file. This is the
agreed shape for when it does.

Nothing here is built. It is written down now because the decisions that
matter are the ones taken before the first line, and because two of them look
like details until the day you try to change them.

---

## 1. The constraint everything follows from

**A file cannot go in the event log.**

The log is the authority and it gets replayed. Put a ten-megabyte PDF in it and
replay stops being cheap, the log stops being readable, and `run.py rebuild`
becomes a data-copying exercise rather than a proof.

So the split is:

> **The log records what was attached — filename, size, media type, and a
> SHA-256 of the contents. The bytes live outside it, addressed by that hash.**

The evidence table stays what it is today: a projection, rebuilt by replay.

This buys a failure mode worth having. Lose the blob store entirely and replay
still reconstructs the complete record of *what was offered, by whom, when, and
against which question* — with the bytes marked missing. The organisation's
memory of its own reasoning survives the loss of its attachments.

It also costs something, stated plainly in §8: CellOS gains a second durable
artefact, and the log stops being the only thing worth backing up.

---

## 2. Content addressing: the digest is the object key

The name of a blob is `sha256(bytes)`. Not a random id, not a path chosen at
upload time.

Four consequences, and the fourth is why this decision comes first:

**Deduplication is free.** The same PDF attached to five decisions is stored
once.

**Integrity is checkable.** You can always prove the bytes being served are the
bytes the log recorded.

**Immutability matches the log.** A hash cannot be updated in place. Evidence
that could be silently swapped after the fact would defeat the point of
evidence — it would be the one part of CellOS that could be rewritten.

**It is what makes the backends interchangeable.** The digest is the key
everywhere: a path segment on disk, an object key in a bucket. No mapping
table, no migration on the day you switch. You copy the directory into the
bucket keeping the same paths and change one environment variable.

There is no `object_key` column. Keeping the key and the hash as separate
fields would create exactly the storage-specific coupling this avoids.

### `file_id` and `digest` are different things

`file_id` — the evidence id — identifies **an attachment**: this person
offered this document, with this label, in support of this question.

`digest` identifies **the bytes**.

Two people attaching the same PDF with different labels is two evidence rows
and one blob. Deletion has to respect that, which is §7.

---

## 3. The seam: `kernel/blobs.py`

One file, beside `db.py`, `events.py` and `relationships.py`. It knows nothing
about evidence, cells or people — bytes in, digest out — the same way `db`
knows nothing about cells.

```
class Store:
    receives_bytes = False               # does CellOS itself take the upload?

    def ticket(digest, media_type, size)  -> where to PUT, and until when
    def has(digest)                       -> bool          # the confirm check
    def grant(digest, filename, seconds)  -> a short-lived URL
    def receive(token, stream)            -> digest        # local only
```

Two implementations: **`OnDisk` now, `InBucket` later.** `CELLOS_BLOBS`
selects one. Nothing above this layer knows which is loaded.

A local grant is constructed the same way a presigned URL is: HMAC-SHA256 over
`digest + filename + expiry`, with a server secret in place of a cloud key.
Stateless — there is no table of outstanding grants. The two backends run
nearly the same function with a different host and a different key.

---

## 4. Upload: authorise, then a temporary capability

```
1  POST /api/evidence/uploads
     { subject_kind, subject_id, label, filename, media_type, size, digest }

   CellOS asks: may this person attach here? is the size under the cap?
   is the type allowed? is the digest well formed?
   → returns a TICKET: { url, method, headers, expires_at }

2  PUT <ticket.url>  ← the bytes
     OnDisk    to CellOS, which hashes as it writes and compares
     InBucket  straight to the bucket; CellOS never sees them

3  POST /api/evidence/uploads/<ticket>/confirm
   → CellOS verifies the object exists          stat / HEAD
   → appends EvidenceAttached
   → returns the evidence row
```

**The browser computes the digest** with `crypto.subtle.digest('SHA-256', …)`
before step 1. It has to: in the bucket case nobody else can. Locally CellOS
hashes as it writes and compares, which costs nothing and catches a broken or
lying client.

### Confirmation verifies before it writes

This ordering is the integrity step, not bookkeeping. There are two ways for
the middle to fail and they are not equally bad:

- bytes land, confirm never comes → **an orphan blob**. Harmless; swept later.
- event written, bytes never landed → **evidence pointing at nothing.**

Always prefer the orphan. `EvidenceAttached` is appended only after the store
confirms the object is really there.

---

## 5. Download: permission once, then a short-lived capability

```
1  GET /api/evidence/<id>/link
   → can this person see the cell this evidence lives in?
   → mint a grant: one object, ~120 seconds, unguessable
   → append EvidenceRequested   (who asked, when)
   → return { url, expires_at }

2  GET <grant.url>
     OnDisk    CellOS checks its own HMAC, streams with
               Content-Disposition: attachment
     InBucket  the bucket checks the signature
```

**Object storage serves the bytes directly.** Downloads are not proxied
through CellOS, and will not be unless a later concrete requirement makes it
necessary.

That was argued and settled. The case for proxying is that permission is then
checked on every request rather than once at issue. The case against is
stronger:

- It is the standard architecture, not a compromise. Authorise the *link*, not
  the *bytes*.
- CellOS runs a stdlib `ThreadingHTTPServer`. Proxying a large download
  occupies a thread and pulls the file through Python. On a small instance,
  three concurrent downloads would be the worst-performing thing in the system
  — introduced to preserve a principle.
- If the **local** backend also issues expiring single-object tokens, then the
  two backends share a security model rather than merely resembling each
  other. Proxying locally and signing remotely would have made them differ,
  which is the opposite of the goal.

The residual risk is named and bounded: **the URL is the credential for its
lifetime.** Short-lived, unguessable, tied to one object, never permanent,
minted again when needed.

### No permanent download URLs in CellOS state

The cell payload carries the digest, filename, size and media type. **It never
carries a URL.** A link is minted when somebody clicks, from a separate
request.

Embedding one would scatter live credentials through a payload that is cached,
logged and re-rendered on every action.

### A short window is not a short download

The signature is checked when the request *begins*, not throughout. A
two-minute grant serves a 500MB download that takes twenty. The window bounds
how long a leaked link is useful, not how long a transfer may take.

---

## 6. What differs between the two backends

Everything above `kernel/blobs.py` is identical. Below it:

| | `OnDisk` | `InBucket` |
|---|---|---|
| step 2 goes to | CellOS | the bucket |
| who hashes | browser, CellOS re-checks | browser only |
| size enforced | while streaming | POST policy `content-length-range` |
| `Content-Disposition` | set when serving | **baked into the object at PUT** |
| grant signed by | server secret | bucket key |
| `has()` | `os.stat` | `HEAD` |

The `Content-Disposition` row is the one that cannot be retrofitted. Serving
from your own origin you control the response headers; serving from a bucket
you do not, unless the header was written into the object's metadata at upload
time. Get it wrong and an uploaded `.html` is live on the storage domain.

---

## 7. Withdrawal, eventually

Evidence should become withdrawable. `EvidenceWithdrawn` hides the row —
the log is append-only, so nothing is erased — and the digest is refcounted so
an unreferenced blob becomes collectable.

This is not speculative. Three separate groups using CellOS hit it: one
double-posted a source because the write gave no confirmation, another
corrupted two labels with a shell quoting slip, and neither could remove
anything. The mangled records are still in those logs.

Files make it urgent rather than tidy. An accidental upload of the wrong
document is not a cosmetic problem.

Deduplication complicates it: the same bytes may be referenced by evidence in
a cell the person asking cannot see. Collection happens at a refcount of zero,
not on withdrawal.

---

## 8. Verification needs a second half

Every version tag so far has claimed the same thing: *N events replay to
byte-identical projections across 12 tables.* That is checked by fingerprinting
every table either side of a `rebuild`.

**That check cannot cover blobs, because blobs are not derived from the log.**

So on the day files exist, that sentence stops describing the whole system
while sounding exactly as complete as it does today. `run.py verify` should
grow a second half:

- every digest referenced by an evidence row is **present** in the store, and
- its bytes still **hash to their name**.

A guarantee that quietly narrows while its wording stays the same is worse
than one that was never claimed.

---

## 9. Still to decide

**The size ceiling.** 10MB covers documents and screenshots. 100MB means video,
and means the answer to "which backend first" changes.

**What a person sees.** Nothing above describes attaching a file, what shows
while a 20MB upload is in flight, what a missing blob looks like on the page,
or what any of it does on a phone. For a project that has spent most of its
life on the interface, that is the largest gap in this document.

---

## 10. The decision, in one paragraph

Evidence metadata stays in the event log and is projected into the evidence
view. The bytes live behind `kernel/blobs.py`, content-addressed by SHA-256,
with the digest as the object key. `OnDisk` first, `InBucket` later, behind the
same abstraction. Upload is a CellOS authorisation followed by a temporary
upload capability; download is a CellOS permission check followed by a
short-lived download capability. No permanent download URLs are stored. Object
storage serves bytes directly. `file_id` identifies the attachment, `digest`
identifies the bytes. Confirmation verifies the blob exists before
`EvidenceAttached` is appended. Withdrawal and the second half of verification
follow later.
