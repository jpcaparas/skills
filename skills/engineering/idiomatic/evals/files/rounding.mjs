// Synthetic standalone library. No framework, dependencies, network or storage.
// Public contract: preserve signed zero; round finite values to integer cents;
// throw RangeError for non-finite input. Consumers depend on those behaviours.
// This file is evidence for a read-only audit, not an invitation to migrate to TS.
export function toCents(value) {
  if (!Number.isFinite(value)) {
    throw new RangeError('amount must be finite');
  }
  return Math.round(value * 100);
}
