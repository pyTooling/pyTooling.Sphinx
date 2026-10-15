# ==================================================================================================================== #
#             _____           _ _               ____        _     _                                                    #
#  _ __  _   |_   _|__   ___ | (_)_ __   __ _  / ___| _ __ | |__ (_)_ __ __  __                                        #
# | '_ \| | | || |/ _ \ / _ \| | | '_ \ / _` | \___ \| '_ \| '_ \| | '_ \\ \/ /                                        #
# | |_) | |_| || | (_) | (_) | | | | | | (_| |_ ___) | |_) | | | | | | | |>  <                                         #
# | .__/ \__, ||_|\___/ \___/|_|_|_| |_|\__, (_)____/| .__/|_| |_|_|_| |_/_/\_\                                        #
# |_|    |___/                          |___/        |_|                                                               #
# ==================================================================================================================== #
# Authors:                                                                                                             #
#   Patrick Lehmann                                                                                                    #
#                                                                                                                      #
# License:                                                                                                             #
# ==================================================================================================================== #
# Copyright 2026-2026 Patrick Lehmann - Bötzingen, Germany                                                             #
#                                                                                                                      #
# Licensed under the Apache License, Version 2.0 (the "License");                                                      #
# you may not use this file except in compliance with the License.                                                     #
# You may obtain a copy of the License at                                                                              #
#                                                                                                                      #
#   http://www.apache.org/licenses/LICENSE-2.0                                                                         #
#                                                                                                                      #
# Unless required by applicable law or agreed to in writing, software                                                  #
# distributed under the License is distributed on an "AS IS" BASIS,                                                    #
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.                                             #
# See the License for the specific language governing permissions and                                                  #
# limitations under the License.                                                                                       #
#                                                                                                                      #
# SPDX-License-Identifier: Apache-2.0                                                                                  #
# ==================================================================================================================== #
#
"""
A Python module's source, condensed to what its documentation coverage is about: the headers and doc-strings of its
classes and functions, its variables and fields; a body is elided to ``...``.

:class:`CondensedSource` holds the condensed lines, each marked by its documentation state; its classmethod
:meth:`~CondensedSource.Parse` condenses a module's source. The pages of :mod:`pyTooling.Sphinx.DocCoveragePages` show
it as a listing.

.. seealso::

   :ref:`DIR/DocCoverage/Pages`
      |rarr| The pages and the condensed listing, with examples.
"""
from __future__                                    import annotations

from ast                                           import AST, AnnAssign, Assign, AsyncFunctionDef, ClassDef, Constant
from ast                                           import Expr, FunctionDef, Name, TypeAlias, iter_child_nodes
from ast                                           import parse, stmt
from typing                                        import TYPE_CHECKING, Any, Generator, Iterable
from typing                                        import Optional as Nullable, Self, Union

from sphinx.util.logging                           import getLogger

from pyTooling.Common                              import getFullyQualifiedName
from pyTooling.Decorators                          import export, readonly
from pyTooling.MetaClasses                         import ExtendedType

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where a package is analyzed.
	from pyEDAA.Reports.DocumentationCoverage        import CoverageState
	from pyEDAA.Reports.DocumentationCoverage.Python import AggregatedCoverage


__all__ = ["DEFINITIONS", "ASSIGNMENTS", "Definition"]

#: The statements docstr_coverage expects a doc-string of: a class and a function or method.
DEFINITIONS = (ClassDef, FunctionDef, AsyncFunctionDef)

#: The statements declaring a variable or a class' field.
ASSIGNMENTS = (Assign, AnnAssign, TypeAlias)

type Definition = Union[ClassDef, FunctionDef, AsyncFunctionDef]
"""A statement docstr_coverage expects a doc-string of."""


@export
def documentationState(coverageState: CoverageState) -> str:
	"""
	Return the state a listing marks a line with, for a coverage state of pyEDAA.Reports' documentation coverage model.

	The state is chosen as the model counts it: excluded before ignored, then documented - covered - or undocumented.
	``Unknown`` isn't counted, so it gets no state.

	:param coverageState: The model's coverage state.
	:returns:             The listing's state: ``documented``, ``undocumented``, ``ignored``, ``excluded`` or ``""``.
	"""
	from pyEDAA.Reports.DocumentationCoverage import CoverageState

	if coverageState == CoverageState.Unknown:
		return ""
	elif CoverageState.Excluded in coverageState:
		return "excluded"
	elif CoverageState.Ignored in coverageState:
		return "ignored"
	elif CoverageState.Covered in coverageState:
		return "documented"

	return "undocumented"


class _Condenser(metaclass=ExtendedType, slots=True):
	"""
	The builder condensing a module's source into the lines of a :class:`CondensedSource`.

	It walks the module's syntax tree once, taking each line as written or eliding it; the source, the model and the
	position reached are its state while walking. It is private to :meth:`CondensedSource.Parse`, which hands the
	resulting lines to the constructor.
	"""

	_source: list[str]                             #: The source's lines, without line ends.
	_unit:   AggregatedCoverage                    #: The module's coverage, holding states of variables and fields.
	_states: dict[int, str]                        #: Documentation state of a class or function, by its keyword's line.
	_lines:  list[tuple[Nullable[int], str, str]]  #: The condensed lines taken so far.
	_last:   int                                   #: Number of the last source line taken or elided.

	def __init__(self, source: str, unit: AggregatedCoverage) -> None:
		"""
		Prepare condensing a module's source.

		:param source: The module's source.
		:param unit:   The module's or package's coverage.
		"""
		self._source = source.split("\n")
		self._unit =   unit
		self._states = {}
		self._lines =  []
		self._last =   0

	def Condense(self, path: str, expected: list[tuple[str, str]]) -> list[tuple[Nullable[int], str, str]]:
		"""
		Condense the module's source.

		An analysis not matching the source - other classes and functions than docstr_coverage found - is logged as a
		warning, and the classes and functions aren't marked.

		:param path:     The module's path, as the warning names it.
		:param expected: docstr_coverage's expected doc-strings of the module, in the order it found them, as
		                 ``(identifier, state)`` pairs.
		:returns:        The condensed lines (see :attr:`CondensedSource.Lines`).
		"""
		tree = parse("\n".join(self._source))

		moduleState = ""
		if len(expected) > 0 and expected[0][0] == "module docstring":
			moduleState = expected[0][1]
			expected = expected[1:]

		definitions = list(self._Definitions(tree))
		if len(definitions) == len(expected) and all(
			definition.name == identifier.rpartition(".")[2]
			for definition, (identifier, _) in zip(definitions, expected)
		):
			self._states = {definition.lineno: state for definition, (_, state) in zip(definitions, expected)}
		else:
			getLogger(__name__).warning(
				f"The documentation coverage analysis of '{path}' doesn't match the source, so its classes and functions "
				f"aren't marked."
			)

		body = tree.body
		if len(body) > 0 and self._IsDocString(body[0]):
			self._Emit(body[0].lineno, body[0].end_lineno, moduleState)
			body = body[1:]

		self._Block(body, True, ())

		return self._lines

	def _Emit(self, first: int, last: int, state: str) -> None:
		"""
		Take source lines as written, except those already taken.

		:param first: Number of the first line.
		:param last:  Number of the last line.
		:param state: The lines' documentation state.
		"""
		for number in range(max(first, self._last + 1), last + 1):
			self._lines.append((number, state, ""))

		self._last = max(self._last, last)

	def _Gap(self, last: int) -> None:
		"""
		Skip the lines between the last line taken and a line: a blank line is taken, unless the line before is blank or
		nothing was taken yet; a comment is left out.

		:param last: Number of the last line to skip.
		"""
		for number in range(self._last + 1, last + 1):
			if self._source[number - 1].strip() != "" or len(self._lines) == 0:
				continue

			previousNumber = self._lines[-1][0]
			if previousNumber is None or self._source[previousNumber - 1].strip() != "":
				self._lines.append((number, "", ""))

		self._last = max(self._last, last)

	def _Block(self, statements: list[stmt], variables: bool, scope: Nullable[tuple[str, ...]]) -> None:
		"""
		Take a block's statements: classes and functions condensed, variables or fields as written, other statements
		elided - consecutive ones to a single ``...``.

		:param statements: The block's statements, without a doc-string.
		:param variables:  Whether assignments are variables or fields - in a module or class - and taken.
		:param scope:      The class names leading to the block - ``()`` for the module -, by which the model is asked
		                   for a variable's or field's state; ``None`` if it can't be asked, e.g. in a function.
		"""
		elided = False
		attributeState: Nullable[str] = None
		for statement in statements:
			# a statement behind a ';' on a line already taken
			if statement.end_lineno <= self._last:
				continue

			docStringState = attributeState
			attributeState = None
			if isinstance(statement, DEFINITIONS):
				self._Definition(statement, scope)
			elif variables and isinstance(statement, ASSIGNMENTS):
				attributeState = self._VariableState(statement, scope)
				first = statement.lineno
				while first - 1 > self._last and self._source[first - 2].lstrip().startswith("#:"):
					first -= 1

				self._Gap(first - 1)
				self._Emit(first, statement.end_lineno, attributeState)
			elif docStringState is not None and self._IsDocString(statement):
				self._Gap(statement.lineno - 1)
				self._Emit(statement.lineno, statement.end_lineno, docStringState)
			elif any(True for _ in self._OutermostDefinitions(statement)):
				self._Compound(statement, scope)
			else:
				if not elided:
					self._Gap(statement.lineno - 1)
					line = self._source[statement.lineno - 1]
					self._lines.append((None, "", line[:len(line) - len(line.lstrip())]))

				self._last = statement.end_lineno
				elided = True
				continue

			elided = False

	def _Definition(self, definition: Definition, scope: Nullable[tuple[str, ...]]) -> None:
		"""
		Take a class or function: its decorators, header and doc-string, then its body's statements.

		:param definition: The class or function.
		:param scope:      The class names leading to the definition, or ``None`` (see :meth:`_Block`).
		"""
		state = self._states.get(definition.lineno, "")
		first = self._FirstLine(definition)
		self._Gap(first - 1)

		body = definition.body
		if self._source[body[0].lineno - 1].encode("utf-8")[:body[0].col_offset].strip() != b"":
			# the body starts in the header's line: 'def f(): pass'
			self._Emit(first, definition.end_lineno, state)
			return

		# the header ends before the body's first statement, without the blank lines and comments in between
		headerEnd = self._FirstLine(body[0]) - 1
		while headerEnd > definition.lineno and (
			(line := self._source[headerEnd - 1].strip()) == "" or line.startswith("#")
		):
			headerEnd -= 1

		self._Emit(first, headerEnd, state)
		if self._IsDocString(body[0]):
			self._Gap(body[0].lineno - 1)
			self._Emit(body[0].lineno, body[0].end_lineno, state)
			body = body[1:]

		if isinstance(definition, ClassDef):
			self._Block(body, True, None if scope is None else (*scope, definition.name))
		else:
			self._Block(body, False, None)

	def _Compound(self, statement: stmt, scope: Nullable[tuple[str, ...]]) -> None:
		"""
		Take a statement holding classes or functions as written, its classes and functions condensed.

		Such a statement is e.g. an ``if`` choosing between two definitions.

		:param statement: The statement.
		:param scope:     The class names leading to the statement, or ``None`` (see :meth:`_Block`).
		"""
		self._Gap(statement.lineno - 1)
		for definition in self._OutermostDefinitions(statement):
			self._Emit(statement.lineno, self._FirstLine(definition) - 1, "")
			self._Definition(definition, scope)

		self._Emit(statement.lineno, statement.end_lineno, "")

	def _VariableState(self, statement: stmt, scope: Nullable[tuple[str, ...]]) -> str:
		"""
		Return a variable's or field's state, if the model holds one: a module's ``Variables``, a class' ``Fields``.

		:param statement: The assignment, which assigns one name.
		:param scope:     The class names leading to the assignment, or ``None`` (see :meth:`_Block`).
		:returns:         The state, or ``""`` if the model holds none.
		"""
		if isinstance(statement, Assign):
			target = statement.targets[0] if len(statement.targets) == 1 else None
		elif isinstance(statement, AnnAssign):
			target = statement.target
		else:
			target = statement.name

		if scope is None or not isinstance(target, Name):
			return ""

		unit: Any = self._unit
		for className in scope:
			if (unit := unit.Classes.get(className, None)) is None:
				return ""

		states = unit.Fields if len(scope) > 0 else unit.Variables
		if (coverageState := states.get(target.id, None)) is None:
			return ""

		return documentationState(coverageState)

	@staticmethod
	def _FirstLine(statement: stmt) -> int:
		"""
		Return a statement's first line: its first decorator's, if it has decorators.

		:param statement: The statement.
		:returns:         The line number.
		"""
		return min((decorator.lineno for decorator in getattr(statement, "decorator_list", ())), default=statement.lineno)

	@staticmethod
	def _IsDocString(statement: stmt) -> bool:
		"""
		Check if a statement is a string literal: a doc-string at the start of a body, or behind a variable or field.

		:param statement: The statement.
		:returns:         ``True``, if the statement is a string literal.
		"""
		return (
			isinstance(statement, Expr) and isinstance(statement.value, Constant) and isinstance(statement.value.value, str)
		)

	@classmethod
	def _Definitions(cls, node: AST) -> Generator[Definition, None, None]:
		"""
		Yield the classes and functions below a node, in the order docstr_coverage visits them: depth-first, each before
		the ones inside it.

		:param node: The node.
		:returns:    A generator of the classes and functions.
		"""
		for child in iter_child_nodes(node):
			if isinstance(child, DEFINITIONS):
				yield child

			yield from cls._Definitions(child)

	@classmethod
	def _OutermostDefinitions(cls, node: AST) -> Generator[Definition, None, None]:
		"""
		Yield the classes and functions below a node, which aren't inside another class or function below it.

		:param node: The node.
		:returns:    A generator of the classes and functions, in source order.
		"""
		for child in iter_child_nodes(node):
			if isinstance(child, DEFINITIONS):
				yield child
			else:
				yield from cls._OutermostDefinitions(child)


@export
class CondensedSource(metaclass=ExtendedType, slots=True):
	"""
	A Python module's source, condensed to what its documentation coverage is about.

	A line is taken as written, at its line number, or replaced by a ``...`` line without a number:

	* The module's doc-string is taken; its imports and other statements are elided.
	* A class or function is taken with its decorators, its header up to the ``:`` - a signature spanning lines too -
	  and its doc-string. Its body follows: a class' members, a function's nested functions and classes; anything else
	  is elided to one ``...`` at the body's indentation. A definition written in one line is taken as written.
	* A variable of the module and a field of a class is taken as written: with a ``#:`` comment on its line or in the
	  lines above it, and a doc-string literal following it.
	* A statement holding a class or function - e.g. an ``if`` or a ``try`` - is taken as written, its classes and
	  functions condensed.
	* Comments between statements are left out; consecutive blank lines become one.

	A class' or function's lines are marked by its state in the analysis, which docstr_coverage expected a doc-string
	for. A variable's or field's lines are marked only if the model holds a state for it; else they - like every other
	line - have no state.
	"""

	_lines: list[tuple[Nullable[int], str, str]]  #: The condensed lines; see :attr:`Lines`.

	def __init__(self, lines: Iterable[tuple[Nullable[int], str, str]]) -> None:
		"""
		Initialize a condensed source from its lines.

		:param lines:       The condensed lines (see :attr:`Lines`).
		:raises ValueError: If parameter ``lines`` is ``None``.
		:raises TypeError:  If parameter ``lines`` isn't iterable.
		:raises TypeError:  If a line isn't a tuple.
		"""
		if lines is None:
			raise ValueError("Parameter 'lines' is None.")
		elif not isinstance(lines, Iterable):
			ex = TypeError("Parameter 'lines' is not iterable.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lines)}'.")
			raise ex

		self._lines = []
		for line in lines:
			if not isinstance(line, tuple):
				ex = TypeError("Parameter 'lines' contains an element, which is not of type 'tuple'.")
				ex.add_note(f"Got type '{getFullyQualifiedName(line)}'.")
				raise ex

			self._lines.append(line)

	@classmethod
	def Parse(cls, source: str, path: str, expected: list[tuple[str, str]], unit: AggregatedCoverage) -> Self:
		"""
		Condense a module's source.

		An analysis not matching the source - other classes and functions than docstr_coverage found - is logged as a
		warning, and the classes and functions aren't marked.

		:param source:   The module's source.
		:param path:     The module's path, as the warning names it.
		:param expected: docstr_coverage's expected doc-strings of the module, in the order it found them, as
		                 ``(identifier, state)`` pairs.
		:param unit:     The module's or package's coverage, which may hold states of its variables and its classes'
		                 fields.
		:returns:        The condensed source.
		"""
		return cls(_Condenser(source, unit).Condense(path, expected))

	@readonly
	def Lines(self) -> list[tuple[Nullable[int], str, str]]:
		"""
		Read-only property to access the condensed lines (:attr:`_lines`).

		:returns: A tuple per line: the line number and its state, and ``""``; or for an elided body, ``None``, ``""``
		          and the body's indentation.
		"""
		return self._lines
