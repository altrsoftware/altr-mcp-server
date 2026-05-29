from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from altr_mcp.settings import get_settings
from altr_mcp.utils import critical_tokenization
from altr_mcp.utils.logging import log_tool

_MAX_VALUES = 1024


def _encode_values(values: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Translate user-supplied key names to field000..fieldNNN for the API.

    Returns:
        encoded: API-ready dict with field000... keys.
        key_map: Mapping from field000... back to original keys.
    """
    keys = list(values.keys())
    encoded = {
        f"field{i:03d}": values[k] for i, k in enumerate(keys)
    }
    key_map = {
        f"field{i:03d}": k for i, k in enumerate(keys)
    }
    return encoded, key_map


def _decode_response(response: dict, key_map: dict[str, str]) -> dict:
    """Translate API field000... keys back to original user-supplied keys."""
    return {
        key_map.get(field_key, field_key): val
        for field_key, val in response.items()
    }


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    @log_tool
    async def critical_tokenize(
            values: dict[str, str],
            deterministic: bool = False
            ) -> dict:
        """Tokenize plaintext values using ALTR critical tokenization.

        Replaces plaintext strings with critical tokens
        (format: `token_XXXX...`, 64+ chars). Tokens can be detokenized
        later. Deterministic tokenization produces the same token for the
        same input value.

        Maximum 1024 values per call. Each value must be under 128 UTF-8
        code units.

        Args:
            values: Dict mapping user-defined keys to plaintext strings
                to tokenize (e.g. {"ssn": "123-45-6789",
                "email": "user@example.com"}).
            deterministic: If True, the same plaintext always produces
                the same token. Default False (random token each time).
        """
        settings = get_settings()
        encoded, key_map = _encode_values(values)
        response = await critical_tokenization.tokenize(
            settings.auth, encoded, deterministic)
        if isinstance(response, dict) and not response.get("success") is False:
            decoded = _decode_response(response, key_map)
            return {"success": True, "data": decoded, "error": None}
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def critical_detokenize(tokens: dict[str, str]) -> dict:
        """Detokenize critical tokens to recover plaintext values.

        Fails if any value in `tokens` is not a valid critical token
        (format: `token_XXXX...`, 64+ chars). For mixed inputs (tokens
        and non-tokens), use `critical_partial_detokenize` instead.

        Maximum 1024 values per call. Tokens are case-sensitive.

        Args:
            tokens: Dict mapping user-defined keys to critical tokens
                (e.g. {"ssn": "token_abc123...",
                "email": "token_xyz456..."}).
        """
        settings = get_settings()
        encoded, key_map = _encode_values(tokens)
        response = await critical_tokenization.detokenize(
            settings.auth, encoded)
        if isinstance(response, dict) and not response.get("success") is False:
            decoded = _decode_response(response, key_map)
            return {"success": True, "data": decoded, "error": None}
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def critical_partial_detokenize(values: dict[str, str]) -> dict:
        """Detokenize critical tokens, passing non-token values through unchanged.

        Unlike `critical_detokenize`, this does not fail when non-token
        values are present. Valid tokens are detokenized; all other values
        are returned as-is.

        Maximum 1024 values per call.

        Args:
            values: Dict mapping user-defined keys to critical tokens or
                plaintext strings. Non-token values are passed through
                (e.g. {"ssn": "token_abc123...",
                "name": "already-plaintext"}).
        """
        settings = get_settings()
        encoded, key_map = _encode_values(values)
        response = await critical_tokenization.partial_detokenize(
            settings.auth, encoded)
        if isinstance(response, dict) and not response.get("success") is False:
            decoded = _decode_response(response, key_map)
            return {"success": True, "data": decoded, "error": None}
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def critical_delete_tokens(tokens: dict[str, str]) -> dict:
        """Delete critical tokens, removing them from the token store.

        Invalid tokens are silently ignored (no failure). If a deleted
        deterministic token is re-tokenized with the same plaintext, a new
        token is generated.

        Maximum 1024 values per call.

        Args:
            tokens: Dict mapping user-defined keys to critical tokens to
                delete (e.g. {"ssn": "token_abc123...",
                "email": "token_xyz456..."}).
        """
        settings = get_settings()
        encoded, key_map = _encode_values(tokens)
        response = await critical_tokenization.delete_tokens(
            settings.auth, encoded)
        if isinstance(response, dict) and not response.get("success") is False:
            decoded = _decode_response(response, key_map)
            return {"success": True, "data": decoded, "error": None}
        return {"success": True, "data": response, "error": None}
