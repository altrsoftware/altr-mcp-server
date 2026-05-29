from fastmcp import FastMCP
from mcp.types import ToolAnnotations
from altr_mcp.utils.logging import log_tool
from altr_mcp.settings import get_settings
from altr_mcp.utils import key_management


def register(mcp: FastMCP) -> None:
    # ── Tweaks ────────────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_tweaks(
            contiguous_id: str | None = None,
            limit: int | None = None,
            contain: str | None = None,
            status: str | None = None,
            ) -> dict:
        """List FPE tweaks for the organization.

        Tweaks are named random values used in format-preserving encryption.
        Results are paginated; use `contiguous_id` from the response to fetch
        subsequent pages.

        Args:
            contiguous_id: Pagination cursor returned by a prior call.
            limit: Max number of tweaks to return.
            contain: Filter tweaks whose name contains this substring.
            status: Filter by status — "active", "deactivated", or "any"
                (default "any").
        """
        settings = get_settings()
        params = {}
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        if limit is not None:
            params["limit"] = limit
        if contain is not None:
            params["contain"] = contain
        if status is not None:
            params["status"] = status
        response = await key_management.list_tweaks(settings.auth, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_tweak(
            name: str,
            sequence: str | None = None,
            ) -> dict:
        """Get a single FPE tweak by name.

        Returns the current (latest) version of the tweak. Pass `sequence`
        to retrieve a specific historical version instead.

        Args:
            name: Name of the tweak.
            sequence: Version sequence identifier. Omit to get the latest.
        """
        settings = get_settings()
        params = {}
        if sequence is not None:
            params["sequence"] = sequence
        response = await key_management.get_tweak(settings.auth, name, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_tweak(name: str) -> dict:
        """Create a new FPE tweak.

        Generates a new named random value for use in format-preserving
        encryption. The tweak name must not have leading or trailing spaces.

        Args:
            name: Name for the new tweak (1–256 characters, no leading or
                trailing spaces).
        """
        settings = get_settings()
        response = await key_management.create_tweak(
            settings.auth, {"name": name})
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def deactivate_tweak(name: str, sequence: str) -> dict:
        """Deactivate a specific version of an FPE tweak.

        Deactivated tweaks cannot be used for new FPE operations. Use
        `get_tweak` to discover the sequence identifier of a tweak version.

        Args:
            name: Name of the tweak.
            sequence: Version sequence identifier to deactivate.
        """
        settings = get_settings()
        response = await key_management.deactivate_tweak(
            settings.auth, name, sequence)
        return {"success": True, "data": response, "error": None}

    # ── Keys ──────────────────────────────────────────────────────────────────

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def list_keys(
            namespace: str,
            contiguous_id: str | None = None,
            limit: int | None = None,
            contain: str | None = None,
            status: str | None = None,
            ) -> dict:
        """List FPE keys within a namespace.

        Results are paginated; use `contiguous_id` from the response to fetch
        subsequent pages. The `fpe` namespace is most common for
        format-preserving encryption keys.

        Args:
            namespace: Namespace to list keys from (e.g. "fpe").
            contiguous_id: Pagination cursor returned by a prior call.
            limit: Max number of keys to return.
            contain: Filter keys whose name contains this substring.
            status: Filter by status — "active", "deactivated", or "any"
                (default "any").
        """
        settings = get_settings()
        params = {}
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        if limit is not None:
            params["limit"] = limit
        if contain is not None:
            params["contain"] = contain
        if status is not None:
            params["status"] = status
        response = await key_management.list_keys(
            settings.auth, namespace, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
    @log_tool
    async def get_key(
            namespace: str,
            name: str,
            sequence: str | None = None,
            ) -> dict:
        """Get a single FPE key by namespace and name.

        Returns the current (latest) version of the key. Pass `sequence`
        to retrieve a specific historical version.

        Args:
            namespace: Namespace where the key resides (e.g. "fpe").
            name: Name of the key.
            sequence: Version sequence identifier. Omit to get the latest.
        """
        settings = get_settings()
        params = {}
        if sequence is not None:
            params["sequence"] = sequence
        response = await key_management.get_key(
            settings.auth, namespace, name, params)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def create_key(namespace: str, name: str) -> dict:
        """Create a new FPE encryption key.

        Generates a new named key in the specified namespace. Keys are
        used for format-preserving encryption operations. The name and
        namespace must not have leading or trailing spaces.

        Args:
            namespace: Namespace for the key (e.g. "fpe"). Must not have
                leading or trailing spaces.
            name: Name for the new key (1–256 characters, no leading or
                trailing spaces).
        """
        settings = get_settings()
        response = await key_management.create_key(
            settings.auth, {"name": name, "namespace": namespace})
        return {"success": True, "data": response, "error": None}

    @mcp.tool(annotations=ToolAnnotations(destructiveHint=True))
    @log_tool
    async def deactivate_key(
            namespace: str, name: str, sequence: str) -> dict:
        """Deactivate a specific version of an FPE key.

        Deactivated keys cannot be used for new encryption operations.
        Use `get_key` to discover the sequence identifier for a key version.

        Args:
            namespace: Namespace where the key resides.
            name: Name of the key.
            sequence: Version sequence identifier to deactivate.
        """
        settings = get_settings()
        response = await key_management.deactivate_key(
            settings.auth, namespace, name, sequence)
        return {"success": True, "data": response, "error": None}

    @mcp.tool()
    @log_tool
    async def rotate_key(
            namespace: str, name: str, sequence: str) -> dict:
        """Rotate the envelope key for a specific FPE key version.

        Envelope rotation re-wraps the data key under a new envelope key
        without changing the underlying encryption material. Use this for
        key rotation compliance requirements.

        Args:
            namespace: Namespace where the key resides.
            name: Name of the key.
            sequence: Version sequence identifier of the key to rotate.
        """
        settings = get_settings()
        response = await key_management.rotate_key(
            settings.auth, namespace, name, sequence)
        return {"success": True, "data": response, "error": None}
