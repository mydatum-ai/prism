import argparse

from prism_evaluation import run_evaluation, write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prism")
    parser.add_argument("--version", action="store_true", help="Print the Prism CLI version.")
    subparsers = parser.add_subparsers(dest="command")
    eval_parser = subparsers.add_parser("eval", help="Run a Prism evaluation dataset.")
    eval_parser.add_argument(
        "--dataset", required=True, help="Dataset directory or cases.jsonl file."
    )
    eval_parser.add_argument(
        "--output", required=True, help="Directory for report.json and report.md."
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.version:
        print("prism 0.1.0")
        return 0
    if args.command == "eval":
        report = run_evaluation(args.dataset)
        write_reports(report, args.output)
        print(f"Wrote evaluation report to {args.output}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
