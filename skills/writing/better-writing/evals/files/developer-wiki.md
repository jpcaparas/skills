# Rotating Staging API Keys

This page is for operators. It explains the staging API key rotation. The production process is not covered.

### 1. Getting Ready

API key rotation should be done only after change `CHG-4821` is approved. You need `key-admin` access. Keep the existing key until verification passes.

## 2. Rotation Steps

1. Go to the portal and click the button on the right.
2. Run the following command:

   ```bash
   keyctl rotate --environment staging --change CHG-4821
   ```

3. (Optional) Save the returned `kid` in `staging.env`.
4. Click [here](https://ops.example.test/audit) to see the audit record.
5. If verification fails, stop. The source does not provide a rollback command.

## Verification

See below. The audit record must show `environment=staging`, the new `kid`, and change `CHG-4821`. The old key must remain active until that record appears.
