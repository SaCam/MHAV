# MHAV Registration V2 – Phase 1B

- Logged-in members can select **only their own** existing dog profiles; selection reuses the profile and existing handler-dog combination.
- New dog details continue to be accepted. A guest or admin-on-behalf submission is **not** automatically matched to an existing dog by name or email: identity must first be verified.
- An optional second handler's **name** is stored on the application and shown to the administrator. It is not yet a verified second-handler account or displayed in trainer execution.
- Database migration `0019_courseapplication_second_handler_name.py` is required.
- Follow-up: add verified second-handler associations, explicit owner-vs-handler records, admin participant selection and profile-linking, and trainer visibility.

Run `python manage.py migrate`, `python manage.py check`, and `python manage.py test` on `feature/registration-v2`. Do not deploy this branch to production.
