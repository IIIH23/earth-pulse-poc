# n8n Integration

> Last updated: 2026-06-27

## Architecture

### Deployment Options

| Option | Pros | Cons | Recommendation |
| --- | --- | --- | --- |
| Self-hosted (staging VPS) | Full control, no extra cost | Uses RAM/CPU on 4 GB VPS | ❌ Not recommended |
| Self-hosted (Hermes VPS) | Separate resources | Single point of failure | ⚠️ Future option |
| n8n Cloud | Managed, reliable | Monthly cost, data leaves infra | ⚠️ Needs owner approval |
| Separate small VPS | Isolated, dedicated | Extra cost | ✅ Recommended (future) |

### Recommended Architecture (Future)

```
GitHub PR merged
  → n8n webhook
  → Linear: update issue status
  → Telegram: notify team

Deployment failed
  → n8n webhook
  → Telegram: alert
  → Linear: create incident issue

Backup failed
  → n8n webhook
  → Telegram: alert
  → Linear: create issue

Health check failed (3x)
  → n8n webhook
  → Linear: create incident issue
  → Telegram: critical alert
```

## Workflows

### 1. GitHub PR Merged → Linear Update

| Step | Action |
| --- | --- |
| Trigger | GitHub webhook (PR merged, main branch) |
| 1 | Extract PR title, labels, issue number |
| 2 | Find linked Linear issue |
| 3 | Update Linear issue status → Done |
| 4 | Add comment with merge details |
| 5 | Telegram: success notification |

### 2. Deployment Failed → Alert

| Step | Action |
| --- | --- |
| Trigger | GitHub Actions workflow failed |
| 1 | Extract commit, error message |
| 2 | Telegram: critical alert |
| 3 | Linear: create incident issue |
| 4 | Auto-rollback trigger |

### 3. Weekly Report → Obsidian

| Step | Action |
| --- | --- |
| Trigger | Schedule (Monday 9:00) |
| 1 | Collect: commits, PRs, deployments, issues |
| 2 | Generate weekly summary |
| 3 | Obsidian: create note in Daily/ |
| 4 | Telegram: summary notification |

### 4. Backup Verification

| Step | Action |
| --- | --- |
| Trigger | Schedule (daily 6:00) |
| 1 | Check backup file exists |
| 2 | Verify checksum |
| 3 | If failed: Telegram + Linear |

## Security Model

### Credential Storage

| Credential | Storage |
| --- | --- |
| n8n API key | n8n internal |
| GitHub token | n8n credentials |
| Linear token | n8n credentials |
| Telegram token | n8n credentials |

### Access Control

- n8n: Basic Auth + SSO (if cloud)
- Webhook endpoints: HMAC signature verification
- No public endpoints
- All communications over HTTPS

### Data Flow Security

- No secrets in logs
- No full stack traces
- Sanitized error messages
- Encrypted credentials at rest

## Deployment Plan (Future)

1. Provision separate VPS (2 vCPU, 2 GB RAM)
2. Install Docker + Docker Compose
3. Deploy n8n container
4. Configure PostgreSQL for n8n
5. Set up HTTPS via Caddy
6. Configure Basic Auth
7. Import workflows
8. Test webhook endpoints
9. Set up monitoring

## Resource Requirements

| Resource | Minimum | Recommended |
| --- | --- | --- |
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disk | 10 GB | 20 GB |
| Network | 100 GB/month | unlimited |

## Owner Actions Required

1. Decide: self-hosted vs n8n Cloud
2. If self-hosted: provision VPS
3. Provide API keys for integrations
4. Approve n8n installation
