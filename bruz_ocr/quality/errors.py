"""Quality assessment errors."""


class QualityAssessmentError(Exception):
    """A page or assessment cannot be evaluated reliably."""


class PageImageUnavailableError(QualityAssessmentError):
    """An ingested page image is missing or unreadable."""
