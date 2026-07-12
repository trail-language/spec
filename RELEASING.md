# Releasing

Each release publishes the specification as a versioned tarball attached to a GitHub Release.
No PyPI package is produced. See `.github/workflows/release.yml`.

## Cutting a release

1. Bump the version where it applies (add a dated entry to `VERSIONING.md`).
2. Commit, then tag and push:
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```
3. The `Release` workflow builds `trail-spec-v0.1.0.tar.gz` (grammar, standard library, reference,
   function catalog, and versioning policy) and attaches it to a new GitHub Release with generated
   notes.

The tarball is the distributable artifact; consumers download it from the repository's Releases
page.
