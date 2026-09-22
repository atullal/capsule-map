# Contributing

Start with [setup](docs/SETUP.md) and [AGENTS.md](AGENTS.md). This is a hardware prototype: a fresh clone can build and run offline integrity checks, but optical verification requires the supported projector and physical targets.

## Development loop

1. Make a focused change. Preserve the separation between host image processing, native playback and vendor camera access.
2. Run relevant checks from the repository root:

   ```sh
   build/mapping-venv/bin/python tools/camera/test_batch.py
   build/mapping-venv/bin/python -m compileall -q tools vendor/projection-mapping
   git diff --check
   ```

3. For Android or controller changes, build both APKs using the setup guide. Edit controller HTML in `web/controller.html`.
4. Use the hardware checks appropriate to the change, with one device owner. See [validation notes](tools/ROBUSTNESS.md). If hardware is unavailable, state what remains unverified.
5. Describe the problem, resulting behavior, tests actually run and any remaining limitations in the PR. Link source/docs, not local private artifact paths as if they were publicly accessible.

Camera integrity tests use synthetic images and do not contact the projector. Existing album guard tests require an actual local calibrated run and reference; their CLI arguments are shown by `--help`. They are not a fresh-clone smoke test.

## Data and dependencies

Keep local artifacts under ignored `build/`. Do not commit album covers, room photographs, generated movies, calibration maps, APKs, virtual environments, credentials or debug signing keys. Share only appropriately cleared diagnostic material. Record source provenance for reference artwork locally.

The bundled upstream helpers retain their MIT license and snapshot hashes. Update `vendor/projection-mapping/UPSTREAM.json` when changing that snapshot; distinguish local patches from an unmodified upstream commit. New dependencies need a documented purpose and setup instructions.

## Reporting an issue

Include the commit, host OS/Python/JDK versions, projector model/firmware if relevant, command or UI action, expected result, actual result, and a minimal redacted log. Never paste pairing codes, controller PINs, credentials or private scene photos by default. Describe whether objects/projector/focus/keystone moved since calibration.
