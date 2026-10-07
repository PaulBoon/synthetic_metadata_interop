# Metasyn API prototype 

This folder contains the code for a fastAPI wrapper for metasyn. It exposes two endpoints: 
- /fit-model/ : accepts a CSV file, fits a metasyn model, and returns the model as GMF (JSON)
- /synthesize/ : accepts a fitted model (as JSON) and generates synthetic data as a CSV file

It does not include any authentication or security features, and is intended for local use and as a starting point for further development.

## Quick start

With [uv](https://docs.astral.sh/uv/) installed:
```bash
uv sync --extra frontend          # once: creates .venv with the locked dependencies
uv run uvicorn main:app --reload  # API on http://127.0.0.1:8000
uv run python frontend/app_flask.py  # optional UI on http://127.0.0.1:5000
```

Or with Docker, which runs the API and the UI in one container:
```bash
docker compose up -d --build
```

## File description 
- `Dockerfile`, `docker-entrypoint.sh` and `.dockerignore` build the container that runs both the API (port 8000) and the Flask UI (port 5000)
- `docker-compose.yml` runs that container with hardened settings
- `main.py` contains the API app 
- `pyproject.toml` and `uv.lock` define the dependencies (`frontend` extra: Flask UI); `requirements.txt` is generated from them for pip users
- `.python-version` pins the Python version used by uv
- `data/input_data.csv` contains a file from an open dataset in the SSH Data Station that is used as a testing example
- `data/synthetic.csv` contains the resulting synthetic version of the input data

## Instructions 

### Install packages
Install the locked dependencies with uv; this creates the `.venv` virtual environment and downloads the pinned Python version if needed. There is no need to activate the environment when using `uv run`. 
```bash
uv sync --extra frontend
```
Without the UI, leave out `--extra frontend`. 

The `metasyn` version is pinned to `2.0.0` because newer versions produce a different GMF structure (the tool and UI expect GMF 1.1). 

Without uv you can use pip: `pip install -r requirements.txt`. 

### Start the API

You can start the API with the following command: 

```bash
uv run uvicorn main:app --reload
```

You can now see the documentation here and test the endpoints: 

```
http://127.0.0.1:8000/docs
```

### Run with Docker

The image contains the API (uvicorn, port 8000) and the UI (gunicorn, port 5000); the UI forwards its requests to the API inside the container. 

```bash
docker compose up -d --build   # start
docker compose down            # stop
```

The compose file ([docker-compose.yml](docker-compose.yml)) applies these settings:
- ports are published on `127.0.0.1` only, so the service is not reachable from other machines
- read-only root filesystem, with small writable tmpfs mounts for `/tmp` and the home directory
- all Linux capabilities dropped and `no-new-privileges` enabled
- limits on processes (`pids_limit`), memory (`mem_limit`) and CPUs (`cpus`)
- the request limits below as environment variables

Without compose, a basic run (without the other settings above) is:
```bash
docker build -t metasyn-api .
docker run --rm -p 127.0.0.1:8000:8000 -p 127.0.0.1:5000:5000 metasyn-api
```

- UI: `http://127.0.0.1:5000`
- API docs: `http://127.0.0.1:8000/docs`

Port 8000 needs to be published for tools that call the API directly from the browser, such as the Dataverse tool in `../dataverse_metasyn` (it expects `http://127.0.0.1:8000`). The container runs as a non-root user and, like the API itself, has no authentication. 

#### Request limits

The API rejects oversized requests. Both limits can be changed with environment variables (in compose under `environment`, with `docker run` use `-e`):

| Variable | Default | Effect |
|---|---|---|
| `MAX_UPLOAD_BYTES` | `104857600` (100 MB) | Larger requests get a 413 response. |
| `MAX_NUM_ROWS` | `100000` | A larger `num_rows` gets a 400 response; a row count inferred from the model is capped to this value. |
| `API_WORKERS` | `2` | Number of API processes in the container (entrypoint only). Memory use grows with each worker. |
| `MAX_CONCURRENT_JOBS` | `2` | Fit/synthesize jobs that run at once per API process, so up to `API_WORKERS` × this value in total. |
| `JOB_WAIT_SECONDS` | `30` | How long an extra request waits for a free job slot before getting a 503 response with a `Retry-After` header. |

Fitting and synthesizing run in worker threads, so a long request does not block the API's other requests. The UI uses threaded workers for the same reason.



### Start the user interface 
Run the following command to start the UI: 

```bash
uv run python frontend/app_flask.py
```

It will run on `http://127.0.0.1:5000`


#### Interface example usage

1. Initial page will show the option to upload a tabular file and generate a GMF

![Initial page](Screenshot-ui-initial-page.png)

2. After the model is fitted you can download it 

![Model fitted page](Screenshot-ui-model-fitted-page.png)

3. And, if you scroll, down, you can have synthetic data generated using that model. Or, just upload another GMF to use that. 

4. When the data is generated it will show the first 10 lines and a button  to download the whole file. 

![Data generated page](Screenshot-ui-data-generated-page.png)



### Manually use the API endpoints
To save the model and synthetic data files to your disk manually without the UI, run the following commands: 

Fit model (upload CSV, save response):
``` bash
curl -s -F "file=@data/input_data.csv" http://127.0.0.1:8000/fit-model/ -o fit_response.json
```

Extract the model into a file:
```bash
jq '.model_json' fit_response.json > model.json
```

Build payload (necessary for next step):
```bash
jq -n --slurpfile m model.json '{model_json: $m[0], num_rows: 109}' > payload.json
```

Call synthesize: 
```bash
curl -s -H "Content-Type: application/json" -d @payload.json http://127.0.0.1:8000/synthesize/ -o synth_response.json
```

Extract csv:
```bash
jq -r '.synthetic_data_csv' synth_response.json > synthetic.csv

```



## AI use 
- `main.py` was initially written with the help of Lumo, the Proton AI assistant. Later on, Copilot (with different models) was used to make adjustments. 

## To do:
- turn instructions into bash script