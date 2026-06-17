# World Cup 2026 Demo Vercel Deployment Guide

This document records the actual deployment shape for this repository. Follow it literally when another model or engineer needs to redeploy the demo.

## Short Answer

- GitHub repo: `https://github.com/jiaqi015/WorldCup2026-Predictor-Skill`
- Local repo path: `/Users/jiaqi/Documents/FIFA 26`
- Demo Vercel project: `world-cup-2026-demo`
- Demo Vercel project ID: `prj_qzcOzoyZGfFno1U9GdsFXkVf35BF`
- Vercel owner/team: `jiaqis-projects-c634fd33`
- Public origin domain / production custom alias: `https://worldcup-origin.cameraclaw.cn`
- Public user URL: `https://www.cameraclaw.cn/2026`
- Public domain owner project: `ai-image-workshop`
- `www.cameraclaw.cn` is not directly bound to the demo project. It belongs to `ai-image-workshop`, which routes `/2026` to the public origin domain.

## Deployment Truth

There are two Vercel projects involved.

1. `world-cup-2026-demo`

   This is the independent static demo project linked from this directory via `.vercel/project.json`.

   ```json
   {
     "projectId": "prj_qzcOzoyZGfFno1U9GdsFXkVf35BF",
     "orgId": "team_9GNanVcNnMhytR1TP8zPmvpF",
     "projectName": "world-cup-2026-demo"
   }
   ```

2. `ai-image-workshop`

   This owns `www.cameraclaw.cn`. Vercel domains are host-based, not path-based, so `www.cameraclaw.cn/2026` cannot be attached directly to `world-cup-2026-demo`. The path has to be routed by the project that owns `www.cameraclaw.cn`.

The deployed `/2026` page is therefore:

```text
Browser
  -> https://www.cameraclaw.cn/2026
  -> Vercel project: ai-image-workshop
  -> /2026 project routes
  -> https://worldcup-origin.cameraclaw.cn
  -> Vercel project: world-cup-2026-demo
  -> current demo HTML
```

The custom origin domain is intentional. The default `*.vercel.app` production
alias is protected by Vercel Authentication for this team, while custom domains
remain public. Rewriting the parent site to the protected alias can leave a
cached HTML page working while uncached images return 404.

The live project routes on `ai-image-workshop` must be:

```text
World Cup 2026 Demo Root
  source: /2026
  syntax: equals
  destination: https://worldcup-origin.cameraclaw.cn/

World Cup 2026 Demo Assets
  source: ^/2026/(.*)$
  syntax: regex
  destination: https://worldcup-origin.cameraclaw.cn/$1
```

Use the regex capture form for the asset route. The earlier
`/2026/:path* -> .../:path*` project route matched requests but did not forward
the captured path correctly, causing all nested static assets to return 404.

## Important Behavior

`vercel --prod` from `/Users/jiaqi/Documents/FIFA 26` deploys the current local working tree to `world-cup-2026-demo`.

It is not the same as "push GitHub and let Vercel auto deploy." If the working tree has uncommitted changes, those changes can go live through the CLI deployment.

Before deploying, always run:

```bash
cd "/Users/jiaqi/Documents/FIFA 26"
git status --short --branch
```

If there are uncommitted files, decide deliberately whether they should be included in the deployment.

## One-Command Redeploy

Use this when the local working tree is exactly what should go live:

```bash
cd "/Users/jiaqi/Documents/FIFA 26"
vercel --prod --yes
```

Expected CLI shape:

```text
Deploying jiaqis-projects-c634fd33/world-cup-2026-demo
Production: https://world-cup-2026-demo-<hash>-jiaqis-projects-c634fd33.vercel.app
Aliased: https://worldcup-origin.cameraclaw.cn
```

The unique deployment URL changes every deployment. The stable alias should remain:

```text
https://worldcup-origin.cameraclaw.cn
```

The public URL should remain:

```text
https://www.cameraclaw.cn/2026
```

## Verify Project Wiring

Run:

```bash
cd "/Users/jiaqi/Documents/FIFA 26"
vercel project inspect world-cup-2026-demo
```

Expected facts:

```text
Found Project jiaqis-projects-c634fd33/world-cup-2026-demo
ID: prj_qzcOzoyZGfFno1U9GdsFXkVf35BF
Framework Preset: Other
Root Directory: .
```

Then verify the domain owner:

```bash
vercel domains inspect www.cameraclaw.cn
```

Expected facts:

```text
Domain www.cameraclaw.cn found under jiaqis-projects-c634fd33
Project: ai-image-workshop
Domain: www.cameraclaw.cn
Nameservers: ns1.vercel-dns.com, ns2.vercel-dns.com
```

Verify both project routes:

```bash
VERCEL_PROJECT_ID=prj_ebkuBLBd5BHFWgiVjX9oVZ7BmiAL \
VERCEL_ORG_ID=team_9GNanVcNnMhytR1TP8zPmvpF \
vercel routes list --expand
```

## Verify Latest Deployment

List recent deployments:

```bash
cd "/Users/jiaqi/Documents/FIFA 26"
vercel ls world-cup-2026-demo
```

Inspect a specific deployment:

```bash
vercel inspect https://world-cup-2026-demo-<hash>-jiaqis-projects-c634fd33.vercel.app
```

Expected facts:

```text
name: world-cup-2026-demo
target: production
status: Ready
Aliases:
  https://worldcup-origin.cameraclaw.cn
```

## Verify Public URL

Run:

```bash
curl -I -L --max-time 20 https://www.cameraclaw.cn/2026
```

Expected:

```text
HTTP/2 200
server: Vercel
content-type: text/html; charset=utf-8
```

Then verify the body is the World Cup demo:

```bash
curl -L --max-time 20 https://www.cameraclaw.cn/2026 \
  | rg "2026 世界杯|var GD=|var PHOTO_MAP="
```

Expected markers:

```text
2026 世界杯
var GD=
var PHOTO_MAP=
var ACTUAL_RESULTS=
var MATCH_DETAILS=
760433
Lionel Messi
Rodrigo De Paul
Nico González
```

Run the repository's public deployment check. It verifies the HTML plus
representative ESPN, SOFIFA, and SVG player images through the real `/2026`
route:

```bash
python3 scripts/verify_public_deployment.py
```

For high-signal release proof, also compare the public route body with the
local canonical app:

```bash
curl -fsSL --max-time 30 https://www.cameraclaw.cn/2026 -o /tmp/wc26-public.html
shasum -a 256 index.html /tmp/wc26-public.html
```

The two hashes should match immediately after a production deploy. If they do
not match, treat the public route as stale even if the Vercel CLI reported a
successful deployment.

## Common Mistakes

- Do not try to attach `www.cameraclaw.cn/2026` as a Vercel domain. Vercel domains are hostnames, not paths.
- Do not move `www.cameraclaw.cn` from `ai-image-workshop` to `world-cup-2026-demo`; that can break the main site.
- Do not assume GitHub push equals production deployment. This project has been deployed by Vercel CLI from the local working tree.
- Do not commit `.vercel/`. It contains local Vercel project linking metadata and should stay ignored.
- Do not delete the `ai-image-workshop` route for `/2026`; that route is why the public URL works.
- Do not point the parent routes back to the protected `*.vercel.app` alias.
- Do not replace the regex asset route with `/2026/:path*`; nested assets must preserve the captured path.

## Safe Redeploy Checklist

1. Check local state.

   ```bash
   cd "/Users/jiaqi/Documents/FIFA 26"
   git status --short --branch
   ```

2. Confirm this directory is linked to the demo project.

   ```bash
   vercel project inspect world-cup-2026-demo
   ```

3. Deploy.

   ```bash
   vercel --prod --yes
   ```

4. Confirm the deployment is Ready.

   ```bash
   vercel ls world-cup-2026-demo
   ```

5. Confirm the public path works.

   ```bash
   python3 scripts/verify_public_deployment.py
   ```

6. If README, share links, or QR URLs changed, make sure they still point to:

   ```text
   https://www.cameraclaw.cn/2026
   ```
