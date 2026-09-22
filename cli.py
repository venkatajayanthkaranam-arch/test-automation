import os
import sys
import json
import argparse

# Force UTF-8 output encoding for Windows command line
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.parser.universal_parser import UniversalParser
from core.models.schema import CanonicalScript

console = Console(force_terminal=True, legacy_windows=False)

def cmd_parse(args):
    file_path = args.file
    if not os.path.exists(file_path):
        console.print(f"[bold red]Error:[/bold red] File not found: {file_path}")
        return

    parser = UniversalParser()
    console.print(f"[bold cyan]Parsing file:[/bold cyan] {file_path}")
    
    try:
        scripts = parser.parse(file_path, target_script=args.script)
    except Exception as e:
        console.print(f"[bold red]Parsing failed:[/bold red] {e}")
        return

    console.print(f"[bold green]Successfully parsed {len(scripts)} test script(s):[/bold green]\n")

    for s in scripts:
        table = Table(title=f"Script: {s.script_id} - {s.title}", show_header=True, header_style="bold magenta")
        table.add_column("Step ID", style="cyan", width=12)
        table.add_column("Role", style="green", width=14)
        table.add_column("Description", style="white", overflow="fold")
        table.add_column("Test Data", style="yellow", width=12)
        table.add_column("Expected Result", style="blue", overflow="fold")
        table.add_column("Status", style="magenta", width=14)

        for step in s.steps:
            table.add_row(
                str(step.id),
                str(step.role or "-"),
                str(step.raw_text),
                str(step.test_data or "-"),
                str(step.expected_result or "-"),
                str(step.status.value)
            )

        console.print(table)
        console.print(f"Total Steps: [bold]{len(s.steps)}[/bold] | Warnings: [bold]{len(s.warnings)}[/bold]\n")

        if args.json:
            out_file = f"{s.script_id}_canonical.json"
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(s.model_dump_json(indent=2))
            console.print(f"[bold yellow]Dumped JSON to:[/bold yellow] {out_file}\n")

def main():
    parser = argparse.ArgumentParser(description="Oracle Fusion Test Automation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parse_cmd = subparsers.add_parser("parse", help="Parse a manual test script in any format")
    parse_cmd.add_argument("--file", "-f", required=True, help="Path to input test script (.xlsx, .csv, .docx, etc.)")
    parse_cmd.add_argument("--script", "-s", default=None, help="Target specific script/sheet ID (optional)")
    parse_cmd.add_argument("--json", "-j", action="store_true", help="Output canonical JSON file")

    args = parser.parse_args()
    if args.command == "parse":
        cmd_parse(args)

if __name__ == "__main__":
    main()
