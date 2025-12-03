# DocBot CLI

Typer-based CLI for interacting with the DocBot API (login, upload, status, search, chat).

Setup (from repo root):
```bash
pip install -r cli/requirements.txt
python -m cli.main --help
```

If you prefer to work inside `cli/`, you can now run:
```bash
python main --help          # uses cli/main wrapper
python main.py --help       # works too
```

Config is stored at `~/.docbot/config.json` (base URL + JWT token).

Seeded user helper:
- Login quickly with the seeded creds: `python -m cli.main login --use-default`
- Defaults: `admin@example.com` / `changeme123!`
