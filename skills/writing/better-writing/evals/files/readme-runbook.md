# Reset the staging database

Run this when a staging checkout has stale records. You need the staging profile and access to the repository. The reset is not for production.

Run `make db-reset ENV=staging` from the repository root. It may take a few minutes. Check the health page after it finishes. If the check fails, restore the last staging snapshot and tell the on-call engineer.
