import argparse
import json as jsonlib
from typing import Any

from app.models.schemas import CheckRequest, ExplainRequest, GenerateRequest
from app.services.command_service import generate_command
from app.services.explain_service import explain_command
from app.services.history_service import build_highlights
from app.services.safety_service import check_command_safety


def main() -> None:
    parser = argparse.ArgumentParser(description="Minimal shell command assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="Generate a shell command")
    gen.add_argument("query")
    gen.add_argument("--shell-type", default="bash")
    gen.add_argument("--os", default="linux")
    gen.add_argument("--context", default="")
    gen.add_argument("--json", action="store_true")

    exp = subparsers.add_parser("explain", help="Explain a shell command")
    exp.add_argument("shell_command")
    exp.add_argument("--json", action="store_true")

    chk = subparsers.add_parser("check", help="Check command risk")
    chk.add_argument("shell_command")
    chk.add_argument("--json", action="store_true")

    hi = subparsers.add_parser("highlights", help="Show history highlights")
    hi.add_argument("--json", action="store_true")

    args = parser.parse_args()

    if args.command == "generate":
        result = generate_command(
            GenerateRequest(
                query=args.query,
                shell_type=args.shell_type,
                os=args.os,
                context=args.context,
            )
        )
    elif args.command == "explain":
        result = explain_command(ExplainRequest(command=args.shell_command))
    elif args.command == "check":
        result = check_command_safety(CheckRequest(command=args.shell_command).command)
    else:
        result = build_highlights()

    if getattr(args, "json", False):
        print(jsonlib.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(args.command, result)


def _print_human(command: str, data: dict[str, Any]) -> None:
    if command == "generate":
        print(f"Command: {data['command']}")
        if data.get("alternatives"):
            print("Alternatives:")
            for item in data["alternatives"]:
                print(f"  - {item}")
        print(f"Explanation: {data['explanation']}")
        print(f"Risk: {data['risk_level']}")
        _print_list("Reasons", data.get("risk_reasons", []))
        _print_list("Tips", data.get("safety_tips", []))
        print(f"Source: {data['source']}")
    elif command == "explain":
        print(f"Summary: {data['summary']}")
        print(f"Risk: {data['risk_level']}")
        if data.get("parts"):
            print("Parts:")
            for part in data["parts"]:
                print(f"  - {part['token']}: {part['meaning']}")
        _print_list("Notes", data.get("notes", []))
    elif command == "check":
        print(f"Risk: {data['risk_level']}")
        _print_list("Reasons", data.get("risk_reasons", []))
        _print_list("Tips", data.get("safety_tips", []))
    else:
        print(f"Total records: {data['total_records']}")
        print(f"High risk count: {data['high_risk_count']}")
        _print_list(
            "Top categories",
            [f"{item['name']} ({item['count']})" for item in data.get("top_categories", [])],
        )
        _print_list("Frequent patterns", data.get("frequent_patterns", []))
        print(f"Summary: {data['summary']}")


def _print_list(title: str, items: list[str]) -> None:
    if not items:
        return
    print(f"{title}:")
    for item in items:
        print(f"  - {item}")


if __name__ == "__main__":
    main()

