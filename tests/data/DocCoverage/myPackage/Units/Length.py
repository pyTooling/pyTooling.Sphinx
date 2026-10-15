"""Lengths and their conversion."""
import sys

if sys.version_info >= (3, 12):
	def toMeter(value: float, unit: str) -> float:
		"""Convert a length to meters."""
		return value * FACTORS[unit]
else:
	def toMeter(value: float, unit: str) -> float:
		return value

FACTORS = {
	"m":  1.0,
	"km": 1000.0,
}  #: Factor per unit.
