import logging
import sys


class _AsyncioNoneCallbackFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # Filter noisy asyncio bug: "Exception in callback None()" + NoneType callable
        if record.name == "asyncio":
            msg = record.getMessage()
            if "Exception in callback None()" in msg:
                return False
            if "NoneType" in msg and "object is not callable" in msg:
                return False
        return True


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(_AsyncioNoneCallbackFilter())

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[handler],
    )
