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
:meth:`~CondensedSource.Parse` condenses a module's source. The pages of :mod:`pyTooling.Sphinx.DocCoverage` show
it as a listing.

.. seealso::

   :ref:`DIR/DocCoverage/Pages`
      |rarr| The pages and the condensed listing, with examples.
"""
from __future__                                    import annotations

from ast                                           import AST, AnnAssign, Assign, AsyncFunctionDef, ClassDef, \
                                                          Constant, Expr, FunctionDef, If, Try, TypeAlias, \
                                                          iter_child_nodes, parse, stmt
from typing                                        import TYPE_CHECKING, Generator, Iterable, Optional as Nullable, \
                                                          Self, Union

from sphinx.util.logging                           import getLogger

from pyTooling.Common                              import getFullyQualifiedName
from pyTooling.Decorators                          import export, readonly
from pyTooling.MetaClasses                         import ExtendedType

if TYPE_CHECKING:  # pragma: no cover
	# pyEDAA.Reports is an optional dependency (extra 'reports'), imported where a package is analyzed.
	from pyEDAA.Reports.DocumentationCoverage        import CoverageState, Item


__all__ = ["DEFINITIONS", "ASSIGNMENTS", "Definition"]

#: The statements expected to have a doc-string: a class and a function or method.
DEFINITIONS = (ClassDef, FunctionDef, AsyncFunctionDef)

#: The statements declaring a variable or a class' field.
ASSIGNMENTS = (Assign, AnnAssign, TypeAlias)

type Definition = Union[ClassDef, FunctionDef, AsyncFunctionDef]
"""A statement expected to have a doc-string."""


@export
def documentationState(coverageState: CoverageState) -> str:
	"""
	Return the state a listing marks a line with, for a coverage state of pyEDAA.Reports' documentation coverage model.

	The state is chosen as the model counts it: excluded before ignored, then documented - covered - or undocumented.
	An item with nothing to document (``Empty``) isn't counted, so it gets no state.

	:param coverageState: The model's coverage state.
	:returns:             The listing's state: ``documented``, ``undocumented``, ``ignored``, ``excluded`` or ``""``.
	"""
	from pyEDAA.Reports.DocumentationCoverage import CoverageState

	if CoverageState.Empty in coverageState:
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

	It walks the module's syntax tree once, taking each line as written or eliding it; the source, the items' states and
	the position reached are its state while walking. It is private to :meth:`CondensedSource.Parse`, which hands the
	resulting lines to the constructor.
	"""

	_source: list[str]                             #: The source's lines, without line ends.
	_module: Item                                  #: The module's item, whose file lists the items declared in it.
	_states: dict[int, str]                        #: Documentation state of an item, by its first line.
	_lines:  list[tuple[Nullable[int], str, str]]  #: The condensed lines taken so far.
	_last:   int                                   #: Number of the last source line taken or elided.

	def __init__(self, source: str, module: Item) -> None:
		"""
		Prepare condensing a module's source.

		:param source: The module's source.
		:param module: The module's or package's item.
		"""
		self._source = source.split("\n")
		self._module = module
		self._states = {}
		self._lines =  []
		self._last =   0

	def Condense(self, path: str) -> list[tuple[Nullable[int], str, str]]:
		"""
		Condense the module's source.

		An analysis not matching the source - a class or function without an item of its name at its first line - is
		logged as a warning, and no class, function, field or variable is marked.

		:param path: The module's path, as the warning names it.
		:returns:    The condensed lines (see :attr:`CondensedSource.Lines`).
		"""
		tree = parse("\n".join(self._source), filename=path)

		items: dict[int, Item] = {}
		if (file := self._module.File) is not None:
			for item in file.Items:
				if item.StartLine is not None:
					items.setdefault(item.StartLine, item)

		if all(
			(declared := items.get(self._FirstLine(definition), None)) is not None and declared.Name == definition.name
			for definition in self._Definitions(tree)
		):
			self._states = {line: documentationState(item.Status) for line, item in items.items()}
		else:
			getLogger(__name__).warning(
				f"The documentation coverage analysis of '{path}' doesn't match the source, so its items aren't marked."
			)

		body = tree.body
		if len(body) > 0 and self._IsDocString(body[0]):
			self._Emit(body[0].lineno, body[0].end_lineno, documentationState(self._module.Status))
			body = body[1:]

		self._Block(body, True)

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

	def _Block(self, statements: list[stmt], variables: bool) -> None:
		"""
		Take a block's statements: classes and functions condensed, variables or fields as written, a statement holding
		them with its clauses' headers, other statements elided - consecutive ones to a single ``...``.

		:param statements: The block's statements, without a doc-string.
		:param variables:  Whether assignments are variables or fields - in a module or class - and taken.
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
				self._Definition(statement)
			elif variables and isinstance(statement, ASSIGNMENTS):
				attributeState = self._states.get(statement.lineno, "")
				first = statement.lineno
				while first - 1 > self._last and self._source[first - 2].lstrip().startswith("#:"):
					first -= 1

				self._Gap(first - 1)
				self._Emit(first, statement.end_lineno, attributeState)
			elif docStringState is not None and self._IsDocString(statement):
				self._Gap(statement.lineno - 1)
				self._Emit(statement.lineno, statement.end_lineno, docStringState)
			elif any(True for _ in self._OutermostDefinitions(statement)) or (
				variables and self._HoldsAssignments(statement)
			):
				self._Compound(statement, variables)
			else:
				if not elided:
					self._Gap(statement.lineno - 1)
					line = self._source[statement.lineno - 1]
					self._lines.append((None, "", line[:len(line) - len(line.lstrip())]))

				self._last = statement.end_lineno
				elided = True
				continue

			elided = False

	def _Definition(self, definition: Definition) -> None:
		"""
		Take a class or function: its decorators, header and doc-string, then its body's statements.

		:param definition: The class or function.
		"""
		first = self._FirstLine(definition)
		state = self._states.get(first, "")
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

		self._Block(body, isinstance(definition, ClassDef))

	def _Compound(self, statement: stmt, variables: bool) -> None:
		"""
		Take a statement holding classes, functions, variables or fields: the headers of its clauses as written, each
		clause's block like a body.

		Such a statement is e.g. an ``if`` choosing between two definitions, or a ``try`` assigning a variable.

		:param statement: The statement.
		:param variables: Whether assignments are variables or fields - in a module or class - and taken.
		"""
		self._Gap(statement.lineno - 1)
		for block in (
			getattr(statement, "body", []),
			*(clause.body for clause in (*getattr(statement, "handlers", []), *getattr(statement, "cases", []))),
			getattr(statement, "orelse", []),
			getattr(statement, "finalbody", [])
		):
			if len(block) == 0:
				continue

			# the clause's header - 'if ...:', 'else:', 'except ...:' -, without the blank lines and comments around it
			for number in range(self._last + 1, self._FirstLine(block[0])):
				if (line := self._source[number - 1].strip()) == "" or line.startswith("#"):
					self._Gap(number)
				else:
					self._Emit(number, number, "")

			self._Block(block, variables)

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
		Yield the classes and functions below a node, depth-first: each before the ones inside it.

		:param node: The node.
		:returns:    A generator of the classes and functions.
		"""
		for child in iter_child_nodes(node):
			if isinstance(child, DEFINITIONS):
				yield child

			yield from cls._Definitions(child)

	@classmethod
	def _HoldsAssignments(cls, statement: stmt) -> bool:
		"""
		Check if a statement is an ``if`` or ``try`` assigning a variable or field, which the analysis reads: in its
		body or ``else`` block, or in such a statement nested in them.

		:param statement: The statement.
		:returns:         ``True``, if the statement holds an assignment.
		"""
		if not isinstance(statement, (If, Try)):
			return False

		return any(
			isinstance(child, ASSIGNMENTS) or cls._HoldsAssignments(child) for child in (*statement.body, *statement.orelse)
		)

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
	* A statement holding a class or function - e.g. an ``if`` or a ``try`` -, and an ``if`` or ``try`` assigning a
	  variable or field, is taken with the headers of its clauses as written; each clause's block is taken like a body.
	* Comments between statements are left out; consecutive blank lines become one.

	A class', function's, field's or variable's lines are marked by the documentation state of its item in
	pyEDAA.Reports' model: the item declared in the module's file, which starts at the definition's first line or at the
	assignment. The module's doc-string is marked by the module's state. Every other line has no state, e.g. a repeated
	assignment of a variable, as its item starts at the first one.
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
	def Parse(cls, source: str, path: str, module: Item) -> Self:
		"""
		Condense a module's source.

		An analysis not matching the source - a class or function without an item of its name at its first line - is
		logged as a warning, and no class, function, field or variable is marked.

		:param source: The module's source.
		:param path:   The module's path, as the warning names it.
		:param module: The module's or package's item of pyEDAA.Reports' model; its file lists the items declared in it.
		:returns:      The condensed source.
		"""
		return cls(_Condenser(source, module).Condense(path))

	@readonly
	def Lines(self) -> list[tuple[Nullable[int], str, str]]:
		"""
		Read-only property to access the condensed lines (:attr:`_lines`).

		:returns: A tuple per line: the line number and its state, and ``""``; or for an elided body, ``None``, ``""``
		          and the body's indentation.
		"""
		return self._lines
