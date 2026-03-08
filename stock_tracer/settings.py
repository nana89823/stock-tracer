# Scrapy settings for stock_tracer project

BOT_NAME = "stock_tracer"

SPIDER_MODULES = ["stock_tracer.spiders"]
NEWSPIDER_MODULE = "stock_tracer.spiders"

# Crawl responsibly by identifying yourself
USER_AGENT = "stock_tracer (+https://github.com/stock-tracer)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 1

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 1

# Disable cookies
COOKIES_ENABLED = False

# Override the default request headers
DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}

# Configure item pipelines
ITEM_PIPELINES = {
    "stock_tracer.pipelines.DatabasePipeline": 200,
    "stock_tracer.pipelines.CsvExportPipeline": 300,
}

# Database connection (from environment variable)
import os
DATABASE_URL_SYNC = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://stock_tracer:stock_tracer_dev@localhost:5433/stock_tracer"
)

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 5

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

# Output directory
OUTPUT_DIR = "output"
