import json
import sys
import uuid
from pathlib import Path
from typing import List, Optional

import httpx
import typer
from rich.console import Console
from rich.markdown import Markdown

try:  # Allow running as `python -m cli.main` or `python cli/main.py`
    from .config import CLIConfig, load_config, save_config
except ImportError:
    sys.path.append(str(Path(__file__).resolve().parent))
    from config import CLIConfig, load_config, save_config

app = typer.Typer(help="DocBot CLI")
console = Console()
DEFAULT_EMAIL = "admin@example.com"
DEFAULT_PASSWORD = "changeme123!"
TIMEOUT = 180.0


def get_client(base_url: str, token: Optional[str]) -> httpx.Client:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=base_url, headers=headers, timeout=TIMEOUT)


def print_json(data) -> None:
    typer.echo(json.dumps(data, indent=2, default=str))


def resolve_config(base_url: Optional[str], token: Optional[str]) -> CLIConfig:
    cfg = load_config()
    if base_url:
        cfg.base_url = base_url
    if token:
        cfg.token = token
    return cfg


def request_token(base_url: str, email: str, password: str) -> str:
    """Perform login against the API and return the access token."""
    with httpx.Client(base_url=base_url, timeout=TIMEOUT) as client:
        resp = client.post(
            "/v1/auth/jwt/login",
            data={"username": email, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            typer.echo(f"Login failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        token = resp.json().get("access_token")
        if not token:
            typer.echo("Login response missing access_token", err=True)
            raise typer.Exit(code=1)
        return token


def login_default_if_needed(cfg: CLIConfig, base_url: Optional[str], use_default: bool) -> CLIConfig:
    """Login with default seeded credentials and persist token when requested."""
    if not use_default:
        return cfg
    target_base = base_url or cfg.base_url
    token = request_token(target_base, DEFAULT_EMAIL, DEFAULT_PASSWORD)
    cfg.base_url = target_base
    cfg.token = token
    save_config(cfg)
    typer.echo(f"Logged in with default user: {DEFAULT_EMAIL}")
    return cfg


@app.command()
def login(
    email: Optional[str] = typer.Option(
        None, prompt=True, help="Login email (use --use-default for seeded user)"
    ),
    password: Optional[str] = typer.Option(
        None, prompt=True, hide_input=True, help="Password (use --use-default for seeded user)"
    ),
    use_default: bool = typer.Option(False, help="Use default seeded credentials"),
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
):
    """Login and store the JWT token."""
    if use_default:
        email = DEFAULT_EMAIL
        password = DEFAULT_PASSWORD
        typer.echo(f"Using default seeded credentials: {email}")

    if not email or not password:
        typer.echo("Email and password are required.", err=True)
        raise typer.Exit(code=1)

    cfg = resolve_config(base_url, None)
    token = request_token(cfg.base_url, email, password)
    cfg.token = token
    save_config(cfg)
    typer.echo("Login successful; token saved.")


@app.command()
def upload(
    pdf_path: Path = typer.Argument(..., exists=True, readable=True),
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
    token: Optional[str] = typer.Option(None, help="Override token"),
):
    """Upload a PDF; returns document_id."""
    cfg = resolve_config(base_url, token)
    with get_client(cfg.base_url, cfg.token) as client, pdf_path.open("rb") as f:
        files = {"file": (pdf_path.name, f, "application/pdf")}
        resp = client.post("/v1/documents:upload", files=files)
        if resp.status_code != 202:
            typer.echo(f"Upload failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        print_json(resp.json())


@app.command()
def status(
    document_id: uuid.UUID,
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
    token: Optional[str] = typer.Option(None, help="Override token"),
):
    """Fetch document status/metadata."""
    cfg = resolve_config(base_url, token)
    with get_client(cfg.base_url, cfg.token) as client:
        resp = client.get(f"/v1/documents/{document_id}")
        if resp.status_code != 200:
            typer.echo(f"Status failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        print_json(resp.json())


@app.command("search-text")
def search_text(
    query: str = typer.Argument(...),
    document_ids: List[uuid.UUID] = typer.Option(None, "--doc", help="Document ID(s) to filter"),
    top_k: int = typer.Option(10, help="Number of results"),
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
    token: Optional[str] = typer.Option(None, help="Override token"),
):
    """Semantic/hybrid text search."""
    cfg = resolve_config(base_url, token)
    payload = {"query": query, "top_k": top_k}
    if document_ids:
        payload["document_ids"] = document_ids
    with get_client(cfg.base_url, cfg.token) as client:
        resp = client.post("/v1/search/text", json=payload)
        if resp.status_code != 200:
            typer.echo(f"Search failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        print_json(resp.json())


@app.command("search-image")
def search_image(
    query_text: str = typer.Argument(..., help="Caption/text query"),
    top_k: int = typer.Option(10, help="Number of results"),
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
    token: Optional[str] = typer.Option(None, help="Override token"),
):
    """Caption-based image search."""
    cfg = resolve_config(base_url, token)
    payload = {"query_text": query_text, "top_k": top_k}
    with get_client(cfg.base_url, cfg.token) as client:
        resp = client.post("/v1/search/image", json=payload)
        if resp.status_code != 200:
            typer.echo(f"Search failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        print_json(resp.json())


@app.command("search-table")
def search_table(
    query: str = typer.Argument(...),
    top_k: int = typer.Option(10, help="Number of results"),
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
    token: Optional[str] = typer.Option(None, help="Override token"),
):
    """Semantic table search."""
    cfg = resolve_config(base_url, token)
    payload = {"query": query, "top_k": top_k}
    with get_client(cfg.base_url, cfg.token) as client:
        resp = client.post("/v1/search/table", json=payload)
        if resp.status_code != 200:
            typer.echo(f"Search failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        print_json(resp.json())


@app.command("chat-create")
def chat_create(
    title: Optional[str] = typer.Option(None, help="Chat title"),
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
    token: Optional[str] = typer.Option(None, help="Override token"),
    use_default: bool = typer.Option(False, help="Login with default seeded user before request"),
):
    """Create a chat."""
    cfg = resolve_config(base_url, token)
    cfg = login_default_if_needed(cfg, base_url, use_default)
    payload = {"title": title} if title else {}
    with get_client(cfg.base_url, cfg.token) as client:
        resp = client.post("/v1/chats", json=payload)
        if resp.status_code != 201:
            typer.echo(f"Chat create failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        print_json(resp.json())


@app.command("chat-send")
def chat_send(
    chat_id: uuid.UUID,
    message: str = typer.Argument(..., help="User message"),
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
    token: Optional[str] = typer.Option(None, help="Override token"),
    use_default: bool = typer.Option(False, help="Login with default seeded user before request"),
):
    """Send a message to a chat and get assistant response (stubbed if agent not wired)."""
    cfg = resolve_config(base_url, token)
    cfg = login_default_if_needed(cfg, base_url, use_default)
    payload = {"content": message}
    with get_client(cfg.base_url, cfg.token) as client:
        resp = client.post(f"/v1/chats/{chat_id}/messages", json=payload)
        if resp.status_code != 201:
            typer.echo(f"Chat send failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        print_json(resp.json())


@app.command("chat-history")
def chat_history(
    chat_id: uuid.UUID,
    limit: int = typer.Option(50, help="Max messages"),
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
    token: Optional[str] = typer.Option(None, help="Override token"),
    use_default: bool = typer.Option(False, help="Login with default seeded user before request"),
):
    """Fetch chat history."""
    cfg = resolve_config(base_url, token)
    cfg = login_default_if_needed(cfg, base_url, use_default)
    params = {"limit": limit}
    with get_client(cfg.base_url, cfg.token) as client:
        resp = client.get(f"/v1/chats/{chat_id}/messages", params=params)
        if resp.status_code != 200:
            typer.echo(f"Chat history failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        print_json(resp.json())


@app.command("chat-loop")
def chat_loop(
    chat_id: Optional[uuid.UUID] = typer.Option(None, help="Existing chat ID; if omitted, a new chat is created"),
    title: Optional[str] = typer.Option(None, help="Title when creating a new chat"),
    show_thoughts: bool = typer.Option(False, help="Display agent/tool thinking if available"),
    document_id: Optional[uuid.UUID] = typer.Option(None, help="Optional document_id to send with each message"),
    base_url: Optional[str] = typer.Option(None, help="API base URL"),
    token: Optional[str] = typer.Option(None, help="Override token"),
    use_default: bool = typer.Option(False, help="Login with default seeded user before request"),
):
    """
    Interactive terminal chat with the backend chat API.

    - If chat_id is omitted, creates a new chat first.
    - show_thoughts toggles display of tool/agent reasoning when returned by the API (stubbed until implemented).
    """
    cfg = resolve_config(base_url, token)
    cfg = login_default_if_needed(cfg, base_url, use_default)
    client = get_client(cfg.base_url, cfg.token)

    def ensure_chat() -> uuid.UUID:
        if chat_id:
            return chat_id
        resp = client.post("/v1/chats", json={"title": title} if title else {})
        if resp.status_code != 201:
            typer.echo(f"Chat create failed: {resp.status_code} {resp.text}", err=True)
            raise typer.Exit(code=1)
        data = resp.json()
        return uuid.UUID(str(data["id"]))

    cid = ensure_chat()
    console.print(f"[bold green]Chat session:[/bold green] {cid}")
    console.print("Type your message. 'exit' or Ctrl+C to quit.")

    try:
        while True:
            user_text = input("You: ").strip()
            if not user_text:
                continue
            if user_text.lower() in ("exit", "quit"):
                break

            payload = {"content": {"text": user_text, "document_id": str(document_id) if document_id else None}}
            resp = client.post(f"/v1/chats/{cid}/messages", json=payload)
            if resp.status_code != 201:
                console.print(f"[red]Send failed:[/red] {resp.status_code} {resp.text}")
                continue
            data = resp.json()
            content = data.get("content")
            if isinstance(content, dict):
                rendered = json.dumps(content, indent=2)
                console.print(Markdown(f"**Assistant:**\n```\n{rendered}\n```"))
            else:
                console.print(Markdown(f"**Assistant:** {content}"))

            if show_thoughts and isinstance(content, dict) and "thoughts" in content:
                console.print(Markdown(f"> Thoughts: {content['thoughts']}"))

    except KeyboardInterrupt:
        console.print("\n[cyan]Bye![/cyan]")


if __name__ == "__main__":
    app()
