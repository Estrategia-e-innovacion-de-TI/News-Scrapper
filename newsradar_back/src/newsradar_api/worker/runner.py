"""Worker entry point for local orchestration."""
from __future__ import annotations

import asyncio
import logging

from newsradar_api.worker.jobs import list_job_statuses

logger = logging.getLogger(__name__)


async def main() -> None:
    rows = await list_job_statuses()
    logger.info("Worker ready. %d job rows available.", len(rows))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
