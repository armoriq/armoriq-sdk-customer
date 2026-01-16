# Changelog

All notable changes to ArmorIQ SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-16

### Added
- Initial beta release of ArmorIQ SDK
- Core `ArmorIQClient` class with CSRG-IAP integration
- Production endpoints configured by default:
  - IAP: `https://iap.armoriq.io`
  - Proxy: `https://cloud-run-proxy.armoriq.io`
  - ConMap: `https://api.armoriq.io`
- Automatic environment detection (`ARMORIQ_ENV`)
- Flexible endpoint configuration (env vars, parameters, per-MCP)
- Core APIs:
  - `capture_plan()` - Plan canonicalization with CSRG
  - `get_intent_token()` - Token acquisition from IAP with Ed25519 signatures
  - `invoke()` - MCP action invocation through proxy
  - `delegate()` - Agent-to-agent delegation with public key cryptography
- Custom exceptions:
  - `InvalidTokenException`
  - `IntentMismatchException`
  - `TokenExpiredException`
  - `MCPInvocationException`
  - `DelegationException`
  - `ConfigurationException`
- Pydantic models for type safety:
  - `IntentToken`
  - `PlanCapture`
  - `MCPInvocation`
  - `MCPInvocationResult`
  - `DelegationRequest`
  - `DelegationResult`
  - `SDKConfig`
- Token caching with expiry checking
- Comprehensive error handling
- Environment variable configuration support
- Context manager support for resource cleanup
- Example scripts:
  - Basic agent usage
  - Multi-MCP coordination
  - Agent delegation
  - Error handling patterns
- Full test suite with pytest
- Development documentation
- README with quick start guide

### Dependencies
- `httpx>=0.27.0` - HTTP client
- `pydantic>=2.0.0` - Data validation
- `csrg-iap>=0.1.0` - CSRG canonicalization

### Notes
- This is an alpha release for testing and feedback
- API may change in future versions
- Requires CSRG-IAP service running
- Requires ArmorIQ Proxy service for MCP invocations

[0.1.0]: https://github.com/armoriq/armoriq-sdk-python/releases/tag/v0.1.0
