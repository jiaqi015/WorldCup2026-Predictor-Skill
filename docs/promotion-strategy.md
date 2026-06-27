# GitHub Growth Strategy

This document keeps promotion useful and non-spammy. The goal is to help people who are already looking for a 2026 World Cup predictor, bracket simulator, football model benchmark, or Codex skill example.

## Positioning

One-line pitch:

> A no-login 2026 FIFA World Cup predictor with a full 48-team bracket, scorer simulation, ESPN-backed result checks, shareable posters, and an installable Codex skill.

Short description for GitHub:

```text
2026 FIFA World Cup predictor: 48-team bracket simulator, live ESPN results, shareable poster, Codex skill
```

Primary promise:

- Fans can open the live demo, simulate the full tournament, and share a read-only bracket.
- Developers can inspect a static app with serious data lineage, tests, and release gates.
- Agent builders can study a real Codex skill that launches, scores, validates, and maintains the app.

## Search Surface

Repository description, topics, README first screen, headings, image alt text, and docs should naturally include these phrases:

- 2026 FIFA World Cup predictor
- World Cup 2026 bracket simulator
- FIFA World Cup bracket predictor
- world cup prediction game
- tournament bracket simulator
- football prediction model
- ESPN soccer scoreboard
- Codex skill example

Current recommended GitHub topics:

```text
world-cup-2026
fifa-world-cup
world-cup
soccer
football
predictor
bracket
tournament-bracket
simulation
static-site
codex-skill
espn
```

## GitHub Conversion Loop

1. First screen: explain the product in one sentence, show the current UI, and link the live demo.
2. Proof: show screenshots, feature list, validation commands, and real data caveats.
3. Action: make star, fork, issue, and contribution paths obvious.
4. Return loop: keep live-result freshness, README screenshots, and release notes current during tournament windows.

## Audience Routes

| Audience | What they care about | Best proof |
| --- | --- | --- |
| Football fans | Fast bracket play and shareable results | Live demo, screenshots, poster, no login |
| Bracket builders | Official 2026 topology and third-place placement | Bracket docs, tests, topology checks |
| Data/model people | Reproducible assumptions and benchmarkable output | prediction architecture, RAG corpus, release checks |
| Codex users | Real skill behavior, not just a prompt list | SKILL.md, playbooks, validator, install commands |
| Chinese users | Clear usage and local-language flow | Chinese README section and bilingual UI |

## Ethical Outreach

Do:

- Open a precise issue or PR when you find a real bug in another 2026 bracket project.
- Mention this repo only when it directly answers a question or provides a reusable reference.
- Lead with the useful observation, then add one short optional link.
- Compare concrete behavior: bracket topology, share links, scorer modeling, validation, or ESPN mapping.

Do not:

- Post generic "check out my repo" comments.
- Comment only to place a link.
- Hijack unrelated football, betting, or model discussions.
- Claim live betting odds or official FIFA affiliation.

## Outreach Templates

Use these only when the surrounding issue or discussion is directly relevant.

### Bracket Topology Reference

```text
I ran into the same 2026 Round-of-32 placement issue while building a bracket simulator. The tricky part for me was keeping third-place slots explicit instead of flattening them too early.

If useful, this implementation has tests around the 2026 bracket topology and third-place placement:
https://github.com/jiaqi015/WorldCup2026-Predictor-Skill
```

### ESPN Mapping Reference

```text
One thing to watch with ESPN soccer payloads: team names and event details can drift separately from score status. I ended up normalizing ESPN result checks behind a small contract and testing mapping failures explicitly.

Reference if helpful:
https://github.com/jiaqi015/WorldCup2026-Predictor-Skill
```

### Codex Skill Example

```text
For anyone looking for a concrete Codex skill example, this repo packages a browser app plus scripts for launch, live-result checks, scoring, freshness checks, and release validation:
https://github.com/jiaqi015/WorldCup2026-Predictor-Skill
```

## Maintenance Rhythm

During tournament windows:

1. Refresh ESPN-backed results and match details.
2. Run `python3 scripts/release_check.py`.
3. Regenerate README screenshots after visible UI changes.
4. Push a short release note when user-facing behavior changes.
5. Verify `https://www.cameraclaw.cn/2026` before announcing the update.

