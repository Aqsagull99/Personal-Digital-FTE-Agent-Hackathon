---
name: post-facebook
description: Post content to Facebook with approval. Use when user says "post to facebook", "facebook post", "share on facebook", or "create facebook post".
---

# Post to Facebook Skill

## Purpose
Post content to Facebook with human-in-the-loop approval workflow.

## Human-in-the-Loop
By default, posts require human approval before publishing:
1. Creates approval file in `/Pending_Approval/`
2. User reviews and moves to `/Approved/`
3. Then post is published

## Workflow

### Step 1: Create Post Content
Generate engaging content based on user request.

### Step 2: Request Approval
```bash
uv run python watchers/facebook_poster.py "Your post content here"
```

This creates: `/Pending_Approval/FACEBOOK_POST_[timestamp].md`

### Step 3: User Approves
User moves file to `/Approved/` folder.

### Step 4: Publish Approved Posts
```bash
uv run python watchers/facebook_poster.py --approve
```

## Direct Post (No Approval)
Only use when explicitly requested:
```bash
uv run python watchers/facebook_poster.py --post-direct "Post without approval"
```

## Get Summary
```bash
uv run python watchers/facebook_poster.py --summary
```

## Content Guidelines

### Good Facebook Posts:
- Professional and engaging tone
- Can include links and hashtags
- No image required (text-only posts work)
- Business updates and announcements
- Industry insights and tips

### Avoid:
- Overly promotional content
- Controversial topics
- Spam-like frequency

## Example Content Templates

### Business Update
```
🚀 Exciting news! We've just launched our new service.

Check it out at example.com

#Business #NewLaunch
```

### Engagement Post
```
What's your experience with [topic]?

Share your thoughts below 👇

#Discussion #YourIndustry
```

## Notes
- Uses Playwright browser automation (not API)
- Requires Facebook login session (run fb_login.py first)
- Session persists in `.facebook_session/` directory
