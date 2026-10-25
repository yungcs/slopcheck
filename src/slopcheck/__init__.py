"""A linter for the mess AI coding agents leave in Python."""

from slopcheck.engine import scan
from slopcheck.models import Finding, ParseError, Report
from slopcheck.version import __version__

__all__ = ["Finding", "ParseError", "Report", "__version__", "scan"]
