import uuid
import pytest
from httpx import AsyncClient


async def login_and_get_token(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/v1/auth/jwt/login",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_create_chat(client: AsyncClient, seeded_user):
    token = await login_and_get_token(client, "admin@example.com", "changeme123!")
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/v1/chats", json={"title": "my chat"}, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "id" in data
    assert data["title"] == "my chat"


@pytest.mark.asyncio
async def test_upload_document_sets_ready(client: AsyncClient, seeded_user):
    token = await login_and_get_token(client, "admin@example.com", "changeme123!")
    headers = {"Authorization": f"Bearer {token}"}

    pdf_bytes = b"%PDF-1.4\n%EOF\n"
    files = {"file": ("sample.pdf", pdf_bytes, "application/pdf")}

    resp = await client.post("/v1/documents:upload", files=files, headers=headers)
    assert resp.status_code == 202, resp.text
    doc_id = resp.json()["document_id"]

    # After fake ingestion, status should be ready
    resp = await client.get(f"/v1/documents/{doc_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_chat_messages_echo(client: AsyncClient, seeded_user):
    token = await login_and_get_token(client, "admin@example.com", "changeme123!")
    headers = {"Authorization": f"Bearer {token}"}

    # create chat
    resp = await client.post("/v1/chats", json={"title": "echo"}, headers=headers)
    assert resp.status_code == 201, resp.text
    chat_id = resp.json()["id"]

    # send first message
    resp = await client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "hello"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "content" in body
    assert "ack: hello" in body["content"]["text"]

    # send second message
    resp = await client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "second"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "ack: second" in body["content"]["text"]
