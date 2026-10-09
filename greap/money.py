"""Money helpers. Decimal avoids float drift on the exact-amount check (FR-5.5)."""

from decimal import ROUND_HALF_UP, Decimal

from greap.constants import MONEY_DECIMALS

CENT = Decimal(1).scaleb(-MONEY_DECIMALS)


def toDecimal(value: float | str | Decimal) -> Decimal:
    """Go through str so 0.1 + 0.2 style float noise never enters the math."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def unitPriceOf(cartonPrice: float, cartonSize: int) -> float:
    """Unit price = carton price / carton size (PRD assumptions)."""
    return float(toDecimal(Decimal(str(cartonPrice)) / cartonSize))


def lineTotal(unitPrice: float, units: int) -> float:
    """Total owed for an entry: units x unit price."""
    return float(toDecimal(Decimal(str(unitPrice)) * units))


def formatMoney(amount: float, currency: str) -> str:
    """Show every amount with two decimals, e.g. 'SGD 5.50'."""
    return f"{currency} {toDecimal(amount):.{MONEY_DECIMALS}f}"


def parseAmount(text: str) -> Decimal | None:
    """Parse what the user typed for /pay; None when it is not a number."""
    cleaned = text.strip().upper().replace(",", "")
    for token in cleaned.split():
        try:
            return toDecimal(token)
        except ArithmeticError:
            continue
    return None
