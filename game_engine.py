from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Literal, Optional, Tuple


GameMode = Literal["prisoners_dilemma", "ultimatum", "contract"]
PairStatus = Literal["paired", "negotiating", "locked", "resolved", "canceled"]


DEFAULT_SETTINGS: Dict[str, Any] = {
    "negotiation_seconds": 25,
    "timeout_policy": "auto_forfeit",  # auto_forfeit | no_move_draw
    "contract": {
        "target": "blue",
    },
    "ultimatum": {
        "pot": 10,
    },
}


@dataclass
class TaskRef:
    service: str
    task_id: str
    name: str
    slot: int


@dataclass
class PairMove:
    task_id: str
    move: Dict[str, Any]
    locked_at: str


@dataclass
class PairChatMessage:
    id: str
    from_task: str
    text: str
    at: str


@dataclass
class PairResolution:
    winner_task_id: Optional[str]
    loser_task_id: Optional[str]
    eliminated_task_ids: List[str]
    reason: str
    score_delta: Dict[str, int] = field(default_factory=dict)


@dataclass
class PairState:
    pair_id: str
    game: GameMode
    status: PairStatus
    task_a: TaskRef
    task_b: TaskRef
    created_at: str
    negotiation_deadline: str
    settings: Dict[str, Any] = field(default_factory=dict)
    proposer_task_id: Optional[str] = None
    moves: Dict[str, PairMove] = field(default_factory=dict)
    chat: List[PairChatMessage] = field(default_factory=list)
    resolved_at: Optional[str] = None
    resolution: Optional[PairResolution] = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str, seed: str) -> str:
    return hashlib.md5(f"{prefix}:{seed}".encode("utf-8")).hexdigest()[:12]


def _merge_settings(overrides: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    merged = {
        "negotiation_seconds": int(DEFAULT_SETTINGS["negotiation_seconds"]),
        "timeout_policy": DEFAULT_SETTINGS["timeout_policy"],
        "contract": dict(DEFAULT_SETTINGS["contract"]),
        "ultimatum": dict(DEFAULT_SETTINGS["ultimatum"]),
    }
    if not overrides:
        return merged

    for key in ("negotiation_seconds", "timeout_policy"):
        if key in overrides:
            merged[key] = overrides[key]

    for key in ("contract", "ultimatum"):
        if isinstance(overrides.get(key), dict):
            merged[key].update(overrides[key])

    merged["negotiation_seconds"] = max(5, min(300, int(merged["negotiation_seconds"])))
    if merged["timeout_policy"] not in {"auto_forfeit", "no_move_draw"}:
        merged["timeout_policy"] = "auto_forfeit"

    pot = int(merged["ultimatum"].get("pot", 10))
    merged["ultimatum"]["pot"] = max(2, min(100, pot))
    return merged


def _plus_seconds(iso_ts: str, seconds: int) -> str:
    start = datetime.fromisoformat(iso_ts)
    return datetime.fromtimestamp(start.timestamp() + seconds, tz=timezone.utc).isoformat()


def validate_pair(task_a: TaskRef, task_b: TaskRef, alive_task_ids: Optional[set[str]] = None, active_paired_task_ids: Optional[set[str]] = None) -> Tuple[bool, Optional[str]]:
    if not task_a.task_id or not task_b.task_id:
        return False, "task IDs are required"
    if task_a.task_id == task_b.task_id:
        return False, "pair must contain two different tasks"
    if task_a.service == task_b.service:
        return False, "pair must be cross-swarm"

    if alive_task_ids is not None:
        if task_a.task_id not in alive_task_ids or task_b.task_id not in alive_task_ids:
            return False, "both tasks must be alive"

    if active_paired_task_ids is not None:
        if task_a.task_id in active_paired_task_ids or task_b.task_id in active_paired_task_ids:
            return False, "task already paired"

    return True, None


def create_pair(task_a: TaskRef, task_b: TaskRef, game: GameMode, settings: Optional[Dict[str, Any]] = None, proposer_task_id: Optional[str] = None) -> PairState:
    now = utc_now_iso()
    merged = _merge_settings(settings)
    pair_id = _id("pair", f"{now}:{task_a.task_id}:{task_b.task_id}:{game}")
    deadline = _plus_seconds(now, int(merged["negotiation_seconds"]))

    if game == "ultimatum" and proposer_task_id not in {task_a.task_id, task_b.task_id}:
        proposer_task_id = task_a.task_id

    return PairState(
        pair_id=pair_id,
        game=game,
        status="negotiating",
        task_a=task_a,
        task_b=task_b,
        created_at=now,
        negotiation_deadline=deadline,
        settings=merged,
        proposer_task_id=proposer_task_id,
    )


def append_pair_chat(pair: PairState, from_task: str, text: str, max_messages: int = 80) -> PairChatMessage:
    text = (text or "").strip()
    if not text:
        raise ValueError("chat text is required")
    allowed = {pair.task_a.task_id, pair.task_b.task_id}
    if from_task not in allowed:
        raise ValueError("from_task must be one of the paired tasks")

    now = utc_now_iso()
    msg = PairChatMessage(
        id=_id("chat", f"{pair.pair_id}:{from_task}:{now}:{text}"),
        from_task=from_task,
        text=text[:400],
        at=now,
    )
    pair.chat.append(msg)
    pair.chat = pair.chat[-max_messages:]
    return msg


def lock_pair_move(pair: PairState, task_id: str, move: Dict[str, Any]) -> PairMove:
    if pair.status == "resolved":
        raise ValueError("pair already resolved")

    allowed = {pair.task_a.task_id, pair.task_b.task_id}
    if task_id not in allowed:
        raise ValueError("task_id must be one of the paired tasks")

    m = PairMove(task_id=task_id, move=move or {}, locked_at=utc_now_iso())
    pair.moves[task_id] = m

    if len(pair.moves) >= 2:
        pair.status = "locked"

    return m


def _parse_ts(iso_ts: str) -> datetime:
    return datetime.fromisoformat(iso_ts)


def _is_timeout(pair: PairState, now_iso: Optional[str] = None) -> bool:
    now = _parse_ts(now_iso) if now_iso else datetime.now(timezone.utc)
    return now >= _parse_ts(pair.negotiation_deadline)


def _resolve_pd(pair: PairState, move_a: str, move_b: str) -> PairResolution:
    a_id, b_id = pair.task_a.task_id, pair.task_b.task_id
    legal = {"cooperate", "betray"}
    if move_a not in legal or move_b not in legal:
        return PairResolution(None, None, [], "invalid_move_payload")

    if move_a == "cooperate" and move_b == "cooperate":
        return PairResolution(None, None, [], "mutual_cooperate", {a_id: 1, b_id: 1})
    if move_a == "betray" and move_b == "cooperate":
        return PairResolution(a_id, b_id, [b_id], "betray_vs_cooperate", {a_id: 2, b_id: -1})
    if move_a == "cooperate" and move_b == "betray":
        return PairResolution(b_id, a_id, [a_id], "cooperate_vs_betray", {a_id: -1, b_id: 2})

    # both betray -> both removed (harsh mode)
    return PairResolution(None, None, [a_id, b_id], "mutual_betray", {a_id: -2, b_id: -2})


def _resolve_ultimatum(pair: PairState, move_a: Dict[str, Any], move_b: Dict[str, Any]) -> PairResolution:
    a_id, b_id = pair.task_a.task_id, pair.task_b.task_id
    proposer = pair.proposer_task_id or a_id
    responder = b_id if proposer == a_id else a_id

    proposer_move = move_a if proposer == a_id else move_b
    responder_move = move_b if proposer == a_id else move_a

    pot = int(pair.settings.get("ultimatum", {}).get("pot", 10))
    offer = proposer_move.get("offer_to_other")
    accept = responder_move.get("accept")

    if not isinstance(offer, int) or offer < 0 or offer > pot or not isinstance(accept, bool):
        return PairResolution(None, None, [], "invalid_move_payload")

    if accept:
        proposer_gain = pot - offer
        responder_gain = offer
        return PairResolution(None, None, [], "offer_accepted", {proposer: proposer_gain, responder: responder_gain})

    # rejected offer: proposer eliminated
    return PairResolution(responder, proposer, [proposer], "offer_rejected", {proposer: -pot, responder: 0})


def _resolve_contract(pair: PairState, move_a: Dict[str, Any], move_b: Dict[str, Any]) -> PairResolution:
    a_id, b_id = pair.task_a.task_id, pair.task_b.task_id
    target = str(pair.settings.get("contract", {}).get("target", "blue")).lower()

    a_choice = str(move_a.get("choice", "")).lower()
    b_choice = str(move_b.get("choice", "")).lower()

    if not a_choice or not b_choice:
        return PairResolution(None, None, [], "invalid_move_payload")

    if a_choice == target and b_choice == target:
        return PairResolution(None, None, [], "contract_met", {a_id: 2, b_id: 2})

    if a_choice == b_choice:
        # coordinated, but wrong contract target
        return PairResolution(None, None, [], "coordinated_wrong_target", {a_id: 0, b_id: 0})

    # failed coordination: both take penalty, lower lexical choice loses for determinism
    loser = a_id if a_choice < b_choice else b_id
    winner = b_id if loser == a_id else a_id
    return PairResolution(winner, loser, [loser], "contract_broken", {a_id: -1, b_id: -1})


def maybe_resolve_pair(pair: PairState, now_iso: Optional[str] = None) -> Optional[PairResolution]:
    if pair.status == "resolved":
        return pair.resolution

    a_id, b_id = pair.task_a.task_id, pair.task_b.task_id
    a_move = pair.moves.get(a_id)
    b_move = pair.moves.get(b_id)

    timed_out = _is_timeout(pair, now_iso)
    both_locked = bool(a_move and b_move)
    if not both_locked and not timed_out:
        return None

    if not both_locked and timed_out:
        policy = pair.settings.get("timeout_policy", "auto_forfeit")
        if policy == "no_move_draw":
            res = PairResolution(None, None, [], "timeout_draw", {a_id: 0, b_id: 0})
        else:
            if a_move and not b_move:
                res = PairResolution(a_id, b_id, [b_id], "timeout_forfeit", {a_id: 1, b_id: -1})
            elif b_move and not a_move:
                res = PairResolution(b_id, a_id, [a_id], "timeout_forfeit", {a_id: -1, b_id: 1})
            else:
                res = PairResolution(None, None, [a_id, b_id], "double_timeout_forfeit", {a_id: -1, b_id: -1})
        pair.resolution = res
        pair.status = "resolved"
        pair.resolved_at = utc_now_iso()
        return res

    if pair.game == "prisoners_dilemma":
        res = _resolve_pd(pair, str(a_move.move.get("choice", "")).lower(), str(b_move.move.get("choice", "")).lower())
    elif pair.game == "ultimatum":
        res = _resolve_ultimatum(pair, a_move.move, b_move.move)
    else:
        res = _resolve_contract(pair, a_move.move, b_move.move)

    pair.resolution = res
    pair.status = "resolved"
    pair.resolved_at = utc_now_iso()
    return res


def pair_to_dict(pair: PairState) -> Dict[str, Any]:
    return asdict(pair)


def pair_from_dict(data: Dict[str, Any]) -> PairState:
    task_a = TaskRef(**data["task_a"])
    task_b = TaskRef(**data["task_b"])

    moves: Dict[str, PairMove] = {}
    for task_id, mv in (data.get("moves") or {}).items():
        moves[task_id] = PairMove(**mv)

    chat = [PairChatMessage(**m) for m in (data.get("chat") or [])]

    resolution = None
    if data.get("resolution"):
        resolution = PairResolution(**data["resolution"])

    return PairState(
        pair_id=data["pair_id"],
        game=data["game"],
        status=data["status"],
        task_a=task_a,
        task_b=task_b,
        created_at=data["created_at"],
        negotiation_deadline=data["negotiation_deadline"],
        settings=data.get("settings") or {},
        proposer_task_id=data.get("proposer_task_id"),
        moves=moves,
        chat=chat,
        resolved_at=data.get("resolved_at"),
        resolution=resolution,
    )
