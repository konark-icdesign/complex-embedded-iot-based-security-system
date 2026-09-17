"""Loopback-only test receiver. Stores evidence durably before acknowledging it."""

from contextlib import contextmanager
import base64
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import threading


@contextmanager
def receiver(directory, lose_first_ack=False):
    root = Path(directory)
    root.mkdir(parents=True, exist_ok=True)
    database = root / "receiver.sqlite"
    with sqlite3.connect(database) as db:
        db.execute("CREATE TABLE IF NOT EXISTS receipts(id TEXT PRIMARY KEY, digest TEXT)")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            if self.path != "/incidents" or not 0 < size <= 16*1024*1024:
                self.send_error(400)
                return
            body = self.rfile.read(size)
            try:
                message = json.loads(body)
                identity = message["id"]
                import uuid
                uuid.UUID(identity)
                raw = base64.b64decode(message["media_base64"], validate=True)
                if hashlib.sha256(raw).hexdigest() != message["manifest"]["media_sha256"]:
                    raise ValueError("media hash mismatch")
                if self.headers.get("Idempotency-Key") != identity:
                    raise ValueError("ID mismatch")
                digest = hashlib.sha256(body).hexdigest()
                with sqlite3.connect(database) as db:
                    old = db.execute("SELECT digest FROM receipts WHERE id=?", (identity,)).fetchone()
                    if old is not None and old[0] != digest:
                        self.send_error(409)
                        return
                    target = root / identity
                    target.mkdir(exist_ok=True)
                    (target / "media.npz").write_bytes(raw)
                    (target / "manifest.json").write_text(json.dumps(message["manifest"], indent=2))
                    db.execute("INSERT OR IGNORE INTO receipts VALUES(?,?)", (identity, digest))
                # A 503 after committing mimics a lost/unsuccessful acknowledgement.
                if lose_first_ack and old is None and not self.server.lost:
                    self.server.lost = True
                    self.send_error(503)
                    return
                reply = json.dumps({"id": identity}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)
            except (ValueError, KeyError, TypeError):
                self.send_error(400)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.lost = False
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/incidents"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
