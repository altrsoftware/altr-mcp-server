import structlog
from altr_mcp.utils import api
from altr_mcp.settings import get_settings
import urllib.parse
import httpx

logger = structlog.get_logger(__name__)


async def _paginate_altr_request(
        url: str,
        params: dict,
        auth,
        resource_type: str
        ) -> dict:
    method = "GET"
    last_evalutated_key = {}
    response = {"data": {resource_type: []}}
    while last_evalutated_key is not None:
        temp_response = await api.request(method, url, auth, params)
        contiguous_id = temp_response.get("contiguous_id", None)
        if contiguous_id is not None:
            params["contiguous_id"] = contiguous_id
        else:
            last_evalutated_key = None
        response["data"][resource_type] += temp_response.get(resource_type, [])
    return response


async def get_classifiers(params: dict, auth, org_id: str) -> dict:
    url = f"{get_settings().classification_base_url}/v1/classifiers"
    response = await _paginate_altr_request(url, params, auth, "classifiers")
    return response


async def get_classifier(params: dict, auth, org_id: str) -> dict:
    url = f"{get_settings().classification_base_url}/v1/classifiers"
    method = "GET"
    params = {
        "classifier_name": params.get("classifier_name")
    }
    response = await api.request(method, url, auth, params)
    return response


async def create_classifier(params: dict, auth, org_id: str) -> dict:
    url = f"{get_settings().classification_base_url}/v1/classifiers"
    method = "POST"
    data = {
        "classifier_name": params.get("classifier_name"),
        "description": params.get("description"),
        "minimum_threshold": params.get("minimum_threshold"),
        "pattern": params.get("pattern"),
        "sample_size": params.get("sample_size"),
    }
    response = await api.request(method, url, auth, {}, data)
    return response


async def delete_classifier(params: dict, auth, org_id: str) -> dict:
    classifier_name = params.get("classifier_name")
    encoded_name = urllib.parse.quote(classifier_name, safe='')
    url = (
        f"{get_settings().classification_base_url}"
        f"/v1/classifiers/{encoded_name}"
    )
    method = "DELETE"
    response = await api.request(method, url, auth, {})
    return response


def format_classifiers(classifiers: dict) -> list:
    formatted_strs = []
    try:
        if not classifiers:
            return formatted_strs
        if not isinstance(classifiers, dict):
            return formatted_strs
        data = classifiers.get("data", {})
        if not isinstance(data, dict):
            return formatted_strs
        classifier_list = data.get("classifiers", [])
        if not classifier_list:
            return formatted_strs
        for classifier in classifier_list:
            if not isinstance(classifier, dict):
                continue
            formatted_str = (
                f"Name: {classifier.get('classifier_name', 'N/A')}\n" +
                f"Description: {classifier.get('description', 'N/A')}\n" +
                f"Pattern: {classifier.get('pattern', 'N/A')}\n" +
                "Minimum Threshold: " +
                f"{classifier.get('minimum_threshold', 'N/A')}\n" +
                f"Sample Size: {classifier.get('sample_size', 'N/A')}"
            )
            formatted_strs.append(formatted_str)
    except Exception as e:
        return [f"Error formatting classifiers: {str(e)}"]
    return formatted_strs


async def get_collections(params: dict, auth, org_id: str) -> dict:
    url = f"{get_settings().classification_base_url}/v1/collections"
    response = await _paginate_altr_request(url, params, auth, "collections")
    return response


async def get_collection(params: dict, auth, org_id: str) -> dict:
    url = f"{get_settings().classification_base_url}/v1/collections"
    method = "GET"
    params = {
        "collection_name": params.get("collection_name")
    }
    response = await api.request(method, url, auth, params)
    return response


async def create_collection(params: dict, auth, org_id: str) -> dict:
    url = f"{get_settings().classification_base_url}/v1/collections"
    method = "POST"
    data = {
        "collection_name": params.get("collection_name"),
        "description": params.get("description", ""),
    }
    response = await api.request(method, url, auth, {}, data)
    return response


async def delete_collection(params: dict, auth, org_id: str) -> dict:
    collection_name = params.get("collection_name")
    encoded_name = urllib.parse.quote(collection_name, safe='')
    url = (
        f"{get_settings().classification_base_url}"
        f"/v1/collections/{encoded_name}"
    )
    method = "DELETE"
    response = await api.request(method, url, auth, {})
    return response


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


def format_collections(collections: dict) -> list:
    formatted_strs = []
    try:
        if not collections:
            return formatted_strs
        if not isinstance(collections, dict):
            return formatted_strs
        data = collections.get("data", {})
        if not isinstance(data, dict):
            return formatted_strs
        collection_list = data.get("collections", [])
        if not collection_list:
            return formatted_strs
        for collection in collection_list:
            if not isinstance(collection, dict):
                continue
            formatted_str = (
                f"Name: {collection.get('collection_name', 'N/A')}\n" +
                f"Description: {collection.get('description', 'N/A')}"
            )
            if 'classifiers' in collection:
                formatted_str += (
                    "\nClassifiers: "
                    f"{len(collection.get('classifiers', []))}"
                )
            formatted_strs.append(formatted_str)
    except Exception as e:
        return [f"Error formatting collections: {str(e)}"]
    return formatted_strs


async def get_jobs(
        params: dict, auth, org_id: str, job_id: str = None) -> dict:
    url = f"{get_settings().classification_base_url}/v1/jobs"
    if job_id:  # get a specific job
        encoded_id = urllib.parse.quote(job_id, safe='')
        url += f"/{encoded_id}"
    response = await _paginate_altr_request(url, params, auth, "jobs")
    return response


async def update_job_status(
        params: dict, auth, org_id: str, job_id: str) -> dict:
    url = f"{get_settings().classification_base_url}/v1/jobs/{job_id}"
    method = "PATCH"
    data = {
        "status": params.get("status"),
    }
    response = await api.request(method, url, auth, {}, data)
    return response


async def create_job(params: dict, auth, org_id: str) -> dict:
    url = f"{get_settings().classification_base_url}/v1/jobs"
    method = "POST"
    data = {
        "job_type": params.get("job_type"),
        "database_id": params.get("database_id"),
        "collection_name": params.get("collection_name"),
    }
    response = await api.request(method, url, auth, {}, data)
    return response


async def _create_job_report(
        params: dict, auth, org_id: str, job_id: str) -> dict:
    encoded_id = urllib.parse.quote(job_id, safe='')
    url = (
        f"{get_settings().classification_base_url}"
        f"/v1/jobs/{encoded_id}/report"
    )
    method = "POST"
    data = {}
    response = await api.request(method, url, auth, params, data)
    return response


async def get_job_report(params: dict, auth, org_id: str, job_id: str) -> dict:
    job_url = await _create_job_report(params, auth, org_id, job_id)
    async with httpx.AsyncClient() as client:
        resp = await client.get(job_url["url"])
        return resp.json()


def format_jobs(jobs: dict) -> list:
    formatted_strs = []
    try:
        if not jobs:
            return formatted_strs
        data = jobs.get("data", {})
        if not isinstance(data, dict):
            return formatted_strs
        job_list = data.get("jobs", [])
        if not job_list:
            return formatted_strs
        for job in job_list:
            if not isinstance(job, dict):
                continue
            formatted_str = (
                f"Job ID: {job.get('job_id', 'N/A')}\n" +
                f"Status: {job.get('status', 'N/A')}\n" +
                f"Job Type: {job.get('job_type', 'N/A')}"
            )
            if job.get('database_id') is not None:
                formatted_str += f"\nDatabase ID: {job.get('database_id')}"
            if job.get('classification_type') is not None:
                formatted_str += (
                    "\nClassification Type: "
                    f"{job.get('classification_type')}"
                )
            if job.get('start_time'):
                formatted_str += f"\nStart Time: {job.get('start_time')}"
            if job.get('end_time'):
                formatted_str += f"\nEnd Time: {job.get('end_time')}"
            formatted_strs.append(formatted_str)
    except Exception as e:
        return [f"Error formatting jobs: {str(e)}"]
    return formatted_strs
