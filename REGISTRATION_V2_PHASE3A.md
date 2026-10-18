# Registration V2 — Phase 3A

Adds applicant start preference and preserves the originally requested season separately from the current planning season. Existing season-specific applications are backfilled as `specific`. No automatic transfer, alternative-season offer, acceptance or notifications are implemented in this patch.

Install on `feature/registration-v2`; run `python manage.py migrate`, `python manage.py check`, `python manage.py test`. Keep production on `main`.
