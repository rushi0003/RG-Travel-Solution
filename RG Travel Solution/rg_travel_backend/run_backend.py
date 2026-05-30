#!/usr/bin/env python
"""
Compatibility launcher.

Use this file to start the full backend app so older scripts/commands that run
`python run_backend.py` still expose all v2/admin endpoints.
"""

from app import create_app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
