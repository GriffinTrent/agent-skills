# LinkedIn Company Employee Insights

Scrape LinkedIn company employee data, validate against live LinkedIn, and generate an insights report with geographic distribution and optional historical growth data.

## Your Task

Generate a company employee insights report for: $ARGUMENTS

If no company identifier is provided, ask the user for one or more LinkedIn company slugs or URLs.

## Input Parsing

Extract the company identifier(s) from the input. Accept any of these formats:

**Single company:**
- Full URL: `https://www.linkedin.com/company/apify/`
- Company slug: `apify`

**Batch (comma-separated):**
- `apify, stripe, cloudflare`
- `https://www.linkedin.com/company/apify/, stripe, cloudflare`

Normalize all inputs to slugs (lowercase, strip URLs to the slug portion, remove trailing slashes).

**Detect mode:**
- 1 company → Single mode
- 2+ companies → Batch mode

## Tool Priority

This skill uses **mcpc** (`@apify/mcpc`) as the primary tool for all Apify interactions.

| Priority | Tool | When to use |
|---|---|---|
| **1st (Primary)** | `mcpc @apify tools-call ...` via Bash | Always try this first. All Apify Actor calls go through mcpc. |
| **2nd (Fallback)** | `mcp__apify__*` MCP server tools | Only if mcpc is not installed or session cannot be established. Load via `ToolSearch` with `+apify ...` queries. |

**Why mcpc?**
- Official Apify MCP CLI ([github.com/apify/mcp-cli](https://github.com/apify/mcp-cli))
- Persistent sessions (`@apify`) — no re-authentication between calls
- `--json` output mode for clean parsing
- Works in any terminal, not just Claude Code with MCP server configured
- OAuth 2.1 with PKCE for secure authentication

## Step 0: mcpc Installation & Apify Connection Check

Before doing anything else, verify mcpc is installed and connected to Apify.

### Check 1: mcpc installed?

Run via Bash:
```bash
which mcpc && mcpc --version
```

**If not installed**, install it:
```bash
npm install -g @apify/mcpc
```
- **What it does**: Installs the Apify MCP command-line client globally
- **Risk**: Safe — it's an npm package install

### Check 2: Apify session exists?

Run via Bash:
```bash
mcpc --json 2>/dev/null
```

Look for an `@apify` session in the output. If no session exists, create one:

```bash
mcpc mcp.apify.com connect @apify
```
- **What it does**: Creates a persistent named session called `@apify` connected to Apify's MCP server
- **Risk**: Safe — read-only connection setup

### Check 3: Authentication

If the session creation fails or tools-list returns an auth error:

```bash
mcpc mcp.apify.com login
```
- **What it does**: Opens a browser window for OAuth 2.1 login to Apify
- **Risk**: Safe — standard OAuth flow

Wait for the user to complete login in their browser, then retry the session creation.

### Check 4: Connection test

Run a lightweight test call:
```bash
mcpc @apify tools-call search-actors --json keywords:="test" limit:=1
```
- **What it does**: Searches for one Actor on Apify to verify the connection works
- **Risk**: Safe — read-only search

### Evaluate results

**If connection succeeds:**
- Display: `mcpc @apify: Connected`
- Proceed to Step 1

**If connection fails (error, timeout, or auth failure):**

Present this to the user:
```
Apify MCP is not connected. To authenticate:

1. Run: mcpc mcp.apify.com login
2. Complete the OAuth login in your browser
3. Then run: mcpc mcp.apify.com connect @apify
4. If you don't have an Apify account, create one at https://console.apify.com/sign-in
```

Troubleshooting steps if still failing:
1. **Check API token**: `open https://console.apify.com/account/integrations`
2. **Bearer token fallback**: `mcpc --header "Authorization: Bearer YOUR_TOKEN" mcp.apify.com connect @apify`
3. **List tools**: `mcpc @apify tools-list --json` to verify available tools
4. **Docs**: `https://docs.apify.com/platform/integrations/mcp`

### Fallback to MCP Server Tools

If mcpc cannot be installed or configured, fall back to Claude Code's MCP server integration:

1. Use `ToolSearch` to load the required Apify tools:
   - `+apify call-actor` → `mcp__apify__call-actor`
   - `+apify fetch-actor-details` → `mcp__apify__fetch-actor-details`
   - `+apify search actors` → `mcp__apify__search-actors`
   - `+apify get-actor-output` → `mcp__apify__get-actor-output`

2. Test with: `mcp__apify__search-actors` with `keywords: "test"`, `limit: 1`

3. If MCP server tools also fail, direct user to `https://mcp.apify.com` to authenticate and configure the MCP server.

Do NOT proceed to Step 1 until the Apify connection is confirmed working (via either mcpc or MCP server tools).

## Step 1: Fetch Actor Schema & Validate

Before calling any actor, always fetch the current input schema to prevent breakage from schema changes.

### Using mcpc (primary):
```bash
mcpc @apify tools-call fetch-actor-details --json actor:="apimaestro/linkedin-company-employees-scraper-no-cookies"
```
- **What it does**: Fetches the actor's README, input schema, and metadata from Apify
- **Risk**: Safe — read-only API call

### Using MCP server tools (fallback):
Use `mcp__apify__fetch-actor-details` with:
- `actor`: `apimaestro/linkedin-company-employees-scraper-no-cookies`
- `output`: `{ "inputSchema": true }`

### Schema mapping

Read the returned schema and map user inputs to the correct field names. As of the last validation (2026-02-17), the schema uses:
- `identifier` — company slug or LinkedIn URL
- `max_employees` — maximum employees to return (default: 100)
- `job_title` — optional filter by job title

If the schema has changed from what's documented here, adapt dynamically. Log the field mapping for transparency.

## Step 2: Scrape Employee Data

### Cost Warning (display before large batches)

If batch size > 10, display this before proceeding:

```
Cost estimate: ~$0.01/employee result
- {N} companies x {max_employees} employees = ~${estimated_cost}
- Proceed? (Y/n)
```

Wait for user confirmation before executing large batches.

### Execution Strategy

**Single company (1):**

Using mcpc (primary):
```bash
mcpc @apify tools-call call-actor --json \
  actor:="apimaestro/linkedin-company-employees-scraper-no-cookies" \
  input:='{"identifier":"{slug}","max_employees":25}'
```
- **What it does**: Runs the LinkedIn employee scraper Actor for a single company
- **Risk**: Low — costs ~$0.25 per run on Apify
- **Note**: The mcpc parameter name is `actor` (not `actorId`)

Using MCP server tools (fallback):
- One call to `mcp__apify__call-actor` with `async: false`
- Actor: `apimaestro/linkedin-company-employees-scraper-no-cookies`
- Input: `{ "identifier": "{slug}", "max_employees": 25 }` (or user-specified limit)

**Small batch (2-20):**
- Fire all calls in parallel (one per company)
- With mcpc: run multiple Bash commands in parallel, each with `--json`
- With MCP server tools: parallel `mcp__apify__call-actor` calls, each with `async: false` and `previewOutput: false`
- Fetch results separately via `get-actor-output`

**Large batch (21-500):**
- Fire calls in waves of 10-20 parallel calls
- Display progress after each wave: `Wave 1/5 complete: 9/10 companies returned data`
- If a wave shows unusually high failure rate (>30%), pause and warn the user

**Concurrent Claude Agents (for batches >10):**
For large batches, use concurrent Claude `Task` agents to parallelize scraping across multiple context windows:

| Total Companies | Companies per Agent | Concurrent Agents |
|---|---|---|
| 11-25 | 5 per agent | 3-5 |
| 26-50 | 5 per agent | 6-10 |
| 51-100 | 5 per agent | 11-20 |
| 100-500 | 10 per agent | 10-50 (in waves) |

- Use `Task` tool with `subagent_type: "general-purpose"`
- Each agent's prompt must include:
  - The company slugs to scrape
  - Instructions to use mcpc (`mcpc @apify tools-call ... --json`) via Bash as the primary tool
  - Fallback: instructions to use `ToolSearch` to load `mcp__apify__*` tools if mcpc is not available
  - Explicit instruction to return COMPLETE raw data
- Run agents in parallel (single message with multiple Task tool calls)
- **CRITICAL**: When assembling the final report from agent results, use ONLY actual scraped data — never fabricate or placeholder any employee names, titles, locations, or profile URLs

### Retrieving Full Results

After each actor run returns, check `itemCount` in the response:

Using mcpc (primary):
```bash
mcpc @apify tools-call get-actor-output --json datasetId:="{datasetId}" fields:="full_name,title,location,country,city,country_code,profile_url"
```
- **What it does**: Fetches the scraped employee data from the actor run's dataset
- **Risk**: Safe — read-only data retrieval

Using MCP server tools (fallback):
- If `itemCount > 0`: Fetch via `mcp__apify__get-actor-output` with the `datasetId`, selecting key fields: `fields: "full_name,title,location,country,city,country_code,profile_url"`
- If `itemCount == 0`: Mark company as "Limited LinkedIn visibility" — do NOT retry

### If user specifies a job title filter

Add `"job_title": "{filter}"` to the actor input. This narrows results to matching titles (e.g., "software engineer", "CEO", "product manager").

## Step 3: Confidence Assessment

After all scraping completes, calculate and display a confidence summary BEFORE generating the report.

### Confidence Levels

| Batch Size | Expected Success | Confidence |
|---|---|---|
| 1-5 companies | ~95% | HIGH |
| 6-20 companies | ~90% | HIGH |
| 21-100 companies | ~85-90% | MEDIUM |
| 100-500 companies | ~85-90% | MEDIUM |

### Status Table

Display a table showing each company's scraping result:

```
Company Results Summary:
| # | Company     | Employees Found | Status                        |
|---|-------------|-----------------|-------------------------------|
| 1 | apify       | 25              | OK                            |
| 2 | stripe      | 25              | OK                            |
| 3 | mongodb     | 0               | Limited LinkedIn visibility   |
| 4 | okta        | 1               | Partial data                  |

Overall: 3/4 companies returned data (75%)
Confidence: HIGH — small batch, results consistent
```

### Warning Triggers

Display explicit warnings for:

- **Any company returning 0 items**: `[WARNING] {company}: No employee data available. LinkedIn may restrict visibility for this company. This is NOT an error — do not retry.`
- **Any company returning <50% of requested employees**: `[NOTE] {company}: Returned {N}/{requested} employees. Data may be incomplete.`
- **Batch success rate below 80%**: `[WARNING] Overall success rate ({X}%) is below expected threshold. Consider verifying company slugs are correct.`
- **Batch size > 100**: `[NOTE] Large batch ({N} companies). Confidence in aggregate statistics is MEDIUM. Recommend spot-checking a 10% sample against LinkedIn.`

## Step 4: Validation (CRITICAL — DO NOT SKIP)

This step is mandatory for every request. Scraped data must be validated against live LinkedIn to avoid reporting hallucinated or stale information.

### Validation Sample Size

| Request Type | Companies to Validate |
|---|---|
| Single company | That company (always) |
| Batch 2-10 | 2-3 companies (random) |
| Batch 11-50 | 3-5 companies (random) |
| Batch 51-500 | 5 companies (random sample) |

### Primary Validation: Apify RAG Web Browser (Preferred)

Use the Apify RAG Web Browser for validation — it handles JavaScript rendering and login walls better than raw scrapers.

Using mcpc (primary):
```bash
mcpc @apify tools-call apify-slash-rag-web-browser --json \
  query:="LinkedIn company {slug} employees" \
  maxResults:=1
```
- **What it does**: Uses Apify's RAG web browser to fetch and parse the LinkedIn company page
- **Risk**: Safe — read-only web fetch

Using MCP server tools (fallback):
- Use `mcp__apify__apify-slash-rag-web-browser` with the company LinkedIn URL

### Alternative Validation Actors

If RAG browser doesn't return enough data, use these Apify Actors:

1. **`apify/cheerio-scraper`** (FREE) — for lightweight HTML checks
2. **`apify/puppeteer-scraper`** (FREE) — for JS-rendered pages
3. **`apify/website-content-crawler`** — for structured content extraction

Using mcpc:
```bash
mcpc @apify tools-call call-actor --json \
  actor:="apify/cheerio-scraper" \
  input:='{"startUrls":[{"url":"https://www.linkedin.com/company/{slug}/"}],"maxRequestsPerCrawl":1}'
```

All validation calls go through mcpc or `mcp__apify__call-actor`. Never use direct HTTP requests or curl.

### How to Validate

For each company in the validation sample:

1. **Fetch the company LinkedIn page** using an Apify tool (preferred) or `WebFetch` on `https://www.linkedin.com/company/{slug}/`
   - Extract: Company name, employee count (from the "X employees" badge), company description, industry

2. **Cross-reference against scraped data:**
   - Company name matches? (exact or close match)
   - Employee count in the right order of magnitude? (scraped 25 of listed 5,000 = plausible; scraped 25 of listed 3 = suspicious)
   - Do scraped job titles look reasonable for this company?

3. **If validation is blocked** (login wall, 999 status, or empty response):
   - Note: `LinkedIn validation was blocked by login wall. Scraped data is from Apify's authenticated proxy and is likely accurate, but could not be independently verified.`
   - This is expected for most LinkedIn pages — it does NOT mean the data is wrong

### Validation Output

Display results clearly:

```
Validation Results:
| Company    | Name Match | Employee Scale | Titles Plausible | Status       |
|------------|-----------|----------------|------------------|--------------|
| apify      | Yes       | 25/116 (OK)    | Yes              | VALIDATED    |
| stripe     | Yes       | Login wall     | N/A              | INCONCLUSIVE |
| mongodb    | N/A       | N/A            | N/A              | NO DATA      |

Validation: 1 confirmed, 1 inconclusive (login wall), 1 no data
```

### Red Flags (halt and warn user)

If ANY of these occur, stop and alert the user before generating the report:
- Company name from scraper does not match the LinkedIn page at all
- Scraped employee count exceeds LinkedIn's listed total by >2x
- All scraped employees have suspiciously similar or generic titles
- Scraped data contains obvious placeholder or test data

## Step 4b: Anti-Hallucination Verification (CRITICAL — DO NOT SKIP)

Before generating the report, verify ALL scraped data for integrity:

### Employee Data Verification
- Every employee profile URL must follow the LinkedIn profile pattern: `https://www.linkedin.com/in/{username}`
- Reject any URL containing placeholder patterns (`example.com`, `#`, `test`, `1234567890`)
- Employee names should not contain obvious template/placeholder text
- Job titles should be plausible for the company (e.g., "Software Engineer" at a tech company is plausible; "Underwater Basket Weaver" is suspicious)

### Company Data Verification
- Company slugs in scraped data must exactly match the requested slugs
- If the scraper returns a different company name than expected, flag it: `[WARNING] Requested '{slug}' but scraper returned company name '{actual}'. Verify this is correct.`
- Employee counts should not exceed the company's LinkedIn-listed total by >2x

### Location Data Verification
- Country codes should be valid ISO codes
- City/country combinations should be geographically plausible
- If >80% of employees list the exact same location, flag as potentially suspicious

### What to do if verification fails
- Do NOT generate the report with bad data
- Re-scrape the affected companies
- If re-scraping returns the same suspicious data, include it with explicit warnings in the report

## Step 5: Historical Growth Data (Phase 2 — Optional)

Skip this step if the user only requests current employee data. Include it by default for single-company reports.

### Scraping GetLatka

Using mcpc (primary):
```bash
mcpc @apify tools-call call-actor --json \
  actor:="apify/cheerio-scraper" \
  input:='{"startUrls":[{"url":"https://getlatka.com/companies/{slug}"}],"maxRequestsPerCrawl":1,"pageFunction":"async function pageFunction(context) { const { $, request } = context; const data = { url: request.url, title: $(\"title\").text(), html: $(\"body\").html() }; return data; }"}'
```
- **What it does**: Scrapes the GetLatka company page for historical revenue and headcount data
- **Risk**: Low — one page scrape, ~$0.005

Using MCP server tools (fallback):
Use `mcp__apify__call-actor` with:
- Actor: `apify/cheerio-scraper` (FREE)
- Input:
  ```json
  {
    "startUrls": [{ "url": "https://getlatka.com/companies/{slug}" }],
    "maxRequestsPerCrawl": 1,
    "pageFunction": "async function pageFunction(context) { const { $, request } = context; const data = { url: request.url, title: $('title').text(), html: $('body').html() }; return data; }"
  }
  ```

### Extract from Results

Parse the returned HTML for:
- Revenue figures (annual, with years)
- Team size / employee count (historical)
- Funding rounds and amounts
- YoY growth percentage

### Fallback

If cheerio scraper returns empty or incomplete data (JS-rendered content):
- Retry with `apify/puppeteer-scraper` (also FREE) using the same URL
- If both fail: note "Historical data unavailable for this company" in the report

### Validation

Cross-reference GetLatka employee count against LinkedIn's listed employee count. If they diverge by >50%, flag as: `[NOTE] GetLatka reports {X} employees vs LinkedIn's {Y}. Numbers may reflect different time periods or methodologies.`

## Step 6: Generate HTML Report

### File Naming
- Single company: `/Users/nami-tech/Claude-base/linkedin-company-{slug}-report.html`
- Batch: `/Users/nami-tech/Claude-base/linkedin-company-batch-report.html`

### Report Structure

#### Confidence Banner (top of report)
Color-coded based on overall confidence:
- **GREEN** (`#e6f4ea`): All companies returned data, validation passed
- **YELLOW** (`#fef3e0`): Some companies had limited data or validation was inconclusive
- **RED** (`#fce8e6`): Significant data gaps or validation failures detected

Text: `Confidence: {HIGH/MEDIUM/LOW} — {explanation}`

#### Company Header Section
- Company name(s), LinkedIn URL(s)
- Report date and data freshness
- Employee count from scraper vs LinkedIn listed count

#### Employee Data Table
Columns: #, Full Name, Title, Location, Country, Profile URL

For each employee:
- **Full Name**: plain text
- **Title**: current role
- **Location**: city + country
- **Country**: country code badge
- **Profile URL**: clickable "View profile" link (target="_blank")

#### Geographic Distribution
- Country breakdown table (country, count, percentage)
- Top 5 cities table
- Summary sentence: "Employees are primarily based in {top country} ({X}%), with presence in {N} countries"

#### Historical Growth (if Phase 2 data available)
- Revenue trend (year-over-year if available)
- Headcount trend
- Funding summary
- Use Chart.js from CDN for visualization (line chart)

#### Validation Summary
- Bullet list of what was verified (with checkmark/cross styling)
- Any warnings or flags from Steps 3-4
- Data source attribution: "Employee data from Apify (apimaestro actor). Historical data from GetLatka."

#### Warnings Section (if applicable)
Yellow/red bordered box listing:
- Companies with 0 results and why
- Companies with partial data
- Validation inconclusive results
- Any data discrepancies found

#### Footer
- "Generated on {date} via mcpc + Apify MCP + Claude Code"
- "Data scraped from LinkedIn. Historical data from GetLatka. All data should be independently verified for business decisions."

### Styling
Use this consistent design system (same as linkedin-posts.md):
- Background: `#f3f2ef` (LinkedIn-like)
- Cards: `#fff`, `border-radius: 12px`, `box-shadow: 0 1px 3px rgba(0,0,0,0.08)`
- Table header: `#1b1f23` background, white text
- Font: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- Max width: `960px`, centered
- Confidence banners: full-width, rounded, with icon prefix

## Step 7: Open & Summarize

Run `open {filepath}` to open the report in the user's default browser.

After opening, provide a text summary:
- Total companies processed and success rate
- Total employees found across all companies
- Top 3 countries by employee concentration
- Key growth trends (if Phase 2 data available)
- Validation status and any warnings
- Cost incurred (number of actor calls x approximate cost)
- Tool used: mcpc or MCP server tools (for transparency)

## Error Handling

- **mcpc not installed**: Guide user to install with `npm install -g @apify/mcpc`. Fall back to MCP server tools if available.
- **mcpc session expired/crashed**: Run `mcpc @apify restart` to restart the session. If that fails, `mcpc mcp.apify.com connect @apify` to create a new session.
- **0 items returned for a company**: Flag as "Limited LinkedIn visibility." Do NOT retry — this is deterministic (the company restricts its employee listings on LinkedIn). Include in the report with explanation.
- **Actor input schema mismatch**: Re-fetch schema via `mcpc @apify tools-call fetch-actor-details --json` and retry with corrected field names. If it fails again, report the error to the user.
- **Apify authentication expired mid-run**: Stop processing, save partial results, run `mcpc mcp.apify.com login` to re-authenticate.
- **GetLatka page not found**: Skip Phase 2 for that company, note "Historical data unavailable" in the report.
- **WebFetch validation blocked (login wall)**: Expected behavior. Note as "inconclusive" — do not treat as failure.
- **Batch >100 companies**: Display processing time estimate upfront. Suggest running in multiple sessions if >200.

## Guidelines

### mcpc as Primary Tool (Mandatory)

- **Always use mcpc (`@apify/mcpc`) as the primary tool** for all Apify interactions. Install with `npm install -g @apify/mcpc`. Source: [github.com/apify/mcp-cli](https://github.com/apify/mcp-cli)
- **Use persistent sessions**: Create a session with `mcpc mcp.apify.com connect @apify` and reuse it with `mcpc @apify tools-call ...` for all subsequent calls.
- **Always use `--json` flag** for parseable output: `mcpc @apify tools-call ... --json`
- **mcpc argument syntax**: Use `:=` with no spaces — `key:="value"` for strings, `key:=5` for numbers, `key:='{"nested":"json"}'` for objects.
- **Fallback only**: Use `mcp__apify__*` MCP server tools only if mcpc cannot be installed or configured.

### Apify MCP (General)
- **Never use REST API calls, curl, or direct HTTP requests** to Apify's API. All actor calls go through mcpc or MCP server tools.
- **If user is not connected to Apify**, authenticate via `mcpc mcp.apify.com login`. If they don't know what MCP is, explain: "MCP (Model Context Protocol) is how tools like Claude connect to external services. mcpc is Apify's official CLI client for MCP."
- **Always fetch actor schema before calling** — prevents breakage from schema changes. This is non-negotiable.

### Batch Execution
- **Use concurrent Claude agents for large batches** — 5 companies per agent is the validated sweet spot for employee scraping. See "Concurrent Claude Agents" section in Step 2.
- **Each agent should use mcpc as primary tool** — include mcpc commands in agent prompts.
- **For batch requests, show progress** — display intermediate results after each wave of parallel calls.

### Anti-Hallucination (Critical)
- **Never guess or hallucinate employee data** — only report what the scraper actually returns. If a company returned 0 items, say 0. Do not estimate or extrapolate.
- **Double-check every profile URL** — must be a real LinkedIn profile URL. Reject placeholder patterns.
- **Verify company slugs match** — scraped data must correspond to the requested company, not a redirect or similar name.
- **Validate employee names, titles, and locations** — ensure they are plausible and not template/placeholder text.

### Confidence & Transparency
- **Always indicate when confidence wanes** — for batches >20 companies, explicitly state that confidence is MEDIUM and recommend spot-checking.
- **Always estimate cost before scraping** — display the estimate and get confirmation for large batches (>10 companies).
- **Always report actual cost at the end** — number of actor calls, companies processed, estimated Apify spend.
- **Be honest about limitations** — ~10% of companies will have visibility restrictions. This is a LinkedIn platform limitation, not an error. Frame it accurately.

### Validation
- **Validate against LinkedIn for every request** — this is the most important step. Do not skip it. Do not claim data is "validated" if validation was blocked — say "inconclusive."

### Report Quality
- **The report should be self-contained HTML** with inline styles and CDN-hosted Chart.js. No external dependencies beyond Chart.js.
- **For companies in non-English-speaking regions**, keep location names in their original form alongside English translations if helpful.
