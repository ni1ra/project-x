#!/usr/bin/env python3
"""Simple server launcher that verifies routes before starting."""

import sys
sys.path.insert(0, ".")

print("=" * 60)
print("LOADING RPJ BRAIN SERVER")
print("=" * 60)

from web.server import app

# Check routes
routes = [r.path for r in app.routes if hasattr(r, 'path')]
print(f"Routes found: {routes}")
print(f"Total routes: {len(routes)}")

if '/chat' in routes:
    print("SUCCESS: /chat endpoint present!")
else:
    print("ERROR: /chat endpoint missing!")
    sys.exit(1)

import uvicorn
print("\nStarting uvicorn on http://0.0.0.0:8420")
uvicorn.run(app, host="0.0.0.0", port=8420)
