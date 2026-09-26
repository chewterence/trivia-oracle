# TriviaOracleBot 🎯

A Telegram group trivia bot built just for fun by **Terence Chew**. Questions are pulled live from the [qbreader](https://www.qbreader.org) quizbowl database and revealed sentence by sentence — buzz in by typing your answer before the clue runs out.

100% vibe coded. No regrets.

---

## Features

- Quizbowl tossups across dozens of categories (Literature, History, Science, Arts, Pop Culture, and more)
- Clues revealed one sentence at a time, answers judged by qbreader's answer checker
- Configurable categories, difficulty levels, timing, and scoring mode via `/configure`
- Combinable scoring modes (see [Scoring](#scoring))
- Persistent scoreboard across restarts
- Admin-only score reset

---

## Bot commands

| Command | Description |
|---------|-------------|
| `/next` | Start a new round |
| `/scores` | Show the current scoreboard |
| `/configure` | Configure timing, categories, difficulty, and scoring mode |

During a round, just type your answer in the chat.
Questions won't repeat in the same chat until 30 minutes pass without a successful `/next` starting a question.
This history is kept in memory and clears when the bot restarts.

---

## Scoring

By default every correct answer is worth **+10** and wrong answers cost nothing.
Under `/configure` → **🏆 Scoring Mode**, tick any combination of these modes, then press **💾 Save**:

| Mode | Effect |
|------|--------|
| **Wrong answers -1pt** | Every wrong answer costs 1 point |
| **Hourglass bonus** | A correct answer scores 10 × the ⏳ still showing (answer on ⏳⏳⏳⏳⏳ for 50) |
| **Medals get penalty** | Whoever holds 🥇🥈🥉 when the round starts loses 3 points per wrong answer |

Penalties stack: with both penalty modes on, a medal holder loses 4 points per wrong answer.
Changes take effect from the next round. Everyone who answers correctly gets credited,
even if several people answer at the same time.

---

## Running it yourself

### 1. Create a bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram, run `/newbot`, and copy the token it gives you.
Add the bot to your group. For it to see plain-text answers, either make it a group admin or turn
off privacy mode with `/setprivacy` in BotFather.

### 2. Configure it

The bot reads these settings from environment variables, falling back to a local `secrets.json`:

| Setting | Required | Description |
|---------|----------|-------------|
| `TELEGRAM_TOKEN` | Yes | Bot token from BotFather |
| `ADMIN_USERNAME` | No | Your Telegram username (without `@`). Unlocks **Admin Settings** in `/configure`. If unset, nobody is admin. |
| `SCORES_FILE` | No | Where to store scores. Default: `data/scores.md` |

For local runs, copy the example file and fill it in (`secrets.json` is gitignored):

```bash
cp secrets.example.json secrets.json
```

### 3a. Run with Docker (recommended)

A prebuilt `linux/amd64` image is on Docker Hub as `chewterence/trivia-oracle`.
The container only sees settings you pass in, so give it your secrets in one of two ways.

**Mount your `secrets.json`:**

```bash
docker run --rm --name trivia-container \
  -v "$(pwd)/secrets.json:/app/secrets.json:ro" \
  -v "$(pwd)/data:/app/data" \
  chewterence/trivia-oracle
```

**Or pass environment variables:**

```bash
docker run --rm --name trivia-container \
  -e TELEGRAM_TOKEN=your-bot-token \
  -e ADMIN_USERNAME=your_username \
  -v "$(pwd)/data:/app/data" \
  chewterence/trivia-oracle
```

The `data` mount keeps the scoreboard across container restarts. Secrets are passed at runtime
and are never baked into the image. If you see `TELEGRAM_TOKEN is not set`, the container
didn't get your secrets: check the mount path or the `-e` flags.

To keep it running on a server after you log out, swap `--rm` for
`-d --restart unless-stopped`, then use `docker logs -f trivia-container` to watch it.

**Building the image yourself.** Build for the architecture of the machine that will run it.
Most Linux servers are `linux/amd64` (`uname -m` prints `x86_64`); ARM servers need `linux/arm64`.

```bash
docker build --platform linux/amd64 -t trivia-oracle .
```

Use `trivia-oracle` in place of `chewterence/trivia-oracle` in the run commands above.

### 3b. Run with Python

Requires Python 3.9+ (python-telegram-bot 13.x doesn't support 3.13+).

```bash
pip install -r requirements.txt
python -m trivia_oracle
```

Only run one instance per bot token — a second instance will shut itself down.

### Running tests

```bash
python -m unittest discover tests
```

The tests fake Telegram and qbreader, so they need no token or network access.

---

## Project layout

```
trivia_oracle/        The bot (run with `python -m trivia_oracle`)
qbreader/             Vendored copy of the qbreader Python API wrapper (MIT)
tests/                Unit tests (python -m unittest discover tests)
assets/               Project images
Dockerfile            Container build
requirements.txt      Python dependencies
secrets.example.json  Template for local secrets.json
AGENTS.md             Architecture notes for contributors and AI coding agents
```

---

## Credits

- Questions and answer judging: [qbreader](https://www.qbreader.org) — please be gentle with their API.
- `qbreader/` is vendored from [qbreader/python-module](https://github.com/qbreader/python-module)
  (MIT License, © 2022 QBreader — see [qbreader/LICENSE](qbreader/LICENSE)), with one small patch: `Musicals` is mapped to Other Fine Arts in `_api_utils.py`.
- Built on [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) v13.
