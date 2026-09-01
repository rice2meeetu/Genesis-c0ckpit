"""Shared, explicit Send-To menu construction for GENESIS image workflows."""

from __future__ import annotations

from dataclasses import dataclass
import tkinter as tk
from typing import Callable, Iterable


@dataclass(frozen=True)
class SendDestination:
    key: str
    label: str


def build_send_to_menu(
    parent,
    destinations: Iterable[SendDestination],
    command: Callable[[str], None],
):
    """Build a menu whose visible labels map to explicit stable destination keys."""
    destinations = tuple(destinations)
    keys = [destination.key for destination in destinations]
    if not destinations:
        raise ValueError("A Send-To menu needs at least one destination.")
    if any(not key or not destination.label for key, destination in zip(keys, destinations)):
        raise ValueError("Send-To destination keys and labels cannot be empty.")
    if len(keys) != len(set(keys)):
        raise ValueError("Send-To destination keys must be unique.")

    menu = tk.Menu(parent, tearoff=False)
    for destination in destinations:
        menu.add_command(
            label=destination.label,
            command=lambda key=destination.key: command(key),
        )
    return menu
