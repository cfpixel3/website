import os
from waitress import serve
from app import app, init_db

if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    threads = int(os.environ.get("WAITRESS_THREADS", 6))
    print(f"Bazaar production server running on http://127.0.0.1:{port}")
    print(f"Threads: {threads}")
    print("Ready for Cloudflare Tunnel traffic (fernhill.site)")
    serve(app, host="127.0.0.1", port=port, threads=threads)
