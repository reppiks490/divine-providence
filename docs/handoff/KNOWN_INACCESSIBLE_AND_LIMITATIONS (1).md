# Known Inaccessible / Non-Serializable Sources

This handoff is designed to be loss-minimizing, but the following cannot be truthfully claimed as fully byte-for-byte exported.

## Three Project-scoped Excel originals
Raw-byte and text materialization were blocked by Project storage:
1. `THE_PULSE_OF_ICARUS_X_AGENT_REACH_ultracoded_CME_MINI_NQ1!_2026-09-15_2cb11.xlsx`
2. `THE_PULSE_OF_ICARUS_X_AGENT_REACH_ultracoded_CME_MINI_NQ1!_2026-09-15_2cb11(1).xlsx`
3. `THE_PULSE_OF_ICARUS_X_AGENT_REACH_ultracoded_CME_MINI_NQ1!_2026-09-15_2cb11(2).xlsx`

The related Pine source and `Pasted text.txt` were recovered in text form in the prior artifact corpus.

## Exact full chat transcripts
ChatGPT does not expose a general byte-for-byte export API for every past conversation to this task. The package therefore includes:
- every recoverable non-3D Library artifact found in the prior export pass
- a chat-derived workstream ledger
- durable repository handoffs that were specifically created to avoid reconstructing work from chats
It does **not** claim to contain every token ever exchanged in every historical chat.

## Hidden model reasoning
Private model chain-of-thought / hidden scratch reasoning is not a normal project artifact and is not exported. User-visible conclusions, generated files, repository changes, handoffs, reports, and accessible control-state are the relevant transfer surface.

## Automation scheduler internals
The automation API exposes titles, schedules, prompts, enabled state and run freshness to ChatGPT but does not provide a raw scheduler-database export to the container. `AUTOMATION_CONTROL_STATE.md` faithfully reconstructs the accessible operational state and mandates.

## Full Git object databases
The container had no DNS/network route to github.com, so it could not `git clone`. GitHub connector metadata was captured instead. Opus should reconnect to GitHub for exact source trees and historical objects.

## External plugin raw transcripts
Research reports and handoffs preserve many external-source findings, but not every low-level raw connector response from every historical plugin invocation exists as a separate durable file.

## Meaning of "absolute"
Within these access constraints, this package contains the broadest recoverable non-3D transfer surface assembled here. Any item not physically exportable is named explicitly instead of being silently omitted.
