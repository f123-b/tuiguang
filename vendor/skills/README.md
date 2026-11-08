# Application short-drama skills

These are software assets consumed by `creator.drama_skills`, not a global
installation into Codex. `registry.json` pins upstream commits and every
distributed file. Original files remain unmodified. Root `.gitattributes`
preserves their exact bytes across Windows/Linux checkouts. Upstream whitespace
is left intact instead of reformatting licensed source files.

- shuohao: https://github.com/eternityspring/shuohao-skills/tree/5612d2a0bd5f19d978c3ee19d1e42840335e3b4b
  Seven skills; Apache-2.0. See `shuohao/LICENSE` and `shuohao/NOTICE`.
- zenstory: https://github.com/zenstory-ai/drama-skills/tree/3d813c30871b4db5f2387d83bdc3a49db8ce7b2b
  `short-drama-review`; MIT. See `zenstory/LICENSE`.

Software integration is original adapter code in `services/api/creator/drama*`
and `scripts/drama-skill-check.mjs`. It reads the exact bounded reference named
in the registry (at most 2300 characters each), then validates the application's
own plan contract. Only the fixed `novel-script` offline validator is executed
at runtime. Other original reports/generation commands are installed for
provenance and future explicit integration; they are not claimed as executed
production stages. No upstream `allowed-tools` permission is granted.

Never run arbitrary skill commands or provider adapters from a request. The
reference image generation instructions do not enable their cloud APIs or
custom shell commands. Use existing authorized asset upload and local Wan
queues. Licensing these skill files does not clear rights for a novel, image,
likeness, voice or finished film.

To verify upstream deterministic helpers: run `node scripts/selftest.mjs` in
each shuohao skill folder. Tests use local synthetic fixtures/mock transports.
Current Windows results and application tests are in
`docs/implementation/DRAMA_SKILLS_VALIDATION.md`.
