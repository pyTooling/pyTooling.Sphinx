"""Shapes with an area."""
from math   import pi
from typing import ClassVar

#: The number of shapes created.
counter = 0

UNIT = "m"
"""The unit of a shape's dimensions."""


class Circle:
	"""A circle, given by its radius."""

	kind: ClassVar[str] = "circle"  #: The shape's kind.

	radius: float  #: The circle's radius.

	def __init__(self, radius: float) -> None:
		"""
		Initialize a circle.

		:param radius: The circle's radius.
		"""
		if radius < 0:
			raise ValueError("Negative radius.")
		self.radius = radius

	def Area(self) -> float:
		return pi * self.radius ** 2

	def Scale(
		self,
		factor: float,
		*,
		inPlace: bool = False  # keeps the circle
	) -> "Circle":
		"""Return the circle scaled by a factor."""
		def scaled(value: float) -> float:
			return value * factor

		return Circle(scaled(self.radius))


class Square:
	def __init__(self, side: float) -> None: self.side = side

	@property
	def Area(self) -> float:
		"""The square's area."""
		return self.side ** 2


def unitArea() -> float: return 1.0
