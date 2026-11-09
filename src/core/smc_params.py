"""Windows of the SMC detector, in one place (MOD-7, CODE-7).

The values are the ones the SMC pattern discovery system v0.1 shipped as its
command line defaults, so results stay comparable with that reference. They are
a starting definition, not a tuned optimum; see `docs/smc.md`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SmcParams:
    """Pivot windows, order block lookback and sweep tolerance of one run."""

    left_bars: int = 3
    right_bars: int = 3
    ob_lookback: int = 12
    sweep_tolerance: float = 0.0

    def as_dict(self) -> dict:
        """Plain dictionary, so the API can report the parameters it used."""
        return asdict(self)


DEFAULT_PARAMS = SmcParams()
