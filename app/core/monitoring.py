"""Error monitoring with Sentry, enabled only when SENTRY_DSN is set."""

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_monitoring(release: str) -> bool:
    if not settings.sentry_dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        release=f"chordweaver-api@{release}",
        environment="production" if settings.is_production else settings.environment,
        traces_sample_rate=0.0,
        # No request bodies or user IPs: chord progressions and emails stay out of the error reports.
        send_default_pii=False,
    )
    logger.info("Sentry error monitoring enabled")
    return True
