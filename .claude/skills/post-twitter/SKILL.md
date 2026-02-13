---
name: post-twitter
description: Post tweet to Twitter (X) with approval. Use when user says "post tweet", "tweet this", "post to twitter", or "share on twitter".
---

# Post Tweet Skill

## Purpose
Post tweets to Twitter (X) with human-in-the-loop approval.

## Execution

### Post New Tweet
```bash
uv run python watchers/twitter_poster.py tweet "Your tweet content here"
```

### Reply to Tweet
```bash
uv run python watchers/twitter_poster.py reply "Your reply" https://twitter.com/user/status/123
```

### Get Summary
```bash
uv run python watchers/twitter_poster.py summary
```

## Character Limit
- Maximum: **280 characters**
- System validates before posting

## Approval Workflow

1. **Create Tweet Request**
   ```bash
   uv run python watchers/twitter_poster.py tweet "Hello Twitter!"
   ```
   Creates: `/Pending_Approval/TWITTER_POST_*.md`

2. **Human Reviews**
   - Check content in Obsidian
   - Verify character count
   - Move to `/Approved/` if OK

3. **Execute Post**
   - Tweet posted
   - File moved to `/Done/`

## Tweet Templates

### Business Update
```
🚀 Exciting news! [Your update here]

#Business #Update
```
(Keep under 280 chars)

### Engagement Tweet
```
What's your take on [topic]?

Reply below 👇

#Discussion
```

### Product Launch
```
🎉 New launch alert!

[Product name] is now live.

Check it out: [link]

#Launch #NewProduct
```

## Notes
- Always validate character count
- Use hashtags strategically (2-3 max)
- Mentions (@user) count toward limit
- Links take ~23 characters (t.co shortening)
