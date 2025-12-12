import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

DEFAULT_BASE_URL = "http://localhost:8000"
CONFIG_PATH = Path.home() / ".docbot" / "config.json"


@dataclass
class CLIConfig:
    base_url: str = DEFAULT_BASE_URL
    token: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None


def load_config() -> CLIConfig:
    """Load CLI config from disk; return defaults if missing/invalid."""
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text())
            return CLIConfig(
                base_url=data.get("base_url", DEFAULT_BASE_URL),
                token=data.get("token"),
                email=data.get("email"),
                password=data.get("password"),
            )
    except Exception:
        pass
    return CLIConfig()


def save_config(cfg: CLIConfig) -> None:
    """Persist config to disk with 600 perms."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps(
            {
                "base_url": cfg.base_url,
                "token": cfg.token,
                "email": cfg.email,
                "password": cfg.password,
            },
            indent=2,
        )
    )
    CONFIG_PATH.chmod(0o600)
