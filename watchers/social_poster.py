"""
Social Poster Orchestrator - Facebook + Instagram posting and summaries.
Gold Tier Requirement: Integrate Facebook and Instagram and generate summary.
"""
from __future__ import annotations

import json
import argparse
from datetime import datetime
from pathlib import Path

from facebook_poster import FacebookPoster
from instagram_poster import InstagramPoster


def _vault_path() -> Path:
    root = Path(__file__).parent.parent
    vault = root / 'AI_Employee_Vault'
    return vault.resolve() if vault.is_symlink() else vault


def create_dual_approval(content: str, image_path: str | None = None) -> dict:
    fb = FacebookPoster()
    ig = InstagramPoster()

    fb_result = fb.post(content, image_path=image_path, require_approval=True)
    ig_result = ig.post(content, image_path=image_path, require_approval=True)

    return {
        'facebook': fb_result,
        'instagram': ig_result
    }


def process_approved() -> dict:
    fb = FacebookPoster()
    ig = InstagramPoster()

    fb_results = fb.process_approved_posts()
    ig_results = ig.process_approved_posts()

    return {
        'facebook': fb_results,
        'instagram': ig_results
    }


def generate_social_summary(days: int = 7) -> dict:
    fb = FacebookPoster()
    ig = InstagramPoster()
    vault = _vault_path()
    reports_path = vault / 'Reports'
    reports_path.mkdir(exist_ok=True)

    fb_summary = fb.generate_summary(days=days)
    ig_summary = ig.generate_summary(days=days)

    combined = {
        'generated_at': datetime.now().isoformat(),
        'period_days': days,
        'facebook': fb_summary,
        'instagram': ig_summary,
        'totals': {
            'posts_created': fb_summary.get('posts_created', 0) + ig_summary.get('posts_created', 0),
            'posts_pending': fb_summary.get('posts_pending', 0) + ig_summary.get('posts_pending', 0),
            'notifications_processed': fb_summary.get('notifications_processed', 0) + ig_summary.get('notifications_processed', 0),
        }
    }

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = reports_path / f'SOCIAL_SUMMARY_{ts}.md'
    report_file.write_text(
        f"""---
type: social_summary
generated: {combined['generated_at']}
period_days: {days}
---

# Social Media Summary

## Facebook
- Posts created: {fb_summary.get('posts_created', 0)}
- Posts pending: {fb_summary.get('posts_pending', 0)}
- Notifications processed: {fb_summary.get('notifications_processed', 0)}

## Instagram
- Posts created: {ig_summary.get('posts_created', 0)}
- Posts pending: {ig_summary.get('posts_pending', 0)}
- Notifications processed: {ig_summary.get('notifications_processed', 0)}

## Combined Totals
- Posts created: {combined['totals']['posts_created']}
- Posts pending: {combined['totals']['posts_pending']}
- Notifications processed: {combined['totals']['notifications_processed']}
"""
    )
    combined['report_file'] = str(report_file)
    return combined


def main():
    parser = argparse.ArgumentParser(description='Facebook + Instagram social poster orchestration')
    parser.add_argument('content', nargs='?', help='Content to post (approval mode by default)')
    parser.add_argument('--image', help='Optional image path (Instagram feed posts require image in real mode)')
    parser.add_argument('--approve', action='store_true', help='Process approved Facebook and Instagram posts')
    parser.add_argument('--summary', action='store_true', help='Generate combined social summary report')
    parser.add_argument('--days', type=int, default=7, help='Summary period in days')
    args = parser.parse_args()

    if args.approve:
        print(json.dumps(process_approved(), indent=2))
        return

    if args.summary:
        print(json.dumps(generate_social_summary(days=args.days), indent=2))
        return

    if not args.content:
        parser.print_help()
        return

    print(json.dumps(create_dual_approval(args.content, image_path=args.image), indent=2))


if __name__ == '__main__':
    main()
