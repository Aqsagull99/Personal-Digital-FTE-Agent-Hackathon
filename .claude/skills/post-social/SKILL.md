---
name: post-social
description: Post to Facebook or Instagram with approval. Use when user says "post to facebook", "post to instagram", "social media post", "share on facebook", or "share on instagram".
---

# Post to Social Media Skill

## Purpose
Create posts for Facebook and Instagram with human approval workflow.

## Execution

### Post to Facebook
```bash
uv run python watchers/social_poster.py facebook "Your post content here"
```

### Post to Instagram (requires image)
```bash
uv run python watchers/social_poster.py instagram "Your caption" /path/to/image.jpg
```

### Get Summary
```bash
uv run python watchers/social_poster.py summary facebook
uv run python watchers/social_poster.py summary instagram
```

## Approval Workflow

1. **Create Post Request**
   - Command creates approval file in `/Pending_Approval/`
   - Example: `FACEBOOK_POST_20260211_120000.md`

2. **Human Reviews**
   - Check content in Obsidian
   - Move to `/Approved/` if OK

3. **Execute Post**
   - Posts with approved content are executed
   - Move completed to `/Done/`

## Content Guidelines

### Facebook Posts
- Professional and engaging
- Can include links
- No image required

### Instagram Posts
- Requires image for feed posts
- Use relevant hashtags
- Keep caption engaging

## Example Posts

### Facebook Business Update
```
🚀 Exciting news! We've just launched our new service.

Check it out at example.com

#Business #NewLaunch
```

### Instagram Product Post
```
Beautiful new arrivals! ✨

Shop now - link in bio

#Product #Shopping #NewArrivals
```
