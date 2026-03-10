---
name: clawbucket
description: Operate and extend the clawbucket Docker Swarm game-control dashboard. Use when working on swarm task controls, pair-game mechanics, task lifecycle actions (outage/self-destruct), Memcached-backed game state/events, UI controls in app.py, or stack deployment/debugging for clawbucket.
---

# clawbucket Skill

Implement, test, and ship changes for the clawbucket swarm game-control platform.

## Work Surface

- Edit primary app logic/UI in `app.py`.
- Edit game model/resolution logic in `game_engine.py`.
- Edit stack/runtime wiring in `docker-stack.yml` and `Dockerfile`.
- Treat `memcached` keys as shared source of truth for live state/event feeds.

## Core System Model

- Two swarm services (`clawbucket_clawbucket`, `clawbucket_clawbucket-b`) provide task pools.
- Tasks are the game actors.
- Pairing is cross-swarm and strictly two-task.
- Resolution may remove losers by killing task containers.
- Swarm reconciliation recreates tasks to desired replica count.

## API Areas

### Swarm / Task Operations

- `GET /api/swarms`
- `POST /api/scale`
- `POST /api/outage`
- `POST /api/self_destruct`

### Pair Game

- `GET /api/game/state`
- `POST /api/game/pair`
- `POST /api/game/unpair`
- `GET /api/game/chat`
- `POST /api/game/chat`
- `POST /api/game/move`
- `POST /api/game/resolve`

### Battle / Feed

- `GET /api/duel`
- `POST /api/duel/now`

## Implementation Rules

- Validate cross-swarm pairing and prevent double-pairing active tasks.
- Keep task actions idempotent and defensive (missing container/task is non-fatal).
- Persist shared state/events in Memcached with bounded history.
- Prefer explicit UI state labels (`none`, `paired`, winner/draw, locked/waiting).
- Keep destructive actions behind a user confirmation in the UI.

## Standard Change Workflow

1. Implement feature/fix in code.
2. Run syntax check:
   - `python3 -m py_compile app.py game_engine.py aggregator.py`
3. Build local image:
   - `docker build -t mallond/clawbucket:arm-agg-local .`
4. Deploy stack:
   - `docker stack deploy -c docker-stack.yml clawbucket`
5. If stale rollout persists, force refresh services or update image tag.
6. Verify via API (not just UI):
   - Pair creation/state, move resolution, and task disappearance after removal actions.
7. Commit with a focused message.
8. Push when requested.

## E2E Verification Checklist (Removal-Sensitive Changes)

- Confirm `/api/game/state` includes expected active pair.
- Submit deterministic moves (for predictable winner/loser).
- Confirm resolution contains expected `winner_task_id` and `eliminated_task_ids`.
- Poll `/api/swarms` and verify loser task ID disappears from running replicas.

## UI Conventions

- Show pairing state directly on each tile.
- Keep paired state visually distinct (red paired button).
- Display matchup line even when unpaired (`Matchup: none`).
- Keep controls fast and obvious for operator testing.

## Notes

- `README.md` is user-facing; `SKILL.md` is agent-operational.
- Prefer small, surgical edits over broad rewrites unless requested.
