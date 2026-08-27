class LinkedInError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        *,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


class InvalidProfileURL(LinkedInError):
    def __init__(self, message: str = "A valid LinkedIn profile URL is required.") -> None:
        super().__init__("INVALID_PROFILE_URL", message, 400)


class ProfileUnavailable(LinkedInError):
    def __init__(self) -> None:
        super().__init__("PROFILE_UNAVAILABLE", "The LinkedIn profile is unavailable.", 404)


class ServiceRateLimited(LinkedInError):
    def __init__(self) -> None:
        super().__init__(
            "SERVICE_RATE_LIMITED",
            "The service request limit has been reached. Try again later.",
            429,
            retryable=True,
        )


class LinkedInRateLimited(LinkedInError):
    def __init__(self) -> None:
        super().__init__(
            "LINKEDIN_RATE_LIMITED",
            "LinkedIn rate-limited the upstream request. Try again later.",
            429,
            retryable=True,
        )


class UpstreamSchemaChanged(LinkedInError):
    def __init__(self) -> None:
        super().__init__(
            "UPSTREAM_SCHEMA_CHANGED",
            "LinkedIn returned an unsupported response shape.",
            502,
        )


class LinkedInUpstreamError(LinkedInError):
    def __init__(self) -> None:
        super().__init__(
            "LINKEDIN_UPSTREAM_ERROR",
            "LinkedIn returned an unexpected upstream error.",
            502,
            retryable=True,
        )


class LinkedInAuthRequired(LinkedInError):
    def __init__(self) -> None:
        super().__init__(
            "LINKEDIN_AUTH_REQUIRED",
            "LinkedIn authentication is missing or has expired.",
            503,
        )


class LinkedInCheckpointRequired(LinkedInError):
    def __init__(self) -> None:
        super().__init__(
            "LINKEDIN_CHECKPOINT_REQUIRED",
            "LinkedIn requires an interactive account checkpoint.",
            503,
        )


class LinkedInTemporarilyBlocked(LinkedInError):
    def __init__(self) -> None:
        super().__init__(
            "LINKEDIN_TEMPORARILY_BLOCKED",
            "LinkedIn temporarily blocked requests from this server.",
            503,
        )


class LinkedInTimeout(LinkedInError):
    def __init__(self) -> None:
        super().__init__(
            "LINKEDIN_TIMEOUT",
            "The LinkedIn upstream request timed out.",
            504,
            retryable=True,
        )
