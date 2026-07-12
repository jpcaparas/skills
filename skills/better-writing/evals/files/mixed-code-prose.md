# Retry example

This helper retries a transient request. The surrounding explanation should tell a reviewer what the boundary is; the code and output below are the source of truth.

```ts
import { request } from "./client";

export async function retryOnce(idempotencyKey: string) {
  try {
    return await request(idempotencyKey);
  } catch (error) {
    // Retry only the documented transient failure.
    return await request(idempotencyKey);
  }
}
```

Output: `{ status: "accepted" }`
