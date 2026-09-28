# Deploying StatScholar to Render + Neon (completely free, no expiry)

This deploys the backend and frontend as two services on
[Render](https://render.com) — using the `render.yaml` blueprint at the
repo root — with the database hosted separately on
[Neon](https://neon.tech). Both are genuinely free, no credit card
required on either, and neither one expires or gets deleted after a set
period (unlike Render's *own* free Postgres, which is deleted after 30
days — this is exactly why Neon is used instead).

## Step 1: Create your free Neon database (do this first)

1. Go to [neon.tech](https://neon.tech) and sign up (no credit card).
2. Click **New Project**. Give it a name (e.g. `statscholar`), pick a
   region close to you, leave the Postgres version at its default.
3. Once created, Neon shows you a **connection string** — a line
   starting with `postgresql://...`. Copy it. You'll paste this into
   Render in Step 3.
   - Neon shows two variants: a **pooled** one (hostname contains
     `-pooler`) and a **direct** one. Either works for this app; the
     pooled one is Neon's recommended default.

## Step 2: Push this repository to GitHub

Render deploys from a Git repository, not a zip file — see the main
README if you haven't done this yet.

## Step 3: Deploy the blueprint on Render

1. Go to [render.com](https://render.com) and sign up (no credit card).
2. **New → Blueprint**, connect your GitHub repo. Render reads
   `render.yaml` and shows two resources: the API web service and the
   frontend static site (no database — that's on Neon instead).
3. Click **Apply**. First deploy takes a few minutes.
4. Once `statscholar-api` is deployed, open its **Environment** tab and
   paste your Neon connection string as the value of
   `STATSCHOLAR_DATABASE_URL` (this variable is left blank in the
   blueprint on purpose, for you to fill in here). Save — this restarts
   the service with the real database connected.

## Step 4: Connect the two Render services to each other

1. Note the real URLs Render assigned to both services (visible in each
   service's dashboard page) — they'll be `https://statscholar-api.onrender.com`
   and `https://statscholar.onrender.com` if those exact names were
   available, or have a random suffix added if not.
2. On `statscholar-api`'s **Environment** tab, make sure
   `STATSCHOLAR_FRONTEND_BASE_URL` and `STATSCHOLAR_CORS_ORIGINS` match
   your frontend's real URL (`CORS_ORIGINS` as a JSON array string, e.g.
   `["https://statscholar-xyz123.onrender.com"]`).
3. On `statscholar`'s **Environment** tab, make sure `VITE_API_BASE_URL`
   matches your backend's real URL. Saving this triggers an automatic
   rebuild, since Vite bakes this value in at **build time**, not runtime.
4. Visit your frontend's URL. You should see the login screen.

## Caveats — read before relying on this for anything real

### Free services sleep after inactivity
Both Render free services spin down after ~15 minutes with no traffic,
and the next request takes 10–60 seconds to wake back up. Neon's free
compute also "scales to zero" similarly and wakes on the next query
(typically under a second). Fine for a demo you're actively showing
someone; noticeable on a "check back later" link.

### Neon's free tier storage limit
512 MB of storage on the free tier — plenty for accounts and CSV-sized
datasets at this app's scope, but worth knowing if you plan to upload
many large files over time.

### Email is still in dev mode until you configure SMTP
Verification and password-reset emails won't actually send until you set
`STATSCHOLAR_SMTP_HOST`, `STATSCHOLAR_SMTP_USERNAME`, and
`STATSCHOLAR_SMTP_PASSWORD` in the `statscholar-api` service's
environment variables (a Gmail account with an
[app password](https://support.google.com/accounts/answer/185833) works
for light use). Until then, verification/reset links appear in the
`statscholar-api` service's logs in the Render dashboard — same dev-mode
behavior as running locally. This part isn't free-vs-paid; it's just
optional either way.

### The JWT secret key
`render.yaml` already handles this correctly (`generateValue: true` makes
Render generate a real random secret for `STATSCHOLAR_SECRET_KEY`
automatically on deploy) — nothing for you to do here.
