from fastapi import Request
from fastapi.responses import JSONResponse

from app.repo.scope import ScopeError


class NotFound(LookupError):
    pass


class Conflict(Exception):
    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.detail = detail or {}


class Forbidden(PermissionError):
    pass


class NotLoggedIn(PermissionError):
    pass


def install(app) -> None:
    def handler(status):
        async def _h(request: Request, exc: Exception):
            body = {"error": str(exc)}
            if isinstance(exc, Conflict):
                body.update(exc.detail)
            return JSONResponse(body, status_code=status)
        return _h

    app.add_exception_handler(NotLoggedIn, handler(401))
    app.add_exception_handler(ScopeError, handler(403))
    app.add_exception_handler(Forbidden, handler(403))
    app.add_exception_handler(NotFound, handler(404))
    app.add_exception_handler(Conflict, handler(409))
    app.add_exception_handler(ValueError, handler(400))
    app.add_exception_handler(RuntimeError, handler(503))  # missing configuration / upstream unavailable

    from pymongo.errors import PyMongoError
    import httpx
    async def database_error(request, exc):
        return JSONResponse({'error':'Database unavailable. Check MONGODB_URI, Atlas network access and setup.'},status_code=503)
    async def upstream_error(request, exc):
        return JSONResponse({'error':'Provider request failed. Check credentials, quota, model access and connectivity.'},status_code=502)
    app.add_exception_handler(PyMongoError, database_error)
    app.add_exception_handler(httpx.HTTPError, upstream_error)
