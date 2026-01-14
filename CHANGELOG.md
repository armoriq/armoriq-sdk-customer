# Changelog

All notable changes to ArmorIQ SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-01-13

### Added
- Initial SDK implementation
- Core `ArmorIQClient` class with CSRG-IAP integration
- `capture_plan()` API for plan canonicalization
- `get_intent_token()` API for token acquisition from IAP
- `invoke()` API for MCP action invocation through proxy
- `delegate()` API for agent-to-agent delegation
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
