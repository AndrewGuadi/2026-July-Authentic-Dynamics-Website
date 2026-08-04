#!/usr/bin/env python3
"""reputation-audit-framework — passive OSINT reputation audit CLI.

Authorized-use only. This entry point performs argument parsing, prints the
legal disclaimer banner, enforces explicit authorization and then hands control
to :class:`core.orchestrator.Orchestrator`.

Example
-------
    python main.py run \\
        --full-name "Sarah Mitchell" \\
        --domain "sarahmitchellhomes.com" \\
        --username "sarahmitchellrealtor" \\
        --image-dir "./images" \\
        --authorized yes
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from core.banner import print_banner
from core.config import AppConfig, load_config
from core.orchestrator import Orchestrator
from core.validator import AuthorizationError, ScopeValidator, ValidationError

__version__ = "1.1.0"

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Passive OSINT reputation audit framework for authorized engagements.",
)
console = Console()

ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config.yaml"


@app.command("run")
def run(
    full_name: str = typer.Option(..., "--full-name", help="Client legal/brand name (audit subject)."),
    domain: Optional[str] = typer.Option(None, "--domain", help="Client-owned domain in scope."),
    username: Optional[str] = typer.Option(None, "--username", help="Primary handle to enumerate."),
    email: Optional[str] = typer.Option(None, "--email", help="Authorized public email identifier."),
    birth_date: Optional[str] = typer.Option(
        None, "--birth-date", help="Optional YYYY or YYYY-MM-DD identity-matching attribute."
    ),
    country: Optional[str] = typer.Option(
        None, "--country", help="Optional two-letter identity-matching country code."
    ),
    subject_type: str = typer.Option(
        "person", "--subject-type", help="Identity type: person, organization, or company."
    ),
    image_dir: Optional[Path] = typer.Option(
        None, "--image-dir", help="Directory of client-supplied images for metadata review."
    ),
    authorized: str = typer.Option(
        "no", "--authorized", help="Must be 'yes'. Written attestation that the scope is authorized."
    ),
    config_file: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c", help="Path to config.yaml."),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Override output root."),
    engagement_id: Optional[str] = typer.Option(None, "--engagement-id", help="Reference/ticket id for the report."),
    no_pdf: bool = typer.Option(False, "--no-pdf", help="Skip PDF rendering even if wkhtmltopdf exists."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate scope + config, print plan, execute nothing."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose console logging (DEBUG)."),
) -> None:
    """Run a passive reputation audit against an authorized scope."""
    print_banner(console)

    try:
        config: AppConfig = load_config(config_file)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]config error:[/bold red] {exc}")
        raise typer.Exit(code=2)

    validator = ScopeValidator(config)
    try:
        validator.require_authorization(authorized)
        scope = validator.build_scope(
            full_name=full_name,
            domain=domain,
            username=username,
            email=email,
            birth_date=birth_date,
            country=country,
            subject_type=subject_type,
            image_dir=image_dir,
            engagement_id=engagement_id,
        )
    except AuthorizationError as exc:
        console.print(f"[bold red]AUTHORIZATION REQUIRED:[/bold red] {exc}")
        console.print("Re-run with [bold]--authorized yes[/bold] only if you hold written permission.")
        raise typer.Exit(code=3)
    except ValidationError as exc:
        console.print(f"[bold red]scope error:[/bold red] {exc}")
        raise typer.Exit(code=2)

    orchestrator = Orchestrator(
        config=config,
        scope=scope,
        output_root=output_dir or Path(config.output_root),
        console=console,
        verbose=verbose,
        render_pdf=not no_pdf,
    )

    if dry_run:
        orchestrator.print_plan()
        raise typer.Exit(code=0)

    summary = orchestrator.execute()
    orchestrator.print_summary(summary)
    successful = {"completed", "completed_with_review"}
    raise typer.Exit(code=0 if summary["status"] in successful else 1)


@app.command("modules")
def modules(
    config_file: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c", help="Path to config.yaml."),
) -> None:
    """List registered modules, their scope requirements and enabled state."""
    from modules import MODULE_REGISTRY

    config = load_config(config_file)
    table = Table(title="Registered modules", header_style="bold green")
    table.add_column("Module")
    table.add_column("Enabled")
    table.add_column("Scope input")
    table.add_column("Execution")
    table.add_column("Passive")
    for name, cls in sorted(MODULE_REGISTRY.items()):
        enabled = config.modules.get(name, False)
        module = cls(config)
        table.add_row(
            name,
            "[green]yes[/green]" if enabled else "[dim]no[/dim]",
            cls.scope_field,
            module.execution_mode(),
            "[green]passive[/green]" if cls.passive else "[red]active[/red]",
        )
    integration_rows = {
        "search_by_image": ("image_dir", "analyst-assisted"),
        "linkscope": ("normalized findings", "exporter"),
        "openaleph": ("engagement workspace", str(config.integration_options("openaleph").get("mode", "package"))),
    }
    for name, (scope_input, execution) in integration_rows.items():
        table.add_row(
            name,
            "[green]yes[/green]" if config.integration_enabled(name) else "[dim]no[/dim]",
            scope_input,
            execution,
            "[green]passive[/green]",
        )
    console.print(table)


@app.command("doctor")
def doctor(
    config_file: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c", help="Path to config.yaml."),
) -> None:
    """Report exact native, image, service, and integration readiness."""
    import os
    from urllib.error import URLError
    from urllib.request import urlopen

    from core.runner import binary_available, docker_available, docker_image_available
    from modules import MODULE_REGISTRY

    config = load_config(config_file)

    table = Table(title="Environment check", header_style="bold green")
    table.add_column("Dependency")
    table.add_column("Status")
    checks = {
        "docker": docker_available(),
        "maigret": binary_available("maigret"),
        "blackbird": binary_available("blackbird"),
        "amass": binary_available("amass"),
        "exiftool": binary_available("exiftool"),
        "trufflehog": binary_available("trufflehog"),
        "theHarvester": binary_available("theHarvester"),
        "social-analyzer": binary_available("social-analyzer"),
        "recon-cli": binary_available("recon-cli"),
        "alephclient": binary_available("alephclient"),
        "wkhtmltopdf": binary_available("wkhtmltopdf"),
    }
    for dep, ok in checks.items():
        table.add_row(dep, "[green]available[/green]" if ok else "[yellow]missing (docker fallback)[/yellow]")
    console.print(table)

    readiness = Table(title=f"Configured module readiness — {config_file.name}", header_style="bold green")
    readiness.add_column("Module")
    readiness.add_column("Enabled")
    readiness.add_column("Execution")
    readiness.add_column("Ready")
    readiness.add_column("Detail")
    unready_enabled: list[str] = []
    for name, cls in sorted(MODULE_REGISTRY.items()):
        enabled = bool(config.modules.get(name, False))
        preference = config.execution_for(name)
        if name == "yente":
            base_url = str(os.environ.get("YENTE_BASE_URL") or config.options_for("yente").get("base_url") or "").rstrip("/")
            try:
                with urlopen(f"{base_url}/healthz", timeout=5) as response:  # nosec: operator-configured service
                    ready = response.status == 200
            except (URLError, TimeoutError, OSError, ValueError):
                ready = False
            detail = f"service {base_url or 'not configured'}"
            mode = "service"
        else:
            native = binary_available(cls(config).binary)
            image = config.image_for(name)
            image_ready = docker_image_available(image)
            mode = preference
            ready = native if preference == "native" else image_ready if preference == "docker" else native or image_ready
            detail = f"native={'yes' if native else 'no'}; image={'yes' if image_ready else 'no'}"
        readiness.add_row(
            name,
            "yes" if enabled else "no",
            mode,
            "[green]yes[/green]" if ready else "[yellow]no[/yellow]",
            detail,
        )
        if enabled and not ready:
            unready_enabled.append(name)
    console.print(readiness)

    integrations = Table(title="Post-collection integrations", header_style="bold green")
    integrations.add_column("Integration")
    integrations.add_column("Enabled")
    integrations.add_column("Ready")
    integrations.add_column("Detail")
    for name in ("linkscope", "search_by_image", "openaleph"):
        options = config.integration_options(name)
        enabled = bool(options.get("enabled", False))
        if name in {"linkscope", "search_by_image"}:
            ready = True
            detail = "built-in exporter/task workflow"
        elif str(options.get("mode", "package")) == "package":
            ready = True
            detail = "package mode"
        else:
            execution = str(options.get("execution", "docker"))
            ready = (
                bool(os.environ.get("ALEPH_HOST") and os.environ.get("ALEPH_API_KEY"))
                and (
                    binary_available("alephclient")
                    if execution == "native"
                    else docker_image_available(str(options.get("image", "")))
                )
            )
            detail = "upload mode; requires ALEPH_HOST and ALEPH_API_KEY"
        integrations.add_row(
            name,
            "yes" if enabled else "no",
            "[green]yes[/green]" if ready else "[yellow]no[/yellow]",
            detail,
        )
        if enabled and not ready:
            unready_enabled.append(name)
    console.print(integrations)
    if unready_enabled:
        console.print(
            "[bold yellow]Not ready:[/bold yellow] "
            + ", ".join(sorted(set(unready_enabled)))
        )
        raise typer.Exit(code=1)


@app.command("version")
def version() -> None:
    """Print the framework version."""
    console.print(f"reputation-audit-framework {__version__}")


@app.command("import-review")
def import_review(
    workspace: Path = typer.Option(..., "--workspace", help="Completed engagement workspace."),
    review_file: Path = typer.Option(..., "--review-file", help="Completed reverse-image or LinkScope JSON."),
    config_file: Path = typer.Option(DEFAULT_CONFIG, "--config", "-c", help="Configuration used for reporting."),
) -> None:
    """Validate analyst decisions and regenerate normalized reports."""
    from integrations.reviews import ReviewImportError, import_review_document

    try:
        config = load_config(config_file)
        result = import_review_document(workspace, review_file, config)
    except (FileNotFoundError, ValueError, ReviewImportError) as exc:
        console.print(f"[bold red]review import error:[/bold red] {exc}")
        raise typer.Exit(code=2)
    console.print(
        f"[green]Imported {result['new_findings']} reviewed record(s).[/green] "
        f"Workspace status: {result['status']}"
    )


def main() -> None:
    """Console-script wrapper."""
    try:
        app()
    except KeyboardInterrupt:  # pragma: no cover - interactive path
        console.print("\n[yellow]Interrupted by operator. Partial output retained.[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    main()
