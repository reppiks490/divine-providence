# V31 Signed Recovery Key-Policy Contract

## Scope
This contract governs authentication trust for recovery evidence only. It grants no infrastructure mutation, promotion, rollback, lease, or execution authority.

## Trust separation
- Recovery producer keys authenticate recovery checkpoint evidence.
- A separate policy-authority key authenticates key-policy epochs.
- The policy authority never signs infrastructure actions.

## Policy epochs
Each immutable policy epoch binds:
- a monotonically increasing `epoch`;
- the previous policy hash;
- one stable recovery producer identity;
- an `effective_generation`;
- exactly one active signing key ID;
- trusted historical key IDs;
- retired key IDs;
- revoked key IDs.

The active key must be trusted and cannot be retired or revoked. Retired keys remain trusted only for historical evidence under the policy epoch that applied when that evidence was issued. Revocation is monotonic: a revoked key cannot reappear in a later policy.

## Append-only policy chain
Policy files are sequential and HMAC-authenticated by the independent policy authority. `HEAD` binds the latest epoch and policy hash. Verification fails closed for signature tamper, epoch gaps, linkage changes, producer substitution, non-monotonic activation generations, revoked-key resurrection, stale/rolled-back HEAD, or unknown policy history.

## Envelope binding
`PolicyBoundRecoveryAuthenticator` requires every new recovery envelope to contain the exact applicable `policy_epoch` and `policy_hash`. New signing is permitted only with the active key for that generation. Verification requires the claimed policy to equal the policy applicable to the envelope generation and rejects revoked/untrusted keys or unknown future epochs.

## Startup behavior
When a policy-bound authenticator is supplied through the existing recovery-authenticator interface, invalid/tampered/rolled-back policy history makes authenticated recovery-chain verification fail. Historical proof restoration therefore fails closed while unrelated supervisory operation remains fail-open.

## Residual risk
V31 policy signatures use a separate HMAC shared secret, not asymmetric signatures or hardware-backed keys. Key-material storage, signed emergency revocation distribution, multi-authority quorum, and external trust-root provisioning remain future work.
