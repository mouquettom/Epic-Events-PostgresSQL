import os

import sentry_sdk


def init_sentry() -> None:
    """ Initialise Sentry si un DSN est configuré. """

    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        return

    sentry_sdk.init(
        dsn=sentry_dsn,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )