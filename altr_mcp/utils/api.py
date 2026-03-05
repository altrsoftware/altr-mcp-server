import httpx


async def request(
        method: str, url: str, auth, params: dict, data=None) -> dict:
    """
    Generic HTTP helper that sends requests
        and returns consistent dict responses.
    Treats non-JSON/empty 2xx responses as success.
    """
    params = params or {}

    async with httpx.AsyncClient(auth=auth, timeout=30.0) as client:
        try:
            if method == "DELETE":
                request_kwargs = {"method": method, "url": url}
            else:
                request_kwargs = {
                    "method": method,
                    "url": url,
                    "params": params
                }

            if data is not None:
                request_kwargs[
                    "json"
                    if method.upper()
                    in {"POST", "PUT", "PATCH"}
                    else "data"
                ] = data

            response = await client.request(**request_kwargs)
            response.raise_for_status()

            # Handle empty responses
            if not response.content:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "raw": None
                }

            # Try JSON, fall back to text
            try:
                body = response.json()
            except ValueError:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "raw": response.text
                }

            # Return dict as-is, wrap other types
            return body if isinstance(body, dict) else {
                "success": True,
                "status_code": response.status_code,
                "data": body,
            }

        except httpx.HTTPStatusError as e:
            status = e.response.status_code if e.response else None
            return {
                "success": False,
                "status_code": status,
                "message": str(e)
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"{type(e).__name__}: {str(e)}"
            }
