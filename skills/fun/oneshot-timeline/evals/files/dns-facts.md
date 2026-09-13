# DNS fact sheet for an offline exercise

Treat this as supplied evidence, not freshly verified web research. Useful references for reader citations: https://www.cloudflare.com/learning/dns/what-is-dns/ and https://www.rfc-editor.org/rfc/rfc1034.

- A user enters a domain name in a browser. DNS helps locate records, such as an IP address; it does not download the web page.
- A browser or operating system may already have a usable cached result. If not, it asks a configured recursive resolver, which may also have a usable cached answer.
- For an uncached example, the resolver follows referrals through a root server and a top-level-domain server toward the domain's authoritative server. The root does not store the final answer for every domain.
- The authoritative server supplies records for its zone. The recursive resolver returns the answer to the client and may cache it for the record's time to live (TTL).
- The browser then uses the result as part of connecting to the website. Aliases and encrypted-DNS transports exist, but this short explanation can name them as omitted details.
- There is no fixed elapsed-time dataset here. Use causal stages, not calendar dates or a made-up latency graph.
