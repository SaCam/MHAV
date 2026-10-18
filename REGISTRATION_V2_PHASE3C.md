# Registration V2 — Phase 3C (safe carry-forward)

This patch adds capacity-aware recommendations and a **manual administrator-triggered**
carry-forward action on the application detail page. It deliberately does not
run a background scheduler or automatically move applications unattended.

## Rules
- Only `earliest` and `flexible` applications without a confirmed enrollment
  or draft group are eligible.
- Never change a `specific` season request.
- Only future seasons with approved/open course offerings and planned groups
  with unreserved capacity are recommended.
- Existing confirmed enrollments and active draft proposals consume capacity.
- Recheck eligibility before changing the season.
- A carry-forward changes the associated season only; it does not confirm a place.
- No schema changes or migration.

## Limitations
Capacity is advisory until the final placement transaction. A subsequent
placement still must revalidate group capacity. This does not yet provide
scheduled/unattended carry-forward, email notifications or waitlist lifecycle
automation. A human initiates the action and verifies availability.

## Testing
`python manage.py check`
`python manage.py test apps.planning.tests_season_recommendations`
`python manage.py test`

Django tests were not executed in this environment.
