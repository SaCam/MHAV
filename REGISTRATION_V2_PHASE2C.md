# Registration V2 — Phase 2C

Administrator-assisted identity verification before attaching a guest or administrator application to an existing account.

- Requires administrator role, POST/CSRF, independently checked identity and a short audit reference.
- Matches exact account email and first/last name; rejects duplicate emails and conflicting handler/dog links.
- Records the verifier, verification time, method and reference. Do not enter identity document numbers or copies.
- Does not automatically match an email to an account.

**Important:** This is a manual verification mechanism, not an automated email-ownership verification flow. The administrator must genuinely verify identity independently. Account-ID is obtained through existing user administration.

Install on `feature/registration-v2`, then run `python manage.py makemigrations --check --dry-run`, `python manage.py migrate`, `python manage.py check`, `python manage.py test`.
