import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="prism")
    parser.add_argument("--version", action="store_true", help="Print the Prism CLI version.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.version:
        print("prism 0.1.0")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
