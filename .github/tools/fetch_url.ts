import { tool } from "@opencode-ai/plugin";

// Domains the agent is allowed to fetch from. Subdomains are allowed
// (e.g. documentation.ubuntu.com, discourse.ubuntu.com). This matches
// the allowlist in probe_issue.py's host_allowed() function.
const ALLOWED_DOMAINS = [
  "canonical.com",
  "ubuntu.com",
  "raw.githubusercontent.com",
  "github.com",
];

const MAX_BYTES = 64 * 1024;

function hostAllowed(host: string): boolean {
  return ALLOWED_DOMAINS.some(
    (d) => host === d || host.endsWith("." + d),
  );
}

export default tool({
  description:
    "Fetch content from a URL on an allowlisted domain (canonical.com, ubuntu.com, " +
    "raw.githubusercontent.com, github.com). Use this to read charm development docs, " +
    "library source code on GitHub, release notes, or PRs. The URL must be HTTP(S) and " +
    "the host must match an allowlisted domain (subdomains are allowed). Returns the " +
    "response body as text (truncated to 64KB). GET requests only.",
  args: {
    url: tool.schema
      .string()
      .describe("The HTTP(S) URL to fetch. Must be on an allowlisted domain."),
  },
  async execute(args) {
    const urlStr: string = args.url;

    // Validate the URL.
    let url: URL;
    try {
      url = new URL(urlStr);
    } catch {
      return `Invalid URL: ${urlStr}`;
    }

    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return `Only HTTP(S) URLs are allowed. Got: ${url.protocol}`;
    }

    const host = url.hostname;
    if (!hostAllowed(host)) {
      return (
        `Domain "${host}" is not allowlisted. Allowed domains: ` +
        ALLOWED_DOMAINS.join(", ")
      );
    }

    try {
      const response = await fetch(urlStr, {
        method: "GET",
        headers: { "User-Agent": "basic-charms-doc-validator" },
        redirect: "follow",
      });

      if (!response.ok) {
        return `Fetch failed: ${response.status} ${response.statusText}`;
      }

      const text = await response.text();
      if (text.length > MAX_BYTES) {
        return text.slice(0, MAX_BYTES) + "\n\n[truncated at 64KB]";
      }
      return text;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      return `Fetch failed with an error: ${msg}`;
    }
  },
});
