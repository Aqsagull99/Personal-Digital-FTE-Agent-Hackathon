---
name: post-linkedin
description: Post content to LinkedIn for business/sales. Use when user says "post to linkedin", "linkedin post", "share on linkedin", or "create linkedin post".
---

# Post to LinkedIn Skill

## Purpose
Create and post content to LinkedIn for business promotion and sales generation.

## Human-in-the-Loop
By default, posts require human approval before publishing:
1. Creates approval file in `/Pending_Approval/`
2. User reviews and moves to `/Approved/`
3. Then post is published

## Workflow

### Step 1: Create Post Content
Generate business-relevant content based on user request.

### Step 2: Request Approval
```bash
uv run python watchers/linkedin_poster.py "Your post content here"
```

This creates: `/Pending_Approval/LINKEDIN_POST_[timestamp].md`

### Step 3: User Approves
User moves file to `/Approved/` folder.

### Step 4: Publish Approved Posts
```bash
uv run python watchers/linkedin_poster.py --approve
```

## Direct Post (No Approval)
Only use when explicitly requested:
```bash
uv run python watchers/linkedin_poster.py "Content" --no-approval
```

## Post Content Guidelines

### Good Business Posts:
- Industry insights and tips
- Company updates and achievements
- Helpful resources and guides
- Client success stories (with permission)
- Professional development content

### Avoid:
- Overly promotional content
- Controversial topics
- Personal/non-business content
- Spam-like frequency

## Example Content Templates

### Insight Post:
```
🔍 [Industry Insight]

[2-3 sentences about the insight]

Key takeaway: [One actionable point]

What's your experience with this? 👇

#YourIndustry #ProfessionalTips
```

### Service Announcement:
```
🚀 Exciting Update!

[Brief announcement]

[How it benefits clients]

DM me to learn more!

#BusinessGrowth #Services
```

## Output
- Pending: `/Pending_Approval/LINKEDIN_POST_*.md`
- After approval: Post published, file moved to `/Done/`
- Logs: `/Logs/[date].json`
