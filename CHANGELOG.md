# Changelog

All notable changes to ArmorIQ SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-01-26

### Added
- **API Key Authentication**: Mandatory API key validation on SDK initialization
- **Production Endpoints**: Updated default endpoints for customer platform:
  - IAP: `https://customer-iap.armoriq.ai`
  - Proxy: `https://customer-proxy.armoriq.ai`
  - ConMap: `https://customer-api.armoriq.ai`
  - Dashboard: `https://platform.armoriq.ai/dashboard/api-keys`
- **Dual-Mode Support**: Local development and production modes
  - Production mode (default): Uses customer-*.armoriq.ai endpoints
  - Local mode: Uses localhost endpoints for development
  - Toggle via `use_production=False` parameter
  - Environment variable: `ARMORIQ_ENV=development`
- **API Key Management**: Integration with API Key Dashboard
  - API keys required in format: `ak_live_*` or `ak_test_*`
  - Set via environment variable: `ARMORIQ_API_KEY`
  - Or pass directly: `ArmorIQClient(api_key="ak_live_...")`
- **Documentation**:
  - `API_KEY_GUIDE.md`: Complete guide for API key usage
  - `PRODUCTION_VS_LOCAL.md`: Dual-mode configuration guide
  - Updated `examples/complete_workflow.py` with API key examples

### Changed
- **BREAKING**: API key now required for SDK initialization
  - Raises `ConfigurationException` if API key is missing
  - API key format validation enforced
- Updated all default endpoints to customer-specific URLs
- Improved error messages for authentication failures
- Enhanced configuration validation

### Security
- API key validation with bcrypt hash verification
- Secure key prefix lookup via database indexing
- Fire-and-forget usage tracking for performance
- Production token signing with GCP KMS
- Local development uses Ed25519 signing

## [0.1.0] - 2026-01-16

### Added
- Initial beta release of ArmorIQ SDK
- Core `ArmorIQClient` class with CSRG-IAP integration
- Production endpoints configured by default:
  - IAP: `https://customer-iap.armoriq.ai`
  - Proxy: `https://cloud-run-customer-proxy.armoriq.ai`
  - ConMap: `https://customer-api.armoriq.ai`
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
