import math


def num(x: object, digits: int = 6) -> float | None:
    """JSON-safe float: results are stored as JSON, which has no NaN."""
    if x is None:
        return None
    f = float(x)  # type: ignore[arg-type]
    return None if math.isnan(f) or math.isinf(f) else round(f, digits)
