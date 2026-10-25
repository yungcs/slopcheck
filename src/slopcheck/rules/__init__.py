"""Registered slopcheck rules, in id order."""

from __future__ import annotations

from slopcheck.rules.comments import CommentedOutCodeRule, NarratingCommentRule
from slopcheck.rules.defensive import OverDefensiveRule
from slopcheck.rules.exceptions import (
    BareExceptRule,
    BroadExceptRule,
    ErrorStringRule,
    FakeFallbackRule,
    TryNestingRule,
)
from slopcheck.rules.hygiene import (
    DebugLeftoverRule,
    NearDuplicateRule,
    PlaceholderStubRule,
    UnusedPrivateRule,
    VerboseDocstringRule,
    VersionedNameRule,
)
from slopcheck.rules.imports import HallucinatedImportRule
from slopcheck.rules.support import Rule

RULES: tuple[Rule, ...] = (
    BareExceptRule(),
    BroadExceptRule(),
    FakeFallbackRule(),
    NarratingCommentRule(),
    DebugLeftoverRule(),
    UnusedPrivateRule(),
    NearDuplicateRule(),
    OverDefensiveRule(),
    PlaceholderStubRule(),
    HallucinatedImportRule(),
    TryNestingRule(),
    VerboseDocstringRule(),
    VersionedNameRule(),
    CommentedOutCodeRule(),
    ErrorStringRule(),
)

BY_ID: dict[str, Rule] = {rule.id: rule for rule in RULES}
