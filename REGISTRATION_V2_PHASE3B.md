# Phase 3B — Alternative season proposal (first increment)

Specific-season applicants must accept an alternative by a signed, expiring (14 days) email link before the application season changes. The original requested season is retained. Flexible/earliest applications can be moved by an administrator without acceptance. The assignment and confirmation views reject unaccepted specific-season alternatives.

**Not yet implemented:** automated discovery/carry-forward to the next suitable season, full capacity-aware alternative recommendations, email retries and a comprehensive browser/security test suite. This patch is not production-ready.

Run `python manage.py migrate`, `python manage.py check`, and `python manage.py test`. Configure the email backend before testing delivery. Keep production on `main`.
