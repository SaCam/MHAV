# Registration V2 — Phase 2B: finalization identity guard

Existing MHAV accounts can no longer be selected at enrollment finalization merely because a guest/admin applicant supplied the same email address. Such applications are blocked for manual identity verification. Applications already linked to a verified user can proceed if their account email matches.

Existing guest applications with no matching account continue to be finalized using the current placeholder-account workflow. No database migration is needed.

Run `python manage.py test apps.planning.tests_finalization_identity` and `python manage.py test` before committing. This patch does **not** yet implement a self-service account-claim flow for existing users, so matching guest applications will remain blocked until that workflow is implemented.
