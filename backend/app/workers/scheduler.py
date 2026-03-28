"""
Background scheduler — runs cron jobs for syncing, baselines, and AI generation.
Uses APScheduler with AsyncIO.
"""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.services.sync_service import sync_all_accounts, compute_all_baselines
from app.services.brief_worker import generate_all_briefs, generate_all_recommendations

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def setup_scheduler():
    """Register all cron jobs."""

    # Sync all accounts every 2 hours
    scheduler.add_job(
        job_sync_all,
        IntervalTrigger(hours=2),
        id="sync_all_accounts",
        name="Sync all accounts (scrape new data)",
        replace_existing=True,
        next_run_time=datetime.now(timezone.utc),  # Run immediately on startup
    )

    # Compute baselines daily at 3:00 AM UTC
    scheduler.add_job(
        job_compute_baselines,
        CronTrigger(hour=3, minute=0),
        id="compute_baselines",
        name="Recompute baselines for all accounts",
        replace_existing=True,
    )

    # Generate daily briefs at 7:00 AM UTC
    scheduler.add_job(
        job_generate_briefs,
        CronTrigger(hour=7, minute=0),
        id="generate_daily_briefs",
        name="Generate daily briefs for all accounts",
        replace_existing=True,
    )

    # Generate recommendations at 7:30 AM UTC
    scheduler.add_job(
        job_generate_recommendations,
        CronTrigger(hour=7, minute=30),
        id="generate_recommendations",
        name="Generate recommendations for all accounts",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with jobs: sync (2h), baselines (3am), briefs (7am), recommendations (7:30am)")


async def job_sync_all():
    """Cron job: sync all accounts."""
    logger.info("CRON: Starting sync for all accounts...")
    try:
        summaries = await sync_all_accounts()
        total_new = sum(s.get("new_posts", 0) for s in summaries if "error" not in s)
        logger.info(f"CRON: Sync complete. {len(summaries)} accounts synced, {total_new} new posts found.")
    except Exception as e:
        logger.error(f"CRON: Sync failed: {e}")


async def job_compute_baselines():
    """Cron job: recompute baselines."""
    logger.info("CRON: Computing baselines for all accounts...")
    try:
        count = await compute_all_baselines()
        logger.info(f"CRON: Baselines computed for {count} accounts.")
    except Exception as e:
        logger.error(f"CRON: Baseline computation failed: {e}")


async def job_generate_briefs():
    """Cron job: generate daily briefs."""
    logger.info("CRON: Generating daily briefs...")
    try:
        count = await generate_all_briefs()
        logger.info(f"CRON: Generated {count} daily briefs.")
    except Exception as e:
        logger.error(f"CRON: Brief generation failed: {e}")


async def job_generate_recommendations():
    """Cron job: generate recommendations."""
    logger.info("CRON: Generating recommendations...")
    try:
        count = await generate_all_recommendations()
        logger.info(f"CRON: Generated recommendations for {count} accounts.")
    except Exception as e:
        logger.error(f"CRON: Recommendation generation failed: {e}")
