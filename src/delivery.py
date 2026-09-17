"""HTTP evidence delivery with durable retries and receiver acknowledgement."""

import json
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


def deliver(journal, endpoint, online=True):
    if not online:
        return 0
    sent = 0
    rows = journal.db.execute("SELECT id,payload FROM deliveries WHERE acked=0").fetchall()
    for identity, body in rows:
        error = None
        acknowledged = False
        try:
            request = Request(endpoint, data=body.encode("utf-8"), method="POST",
                              headers={"Content-Type": "application/json",
                                       "Idempotency-Key": identity})
            with urlopen(request, timeout=3) as response:
                reply = json.loads(response.read(4096))
                acknowledged = response.status == 200 and reply.get("id") == identity
            if not acknowledged:
                error = "receiver did not acknowledge this incident"
        except (URLError, HTTPError, TimeoutError, OSError, ValueError) as exc:
            error = str(exc)
        with journal.db:
            journal.db.execute("UPDATE deliveries SET attempts=attempts+1,acked=?,error=? WHERE id=?",
                               (int(acknowledged), error, identity))
        sent += int(acknowledged)
    return sent
