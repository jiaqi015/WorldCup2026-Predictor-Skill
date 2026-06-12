# Optional Local Audio

The predictor includes background-music controls, but the repository and Codex
Skill intentionally ship without audio files.

This keeps the project:

- legally safer for public GitHub distribution;
- small enough to clone and install quickly;
- usable without media licenses or external audio services.

## Enable Audio In The Root Web App

Add audio files you have the right to use:

```text
assets/music-1.mp3
assets/music-2.mp3
assets/music-3.mp3
assets/music-4.mp3
```

Supported local formats include MP3, WAV, M4A, and OGG. These files are ignored
by Git and must not be committed.

## Enable Audio In The Skill App

In this source repository, the Skill serves its bundled application from:

```text
skills/world-cup-2026-predictor/assets/predictor/
```

For a local-only source checkout, place licensed tracks under:

```text
skills/world-cup-2026-predictor/assets/predictor/assets/
```

Use the same `music-1` through `music-4` filenames. Keep these files local and
out of commits.

Audio is optional. If no files are present, the predictor displays a short
notice and every prediction, scoring, sharing, and validation feature continues
to work.
