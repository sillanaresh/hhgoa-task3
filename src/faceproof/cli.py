"""Command line interface for setup, automation, and independent verification."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from faceproof.blockchain import BaseSepoliaClient
from faceproof.config import get_settings
from faceproof.domain import RunRecord, RunStatus
from faceproof.evidence import evidence_id, load_manifest
from faceproof.model_files import ensure_models
from faceproof.pipeline import Pipeline
from faceproof.store import RunStore
from faceproof.utils import short_hash
from faceproof.wallet import create_wallet

app = typer.Typer(
    no_args_is_help=True,
    help="Find public face matches and verify their evidence on Base Sepolia.",
)
console = Console()


def _client() -> BaseSepoliaClient:
    settings = get_settings()
    return BaseSepoliaClient(
        settings.base_rpc_url,
        settings.base_chain_id,
        settings.base_explorer_url,
        settings.wallet_file,
    )


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Address for the local interface."),
    port: int = typer.Option(8765, min=1, max=65535, help="Port for the local interface."),
    reload: bool = typer.Option(False, help="Reload the server after source changes."),
) -> None:
    """Open the local evidence workbench."""

    console.print(f"[bold]FaceProof[/bold] is starting at http://{host}:{port}")
    uvicorn.run("faceproof.api:app", host=host, port=port, reload=reload)


@app.command("models")
def download_models() -> None:
    """Download pinned OpenCV face models and verify their SHA-256 values."""

    settings = get_settings()
    with console.status("Downloading and verifying face models"):
        models = ensure_models(settings.models_dir)
    for name, path in models.items():
        console.print(f"[green]Ready[/green]  {name}  [dim]{path}[/dim]")


@app.command("wallet-create")
def wallet_create() -> None:
    """Create a disposable wallet for Base Sepolia test ETH only."""

    settings = get_settings()
    address = create_wallet(settings.wallet_file)
    console.print(
        Panel.fit(
            f"[bold]{address}[/bold]\n\nFund this address with free Base Sepolia test ETH only.",
            title="Disposable test wallet",
            border_style="cyan",
        )
    )


@app.command("doctor")
def doctor(
    strict: Annotated[
        bool,
        typer.Option(help="Exit with an error unless the full public pipeline is ready."),
    ] = False,
) -> None:
    """Check local models, search credentials, wallet, and public network access."""

    settings = get_settings()
    status = _client().status()
    table = Table(title="FaceProof readiness", show_lines=False)
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    table.add_row(
        "Search",
        "Ready" if settings.search_is_configured else "Needs setup",
        (
            "SerpApi key found"
            if settings.search_is_configured
            else "Add the key to .context/secrets.env"
        ),
    )
    models_ready = all(
        (settings.models_dir / name).is_file()
        for name in (
            "face_detection_yunet_2023mar.onnx",
            "face_recognition_sface_2021dec.onnx",
        )
    )
    table.add_row(
        "Face models",
        "Ready" if models_ready else "Needs setup",
        str(settings.models_dir),
    )
    table.add_row(
        "Test wallet",
        "Ready" if status.wallet_address else "Needs setup",
        status.wallet_address or "Run faceproof wallet-create",
    )
    table.add_row(
        "Base Sepolia",
        (
            "Reachable"
            if status.reachable and status.chain_id == settings.base_chain_id
            else "Unavailable"
        ),
        f"Chain {status.chain_id}" if status.chain_id else settings.base_rpc_url,
    )
    balance = status.balance_wei or 0
    table.add_row(
        "Test ETH",
        "Ready" if balance > 0 else "Needs funding",
        f"{balance / 10**18:.8f} ETH",
    )
    console.print(table)
    all_ready = (
        settings.search_is_configured
        and models_ready
        and status.wallet_address is not None
        and status.reachable
        and status.chain_id == settings.base_chain_id
        and balance > 0
    )
    if strict and not all_ready:
        console.print("[red]The complete public pipeline is not ready.[/red]")
        raise typer.Exit(1)


@app.command("run")
def run_pipeline(
    image: Annotated[
        Path,
        typer.Argument(exists=True, dir_okay=False, readable=True),
    ],
    publish: Annotated[
        bool,
        typer.Option(help="Publish after local evidence preparation."),
    ] = False,
) -> None:
    """Run face detection, live search, comparison, and optional publication."""

    settings = get_settings()
    store = RunStore(settings.runs_dir)
    record = store.create(image.name)
    upload = store.artifact_path(record.run_id, "upload.bin")
    upload.write_bytes(image.read_bytes())
    pipeline = Pipeline(settings, store)

    async def execute() -> RunRecord:
        prepared = await pipeline.prepare(record.run_id, upload)
        _print_run(prepared)
        if publish and prepared.status == RunStatus.AWAITING_PUBLISH:
            console.print("\nPublishing the reviewed fingerprint to Base Sepolia…")
            published = await pipeline.publish_and_verify(record.run_id)
            _print_run(published)
            return published
        return prepared

    completed = asyncio.run(execute())
    if completed.status in {RunStatus.FAILED, RunStatus.CANCELED}:
        raise typer.Exit(1)


@app.command("verify")
def verify(run_id: Annotated[str, typer.Argument(help="Saved run identifier.")]) -> None:
    """Recompute a saved evidence fingerprint and compare it with Base Sepolia."""

    settings = get_settings()
    store = RunStore(settings.runs_dir)
    pipeline = Pipeline(settings, store)
    verified = asyncio.run(pipeline.verify_saved(run_id))
    _print_run(verified)
    if not verified.blockchain or not verified.blockchain.verification_passed:
        raise typer.Exit(1)


@app.command("hash-evidence")
def hash_evidence(
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
) -> None:
    """Print the deterministic fingerprint for an evidence JSON file."""

    manifest = load_manifest(path)
    console.print(evidence_id(manifest))


@app.command("verify-file")
def verify_file(
    path: Annotated[Path, typer.Argument(exists=True, dir_okay=False)],
    transaction_hash: Annotated[str, typer.Argument(help="Base Sepolia transaction hash.")],
) -> None:
    """Verify any evidence file directly against a public transaction."""

    digest = evidence_id(load_manifest(path))
    receipt = _client().verify(transaction_hash, digest)
    if receipt.verification_passed:
        console.print(
            Panel.fit(
                f"[green]Verified[/green]\n{digest}\n\n{receipt.explorer_url}",
                title="Public proof",
            )
        )
        return
    console.print("[red]Verification failed.[/red] The evidence does not match the transaction.")
    raise typer.Exit(1)


def _print_run(record: RunRecord) -> None:
    data = record.model_dump(mode="json", exclude_none=True)
    console.print(f"\n[bold]Run[/bold] {data['run_id']}  [bold]Status[/bold] {data['status']}")
    error = data.get("error")
    if error:
        console.print(f"[red]{error['message']}[/red]")
    else:
        console.print(data["status_message"])
    if evidence := data.get("evidence"):
        console.print(f"[bold]Evidence[/bold] {short_hash(evidence['evidence_id'])}")
    if blockchain := data.get("blockchain"):
        console.print(f"[bold]Transaction[/bold] {blockchain['explorer_url']}")
        console.print(f"[bold]Verified[/bold] {blockchain['verification_passed']}")
    if error and (recovery := error.get("recovery")):
        console.print(recovery)


if __name__ == "__main__":
    app()
