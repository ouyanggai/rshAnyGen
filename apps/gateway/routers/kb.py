"""Knowledge Base Proxy API"""
from fastapi import APIRouter, HTTPException, Request, Response, Depends
import httpx

from apps.shared.config_loader import ConfigLoader
from apps.shared.logger import LogManager
from apps.gateway.middleware.auth import require_any_role

config = ConfigLoader()
logger = LogManager("gateway").get_logger()

router = APIRouter(prefix="/api/v1/kb", tags=["kb"], dependencies=[Depends(require_any_role(["admin"]))])
router.redirect_slashes = False

RAG_PIPELINE_URL = f"http://localhost:{config.get('ports.rag_pipeline', 9305)}"


async def _proxy_request(request: Request, target_url: str) -> Response:
    logger.info(f"Proxying {request.method} {request.url} to {target_url}")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
            content = await request.body()

            req_headers = dict(request.headers)
            req_headers.pop("host", None)
            req_headers.pop("content-length", None)

            response = await client.request(
                method=request.method,
                url=target_url,
                headers=req_headers,
                content=content,
                params=request.query_params,
            )

            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )
    except Exception as e:
        logger.error(f"Proxy error to {target_url}: {e}")
        raise HTTPException(status_code=502, detail=f"RAG Service unavailable: {str(e)}")


@router.api_route("", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_kb_root(request: Request):
    return await _proxy_request(request, f"{RAG_PIPELINE_URL}/api/v1/kb")


@router.api_route("/", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_kb_root_slash(request: Request):
    return await _proxy_request(request, f"{RAG_PIPELINE_URL}/api/v1/kb")


@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_kb(request: Request, path: str):
    return await _proxy_request(request, f"{RAG_PIPELINE_URL}/api/v1/kb/{path}")
