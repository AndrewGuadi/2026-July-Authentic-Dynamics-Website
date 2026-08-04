"""Runtime legal disclaimer banner."""
from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

ASCII_LOGO = r"""
  ___ ___ ___ _   _ _____ _ _____ ___ ___  _  _
 | _ \ __| _ \ | | |_   _/_\_   _|_ _/ _ \| \| |
 |   / _||  _/ |_| | | |/ _ \| |  | | (_) | .` |
 |_|_\___|_|  \___/  |_/_/ \_\_| |___\___/|_|\_|
      A U D I T   F R A M E W O R K   v1.1.0
"""

DISCLAIMER = """[bold yellow]AUTHORIZED USE ONLY — PASSIVE RECONNAISSANCE[/bold yellow]

This framework performs [bold]passive[/bold] open-source collection against a scope you
have been [bold]explicitly authorized in writing[/bold] to assess. By continuing you attest that:

  1. You have documented, written permission from the audit subject or asset owner.
  2. You will not use this tooling to harass, stalk, dox or impersonate any person.
  3. No authentication, paywall or CAPTCHA control will be bypassed by this tool.
  4. No brute-force, credential testing or intrusive scanning is performed.
  5. Collected material is confidential and handled per your data-retention policy.

Scope inputs, operator identity and collection timestamps are logged for the record.
Unauthorized use may violate the CFAA, UK CMA 1990, GDPR/CCPA and equivalent statutes."""


def print_banner(console: Console) -> None:
    """Render the ASCII logo and the mandatory legal disclaimer.

    Args:
        console: Rich console used for output.
    """
    console.print(f"[bold green]{ASCII_LOGO}[/bold green]")
    console.print(
        Panel(
            DISCLAIMER,
            title="[bold red]LEGAL NOTICE[/bold red]",
            border_style="red",
            padding=(1, 2),
        )
    )
