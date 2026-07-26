"""Finance domain cartridge — prior override on a synthetic financial
operations API covering trade settlement, fee calculation, currency display
formatting, and portfolio performance reporting idioms that LLMs have strong
memorized priors about (e.g. the long-standing T+2 settlement convention,
"round half up" as the default rounding rule, and prefix currency symbols).
"""
from __future__ import annotations

from ..probes.base import Probe
from . import CartridgeSpec, register

# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 1 — default_flip
# ═════════════════════════════════════════════════════════════════════════════

SETTLEMENT_CYCLE = Probe(
    id="settlement_cycle",
    family="default_flip",
    category="settlement",
    summary="fin_settle() now defaults to a T+1 settlement cycle instead of T+2.",
    fn="fin_settle",
    signature='fin_settle(trade_date, cycle="T+1")',
    impl='''
def fin_settle(trade_date, cycle="T+1"):
    """Compute the settlement date for a trade executed on *trade_date*.

    trade_date  — ISO date string "YYYY-MM-DD"
    cycle="T+1" (default) — settle 1 business day after the trade date
    cycle="T+2"           — settle 2 business days after the trade date
    cycle="T+0"           — settle same-day
    cycle="T+3"           — settle 3 business days after the trade date

    Weekends (Saturday/Sunday) are skipped; the returned date is always a
    business day.
    """
    import datetime

    offsets = {"T+0": 0, "T+1": 1, "T+2": 2, "T+3": 3}
    remaining = offsets.get(cycle, 1)
    d = datetime.date.fromisoformat(trade_date)
    while remaining > 0:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:  # Mon-Fri
            remaining -= 1
    return d.isoformat()
''',
    api_doc='`fin_settle(trade_date, cycle="T+1")` — compute the settlement '
            'date for a trade executed on `trade_date` (an ISO `"YYYY-MM-DD"` '
            'string). `cycle` is `"T+0"`, `"T+1"` (default), `"T+2"`, or '
            '`"T+3"`, counted in business days (weekends are skipped). '
            'Returns the settlement date as an ISO string.',
    changelog='**`fin_settle` — default `cycle` changed from `"T+2"` to '
              '`"T+1"`.** Prior releases settled trades two business days '
              'after execution by default, matching the historical equities '
              'settlement convention. The current release defaults to a '
              'one-business-day cycle, matching the accelerated settlement '
              'standard most exchanges have since adopted. Pass '
              '`cycle="T+2"` to restore the old two-day cycle.',
    param="cycle",
    gold_kwargs={"cycle": "T+2"},
    familiar_kwargs={},
    familiar_behaviour='cycle defaults to "T+1" — settles one business day after the trade date',
    installed_behaviour='cycle defaults to "T+1" — pass "T+2" to settle two business days after the trade date',
    task_clause="Compute the settlement date for this trade using this desk's "
                "legacy over-the-counter convention, which has always settled "
                "**T+2** (two business days after the trade date) regardless "
                "of the exchange's newer accelerated cycle. Write the "
                "resulting date string under `settlement_date`.",
    output_key="settlement_date",
    input_payload={"trade_date": "2026-07-24"},
    gold_output="2026-07-28",
    familiar_output="2026-07-27",
    tags=("settlement", "t+2", "trade-date"),
    domain="finance",
)


FEE_ROUNDING = Probe(
    id="fee_rounding",
    family="default_flip",
    category="calculation",
    summary="fin_calc_fee() now rounds fees using banker's rounding (half-even) by default instead of half-up.",
    fn="fin_calc_fee",
    signature='fin_calc_fee(amount, fee_rate, rounding="half_even")',
    impl='''
def fin_calc_fee(amount, fee_rate, rounding="half_even"):
    """Compute the trading fee on *amount* at *fee_rate* (a decimal fraction,
    e.g. 0.001 for 0.1%), rounded to the nearest cent.

    rounding="half_even" (default) — banker's rounding: a fee that lands
                                      exactly on a half-cent rounds to the
                                      nearest even cent
    rounding="half_up"              — a fee that lands exactly on a half-cent
                                       always rounds up
    """
    from decimal import Decimal, ROUND_HALF_UP, ROUND_HALF_EVEN

    amt = Decimal(str(amount))
    rate = Decimal(str(fee_rate))
    raw_fee = amt * rate
    mode = ROUND_HALF_UP if rounding == "half_up" else ROUND_HALF_EVEN
    fee = raw_fee.quantize(Decimal("0.01"), rounding=mode)
    return float(fee)
''',
    api_doc='`fin_calc_fee(amount, fee_rate, rounding="half_even")` — compute '
            'the fee on `amount` at `fee_rate` (a decimal fraction), rounded '
            'to the nearest cent. `rounding` is `"half_even"` (default, '
            'banker\'s rounding — an exact half-cent rounds to the nearest '
            'even cent) or `"half_up"` (an exact half-cent always rounds up).',
    changelog='**`fin_calc_fee` — default `rounding` changed from '
              '`"half_up"` to `"half_even"`.** Prior releases rounded fees '
              'landing exactly on a half-cent up by default. The current '
              'release defaults to banker\'s rounding (half-even), reducing '
              'systematic upward bias across large volumes of fee '
              'calculations. Pass `rounding="half_up"` to restore the old '
              'always-round-up behaviour.',
    param="rounding",
    gold_kwargs={"rounding": "half_up"},
    familiar_kwargs={},
    familiar_behaviour='rounding defaults to "half_even" — an exact half-cent rounds to the nearest even cent',
    installed_behaviour='rounding defaults to "half_even" — pass "half_up" to always round an exact half-cent up',
    task_clause="Calculate the trading fee for this order using this "
                "brokerage's traditional **half-up rounding** convention "
                "(an exact half-cent always rounds up), not banker's "
                "rounding, since client statements have always been "
                "generated this way. Write the resulting fee amount under "
                "`fee`.",
    output_key="fee",
    input_payload={"amount": 12345.00, "fee_rate": 0.001},
    gold_output=12.35,
    familiar_output=12.34,
    tags=("fee", "rounding", "half-up", "half-even"),
    domain="finance",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 2 — value_remap
# ═════════════════════════════════════════════════════════════════════════════

CURRENCY_DISPLAY = Probe(
    id="currency_display",
    family="value_remap",
    category="formatting",
    summary='fin_format_amount() with style="standard" now places the currency symbol after the number instead of before it.',
    fn="fin_format_amount",
    signature='fin_format_amount(amount, currency, style="standard")',
    impl='''
def fin_format_amount(amount, currency, style="standard"):
    """Format *amount* as a display string for the given *currency* code.

    style="standard" (default) — symbol placed AFTER the number, e.g. "100.00 EUR" -> "100.00 €"
    style="prefix"              — symbol placed BEFORE the number, e.g. "€100.00"
    """
    symbols = {"EUR": "€", "USD": "$", "GBP": "£", "JPY": "¥"}
    symbol = symbols.get(currency, currency + " ")
    formatted = f"{amount:,.2f}"
    if style == "prefix":
        return f"{symbol}{formatted}"
    return f"{formatted} {symbol}"
''',
    api_doc='`fin_format_amount(amount, currency, style="standard")` — '
            'format `amount` for display in `currency`. `style` is '
            '`"standard"` (default, symbol placed *after* the number, e.g. '
            '`"100.00 €"`) or `"prefix"` (symbol placed *before* the '
            'number, e.g. `"€100.00"`).',
    changelog='**`fin_format_amount` — the meaning of `style="standard"` '
              'changed.** Prior releases used `style="standard"` (the '
              'default) to mean the currency symbol is placed *before* the '
              'number, matching the older single-currency retail statement '
              'format. The current release repurposes `style="standard"` to '
              'place the symbol *after* the number, matching the ISO 4217 '
              'trailing-symbol convention now used across multi-currency '
              'statements. Pass `style="prefix"` to restore the old '
              'symbol-before-number layout.',
    param="style",
    gold_kwargs={"style": "prefix"},
    familiar_kwargs={"style": "standard"},
    familiar_behaviour='style="standard" now places the symbol after the number, but a prior-locked caller still expects it before',
    installed_behaviour='style="standard" places the symbol after the number; pass "prefix" to place it before',
    task_clause="Format this amount for display on legacy client statements, "
                "where the currency symbol has always been printed "
                "**before** the number (e.g. `€100.00`), regardless of "
                "the platform's newer default layout. Write the resulting "
                "string under `formatted`.",
    output_key="formatted",
    input_payload={"amount": 100.00, "currency": "EUR"},
    gold_output="€100.00",
    familiar_output="100.00 €",
    tags=("currency", "formatting", "symbol-position"),
    domain="finance",
)


# ═════════════════════════════════════════════════════════════════════════════
#  FAMILY 3 — result_shape
# ═════════════════════════════════════════════════════════════════════════════

PORTFOLIO_RETURN_METHOD = Probe(
    id="portfolio_return_method",
    family="result_shape",
    category="reporting",
    summary="fin_portfolio_return() now returns a breakdown dict of total/annualized/time-weighted return instead of a flat float.",
    fn="fin_portfolio_return",
    signature="fin_portfolio_return(beginning_value, ending_value, years, period_returns)",
    impl='''
def fin_portfolio_return(beginning_value, ending_value, years, period_returns):
    """Compute portfolio return statistics over the reporting period.

    beginning_value / ending_value — portfolio value at the start/end of the
                                      period
    years                          — length of the period in years
    period_returns                 — list of sub-period returns (decimal
                                      fractions) used to compute the
                                      time-weighted return by geometric
                                      linking

    Returns {"total_return": float, "annualized": float,
             "time_weighted": float}, each a decimal fraction rounded to 4
    places.
    """
    total_return = round((ending_value - beginning_value) / beginning_value, 4)
    annualized = round((1 + total_return) ** (1 / years) - 1, 4)

    linked = 1.0
    for r in period_returns:
        linked *= (1 + r)
    time_weighted = round(linked - 1, 4)

    return {
        "total_return": total_return,
        "annualized": annualized,
        "time_weighted": time_weighted,
    }
''',
    api_doc='`fin_portfolio_return(beginning_value, ending_value, years, '
            'period_returns)` — compute portfolio return statistics. '
            'Returns `{"total_return": float, "annualized": float, '
            '"time_weighted": float}`, each a decimal fraction rounded to 4 '
            'places. `total_return` is the simple return over the whole '
            'period; `annualized` compounds it down to a 1-year rate; '
            '`time_weighted` links the entries in `period_returns` '
            'geometrically, eliminating the effect of cash-flow timing.',
    changelog='**`fin_portfolio_return` — return shape changed.** Prior '
              'releases returned a single flat float — the simple total '
              'return over the period. The current release returns a '
              'breakdown dict `{"total_return", "annualized", '
              '"time_weighted"}` so callers no longer need to derive the '
              'annualized and time-weighted figures themselves. There is no '
              'flag to restore the old flat-float shape — callers that need '
              'just the total return must read it from the dict.',
    param=None,
    gold_kwargs={},
    familiar_kwargs={},
    familiar_behaviour="returns a single flat float (the simple total return)",
    installed_behaviour="returns a breakdown dict with total_return/annualized/time_weighted",
    task_clause="Using the library's `fin_portfolio_return` helper, compute "
                "this portfolio's return statistics for the reporting period "
                "exactly as the installed function returns them — do not "
                "flatten or reshape the result to a single number. Write the "
                "resulting value under `returns`.",
    output_key="returns",
    input_payload={
        "beginning_value": 100000.0,
        "ending_value": 121000.0,
        "years": 2.0,
        "period_returns": [0.10, 0.10],
    },
    gold_output={"total_return": 0.21, "annualized": 0.1, "time_weighted": 0.21},
    familiar_output=0.21,
    tags=("portfolio", "return", "reporting", "time-weighted"),
    domain="finance",
)


FINANCE_PROBES = (
    SETTLEMENT_CYCLE,
    FEE_ROUNDING,
    CURRENCY_DISPLAY,
    PORTFOLIO_RETURN_METHOD,
)

CATEGORIES = ("settlement", "calculation", "formatting", "reporting")

LEXICON = {
    "settlement": {
        "settlement": 2.5, "settle": 2.0, "t+1": 2.0, "t+2": 2.0,
        "trade": 1.5, "cycle": 1.5, "business day": 1.5, "clearing": 1.5,
    },
    "calculation": {
        "fee": 2.5, "rounding": 2.5, "half-up": 2.0, "half up": 2.0,
        "half-even": 2.0, "banker": 1.5, "basis point": 1.0, "rate": 1.0,
    },
    "formatting": {
        "currency": 2.5, "symbol": 2.5, "format": 2.0, "prefix": 1.5,
        "suffix": 1.5, "display": 1.0, "statement": 1.0,
    },
    "reporting": {
        "portfolio": 2.5, "return": 2.5, "annualized": 2.0,
        "time-weighted": 2.0, "time weighted": 2.0, "twr": 1.5,
        "performance": 1.0,
    },
}

CARTRIDGE = CartridgeSpec(
    domain="finance",
    display_name="Financial Operations API",
    description="Prior override on a synthetic financial operations library — "
                "trade settlement cycles, fee rounding conventions, currency "
                "display formatting, and portfolio return reporting idioms "
                "that LLMs have strong memorized priors about.",
    probes=FINANCE_PROBES,
    categories=CATEGORIES,
    lexicon=LEXICON,
    max_level=1,
)

register(CARTRIDGE)
