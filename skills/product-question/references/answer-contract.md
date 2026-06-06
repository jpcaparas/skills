# Answer Contract

Use this when writing the final response.

## Default Shape

```text
Short answer: <direct answer in 1-2 sentences>

What this means for users: <plain-language behavior and practical impact>

Rules and exceptions: <only the conditions that change the answer>

Checked: <short list of product areas, files, tests, or config that support the answer>

Confidence: <only include when not high, or when part of the answer is inferred>
```

Do not include every section if it makes the answer feel stiff. The response should read like a polished product note, not a template exercise.

## Writing Rules

- Put the answer before the evidence.
- Use words a product manager would use in a customer or stakeholder discussion.
- Convert implementation details into product meaning.
- Mention code names only when they help verify the answer.
- Use "the app" or the product name, not "the code", when describing behavior.
- Keep bullets short when comparing rules, user states, or exceptions.
- Avoid code blocks unless the user explicitly asks for code.

## Good Phrases

| Technical finding | Product wording |
| --- | --- |
| Component renders only when permission check passes | Users only see this option if their role includes that permission |
| API returns 409 on duplicate request | The app blocks duplicate submissions instead of creating a second record |
| Feature flag gates route | This feature is controlled by a flag, so it may not be available to every account yet |
| Background job retries failed send | Failed messages are retried automatically instead of being abandoned immediately |
| Null state falls back to default copy | If the app does not have custom text, it shows the default message |

## Example

Question: "Can a customer cancel from the billing page, or do they need support?"

Share-ready answer:

```text
Short answer: Customers can start cancellation from the billing page, but only when they already have an active subscription loaded on the account.

What this means for users: If the subscription is active, the billing page shows the cancellation action. If the account is on a trial, already canceled, or the subscription data is missing, the page does not show that option and the customer would need another path.

Rules and exceptions: The behavior depends on subscription status. I did not find evidence that admins can override this from the same customer-facing page.

Checked: billing settings screen, subscription status handling, and cancellation-related tests.
```

## When Evidence Is Incomplete

Be useful without pretending certainty:

```text
Short answer: The web app appears to block this for inactive accounts, but I would treat that as medium confidence until we check the mobile client.

What I could verify: The web flow checks account status before showing the action, and inactive accounts do not get the normal path.

What is still unknown: I did not find mobile-specific code in the available repository, so I cannot confirm whether mobile follows the same rule.
```
