# Ecommerce, Local, And Agentic Experiences

Use this when the site sells products, represents a local business, or needs browser-agent-friendly journeys.

## Ecommerce

Google's ecommerce guidance focuses on helping Google find, parse, and present product content across Search surfaces.

Implementation priorities:

- Product detail pages must have crawlable, indexable, unique product information.
- Product data should be consistent across visible content, JSON-LD, feeds, Merchant Center, and checkout availability.
- Use `Product` structured data only for visible product details.
- Keep price, availability, shipping, returns, ratings, and variants current.
- Design URL structures for categories, products, variants, pagination, and filters before scaling catalog pages.
- Avoid indexing low-value faceted combinations that duplicate product lists.
- Keep important product links crawlable from category, collection, and internal search alternatives.

For product reviews, prioritize first-hand, high-quality review content that helps shoppers decide. Do not fabricate ratings or mark up reviews that are not visible and genuine.

## Local Business

For local businesses, generative AI responses can surface business information when appropriate. Treat consistency as the core implementation problem.

Implementation priorities:

- Keep name, address, phone, hours, services, service area, menus, reservations, and business URLs consistent.
- Use Google Business Profile for business details where relevant.
- Use `LocalBusiness` structured data on pages that visibly describe the business or location.
- Use the most specific applicable subtype, such as `Restaurant`, `Dentist`, or `AutoRepair`, when accurate.
- For multi-location businesses, create distinct useful location pages with unique local details, not doorway pages.
- If reviews are shown, ensure they are genuine, visible, and follow the relevant Google review/rating guidelines.

## Agentic Website Readiness

Google's AI Search guidance points developers toward agentic experiences. Browser agents may inspect screenshots, raw HTML, and the accessibility tree.

Build journeys that are clear across all three:

- Use semantic HTML for actions: `<button>` for actions, `<a href>` for navigation.
- Attach labels to inputs with `for`/`id` or accessible name equivalents.
- Keep key actions visible and stable across products, categories, and viewport states.
- Avoid transparent overlays, ghost elements, or invisible controls that cover real controls.
- Use `cursor: pointer` for actionable custom controls.
- Make interactive elements large enough to be visually detectable.
- Keep forms predictable: visible labels, errors near fields, stable submit buttons, and clear success states.
- Do not put critical actions behind hover-only interactions.

These changes help humans, assistive technology, crawlers, and agents. Treat them as product quality improvements rather than a separate SEO trick.

## Cross-Surface Consistency Checklist

For each important product or local page, compare:

- visible page content
- JSON-LD
- metadata and canonical URL
- sitemap URL
- Merchant Center feed or Business Profile
- internal links and breadcrumbs
- rendered mobile layout
- checkout, booking, contact, or lead flow

Any contradiction is a Search and user trust risk.
