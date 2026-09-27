# Dynamic Discovery

SuperMesh-X separates discovery from execution. A discovered provider is metadata only until runtime compatibility, authentication, trust, and health checks succeed.

Discovery sources may include the runtime tool catalog, installed plugins, MCP registries, provider manifests, user-authorized private registries, package configuration, and explicitly approved public discovery mechanisms. Discovery never grants permission to call a provider.

Normalize each candidate into a provider descriptor: name, capability contracts, runtime targets, transports, auth modes, trust class, preflight requirements, quotas, cost class, and freshness metadata. Then negotiate the adapter and rank only compatible providers.

Use previews and registry metadata for candidate selection; treat the provider's live tool list/schema after connection as authoritative. Unknown trust posture must be handled conservatively.
