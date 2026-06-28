"""Setup branch protection via GitHub API using PAT from .github_pat file."""
import json, os, pathlib, urllib.request, urllib.error

token_file = pathlib.Path(__file__).parent.parent / ".github_pat"
token = token_file.read_text().strip()
owner, repo = "IIIH23", "earth-pulse-poc"
base = f"https://api.github.com/repos/{owner}/{repo}"

def api(method, path, data=None):
    url = base + path
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()) if resp.status != 204 else {}
    except urllib.error.HTTPError as e:
        return {"error": json.loads(e.read()), "status": e.code}

# 1. Branch protection
print("=== Branch Protection ===")
protection = {
    "required_status_checks": {"strict": True, "contexts": ["lint", "test"]},
    "enforce_admins": False,
    "required_pull_request_reviews": {
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": False,
        "required_approving_review_count": 1,
    },
    "restrictions": None,
    "allow_force_pushes": False,
    "allow_deletions": False,
    "required_conversation_resolution": True,
}
r = api("PUT", "/branches/master/protection", protection)
print(f"Status: {r.get('status', 'FAIL')}")
if "url" in r:
    print(f"URL: {r['url'][:80]}")

# 2. Vulnerability alerts
print("\n=== Dependabot ===")
r = api("PUT", "/vulnerability-alerts", {})
print(f"Status: {r.get('status', 'FAIL')}")

# 3. Dependabot auto-fix
print("\n=== Dependabot Auto-fix ===")
r = api("PUT", "/automated-security-fixes", {})
print(f"Status: {r.get('status', 'FAIL')}")

# 4. Environments
print("\n=== Environments ===")
for env_name in ["staging", "production"]:
    r = api("PUT", f"/environments/{env_name}", {})
    print(f"  {env_name}: {r.get('status', 'FAIL')}")
