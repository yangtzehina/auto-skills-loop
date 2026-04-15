from __future__ import annotations


def summarize(topic: str) -> str:
    return f"Summary for {topic}"


def main() -> int:
    print(summarize("compose reuse"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
