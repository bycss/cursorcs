"""A simple command-line to-do list application."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

DATA_FILE = Path("tasks.json")


def load_tasks() -> List[Dict[str, Any]]:
    """Load tasks from the data file."""
    if DATA_FILE.exists():
        with DATA_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_tasks(tasks: List[Dict[str, Any]]) -> None:
    """Persist tasks to the data file."""
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)


def add_task(description: str) -> None:
    tasks = load_tasks()
    tasks.append({"description": description, "done": False})
    save_tasks(tasks)
    print(f"Added task: {description}")


def list_tasks(show_all: bool = True) -> None:
    tasks = load_tasks()
    if not tasks:
        print("No tasks found.")
        return
    for idx, task in enumerate(tasks, start=1):
        status = "✓" if task["done"] else "✗"
        if show_all or not task["done"]:
            print(f"{idx}. [{status}] {task['description']}")


def complete_task(index: int) -> None:
    tasks = load_tasks()
    try:
        task = tasks[index - 1]
    except IndexError:
        print(f"No task with index {index}")
        return
    task["done"] = True
    save_tasks(tasks)
    print(f"Completed task {index}: {task['description']}")


def delete_task(index: int) -> None:
    tasks = load_tasks()
    try:
        task = tasks[index - 1]
    except IndexError:
        print(f"No task with index {index}")
        return
    tasks.pop(index - 1)
    save_tasks(tasks)
    print(f"Deleted task {index}: {task['description']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple task manager")
    subparsers = parser.add_subparsers(dest="command")

    add_parser = subparsers.add_parser("add", help="Add a new task")
    add_parser.add_argument("description")

    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument(
        "--pending",
        action="store_true",
        help="Show only pending tasks",
    )

    done_parser = subparsers.add_parser("done", help="Mark a task as completed")
    done_parser.add_argument("index", type=int)

    delete_parser = subparsers.add_parser("delete", help="Delete a task")
    delete_parser.add_argument("index", type=int)

    args = parser.parse_args()

    if args.command == "add":
        add_task(args.description)
    elif args.command == "list":
        list_tasks(show_all=not args.pending)
    elif args.command == "done":
        complete_task(args.index)
    elif args.command == "delete":
        delete_task(args.index)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
