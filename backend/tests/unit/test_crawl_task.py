from unittest.mock import patch, MagicMock


def test_run_spider_calls_subprocess_with_correct_args():
    """run_spider should invoke 'scrapy crawl <spider_name>' via subprocess."""
    with patch("app.tasks.crawl_task.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")

        from app.tasks.crawl_task import run_spider
        result = run_spider.apply(args=("raw_price",)).get()

        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert "scrapy" in cmd
        assert "crawl" in cmd
        assert "raw_price" in cmd
        assert result["status"] == "success"


def test_run_spider_returns_failure_on_nonzero_exit():
    """run_spider should return failure status when subprocess exits non-zero."""
    with patch("app.tasks.crawl_task.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error msg")

        from app.tasks.crawl_task import run_spider
        result = run_spider.apply(args=("bad_spider",)).get()

        assert result["status"] == "failed"
        assert "error msg" in result["error"]
