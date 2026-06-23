from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from starlette.middleware.trustedhost import TrustedHostMiddleware


def _app_with_allowed_hosts(*hosts: str) -> FastAPI:
    app = FastAPI()
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(hosts))

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"pong": "1"}

    return app


async def test_disallowed_host_is_rejected():
    app = _app_with_allowed_hosts("allowed.test")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://evil.test") as client:
        response = await client.get("/ping")
    assert response.status_code == 400


async def test_allowed_host_passes():
    app = _app_with_allowed_hosts("allowed.test")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://allowed.test") as client:
        response = await client.get("/ping")
    assert response.status_code == 200
