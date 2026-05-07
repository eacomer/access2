Railway frontend URL
Railway backend URL
Custom domain targets
Required Railway variables
Backend startup command
Seeded demo users
Seeded demo patient IDs
E2E command
Expected E2E result: 5 passed, 2 skipped, 0 failed
Reason for skipped tests
Security reminder to rotate Railway public Postgres credentials

Custom domain validation:

Frontend:
https://access2.salvardata.com

Backend API:
https://api.salvardata.com/api/v1

Backend FRONTEND_ORIGIN:
https://access2.salvardata.com

E2E result:
5 passed, 2 skipped, 0 failed

Expected skips:
- Demo Patient 3 reviewer rejection through UI
- Demo Patient 4 superuser override approval through UI

Reason:
ACCESS2 V1 frontend audit panels are read-only; rejection and override approval are intentionally not exposed as frontend mutation controls.

Security cleanup:

The Railway Postgres password/connection string was rotated after troubleshooting.
The backend DATABASE_URL now uses the Railway internal Postgres host:
postgres.railway.internal:5432/railway

Post-rotation validation:
- Backend /health/live returned ok.
- Backend /health/ready returned ok with database=ok and redis=ok.
- E2E against https://access2.salvardata.com returned 5 passed, 2 skipped, 0 failed.