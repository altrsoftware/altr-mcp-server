from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from altr_mcp.settings import get_settings
from altr_mcp.utils import vault_tokenization
from altr_mcp.utils.logging import log_tool

_MAX_VALUES = 4096


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
    async def vault_tokenize(
            values: dict[str, str],
            deterministic: bool = False
            ) -> dict:
        """Tokenize plaintext values using ALTR vaulted tokenization.

        Replaces plaintext strings with vault tokens
        (format: `vaultd_XXXX...`). Tokens are stored in the ALTR vault
        and can be detokenized later. Deterministic tokenization produces
        the same token for the same input value.

        Rate-limited to 492 requests/month and 50 requests/second.
        Maximum 4096 values per call. Each value must be under 1024
        characters.

        Args:
            values: Dict mapping user-defined keys to plaintext strings
                to tokenize (e.g. {"ssn": "123-45-6789",
                "email": "user@example.com"}).
            deterministic: If True, the same plaintext always produces
                the same token. Default False (random token each time).
        """
        settings = get_settings()
        encoded, key_map = _encode_values(values)
        response = await vault_tokenization.tokenize(
            settings.auth, encoded, deterministic)
        if (isinstance(response, dict)
                and response.get("success") is True
                and "data" in response):
            decoded = _decode_response(response["data"], key_map)
            return {"success": True, "data": decoded, "error": None}
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def vault_detokenize(tokens: dict[str, str]) -> dict:
        """Detokenize vault tokens to recover plaintext values.

        Fails if any value in `tokens` is not a valid vault token
        (format: `vaultd_XXXX...`). For mixed inputs (tokens and
        non-tokens), use `vault_partial_detokenize` instead.

        Rate-limited to 492 requests/month and 50 requests/second.
        Maximum 4096 values per call. Tokens are case-sensitive.

        Args:
            tokens: Dict mapping user-defined keys to vault tokens
                (e.g. {"ssn": "vaultd_abc123...",
                "email": "vaultd_xyz456..."}).
        """
        settings = get_settings()
        encoded, key_map = _encode_values(tokens)
        response = await vault_tokenization.detokenize(settings.auth, encoded)
        if (isinstance(response, dict)
                and response.get("success") is True
                and "data" in response):
            decoded = _decode_response(response["data"], key_map)
            return {"success": True, "data": decoded, "error": None}
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def vault_partial_detokenize(values: dict[str, str]) -> dict:
        """Detokenize vault tokens, passing non-token values through unchanged.

        Unlike `vault_detokenize`, this does not fail when non-token values
        are present. Valid tokens are detokenized; all other values are
        returned as-is.

        Rate-limited to 492 requests/month and 50 requests/second.
        Maximum 4096 values per call.

        Args:
            values: Dict mapping user-defined keys to vault tokens or
                plaintext strings. Non-token values are passed through
                (e.g. {"ssn": "vaultd_abc123...",
                "name": "already-plaintext"}).
        """
        settings = get_settings()
        encoded, key_map = _encode_values(values)
        response = await vault_tokenization.partial_detokenize(
            settings.auth, encoded)
        if (isinstance(response, dict)
                and response.get("success") is True
                and "data" in response):
            decoded = _decode_response(response["data"], key_map)
            return {"success": True, "data": decoded, "error": None}
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def vault_delete_tokens(tokens: dict[str, str]) -> dict:
        """Permanently delete vault tokens from the ALTR vault.

        Deleted tokens cannot be detokenized. If a deleted deterministic
        token is re-tokenized with the same plaintext, a new token is
        generated.

        Rate-limited to 492 requests/month and 50 requests/second.
        Maximum 4096 values per call.

        Args:
            tokens: Dict mapping user-defined keys to vault tokens to
                delete (e.g. {"ssn": "vaultd_abc123...",
                "email": "vaultd_xyz456..."}).
        """
        settings = get_settings()
        encoded, key_map = _encode_values(tokens)
        response = await vault_tokenization.delete_tokens(settings.auth, encoded)
        if (isinstance(response, dict)
                and response.get("success") is True
                and "data" in response):
            decoded = _decode_response(response["data"], key_map)
            return {"success": True, "data": decoded, "error": None}
        return {"success": True, "data": response, "error": None}
