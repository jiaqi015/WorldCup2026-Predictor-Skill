# GitHub Presentation Assets

This directory contains the visual assets used by the repository's main
GitHub README. These files document the bundled predictor; they are not
required for Codex to load or run the Skill.

## Asset Inventory

| File | Recommended size | README role |
|---|---:|---|
| `banner.png` | 1280 x 640 | Repository hero image |
| `demo.gif` | 780 x 460 or similar | Short champion-reveal workflow |
| `screenshot-bracket.png` | Wide desktop capture | Full knockout bracket |
| `screenshot-poster.png` | 1080 x 1620 | Generated champion poster |
| `screenshot-leaderboard.png` | Wide desktop capture | Scorer and assist tables |
| `/og-image.png` | 1200 x 630 | Social sharing image; stored in repository root |

## Refresh Workflow

1. Launch the bundled Skill app:

   ```bash
   python3 \
     skills/world-cup-2026-predictor/scripts/serve_predictor.py \
     --port 8000
   ```

2. Complete all group and knockout matches.
3. Capture the bracket, champion poster, and leaderboard at a desktop width.
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
