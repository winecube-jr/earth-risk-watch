# Setup

## Local development

Use Python 3.11 or 3.12. The current host may have a newer Python version, but
the scientific GIS ecosystem is most reliable on the supported versions declared
in `pyproject.toml`.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Google Earth Engine

Account-side registration is deliberately not automated.

1. Create or select a Google Cloud project.
2. Register it for non-commercial Earth Engine access.
3. Install the cloud dependencies: `pip install -e ".[cloud]"`.
4. Copy `.env.example` to `.env` and set `EARTHENGINE_PROJECT`.
5. In an interactive notebook, run `ee.Authenticate()` once.
6. Verify with `ee.Initialize(project="your-project-id")`.

Do not commit `.env`, OAuth tokens, service-account keys, or downloaded credentials.

## Colab

Open a notebook from GitHub, clone the repository into the runtime, install the
package, authenticate Earth Engine interactively, and write durable products to
an approved persistent target before the runtime ends.

## GitHub

The initial workflows require no secrets. Future unattended Earth Engine jobs
will require a deliberately chosen workload-identity or service-account design;
do not create long-lived JSON keys merely for convenience.
