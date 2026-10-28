"""The audit filter tree shared by DAM alert rules and the audit searches."""

import json


def parse_filter_tree(value) -> dict:
    """Accept a dict or a JSON string encoding one; return a dict."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError as e:
            raise ValueError(f"filter_tree is not valid JSON: {e}") from e
    if not isinstance(value, dict):
        raise ValueError("filter_tree must be a JSON object")
    return value


def uses_dimension(tree: dict, dimension: str) -> bool:
    """True when any leaf of the tree filters on the dimension."""
    if tree.get("dimension") == dimension:
        return True
    return any(uses_dimension(child, dimension)
               for child in tree.get("children") or []
               if isinstance(child, dict))
