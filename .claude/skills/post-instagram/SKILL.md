---
name: post-instagram
description: Post content to Instagram with approval. Use when user says "post to instagram", "instagram post", "share on instagram", or "create instagram post".
---

# Post to Instagram Skill

## Purpose
Post content to Instagram with human-in-the-loop approval workflow.

## Human-in-the-Loop
By default, posts require human approval before publishing:
1. Creates approval file in `/Pending_Approval/`
2. User reviews and moves to `/Approved/`
3. Then post is published

## Workflow

### Step 1: Create Post Content
Generate engaging caption and select/create image.

### Step 2: Request Approval
```bash
uv run python watchers/instagram_poster.py "Your caption here" /path/to/image.jpg
```

This creates: `/Pending_Approval/INSTAGRAM_POST_[timestamp].md`

### Step 3: User Approves
User moves file to `/Approved/` folder.

### Step 4: Publish Approved Posts
```bash
uv run python watchers/instagram_poster.py --approve
```

## Direct Post (No Approval)
Only use when explicitly requested:
```bash
uv run python watchers/instagram_poster.py --post-direct "Caption here" /path/to/image.jpg
```

## Get Summary
```bash
uv run python watchers/instagram_poster.py --summary
```

## Important: Image Required
Instagram feed posts **require an image**. Always provide an image path.

## Content Guidelines

### Good Instagram Posts:
- Engaging captions with personality
- Relevant hashtags (5-15 recommended)
- High quality images
- Product showcases and behind-the-scenes
- User-generated content (with permission)

### Avoid:
- Posts without images (will fail)
- Too many hashtags (looks spammy)
- Low quality or irrelevant images

## Example Content Templates

### Product Post
```
Beautiful new arrivals! ✨

Shop now - link in bio

#Product #Shopping #NewArrivals
```

### Behind the Scenes
```
A sneak peek at what we're working on 👀

Stay tuned for something exciting!

#BehindTheScenes #ComingSoon #YourBrand
```

## Notes
- Uses Playwright browser automation (not API)
- Requires Instagram login session (run instagram_watcher.py first)
- Session persists in `.instagram_session/` directory
- Uses pushState + popstate trick to open create dialog
