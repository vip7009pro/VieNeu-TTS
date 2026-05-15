# Context

- Repo already had a FastAPI server in `apps/web_stream.py` with `/voices`, `/models`, `/set_model`, `/extract_url`, and `/stream`.
- Added browser-friendly CORS, `/health`, and `POST /synthesize` that saves a WAV under `outputs/api/` and returns the file to the client.
- The API now returns explicit HTTP errors when the model is unavailable instead of failing silently.
- The packaged entrypoint already exists as `vieneu-stream = apps.web_stream:main` in `pyproject.toml`.
- Validation passed: `python -m py_compile apps/web_stream.py`.
- Added `USER_API_MANUAL.md` documenting how to use the API from a web app and HTTP clients.