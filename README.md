# Codex warmer

Personal Codex-only adaptation of [viseshb/claude-codex-warmer](https://github.com/viseshb/claude-codex-warmer), retaining the upstream MIT license and Git history.

Status: implementation prepared October 10, 2026; live deployment verification pending. This active engineering project explores scheduled subscription-window activation. It does not increase allowances or resume local tasks.

## Layout

- `.github/workflows/warm.yml`: scheduled and manual execution, concurrency, pinned checkout, failure issues.
- `scripts/warm.py`: authenticated quota check, tiny CLI request, post-request verification, token persistence.
- `scripts/policy.py`: conservative window policy.
- `tests/`: deterministic quota policy tests.
- `.state/`: timestamps only; never credentials.

## Setup

Use a public repository with standard Linux runners. Store login credentials only in Actions Secrets:

- `CODEX_AUTH_JSON`: existing Codex file-backed ChatGPT login.
- `GH_PAT`: fine-grained PAT limited to this repository, with repository Secrets read/write permission. Metadata read is implicit. Set an expiry and maintain it.

Do not use a broad account-wide PAT. Do not paste credentials into issues or logs. Enable Actions only after both secrets exist. Run the workflow manually and inspect request, activation, and persistence outcomes. A CLI success alone is insufficient.

Default schedule: minute 7 and 37 each hour (UTC). Manual runs obey the same safety checks. Set repository variable `WARM_MODEL` if necessary; default `gpt-6-luna`. Model availability and whether a request activates the relevant quota must be verified for your account. CLI is pinned to 0.144.1.

A window already active is skipped. Weekly exhaustion blocks sends. Missing, invalid or unexpected usage data fails closed. Requests are not automatically retried because a failed connection can conceal a completed metered request. Verification polls up to three times without resending. Successful requests record timestamps even if activation cannot be confirmed.

The usage endpoint is undocumented. Activation checks use its reported absolute reset time and require the timer to stop sliding; they are conservative heuristics, not an official contract. GitHub schedules can be delayed. Token rotation between local clients and CI remains a reliability risk; a repository concurrency lock cannot coordinate local clients.

Updated credentials are sent through stdin to GitHub CLI, never command arguments. Credential write-back failures fail the job. Failures create one issue; recovery closes it. Issue notifications depend on your GitHub notification settings. A daily timestamp commit maintains repository activity.

## Validation

`python3 -m unittest discover -s tests`

Never upload `auth.json`, CLI session logs, or credentials as artifacts/cache. The CLI runs in `/tmp`, in read-only sandbox mode, and output is suppressed. Workflow owners and third-party executable dependencies remain part of the trust boundary.
