---
name: vinyl-show-parallel
description: Coordinate parallel agents creating separate vinyl album animations, then validate and assemble one calibrated projection show. Use when the user requests parallel album work or a multi-sleeve light show.
---

Act as the coordinator. Assign independent cover research and animation work to per-album agents; retain all projector and camera control in this agent. Use the available delegation interface only when authorized by the user or applicable instructions. Parallel rendering processes are different from model agents: both can reduce elapsed time, but a render pool does not create or direct AI workers.

## Establish the shared inputs

Locate the Capsule Map repository and any read-only source projection-mapping checkout. Fix shared timing and a fresh show/output directory before delegation. Use the existing demo's 100 BPM, 48 beats, 30 fps, 28.8 seconds only when appropriate to the request. Keep a single immutable calibration snapshot for all worker renders. Movement of sleeves, projector, focus, or keystone invalidates it.

Give each album worker its verified reference or an isolated cover-research task, a unique output directory, exact timing, visual direction, and the relevant skill path. The sibling skills `vinyl-artwork/SKILL.md` and `vinyl-animation/SKILL.md` are separate entrypoints; pass their actual installed or repository paths so a worker can open them. Read [the delegation and assembly procedure](references/coordination.md) for a concrete task template and commands.

## Parallel ownership

- Each worker writes only its album's code, masks, previews, and result. Independent workers can research, design, and preview different albums concurrently.
- The coordinator owns camera/device access, shared source changes, capture/calibration, verification, timing, manifest aggregation, final composition, encoding, and deployment. Do not delegate simultaneous capture or calibration against the same projector.
- Cap combined rendering concurrency to machine capacity. Three album agents each starting a large process pool can be slower than three single-process album renders. Avoid loading unrelated albums or complete camera sweeps into every model.
- Use the user's chosen model when the runtime supports it; otherwise use the available agent without pretending it is another provider. These skills use files and commands and can be supplied to another agent runtime; they do not themselves connect API accounts or select external models.

## Accept the completed show

Review each worker's region/contact-sheet images and validation report. Reassign only the failed album, preserving unaffected results. Check common timing, reference/calibration fingerprints, completeness, and dark seams before composition. Compose by a single projector-space warp per album with black gaps and no bright rectangular background.

Project and inspect an edge-outline photograph after geometry changes. Then deploy the assembled show, photograph multiple animation phases, and check playback. Report measurements and remaining uncertainty; a low fitting residual or successful render is not proof of optical alignment. Never fabricate verification files or silently lower quality gates to obtain a video.
