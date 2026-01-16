# ArmorIQ SDK Documentation

This directory contains additional documentation for the ArmorIQ SDK.

## Directory Structure

```
docs/
├── README.md                          # This file
├── DOCUMENTATION_STRUCTURE.md         # Documentation organization guide
├── IAM_DELEGATION_GUIDE.md           # IAM and delegation details
├── deployment/                        # Deployment and publishing guides
│   ├── PRODUCTION_DEPLOYMENT_GUIDE.md
│   └── QUICK_PUBLISH.md
├── guides/                            # Additional guides (future)
└── internal/                          # Internal development docs (not for distribution)
    ├── Test reports and results
    ├── Implementation reports
    ├── Progress tracking
    └── Development verification files
```

## Main Documentation (Root Level)

The following user-facing documentation is available in the repository root:

- **[README.md](../README.md)** - Main SDK overview and getting started
- **[QUICKSTART.md](../QUICKSTART.md)** - Quick start guide
- **[ARCHITECTURE.md](../ARCHITECTURE.md)** - Architecture and design details
- **[DEVELOPMENT.md](../DEVELOPMENT.md)** - Development guide for contributors
- **[PUBLISHING_GUIDE.md](../PUBLISHING_GUIDE.md)** - Guide for publishing the SDK
- **[CHANGELOG.md](../CHANGELOG.md)** - Version history and changes

## Deployment Documentation

For production deployment and distribution:

- **[PRODUCTION_DEPLOYMENT_GUIDE.md](deployment/PRODUCTION_DEPLOYMENT_GUIDE.md)** - Complete production deployment guide
- **[QUICK_PUBLISH.md](deployment/QUICK_PUBLISH.md)** - Quick publishing reference

## IAM and Security

- **[IAM_DELEGATION_GUIDE.md](IAM_DELEGATION_GUIDE.md)** - Detailed guide on IAM context injection and public key delegation

## Examples

All code examples are located in the `examples/` directory at the repository root. See [examples/README.md](../examples/README.md) for details.

## Internal Documentation

The `internal/` directory contains development-specific documentation including test reports, implementation progress, and verification files. These are not intended for end users and are excluded from distribution packages.

## Contributing

See [DEVELOPMENT.md](../DEVELOPMENT.md) for contribution guidelines and development setup instructions.
