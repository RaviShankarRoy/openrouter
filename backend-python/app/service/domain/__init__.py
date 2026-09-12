"""Domain layer — pure business rules, no I/O, no framework dependencies.

This layer is deliberately small. The DRD describes a coordination platform,
not a heavy domain. Most invariants are around billing (atomic credit deduction),
key validity (expired/revoked), and budgets (hierarchy enforcement).
"""
