# scientific-illustration (for any coding agent)

This folder is an Agent Skill. It works with any model and any harness that can read files and run shell commands
(Claude Code, Codex CLI, Gemini CLI, Cursor, Copilot, OpenCode, Aider, Cline and others).

1. Read `SKILL.md` first and follow it. Read files under `references/` only when SKILL.md points to them.
2. Everything is plain command-line tools: `python scripts/<name>.py ...` and `node`/`npx` for 3D and video.
   Nothing needs a Claude-specific tool. If your harness cannot show images, open the rendered PNG files in the user's viewer instead of looking at them.
3. Run `python scripts/setup_check.py` once to see which dependencies are missing.
4. Install locations: copy or link this folder to your harness's skills folder (`~/.claude/skills/`, `~/.codex/skills/`, `~/.gemini/skills/`, `.agents/skills/`),
   or just point the agent at this file.
