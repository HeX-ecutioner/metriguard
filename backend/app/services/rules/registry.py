"""
Rule Registry for MetriGuard.
Stores, registers, filters, and retrieves versioned regulatory compliance rules.
"""

import logging
from typing import Dict, List, Optional
from app.services.rules.base import RegulatoryRule
from app.services.rules.lmr_2011 import get_lmr_2011_prototype_rules

logger = logging.getLogger(__name__)


class RuleRegistry:
    """
    Registry managing the lifecycle and retrieval of versioned regulatory rules.
    """

    def __init__(self, load_defaults: bool = True):
        self._rules: Dict[str, RegulatoryRule] = {}
        if load_defaults:
            self.load_default_rules()

    def register_rule(self, rule: RegulatoryRule) -> None:
        """Registers a versioned rule in the registry."""
        if rule.rule_id in self._rules:
            logger.info(f"Overwriting existing rule registration for '{rule.rule_id}'.")
        self._rules[rule.rule_id] = rule

    def unregister_rule(self, rule_id: str) -> Optional[RegulatoryRule]:
        """Removes a rule from the registry."""
        return self._rules.pop(rule_id, None)

    def get_rule(self, rule_id: str) -> Optional[RegulatoryRule]:
        """Retrieves a rule by its unique identifier."""
        return self._rules.get(rule_id)

    def get_all_rules(self, only_enabled: bool = True) -> List[RegulatoryRule]:
        """Returns all registered rules, optionally filtered by enabled status."""
        rules = list(self._rules.values())
        if only_enabled:
            return [r for r in rules if r.enabled]
        return rules

    def load_default_rules(self) -> None:
        """Loads the official LMR 2011 prototype rules into the registry."""
        for rule in get_lmr_2011_prototype_rules():
            self.register_rule(rule)

    def clear(self) -> None:
        """Clears all rules from the registry."""
        self._rules.clear()


# Default singleton registry
_global_registry: Optional[RuleRegistry] = None


def get_rule_registry() -> RuleRegistry:
    """Returns or creates the global RuleRegistry singleton."""
    global _global_registry
    if _global_registry is None:
        _global_registry = RuleRegistry(load_defaults=True)
    return _global_registry
