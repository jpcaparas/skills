# Check a local worker

Start the worker with the local profile, then send one request with an idempotency key. The service uses eventual consistency, so a successful write can appear in a read a moment later.

Verify the worker with:

```sh
curl -fsS http://localhost:8787/healthz
```

If the response is not healthy, stop here and inspect the worker log before retrying the request.
