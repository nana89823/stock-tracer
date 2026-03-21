import logging
import os
import subprocess

from app.celery_app import celery

logger = logging.getLogger(__name__)

# In Docker: scrapy.cfg + stock_tracer/ mounted at /scrapy_project
# Locally: project root (parent of backend/)
SCRAPY_PROJECT_DIR = os.environ.get("SCRAPY_PROJECT_DIR", "/scrapy_project")

# Spiders that need longer timeout (large CSV downloads)
SLOW_SPIDERS = {"major_holders", "raw_chip", "broker_trading"}
DEFAULT_TIMEOUT = 300
SLOW_TIMEOUT = 900


@celery.task(name="app.tasks.crawl_task.run_spider", bind=True, max_retries=2)
def run_spider(self, spider_name: str) -> dict:
    """Run a Scrapy spider via subprocess.

    Args:
        spider_name: Name of the spider (e.g. 'raw_price', 'tpex_chip').

    Returns:
        dict with status and details.
    """
    timeout = SLOW_TIMEOUT if spider_name in SLOW_SPIDERS else DEFAULT_TIMEOUT
    logger.info("Starting spider '%s' (task %s, timeout=%ds)", spider_name, self.request.id, timeout)

    try:
        result = subprocess.run(
            ["scrapy", "crawl", spider_name],
            cwd=SCRAPY_PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode == 0:
            logger.info("Spider '%s' completed successfully", spider_name)
            return {"status": "success", "spider": spider_name}
        else:
            logger.error(
                "Spider '%s' failed (exit %d): %s",
                spider_name, result.returncode, result.stderr[-500:]
            )
            return {
                "status": "failed",
                "spider": spider_name,
                "error": result.stderr[-500:],
            }

    except subprocess.TimeoutExpired:
        logger.error("Spider '%s' timed out after 300s", spider_name)
        return {"status": "failed", "spider": spider_name, "error": "timeout"}

    except Exception as exc:
        logger.exception("Spider '%s' unexpected error", spider_name)
        raise self.retry(exc=exc, countdown=60)
