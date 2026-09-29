class HarnessError(Exception):
    """Every message must say what to do next."""


class StateError(HarnessError):
    pass


class ValidationError(HarnessError):
    pass


class NotFound(HarnessError):
    pass
