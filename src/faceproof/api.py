"""FastAPI surface for the local evidence workbench."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from contextlib import suppress
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.requests import Request
from starlette.responses import Response

from faceproof import __version__
from faceproof.blockchain import BaseSepoliaClient
from faceproof.config import Settings, get_settings
from faceproof.domain import HealthResponse, RunRecord, RunStatus
from faceproof.errors import FaceProofError, ImageValidationError
from faceproof.pipeline import Pipeline
from faceproof.store import RunStore
from faceproof.wallet import create_wallet

STATIC_DIR = Path(__file__).resolve().parent / "static"
TOKENS_PATH = STATIC_DIR / "tokens.css"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "script-src 'self'; "
            "connect-src 'self'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


class LocalOriginMiddleware(BaseHTTPMiddleware):
    """Reject browser mutations initiated by a different web origin."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            host = request.headers.get("host", "")
            allowed_origins = {f"http://{host}", f"https://{host}"}
            if origin and origin not in allowed_origins:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "origin_rejected",
                            "message": "Cross-origin changes are not allowed.",
                            "recovery": "Open FaceProof directly on 127.0.0.1 and retry.",
                        }
                    },
                )
        response: Response = await call_next(request)
        return response


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or get_settings()
    store = RunStore(active_settings.runs_dir)
    pipeline = Pipeline(active_settings, store)
    tasks: dict[str, asyncio.Task[RunRecord]] = {}

    application = FastAPI(
        title="FaceProof",
        version=__version__,
        docs_url="/api/docs",
        redoc_url=None,
    )
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"],
    )
    application.add_middleware(LocalOriginMiddleware)
    application.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    def load_run(run_id: str) -> RunRecord:
        try:
            return store.get(run_id)
        except (FileNotFoundError, ValueError):
            raise HTTPException(status_code=404, detail="Run not found") from None

    def remember(run_id: str, awaitable: Coroutine[Any, Any, RunRecord]) -> None:
        task: asyncio.Task[RunRecord] = asyncio.create_task(awaitable)
        tasks[run_id] = task

        def discard(completed: asyncio.Task[RunRecord]) -> None:
            with suppress(asyncio.CancelledError):
                completed.exception()
            tasks.pop(run_id, None)

        task.add_done_callback(discard)

    @application.exception_handler(FaceProofError)
    async def faceproof_error_handler(_: Request, exc: FaceProofError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": exc.code, "message": exc.message, "recovery": exc.recovery}},
        )

    @application.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @application.get("/tokens.css", include_in_schema=False)
    async def tokens() -> FileResponse:
        return FileResponse(TOKENS_PATH, media_type="text/css")

    @application.get("/api/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        client = BaseSepoliaClient(
            active_settings.base_rpc_url,
            active_settings.base_chain_id,
            active_settings.base_explorer_url,
            active_settings.wallet_file,
        )
        status = await asyncio.to_thread(client.status)
        models_ready = all(
            (active_settings.models_dir / filename).is_file()
            for filename in (
                "face_detection_yunet_2023mar.onnx",
                "face_recognition_sface_2021dec.onnx",
            )
        )
        wallet_funded = bool(status.balance_wei and status.balance_wei > 0)
        all_ready = (
            active_settings.search_is_configured
            and models_ready
            and status.wallet_address is not None
            and wallet_funded
            and status.reachable
            and status.chain_id == active_settings.base_chain_id
        )
        return HealthResponse(
            status="ready" if all_ready else "setup_required",
            version=__version__,
            search_configured=active_settings.search_is_configured,
            models_ready=models_ready,
            wallet_configured=status.wallet_address is not None,
            wallet_address=status.wallet_address,
            wallet_funded=wallet_funded,
            wallet_balance_wei=status.balance_wei,
            blockchain_reachable=(
                status.reachable and status.chain_id == active_settings.base_chain_id
            ),
            chain_id=active_settings.base_chain_id,
            network="Base Sepolia",
        )

    @application.post("/api/wallet", response_model=dict[str, str])
    async def wallet_create() -> dict[str, str]:
        address = await asyncio.to_thread(create_wallet, active_settings.wallet_file)
        return {
            "address": address,
            "network": "Base Sepolia",
            "warning": "Use only free Base Sepolia test ETH with this disposable wallet.",
        }

    @application.post("/api/runs", response_model=RunRecord, status_code=202)
    async def create_run(
        image: Annotated[UploadFile, File()],
        consent: Annotated[bool, Form()],
    ) -> RunRecord:
        if not consent:
            raise ImageValidationError(
                "Permission confirmation is required before the image can be searched.",
                "Confirm that the image is yours to use or depicts a public figure.",
            )
        filename = Path(image.filename or "face-image").name
        payload = await image.read(active_settings.max_upload_bytes + 1)
        if len(payload) > active_settings.max_upload_bytes:
            raise ImageValidationError(
                f"The image is larger than {active_settings.max_upload_bytes // (1024 * 1024)} MB.",
                "Choose a smaller JPEG, PNG, or WebP image.",
            )
        record = store.create(filename)
        uploaded_path = store.artifact_path(record.run_id, "upload.bin")
        await asyncio.to_thread(uploaded_path.write_bytes, payload)
        remember(record.run_id, pipeline.prepare(record.run_id, uploaded_path))
        await asyncio.sleep(0)
        return store.get(record.run_id)

    @application.get("/api/runs/{run_id}", response_model=RunRecord)
    async def get_run(run_id: str) -> RunRecord:
        return load_run(run_id)

    @application.post("/api/runs/{run_id}/cancel", response_model=RunRecord)
    async def cancel_run(run_id: str) -> RunRecord:
        record = load_run(run_id)
        if record.status == RunStatus.PUBLISHING:
            raise FaceProofError(
                "A blockchain transaction cannot be canceled after signing has started.",
                "Wait for confirmation, then use Verify again if the network response is delayed.",
            )
        task = tasks.get(run_id)
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        record = load_run(run_id)
        if record.status not in {RunStatus.VERIFIED, RunStatus.AWAITING_PUBLISH}:
            record.status = RunStatus.CANCELED
            record.status_message = "The run was canceled. Saved results remain available."
            store.save(record)
        return record

    @application.post("/api/runs/{run_id}/publish", response_model=RunRecord, status_code=202)
    async def publish_run(run_id: str) -> RunRecord:
        record = load_run(run_id)
        if record.status != RunStatus.AWAITING_PUBLISH:
            raise FaceProofError(
                "This run is not ready for blockchain publication.",
                "Wait for evidence preparation to finish or start a new run.",
            )
        remember(run_id, pipeline.publish_and_verify(run_id))
        await asyncio.sleep(0)
        return store.get(run_id)

    @application.post("/api/runs/{run_id}/verify", response_model=RunRecord)
    async def verify_run(run_id: str) -> RunRecord:
        load_run(run_id)
        return await pipeline.verify_saved(run_id)

    @application.get("/api/runs/{run_id}/files/{filename}", include_in_schema=False)
    async def run_file(run_id: str, filename: str) -> FileResponse:
        try:
            path = store.artifact_path(run_id, filename)
        except ValueError:
            raise HTTPException(status_code=404, detail="Artifact not found") from None
        if not path.is_file() or path.name == "upload.bin" or path.name == "state.json":
            raise HTTPException(status_code=404, detail="Artifact not found")
        media_type = "application/json" if path.suffix == ".json" else "image/jpeg"
        download_name = path.name if media_type == "application/json" else None
        return FileResponse(path, media_type=media_type, filename=download_name)

    @application.get("/api/runs/{run_id}/evidence/download", include_in_schema=False)
    async def download_evidence(run_id: str) -> FileResponse:
        path = store.artifact_path(run_id, "evidence.json")
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Evidence not found")
        return FileResponse(
            path,
            media_type="application/json",
            filename=f"faceproof-{run_id}.json",
        )

    return application


app = create_app()
