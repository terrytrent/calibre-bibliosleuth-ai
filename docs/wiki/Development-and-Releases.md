# Development and releases

The source repository is organized into plugin code, tests, documentation, assets, packaging scripts, and CI configuration. Start with the root `README.md`, `AGENTS.md`, and `Makefile`.

Common commands:

```sh
make test
make build
make verify
make install
make release
```

The build downloads the pinned `defusedxml` dependency, verifies its hash, and vendors only the runtime package into the distributable ZIP. Third-party source is not committed to the repository.

Continuous integration runs cross-platform tests, package validation, Ruff, Qlty, Bandit, dependency auditing, Trivy, CodeQL, dependency review, repository-specific Semgrep rules, actionlint/zizmor workflow auditing, documentation and link checks, and a coverage non-regression gate. A compatibility workflow installs the built plugin into the oldest and current supported Calibre releases. Every workflow action is pinned to an immutable commit.

Tagged releases build the plugin and publish the ZIP, checksum, CycloneDX SBOM, and GitHub artifact attestations. Main-branch releases are protected and signed according to project policy. Files in `docs/wiki/` are the canonical wiki source and are synchronized after reviewed changes merge to `main`.

- [Contributing](https://github.com/terrytrent/calibre-bibliosleuth-ai/blob/main/CONTRIBUTING.md)
- [Changelog](https://github.com/terrytrent/calibre-bibliosleuth-ai/blob/main/CHANGELOG.md)
- [Release artifacts](https://github.com/terrytrent/calibre-bibliosleuth-ai/releases)
