# Linear Setup Guide

> Last updated: 2026-06-27

## Prerequisites

- Linear account (free or paid)
- Linear API key

## Step 1: Create Workspace

1. Go to https://linear.app
2. Click **Create workspace**
3. Name: `TerraBits`
4. Choose plan: Free (up to 250 issues) is fine for now

## Step 2: Create Project

1. In TerraBits workspace, click **Projects** → **New project**
2. Name: `Pulse of Earth`
3. Description: "Research and software project for Earth data"
4. Icon: 🌍

## Step 3: Create Labels

1. Go to **Settings** → **Labels** → **New label**
2. Create these labels:

| Label | Color | Type |
| --- | --- | --- |
| discovery | #3b82f6 (blue) | status |
| architecture | #8b5cf6 (purple) | status |
| backend | #22c55e (green) | topic |
| frontend | #eab308 (yellow) | topic |
| devops | #f97316 (orange) | topic |
| security | #ef4444 (red) | topic |
| testing | #6b7280 (gray) | topic |
| documentation | #06b6d4 (teal) | topic |
| low-risk | #22c55e (green) | risk |
| medium-risk | #eab308 (yellow) | risk |
| high-risk | #ef4444 (red) | risk |
| blocked | #000000 (black) | status |
| needs-owner | #ffffff (white) | status |

## Step 4: Create Cycles (Optional)

1. In Pulse of Earth project, click **Cycles**
2. Create Cycle 1: "Phase 0-1: Bootstrap"
3. Start date: 2026-06-28

## Step 5: Generate API Key

1. Go to **Settings** → **API** → **Personal API tokens**
2. Click **Create token**
3. Name: `hermes-bot`
4. Scopes: **Read and write**
5. Copy the key (starts with `lin_api_`)

### Provide to Hermes

Send me the Linear API key, and I'll configure:
- Automatic issue creation after discovery
- Status sync after commits
- Roadmap alignment

## Step 6: Team Setup (Optional)

1. **Settings** → **Members** → **Invite**
2. Add team members with roles:
   - Admin: owner
   - Member: developers
   - Guest: observers

## Cost

| Plan | Price | Issues | Members |
| --- | --- | --- | --- |
| Free | $0/mo | 250 | Unlimited |
| Plus | $8/user/mo | Unlimited | Unlimited |

For Proof of Concept, **Free** is sufficient.
