# GitHub README Assets

This directory contains the visual assets used by the repository's main GitHub
README plus the source-backed architecture notes linked from it. These files are
not required for Codex to load or run the Skill, but they are part of the public
project presentation and maintenance handoff.

## Asset Inventory

| File | README role |
|---|---|
| `readme-groups.jpg` | Group-stage and completed-result context |
| `readme-knockout.jpg` | Knockout bracket overview |
| `readme-stats.jpg` | Scorer and assist leaderboard |
| `readme-share.jpg` | Share poster and link modal |
| `/og-image.png` | Social sharing image; stored in repository root |

## Reference Documents

| File | Purpose |
|---|---|
| `domain-model.md` | Canonical domain entities and source boundaries |
| `prediction-architecture.md` | Prediction model and scoring architecture |
| `rag-corpus.md` | Kimi report corpus regeneration and retrieval rules |
| `vercel-deployment-guide.md` | Production route and deployment verification notes |

## Refresh Workflow

1. Launch the bundled Skill app:

   ```bash
   python3 \
     skills/world-cup-2026-predictor/scripts/serve_predictor.py \
     --port 8000
   ```

2. Complete all group and knockout matches.
3. Capture the group stage, bracket, stats, and share modal at a desktop width.
4. Keep screenshots free of browser chrome, personal data, and local file
   paths.
5. Replace only the corresponding files in this directory.
6. Open the GitHub README preview and check image sharpness, dimensions, and
   ordering.

## Content Rules

- Show the current UI shipped in the bundled Skill asset.
- Regenerate screenshots after visible layout or branding changes.
- Do not include copyrighted music, FIFA logos, or third-party broadcast
  footage.
- Keep the fan-project and non-affiliation positioning clear.
- Optimize large PNG and GIF files before committing when quality is preserved.
