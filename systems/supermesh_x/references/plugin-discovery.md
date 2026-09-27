# Plugin and tool discovery

## Principle

Treat the runtime's live catalog as the source of truth. Never assume a provider exists because it existed in a previous runtime or session.

## Discovery sequence

1. enumerate native tools and installed skills/plugins
2. map each to normalized capabilities
3. inspect authentication/connection status where available
4. rank installed providers first
5. when the requested capability is missing or weak, search the plugin/skill catalog for additional providers
6. suggest optional providers to the user; installation/connection remains explicit user action
7. once connected, register the provider without changing core routing logic

## Examples of useful optional expansions

Search/crawl: Tavily, Firecrawl, Parallel Search, Exa.
Academic: Consensus, Scite.
Developer docs/code: Context7 or equivalent current providers.
Data/warehouse: Databricks, Airtable, connected databases/warehouses when authorized.

Availability changes over time; discover rather than hard-code.
