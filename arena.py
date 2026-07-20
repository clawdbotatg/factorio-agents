"""Multi-agent Factorio arena runner.

Replaces `fle inspect-eval` (single-agent) with a custom loop over FLE's
multi-agent instance API: N agents in ONE world, each with its own character,
isolated Python namespace, model, and persona. Agents run in parallel threads,
so while one thinks another is acting — the world always has motion.

Run (resets the world state the instance connects to):
    FLE_SPECTATOR_MODE=1 uv run python arena.py

Config below. Requires ANTHROPIC_API_KEY in .env (metered API).
"""

import json
import os
import re
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("FLE_SPECTATOR_MODE", "1")  # never pause the world

import anthropic  # noqa: E402
from fle.env import FactorioInstance  # noqa: E402

# ---------------------------------------------------------------- config ----
# brain "claude-p": subscription-billed `claude -p` session (model = CLI model
#   alias, config_dir = a ~/.clawd-accounts/<name> login; each account is its
#   own rate-limit pool, so give parallel agents different accounts).
# brain "api": metered Anthropic API (model = API model id).
AGENTS = [
    {
        "name": "Factory One",
        "brain": "claude-p",
        "model": "opus",
        "accounts": ["~/.clawd-accounts/sub2", "~/.clawd-accounts/slop",
                     "~/.clawd-accounts/clawd", "~/.clawd-accounts/sub4"],
        "persona": (
            "You are FACTORY ONE, a solo master engineer. No partner, no "
            "coordination overhead - every step is yours. You are being "
            "compared against a two-agent team's hour: beat them."
        ),
    },
]

SHARED_GOAL = (
    "SPRINT: the human grades the factory after one hour. Fast mode is ON "
    "(instant moves/actions) - build at maximum scale, many entities per "
    "program. Hour targets in order: drills on all resources, power online, "
    "8-furnace smelting columns, ASSEMBLERS for gears/belts/inserters "
    "(phase-gate: by program ~20), belt lines connecting everything, then "
    "scale it all x2. Research is fully unlocked: go electric early. "
    "Narrate via send_message() for the spectator log. Check PLAN.md "
    "against targets constantly."
)

STEPS = 400               # think→act cycles per agent
STEP_TIMEOUT = 60         # seconds per code execution
MAX_HISTORY = 40          # messages kept per agent conversation
MIN_STEP_S = 8            # sprint pacing: maximize build rate
RCON = ("127.0.0.1", 27000)
LOG_DIR = Path(__file__).parent / "arena-logs"

# ARENA_CONFIG=<path.json> overrides any of: AGENTS, SHARED_GOAL, STEPS,
# MIN_STEP_S — the experiment runner uses this to A/B without code edits.
_cfg_path = os.environ.get("ARENA_CONFIG")
if _cfg_path:
    _cfg = json.loads(Path(_cfg_path).read_text())
    AGENTS = _cfg.get("agents", AGENTS)
    SHARED_GOAL = _cfg.get("shared_goal", SHARED_GOAL)
    STEPS = _cfg.get("steps", STEPS)
    MIN_STEP_S = _cfg.get("min_step_s", MIN_STEP_S)

# --------------------------------------------------------------- runtime ----
client = anthropic.Anthropic()
LOG_DIR.mkdir(exist_ok=True)
print_lock = threading.Lock()


def log(agent_name: str, kind: str, text: str):
    with print_lock:
        print(f"[{agent_name}] {kind}: {text[:200]}", flush=True)
    with open(LOG_DIR / f"{agent_name.replace(' ', '_').lower()}.jsonl", "a") as f:
        f.write(json.dumps({"ts": time.time(), "kind": kind, "text": text}) + "\n")


def extract_code(reply: str) -> str | None:
    blocks = re.findall(r"```(?:python)?\n(.*?)```", reply, re.S)
    return blocks[-1].strip() if blocks else None


class ClaudePBrain:
    """One persistent `claude -p` conversation, subscription-billed.

    The CLI session holds the conversation server-side (--resume), so we only
    send the newest observation each step. Env is scrubbed per the
    clawd-harness gotchas (CLAUDECODE / CLAUDE_CODE_* / ANTHROPIC_API_KEY
    leak into nested claude and flip it to embedded/metered mode).
    """

    def __init__(self, name: str, model: str, accounts: list, system: str):
        self.name = name
        self.model = model
        self.accounts = [os.path.expanduser(a) for a in accounts]
        self.acct_i = 0
        self.system = system
        self.session_id = None
        self.workdir = LOG_DIR / f"{name.replace(' ', '_').lower()}-workdir"
        self.workdir.mkdir(parents=True, exist_ok=True)

    def think(self, prompt: str) -> str:
        """Try the current account; on failure roll to the next (fresh
        session there — the prompt carries the latest observation, which is
        enough to keep playing). Mirrors the harness's hot account handoff."""
        last_err = None
        for attempt in range(len(self.accounts)):
            try:
                return self._call(prompt)
            except Exception as e:
                last_err = e
                old = Path(self.accounts[self.acct_i]).name
                self.acct_i = (self.acct_i + 1) % len(self.accounts)
                self.session_id = None  # fresh session on the new account
                log(self.name, "handoff",
                    f"{old} failed -> rolling to "
                    f"{Path(self.accounts[self.acct_i]).name}: {str(e)[:150]}")
        raise last_err

    def _call(self, prompt: str) -> str:
        import subprocess
        env = {k: v for k, v in os.environ.items()
               if k != "ANTHROPIC_API_KEY" and k != "CLAUDECODE"
               and not k.startswith("CLAUDE_CODE_")}
        env["CLAUDE_CONFIG_DIR"] = self.accounts[self.acct_i]
        # pure text brain: no Claude Code tools (a tool call would burn
        # turns and never yield the final answer), a few turns of headroom
        cmd = ["claude", "-p", prompt, "--output-format", "json",
               "--model", self.model, "--max-turns", "8",
               "--allowedTools", "Read,Write,Edit"]
        if self.session_id:
            cmd += ["--resume", self.session_id]
        else:
            cmd += ["--append-system-prompt", self.system]
        log(self.name, "prompt", prompt)
        t0 = time.time()
        out = subprocess.run(cmd, capture_output=True, text=True, env=env,
                             cwd=self.workdir, timeout=600)
        if out.returncode != 0:
            raise RuntimeError(
                f"claude -p failed rc={out.returncode}: "
                f"stdout={out.stdout[-300:]} stderr={out.stderr[:200]}")
        data = json.loads(out.stdout)
        self.session_id = data.get("session_id", self.session_id)
        usage = data.get("usage") or {}
        log(self.name, "metrics", json.dumps({
            "think_s": round(time.time() - t0, 1),
            "api_ms": data.get("duration_api_ms"),
            "turns": data.get("num_turns"),
            "in_tokens": usage.get("input_tokens"),
            "out_tokens": usage.get("output_tokens"),
            "cache_read": usage.get("cache_read_input_tokens"),
            "session_id": self.session_id,
        }))
        return data.get("result", "")


def one_shot_claude(model: str, accounts: list, prompt: str) -> str:
    """Single stateless claude -p call (used by the foreman/advisor)."""
    import subprocess
    env = {k: v for k, v in os.environ.items()
           if k != "ANTHROPIC_API_KEY" and k != "CLAUDECODE"
           and not k.startswith("CLAUDE_CODE_")}
    for acct in accounts:
        env["CLAUDE_CONFIG_DIR"] = os.path.expanduser(acct)
        try:
            out = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "json",
                 "--model", model, "--max-turns", "4", "--disallowedTools", "*"],
                capture_output=True, text=True, env=env, timeout=300)
            if out.returncode == 0:
                return json.loads(out.stdout).get("result", "")
        except Exception:
            continue
    return ""


def agent_loop(instance: FactorioInstance, idx: int, cfg: dict):
    if cfg.get("mode") == "skills":
        # LLM plans priorities; a scripted autopilot executes (skills.py)
        from skills import run_skills_agent
        return run_skills_agent(instance, idx, cfg, SHARED_GOAL,
                                ClaudePBrain, log, max_steps=STEPS)
    name = cfg["name"]
    system = (
        instance.get_system_prompt(idx)
        + "\n\n" + cfg["persona"] + "\n\n" + SHARED_GOAL
        + "\n\nYour project memory (CLAUDE.md) is a PLAYBOOK distilled from "
        "human speedruns — follow its phase build-order strictly.\n"
        "\nSTRATEGY DOCTRINE:\n"
        "- Think like a speedrunner: burner drills on iron + coal first, stone "
        "furnaces smelting immediately, then electricity (offshore pump -> "
        "boiler -> steam engine), then automate everything with assemblers "
        "and belts. Scale beats tidiness; throughput beats caution.\n"
        "- Write AMBITIOUS programs (20-60 lines) that complete a whole "
        "subgoal with verification (asserts) and fallbacks - one timid action "
        "per step wastes your life.\n"
        "- You have Read/Write/Edit file tools in your working directory: "
        "maintain PLAN.md (your build plan with locations + next 3 subgoals) "
        "and LESSONS.md (API mistakes you made and the correct form). Reread "
        "them when unsure; revise PLAN.md as the factory grows.\n"
        "- If a step errored, do not retry blindly: diagnose from the error, "
        "check LESSONS.md, simplify.\n"
        "\nAfter any file-tool use, ALWAYS end your reply with brief "
        "reasoning and ONE ```python``` code block to execute in the game. "
        "The world runs in REAL TIME while you think."
    )
    intro = ("You have just crash-landed. Look around, introduce "
             "yourself to your partner via send_message(), and begin.")
    brain = None
    if cfg.get("brain", "api") == "claude-p":
        brain = ClaudePBrain(name, cfg["model"], cfg["accounts"], system)
    messages = [{"role": "user", "content": intro}]
    for step in range(STEPS):
        try:
            if brain is not None:
                reply = brain.think(messages[-1]["content"])
            else:
                resp = client.messages.create(
                    model=cfg["model"],
                    max_tokens=8000,
                    system=[{"type": "text", "text": system,
                             "cache_control": {"type": "ephemeral"}}],
                    messages=messages,
                )
                reply = "".join(b.text for b in resp.content if b.type == "text")
        except Exception as e:
            log(name, "brain-error", str(e))
            time.sleep(20)
            continue

        messages.append({"role": "assistant", "content": reply})
        log(name, "thought", reply)

        code = extract_code(reply)
        if code is None:
            feedback = ("No ```python``` block found in your reply. Respond "
                        "with exactly one code block to execute.")
        else:
            log(name, "code", code)
            score, _goal, result = instance.eval(code, agent_idx=idx,
                                                 timeout=STEP_TIMEOUT)
            log(name, "result", str(result))
            try:
                ec = int(instance.rcon_client.send_command(
                    "/sc rcon.print(game.surfaces[1].count_entities_filtered{force='player'})"))
            except Exception:
                ec = None
            log(name, "score", json.dumps(
                {"step": step + 1, "score": score, "entities": ec}))
            obs = ""
            try:
                _, _, obs_out = instance.eval(
                    "print('INVENTORY:', inspect_inventory())\n"
                    "print('NEARBY:', get_entities(radius=30))",
                    agent_idx=idx, timeout=20)
                obs = f"\nCurrent state:\n```\n{str(obs_out)[:1200]}\n```"
            except Exception:
                pass
            adv = cfg.get("advisor")
            if adv and (step + 1) % adv.get("every", 8) == 0:
                recent = "\n".join(
                    m["content"][:400] for m in messages[-6:]
                    if isinstance(m.get("content"), str))
                advice = one_shot_claude(
                    adv["model"], adv["accounts"],
                    "You are a Factorio FOREMAN reviewing a worker agent's "
                    "recent progress. Their goal: build the largest scoring "
                    "factory (10 pts/entity + 1 pt/item crafted by machines). "
                    f"Recent activity:\n{recent}\n\nLatest result:\n"
                    f"{str(result)[:800]}\n\nGive 3 blunt, specific orders "
                    "for what to do next to maximize score. Be concrete "
                    "(what to build, where, how many).")
                if advice:
                    log(name, "advisor", advice)
                    feedback_advice = f"\n\nFOREMAN REVIEW (follow these orders):\n{advice[:1200]}"
                else:
                    feedback_advice = ""
            else:
                feedback_advice = ""
            goal_nudge = feedback_advice
            if (step + 1) % 8 == 0:
                goal_nudge += ("\nZOOM OUT: reread PLAN.md. Is the factory "
                               "actually growing? What would a speedrunner do "
                               "next? Update PLAN.md, then act at scale.")
            feedback = (f"Step {step + 1}/{STEPS} executed.\n"
                        f"Output:\n```\n{result}\n```\n"
                        f"Production score: {score}{obs}{goal_nudge}")

        step_started = time.time()
        messages.append({"role": "user", "content": feedback})
        # pacing: don't re-think instantly; deeper, cheaper decisions
        elapsed = time.time() - step_started
        if elapsed < MIN_STEP_S:
            time.sleep(MIN_STEP_S - elapsed)
        # bound history: keep first exchange + most recent
        if len(messages) > MAX_HISTORY:
            messages = messages[:2] + messages[-(MAX_HISTORY - 2):]
    log(name, "done", f"completed {STEPS} steps")


def main():
    n = len(AGENTS)
    print(f"Connecting A2AFactorioInstance (num_agents={n}) — this resets the world…")
    import asyncio
    from fle.env.a2a_instance import A2AFactorioInstance
    instance = asyncio.run(A2AFactorioInstance.create(
        address=RCON[0],
        tcp_port=RCON[1],
        num_agents=n,
        fast=True,   # SPRINT: instant actions, maximum build rate
        peaceful=True,
        # ARENA_KEEP_WORLD=1 -> relaunch without wiping what's been built
        clear_entities=not os.environ.get("ARENA_KEEP_WORLD"),
        reset_paused=False,
    ))
    print("Instance ready. Launching agent threads…")

    def render_loop():
        """Tier-2 live look: save a game-look PNG per agent every few seconds
        (FLE sprite renderer; needs `fle sprites` downloaded)."""
        rdir = LOG_DIR / "render"
        rdir.mkdir(exist_ok=True)
        while True:
            for i, cfg in enumerate(AGENTS):
                slug = cfg["name"].replace(" ", "_").lower()
                try:
                    img = instance.namespaces[i]._render(radius=24)
                    img.save(str(rdir / f"{slug}.tmp.png"))
                    (rdir / f"{slug}.tmp.png").rename(rdir / f"{slug}.png")
                except Exception:
                    pass
            time.sleep(6)

    threading.Thread(target=render_loop, daemon=True, name="render").start()
    threads = [
        threading.Thread(target=agent_loop, args=(instance, i, cfg),
                         daemon=True, name=cfg["name"])
        for i, cfg in enumerate(AGENTS)
    ]
    for i, t in enumerate(threads):
        t.start()
        time.sleep(20 * (i < len(threads) - 1))  # stagger the think-clocks
    label = os.environ.get("RUN_LABEL", time.strftime("run-%m%d-%H%M"))
    try:
        from scorecard import snapshot as sc_snap
        sc_snap(label + ":start")
    except Exception as e:
        print("scorecard start failed:", e)
    for t in threads:
        t.join()
    try:
        sc_snap(label + ":end")
    except Exception as e:
        print("scorecard end failed:", e)
    print("Arena run complete.")


if __name__ == "__main__":
    main()
