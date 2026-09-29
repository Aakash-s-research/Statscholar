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

### Real email requires Brevo, not SMTP — on Render's free tier

Until you configure this, verification/reset links appear in the
`statscholar-api` service's Logs tab in the Render dashboard, instead of
actually being emailed — same dev-mode behavior as running locally.

**Render's free web services block outbound traffic on SMTP ports
(25/465/587)** as a platform policy (in effect since September 2025) —
this isn't fixable by entering different SMTP credentials, it's blocked
at the network level regardless of what's correct or not. Gmail's SMTP
server (or any SMTP server) simply cannot be reached from a free Render
service. SMTP works fine locally, and works on a paid Render plan, but
not on the free tier.

For real email on the free tier, use **Brevo** instead — it sends over
HTTPS, which Render's block doesn't touch. Free forever, 300 emails/day,
no card required:

1. Go to [brevo.com](https://www.brevo.com), sign up (no card).
2. In your Brevo dashboard, go to **SMTP & API** settings → **API Keys**
   tab → **Generate a new API key**. Name it anything, copy the key shown
   (Brevo only displays it once).
3. In Render, open `statscholar-api` → **Environment**, and set:
   - `STATSCHOLAR_BREVO_API_KEY` to the key you just copied
   - `STATSCHOLAR_BREVO_SENDER_EMAIL` to an email address you control
     (Brevo may ask you to verify this sender address the first time)
4. Save. The backend restarts, and Brevo takes over automatically —
   nothing else to configure, and the SMTP variables can stay empty.

If `STATSCHOLAR_BREVO_API_KEY` is set, the app uses Brevo automatically
and ignores the SMTP variables entirely. If a Brevo send ever fails (bad
key, hit the daily limit), the app logs the error and falls back to the
same dev-mode logging — signup/reset still work, you'd just need to check
the Logs tab for that one link instead.

### The JWT secret key
`render.yaml` already handles this correctly (`generateValue: true` makes
Render generate a real random secret for `STATSCHOLAR_SECRET_KEY`
automatically on deploy) — nothing for you to do here.
