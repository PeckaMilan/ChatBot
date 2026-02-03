# Changelog

All notable changes to **{{PROJECT_NAME}}** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Version Format

`MAJOR.MINOR.PATCH` where:
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Iteration Markers

Each release is tagged with its development iteration:

| Marker | Meaning |
|--------|---------|
| [I1] | Iteration 1 - Foundation |
| [I2] | Iteration 2 - Core Features |
| [I3] | Iteration 3 - Enhancement |
| [I4] | Iteration 4 - Polish |
| [I5] | Iteration 5 - Release |

## Change Categories

- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Vulnerability fixes
- **Performance** - Performance improvements
- **Documentation** - Documentation updates
- **Infrastructure** - Build, CI/CD, tooling changes

---

## [Unreleased]

### Added
- {{UNRELEASED_ADDED_1}}

### Changed
- {{UNRELEASED_CHANGED_1}}

### Fixed
- {{UNRELEASED_FIXED_1}}

---

## [{{VERSION_1}}] - {{DATE_1}} [I{{ITERATION_1}}]

### Added
- {{VERSION_1_ADDED_1}}
- {{VERSION_1_ADDED_2}}

### Changed
- {{VERSION_1_CHANGED_1}}

### Fixed
- {{VERSION_1_FIXED_1}}

### Infrastructure
- {{VERSION_1_INFRA_1}}

**Full Changelog:** {{COMPARE_URL_1}}

---

## [{{VERSION_2}}] - {{DATE_2}} [I{{ITERATION_2}}]

### Added
- {{VERSION_2_ADDED_1}}

### Changed
- {{VERSION_2_CHANGED_1}}

### Deprecated
- {{VERSION_2_DEPRECATED_1}}

### Removed
- {{VERSION_2_REMOVED_1}}

### Fixed
- {{VERSION_2_FIXED_1}}

### Security
- {{VERSION_2_SECURITY_1}}

**Full Changelog:** {{COMPARE_URL_2}}

---

## [{{VERSION_3}}] - {{DATE_3}} [I{{ITERATION_3}}]

### Added
- {{VERSION_3_ADDED_1}}

### Performance
- {{VERSION_3_PERF_1}}

### Documentation
- {{VERSION_3_DOCS_1}}

**Full Changelog:** {{COMPARE_URL_3}}

---

<!--
Template for new releases:

## [X.Y.Z] - YYYY-MM-DD [I#]

### Added
- New feature description (#issue)

### Changed
- Change description (#issue)

### Deprecated
- Deprecated feature (#issue)

### Removed
- Removed feature (#issue)

### Fixed
- Bug fix description (#issue)

### Security
- Security fix description (#issue)

### Performance
- Performance improvement (#issue)

### Documentation
- Documentation update (#issue)

### Infrastructure
- Infrastructure change (#issue)

**Full Changelog:** https://github.com/{{OWNER}}/{{REPO}}/compare/vX.Y.Z...vX.Y.Z
-->

---

## Release Checklist

Before releasing a new version:

- [ ] All tests passing
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] Version bumped in package files
- [ ] Git tag created
- [ ] Release notes drafted

---

[Unreleased]: {{REPO_URL}}/compare/v{{LATEST_VERSION}}...HEAD
[{{VERSION_1}}]: {{REPO_URL}}/compare/v{{VERSION_2}}...v{{VERSION_1}}
[{{VERSION_2}}]: {{REPO_URL}}/compare/v{{VERSION_3}}...v{{VERSION_2}}
[{{VERSION_3}}]: {{REPO_URL}}/releases/tag/v{{VERSION_3}}
