from contextlib import asynccontextmanager
import sys
from pathlib import Path
# Optional workspace-local dependencies used by the supplied development setup.
sys.path.insert(0, str(Path(__file__).resolve().parent / '.deps'))
from fastapi import FastAPI,Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from database.migrations import migrate
from api.routes import router
from api.routes.health import router as health_router
from core.exceptions import AppError
from schemas.session import ErrorResponse
from agents.orchestrator import recover
import config

@asynccontextmanager
async def lifespan(app):
    migrate()
    recover()
    yield

app = FastAPI(title='SkillProof AI', version='2.0', lifespan=lifespan,
    responses={code:{'model':ErrorResponse} for code in [403,404,409,422,500,502,503]})
app.add_middleware(CORSMiddleware,allow_origins=config.CORS_ORIGINS,allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['Content-Type','X-Reviewer-Token'])
app.include_router(router, prefix='/api')
app.include_router(health_router)

@app.exception_handler(AppError)
async def application_error(request:Request,exc:AppError):
    return JSONResponse(status_code=exc.status,content={'error':{'code':exc.code,'message':exc.message,'details':[]}})

@app.exception_handler(RequestValidationError)
async def validation_error(request:Request,exc:RequestValidationError):
    details=[{'field':'.'.join(str(x) for x in e['loc']),'message':e['msg']} for e in exc.errors()]
    return JSONResponse(status_code=422,content={'error':{'code':'VALIDATION_ERROR','message':'Invalid request','details':details}})

@app.exception_handler(HTTPException)
async def http_error(request:Request,exc:HTTPException):
    return JSONResponse(status_code=exc.status_code,content={'error':{'code':'HTTP_ERROR','message':str(exc.detail),'details':[]}})

@app.exception_handler(Exception)
async def unexpected_error(request:Request,exc:Exception):
    return JSONResponse(status_code=500,content={'error':{'code':'INTERNAL_ERROR','message':'Internal operation failed','details':[]}})
