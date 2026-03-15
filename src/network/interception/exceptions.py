"""Exception classes for network interception."""


class TimingError(Exception):
    """Raised when attach() is called after page.goto().

    This error indicates that the network interceptor was attached
    to the page after navigation occurred, which means some network
    responses may have been missed.
    """

    pass


class PatternError(Exception):
    """Raised for invalid pattern input at construction time.

    This error indicates that the URL pattern provided to the
    NetworkInterceptor is invalid or malformed.
    """

    pass
