"""Hermes plugin entry point for the HMP repository checkout."""

from .server.hmp_plugin import register

__all__ = ["register"]
