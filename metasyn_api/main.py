# This code is written by Alessandra Polimeno with the help of Lumo, the Proton AI assistant. 
# It is a fastAPI application that provides endpoints for using metasyn. 
# The main features are:
# - /fit-model/ : accepts a CSV file, fits a metasyn model, and returns the model as GMF (JSON)
# - /synthesize/ : accepts a fitted model (as JSON) and generates synthetic data
# The code does not include any authentication or security features, and is intended for local use or as a starting point for further development.


from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from metasyn import MetaFrame
import tempfile
import os
import json
import logging
from fastapi.responses import JSONResponse
from typing import Optional

app = FastAPI(
    title="Metasyn API",
    description="API for generating synthetic data with metasyn"
)

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
    num_rows: Optional[int] = None

class SynthesizeResponse(BaseModel):
    status: str
    synthetic_data_csv: str

# -----------------------------
# Endpoint: Fit model
# -----------------------------
@app.post("/fit-model/")
async def fit_model(file: UploadFile = File(...)):
    """
    Upload a CSV file, fit a metasyn model,
    and return the model as GMF (JSON).
    """

    try:
        # Save uploaded CSV to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Load data and fit model
        # Auto-detect the delimiter; Dataverse serves ingested tabular files as TSV.
        df = pd.read_csv(tmp_path, sep=None, engine="python")
        model = MetaFrame.fit_dataframe(df)

        # Save model to a temporary JSON file (metasyn expects file-based save/load)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_json:
            json_path = tmp_json.name
        model.save_json(json_path)

        # Read JSON back into a Python dict so it can be returned in the response
        with open(json_path, "r") as f:
            model_json_dict = json.load(f)

        # Cleanup temp files
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        try:
            os.remove(json_path)
        except Exception:
            pass

        return {
            "status": "success",
            "model_json": model_json_dict
        }

    except Exception as e:
        logging.exception("Error in fit_model")
        raise HTTPException(status_code=500, detail=str(e))


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
        else:
            num_rows = int(num_rows)

        # Write model JSON to a temp file because metasyn expects a file path
        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp_json:
            json_path = tmp_json.name
            tmp_json.write(json.dumps(model_json).encode("utf-8"))

        # Load the model and synthesize
        model = MetaFrame.load_json(json_path)
        synthetic_df = model.synthesize(num_rows)

        # Ensure we produce a CSV string regardless of the object API
        if hasattr(synthetic_df, "to_csv"):
            csv_str = synthetic_df.to_csv(index=False)
        elif hasattr(synthetic_df, "write_csv"):
            # write to temp file then read
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_out:
                out_path = tmp_out.name
            synthetic_df.write_csv(out_path)
            with open(out_path, "r", encoding="utf-8") as f:
                csv_str = f.read()
            try:
                os.remove(out_path)
            except Exception:
                pass
        else:
            csv_str = str(synthetic_df)

        # Cleanup
        try:
            os.remove(json_path)
        except Exception:
            pass

        return JSONResponse({"status": "success", "synthetic_data_csv": csv_str})

    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error in synthesize_data")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------
# Root endpoint
# -----------------------------
@app.get("/")
async def root():
    return {"message": "Welcome to the Metasyn API!"}