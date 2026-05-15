from altr_mcp.utils import api
from altr_mcp.settings import get_settings
import urllib.parse
import httpx


async def _paginate_altr_request(
        url: str,
        params: dict,
        auth,
        resource_type: str
        ) -> dict:
    method = "GET"
    last_evaluated_key = {}
    response = {"data": {resource_type: []}}
    while last_evaluated_key is not None:
        temp_response = await api.request(method, url, auth, params)
        contiguous_id = temp_response.get("contiguous_id", None)
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        else:
            last_evaluated_key = None
        response["data"][resource_type] += temp_response.get(resource_type, [])
    return response


async def get_classifiers(params: dict, auth) -> dict:
    url = f"{get_settings().classification_base_url}/v1/classifiers"
    return await _paginate_altr_request(url, params, auth, "classifiers")


async def create_classifier(params: dict, auth) -> dict:
    url = f"{get_settings().classification_base_url}/v1/classifiers"
    data = {
        "classifier_name": params.get("classifier_name"),
        "description": params.get("description"),
        "minimum_threshold": params.get("minimum_threshold"),
        "pattern": params.get("pattern"),
        "sample_size": params.get("sample_size"),
    }
    return await api.request("POST", url, auth, {}, data)


async def delete_classifier(params: dict, auth) -> dict:
    classifier_name = params.get("classifier_name")
    encoded_name = urllib.parse.quote(classifier_name, safe='')
    url = (
        f"{get_settings().classification_base_url}"
        f"/v1/classifiers/{encoded_name}"
    )
    return await api.request("DELETE", url, auth, {})


async def get_collections(params: dict, auth) -> dict:
    url = f"{get_settings().classification_base_url}/v1/collections"
    return await _paginate_altr_request(url, params, auth, "collections")


async def create_collection(params: dict, auth) -> dict:
    url = f"{get_settings().classification_base_url}/v1/collections"
    data = {
        "collection_name": params.get("collection_name"),
        "description": params.get("description", ""),
    }
    return await api.request("POST", url, auth, {}, data)


async def delete_collection(params: dict, auth) -> dict:
    collection_name = params.get("collection_name")
    encoded_name = urllib.parse.quote(collection_name, safe='')
    url = (
        f"{get_settings().classification_base_url}"
        f"/v1/collections/{encoded_name}"
    )
    return await api.request("DELETE", url, auth, {})


async def append_classifiers_to_collection(
        collection_name: str, classifier_names: list, auth) -> dict:
    encoded_name = urllib.parse.quote(collection_name, safe='')
    url = (
        f"{get_settings().classification_base_url}"
        f"/v1/collections/{encoded_name}/classifiers/append"
    )
    data = {"classifier_names": classifier_names}
    return await api.request("PATCH", url, auth, {}, data=data)


async def remove_classifiers_from_collection(
        collection_name: str, classifier_names: list, auth) -> dict:
    encoded_name = urllib.parse.quote(collection_name, safe='')
    url = (
        f"{get_settings().classification_base_url}"
        f"/v1/collections/{encoded_name}/classifiers/remove"
    )
    data = {"classifier_names": classifier_names}
    return await api.request("PATCH", url, auth, {}, data=data)


async def get_jobs(params: dict, auth) -> dict:
    url = f"{get_settings().classification_base_url}/v1/jobs"
    return await _paginate_altr_request(url, params, auth, "jobs")


async def update_job_status(params: dict, auth, job_id: str) -> dict:
    url = f"{get_settings().classification_base_url}/v1/jobs/{job_id}"
    data = {"status": params.get("status")}
    return await api.request("PATCH", url, auth, {}, data)


async def create_job(params: dict, auth) -> dict:
    url = f"{get_settings().classification_base_url}/v1/jobs"
    data = {
        "job_type": params.get("job_type"),
        "database_id": params.get("database_id"),
        "collection_name": params.get("collection_name"),
    }
    return await api.request("POST", url, auth, {}, data)


async def create_databricks_job(params: dict, auth) -> dict:
    url = f"{get_settings().classification_base_url}/v1/jobs/databricks"
    data = {"database_id": params.get("database_id")}
    return await api.request("POST", url, auth, {}, data)


async def _create_job_report(params: dict, auth, job_id: str) -> dict:
    encoded_id = urllib.parse.quote(job_id, safe='')
    url = (
        f"{get_settings().classification_base_url}"
        f"/v1/jobs/{encoded_id}/report"
    )
    return await api.request("POST", url, auth, params, {})


async def get_job_report(params: dict, auth, job_id: str) -> dict:
    job_url = await _create_job_report(params, auth, job_id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(job_url["url"])
        return resp.json()
