
"""A slightly more complex greeting script."""

import datetime


def greet(name: str) -> str:
    """Return a greeting with the current timestamp."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Hello, {name}! The time is {now}."


def main() -> None:
    names = ["Alice", "Bob", "Charlie"]
    for person in names:
        print(greet(person))


if __name__ == "__main__":
    main()
