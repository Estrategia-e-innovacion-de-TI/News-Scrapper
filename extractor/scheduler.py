"""Simple local scheduling helper for periodic extraction runs."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Awaitable

logger = logging.getLogger("news_radar.scheduler")


class SimpleScheduler:
    """Simple scheduler for periodic extraction runs."""
    
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
    
    async def run_periodic(
        self,
        func: Callable[[], Awaitable],
        interval_hours: float = 6,
        run_immediately: bool = True,
    ):
        """Run function periodically."""
        self._running = True
        interval = timedelta(hours=interval_hours)
        
        if run_immediately:
            logger.info("Running initial extraction...")
            try:
                await func()
            except Exception as e:
                logger.error(f"Initial run failed: {e}")
        
        while self._running:
            next_run = datetime.now() + interval
            logger.info(f"Next run scheduled at {next_run.isoformat()}")
            
            await asyncio.sleep(interval.total_seconds())
            
            if not self._running:
                break
            
            logger.info("Starting scheduled extraction...")
            try:
                await func()
            except Exception as e:
                logger.error(f"Scheduled run failed: {e}")
    
    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()


async def schedule_extraction(
    interval_hours: float = 6,
    **extraction_kwargs,
):
    """Schedule periodic extraction runs."""
    from .graph import run_extraction
    
    scheduler = SimpleScheduler()
    
    async def run():
        await run_extraction(**extraction_kwargs)
    
    try:
        await scheduler.run_periodic(run, interval_hours=interval_hours)
    except asyncio.CancelledError:
        logger.info("Scheduler cancelled")
    finally:
        scheduler.stop()
