# Neon PostgreSQL Setup

Use Neon free tier for persistent MVP history on Render. This keeps diagnostic reports after Render redeploys or restarts.

## 1. Create Neon Account

1. Go to `https://neon.tech`.
2. Sign up or log in.
3. Create a new project.

## 2. Create Project and Database

During project setup:

- Choose a project name such as `lmx-device-certification`.
- Use the default branch, usually `main`.
- Use the default database, or create one named `lmx_certification`.

## 3. Copy Connection String

In the Neon console:

1. Open the project dashboard.
2. Click `Connect`.
3. Select the database and role.
4. Copy the connection string.

Use the SQLAlchemy-compatible URL format:

```text
postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

Neon may include extra parameters such as `channel_binding=require`; keep them if Neon provides them.

Example:

```text
postgresql://lmx_owner:password@ep-example-pooler.ap-southeast-1.aws.neon.tech/lmx_certification?sslmode=require&channel_binding=require
```

## 4. Add DATABASE_URL in Render

1. Open the Render backend service.
2. Go to `Environment`.
3. Add:

```text
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

4. Save changes.
5. Redeploy the backend.

Do not add `DATABASE_URL` to the dashboard static site. Only the backend uses it.

## 5. Verify Backend Uses Neon

After redeploy:

1. Open:

```text
https://device-certification-platform.onrender.com/health
```

2. Upload a diagnostic report from Android or POST the sample report.
3. Open the dashboard and confirm the device appears.
4. Redeploy the backend again.
5. Refresh the dashboard.

Expected result:

- Device history remains after redeploy.
- Diagnostic History still shows previous reports.

## 6. Local Development

No local database setup is required.

If `DATABASE_URL` is not set, the backend uses local SQLite:

```text
backend/lmx_certification.db
```

Optional local Postgres testing:

```powershell
$env:DATABASE_URL="postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require"
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Notes

- Keep the Neon connection string private.
- Neon stores history outside Render's ephemeral filesystem.
- SQLite is still useful locally, but should not be used on Render if you need persistent history.
- No Alembic migrations are used yet; tables are created automatically at startup for this MVP.

