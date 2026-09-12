# Retry operation

The following command is utilized in order to retry the job, and operators should ensure the configured maximum hasn't been exceeded before running it.

`POST /v1/jobs/{job_id}/retry`

```bash
curl -fsS -X POST "https://api.example.test/v1/jobs/${job_id}/retry"
```

The response contains `retry_after_ms` and the configuration key `MAX_RETRY_COUNT`.

```yaml
retry:
  MAX_RETRY_COUNT: 4
  status_label: "SYSTEM READY FOR OPERATION"
```

Preserve every inline literal and fenced block character-for-character.
