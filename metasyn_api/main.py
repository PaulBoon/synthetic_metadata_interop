# This code is written by Alessandra Polimeno with the help of Lumo, the Proton AI assistant. 
# It is a fastAPI application that provides endpoints for using metasyn. 
# The main features are:
# - /fit-model/ : accepts a CSV file, fits a metasyn model, and returns the model as GMF (JSON)
# - /synthesize/ : accepts a fitted model (as JSON) and generates synthetic data
# The code does not include any authentication or security features, and is intended for local use or as a starting point for further development.
# After Alessandra Polimeno, I (Paul Boon) made extensive and shameless use of Copilot to assist in development.

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
from metasyn import MetaFrame
import asyncio
import tempfile
import os
import csv
import json
import logging
from fastapi.responses import JSONResponse
from typing import Optional

# Limits that protect against requests that exhaust memory or CPU; override with environment variables.
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", 100 * 1024 * 1024))
MAX_NUM_ROWS = int(os.environ.get("MAX_NUM_ROWS", 100_000))
# Per API worker process: how many fit/synthesize jobs run at once, and how long others wait for a slot.
MAX_CONCURRENT_JOBS = max(1, int(os.environ.get("MAX_CONCURRENT_JOBS", 2)))
JOB_WAIT_SECONDS = float(os.environ.get("JOB_WAIT_SECONDS", 30))

_job_slots = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

app = FastAPI(
    title="Metasyn API",
    description="API for generating synthetic data with metasyn"
)

class LimitRequestSize:
    """Rejects requests over MAX_UPLOAD_BYTES: by Content-Length when it is sent, otherwise while the body is read."""

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        too_large = HTTPException(
            status_code=413,
            detail=f"The request is larger than the limit of {self.max_bytes} bytes.",
        )
        length = next((v for k, v in scope["headers"] if k == b"content-length"), None)
        if length is not None:
            if not length.isdigit():
                response = JSONResponse(
                    status_code=400,
                    content={"detail": "Content-Length must be a non-negative integer."},
                )
                await response(scope, receive, send)
                return
            if int(length) > self.max_bytes:
                response = JSONResponse(status_code=413, content={"detail": too_large.detail})
                await response(scope, receive, send)
                return

        received = 0

        async def limited_receive():
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                # Raised while the route reads the body, so it is rendered as a normal 413 response.
                if received > self.max_bytes:
                    raise too_large
            return message

        await self.app(scope, limited_receive, send)

# Added before the CORS middleware so that CORS stays outermost and a 413 still gets CORS headers.
app.add_middleware(LimitRequestSize, max_bytes=MAX_UPLOAD_BYTES)

# Wildcard origin is incompatible with credentials, so allow_credentials stays False.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Request/Response models
# -----------------------------
class SynthesizeRequest(BaseModel):
    model_json: dict
    num_rows: Optional[int] = Field(
        default=None,
        ge=1,
        le=MAX_NUM_ROWS,
        description=f"Number of rows to generate, from 1 to {MAX_NUM_ROWS}. If omitted, uses the model row count, capped at {MAX_NUM_ROWS}.",
    )

class SynthesizeResponse(BaseModel):
    status: str
    synthetic_data_csv: str

# -----------------------------
# Blocking work, run in worker threads so the event loop keeps serving other requests
# -----------------------------
async def run_job(func, *args):
    try:
        await asyncio.wait_for(_job_slots.acquire(), timeout=JOB_WAIT_SECONDS)
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=503,
            detail="The server is busy with other requests; try again later.",
            headers={"Retry-After": str(int(JOB_WAIT_SECONDS))},
        )
    try:
        return await run_in_threadpool(func, *args)
    finally:
        _job_slots.release()

def _fit_model(source, tmp_dir: str) -> dict:
    # Auto-detect the delimiter; Dataverse serves ingested tabular files as TSV.
    df = pd.read_csv(source, sep=None, engine="python")
    model = MetaFrame.fit_dataframe(df)

    # metasyn expects file-based save/load
    json_path = os.path.join(tmp_dir, "model.json")
    model.save_json(json_path)
    with open(json_path, "r") as f:
        return json.load(f)

def _synthesize_csv(model_json: dict, num_rows: int) -> str:
    # The directory and everything in it is removed on exit, also when an error occurs
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Write model JSON to a file because metasyn expects a file path
        json_path = os.path.join(tmp_dir, "model.json")
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(model_json))

        try:
            model = MetaFrame.load_json(json_path)
        except Exception:
            logging.exception("Could not load model_json in synthesize_data")
            raise HTTPException(status_code=400, detail="model_json is not a valid metasyn (GMF) model.")
        synthetic_df = model.synthesize(num_rows)

        # Ensure we produce a CSV string regardless of the object API
        if hasattr(synthetic_df, "to_csv"):
            return synthetic_df.to_csv(index=False)
        if hasattr(synthetic_df, "write_csv"):
            out_path = os.path.join(tmp_dir, "synthetic.csv")
            synthetic_df.write_csv(out_path)
            with open(out_path, "r", encoding="utf-8") as f:
                return f.read()
        return str(synthetic_df)

# -----------------------------
# Endpoint: Fit model
# -----------------------------
@app.post("/fit-model/")
async def fit_model(
    file: UploadFile = File(
        ...,
        description=f"CSV/TSV file to fit. Maximum file and request size: {MAX_UPLOAD_BYTES} bytes.",
    )
):
    """
    Upload a CSV file, fit a metasyn model,
    and return the model as GMF (JSON).
    """

    try:
        # The directory and everything in it is removed on exit, also when an error occurs
        with tempfile.TemporaryDirectory() as tmp_dir:
            size = 0
            # Backstop for requests without a Content-Length header
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"The file is larger than the limit of {MAX_UPLOAD_BYTES} bytes.",
                    )
            await file.seek(0)

            # Fit directly from the already-spooled upload
            model_json_dict = await run_job(_fit_model, file.file, tmp_dir)

        return {
            "status": "success",
            "model_json": model_json_dict
        }

    except HTTPException:
        raise
    except (pd.errors.EmptyDataError, pd.errors.ParserError, csv.Error, UnicodeDecodeError):
        logging.exception("Could not read the uploaded file in fit_model")
        raise HTTPException(status_code=400, detail="The file could not be read as a CSV/TSV table.")
    except Exception:
        logging.exception("Error in fit_model")
        raise HTTPException(status_code=500, detail="Internal error while fitting the model.")


# -----------------------------
# Endpoint: Synthesize data
# -----------------------------
@app.post("/synthesize/")
async def synthesize_data(request: SynthesizeRequest = Body(...)):
    """
    Generate synthetic data from a metasyn model JSON (passed as dict in the request body).
    Returns a JSON response directly to avoid response_model validation issues.
    """
    try:
        model_json = request.model_json

        # If the client sent a JSON string for the model, parse it
        if isinstance(model_json, str):
            try:
                model_json = json.loads(model_json)
            except Exception:
                raise HTTPException(status_code=400, detail="model_json is not valid JSON")

        if not isinstance(model_json, dict):
            raise HTTPException(status_code=400, detail="model_json must be an object/dict")

        ## Determine number of rows to synthesize
        # This assumes that the model JSON contains an "n_rows" field that indicates the original number of rows used to fit the model.
        # If that field is missing, we default to 100 rows. 
        num_rows = request.num_rows
        if num_rows is None:
            v = model_json.get("n_rows")
            if isinstance(v, int) and v > 0:
                num_rows = int(v)
                logging.info(f"Inferred num_rows={num_rows} from model JSON 'n_rows'")
            else:
                logging.info("n_rows not found in model JSON; defaulting to 109")
                num_rows = 100
            if num_rows > MAX_NUM_ROWS:
                logging.info(f"Limiting inferred num_rows={num_rows} to {MAX_NUM_ROWS}")
                num_rows = MAX_NUM_ROWS
        else:
            num_rows = int(num_rows)

        csv_str = await run_job(_synthesize_csv, model_json, num_rows)

        return JSONResponse({"status": "success", "synthetic_data_csv": csv_str})

    except HTTPException:
        raise
    except Exception:
        logging.exception("Error in synthesize_data")
        raise HTTPException(status_code=500, detail="Internal error while generating synthetic data.")

# -----------------------------
# Root endpoint
# -----------------------------
@app.get("/")
async def root():
    return {"message": "Welcome to the Metasyn API!"}