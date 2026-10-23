# 036 — A reloaded room doesn't know where it is: no relocalization into a new ARCore session

**Area:** ar + recon · **Status:** known (not scheduled) · **Filed from:** 005

## Context

*Filed 2026-10-23.*

When Android kills the app, 005 saves the field and the anchor pose. A new process starts a new
ARCore session with **a new, unrelated tracking space**, so the saved field reloads in the wrong
place. 005 shows it as an unregistered ghost and integrates nothing into it.

Bringing it back means finding the transform between the old tracking space and the new one.
Candidates, not a verdict:

- **ARCore Cloud Anchors.** Hosted by Google, and they need an API key and a network. They also
  persist for days, and that's the feature this card asks for.
- **ICP against the TSDF.** The Chisel paper's own pose refinement (§III-J) aligns a depth scan to the
  field by its gradient. Align the new session's first depth frames to the saved field, and the
  result is the transform.
- **Ask the user.** Show the ghost and let a drag-and-rotate gesture register it, with ICP refining
  it.

## The tempting wrong fixes

- **Integrating anyway and hoping the new depth "corrects" it.** Two rooms are superimposed, and
  carving fights the wrong one.

## Files

```
issues/005-the-room-dies-with-the-activity.md
klingensmith2015chisel.pdf   §III-J
```
