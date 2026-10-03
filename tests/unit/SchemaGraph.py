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
Unit tests for the schema graphs: :class:`~pyTooling.Sphinx.SchemaGraph.DotGraph` and the ``xsd-graph`` directive's
rendering in :class:`~pyTooling.Sphinx.XSDSchemaGraph.XSDSchemaGraph`.
"""
from pathlib                         import Path
from tempfile                        import TemporaryDirectory
from textwrap                        import dedent
from typing                          import Optional as Nullable

from pyTooling                       import Resources
from pyTooling.Common                import getResourceFile
from pyTooling.Sphinx.SchemaGraph    import DotGraph
from pyTooling.Sphinx.XSDSchemaGraph import XSDSchemaGraph
from pyTooling.Testing               import Testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


class Graphs(Testcase):
	"""The graph every schema graph is drawn as."""

	def test_SharedAttributes(self) -> None:
		"""Where the graph flows, how a record is shaped and the fonts belong to every schema graph alike."""
		self.assertEqual(dedent("""\
			digraph "schema" {
			  rankdir="LR";
			  nodesep=0.4;
			  node [shape="record", fontname="sans-serif", fontsize=10];
			  edge [fontname="sans-serif", fontsize=9];
			}
			"""), str(DotGraph()))

	def test_Identifier(self) -> None:
		self.assertTrue(str(DotGraph("other")).startswith('digraph "other" {'))

	def test_Identifier_Parameters(self) -> None:
		for identifier, exceptionType, message in (
			(None, ValueError, "Parameter 'identifier' is None."),
			(1,    TypeError,  "Parameter 'identifier' is not of type 'str'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					DotGraph(identifier)
				self.assertEqual(message, str(context.exception))

	def test_Record(self) -> None:
		"""The title is written in guillemets, and every compartment follows it below - an empty one as a space."""
		graph = DotGraph()
		node = graph.AddRecord("t", "t|1", (("a", "b"), ()), {"style": "filled"})

		self.assertIs(node, graph.GetNode("t"))
		self.assertIn('  "t" [style="filled", label="{«t\\|1»|a\\lb\\l| }"];\n', str(graph))

	def test_Record_Parameters(self) -> None:
		graph = DotGraph()
		for title, exceptionType, message in (
			(None, ValueError, "Parameter 'title' is None."),
			(1,    TypeError,  "Parameter 'title' is not of type 'str'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					graph.AddRecord("t", title)
				self.assertEqual(message, str(context.exception))

	def test_GetOrAddNode(self) -> None:
		"""An edge's target without a record of its own becomes a plain node, once."""
		graph = DotGraph()
		record = graph.AddRecord("t", "t")

		self.assertIs(record, graph.GetOrAddNode("t"))
		plain = graph.GetOrAddNode("xsd:anyType")
		self.assertIs(plain, graph.GetOrAddNode("xsd:anyType"))
		self.assertIn('  "xsd:anyType";\n', str(graph))


class XMLSchemaGraphs(Testcase):
	"""The XML schema pyTooling ships, drawn as the 'xsd-graph' directive draws it."""

	_dot: str  #: The rendered schema, shared by the testcases.

	@classmethod
	def setUpClass(cls) -> None:
		"""Render the schema once for all testcases of this class."""
		cls._dot = XSDSchemaGraph._RenderGraph(getResourceFile(Resources, "TestReport-v0.1.xsd"))

	def test_ComplexType(self) -> None:
		"""A complex type is a record; its attributes and simple-typed children are its compartments."""
		for typeIdentifier in ("testreport", "testsuite", "testcase"):
			with self.subTest(typeIdentifier=typeIdentifier):
				self.assertIn(f'"{typeIdentifier}" [label="{{«{typeIdentifier}»|', self._dot)

	def test_Attribute(self) -> None:
		"""A builtin type keeps the 'xsd:' prefix its namespace stands for."""
		self.assertIn("duration : xsd:float", self._dot)

	def test_Containment(self) -> None:
		"""A complex-typed child is an edge carrying the cardinality."""
		self.assertIn('"testreport" -> "testsuite" [label="Testsuite [0..*]"];', self._dot)

	def test_Containment_Recursive(self) -> None:
		self.assertIn('"testsuite" -> "testsuite" [label="Testsuite [0..*]"];', self._dot)

	def test_RootElement(self) -> None:
		root = '"<TestReport>" [shape="doublecircle", style="filled", fillcolor="#e8e8ff", label="TestReport"];'
		self.assertIn(root, self._dot)
		self.assertIn('"<TestReport>" -> "testreport" [label="root"];', self._dot)

	def test_Enumeration(self) -> None:
		"""A simple type earns a node only when it has values a type name cannot say."""
		self.assertIn('"status" [style="filled", fillcolor="#f0f0f0", label="{«status»|passed\\lfailed\\l', self._dot)
		self.assertIn('"testcase" -> "status" [style="dashed", arrowhead="open", constraint=false];', self._dot)

	def test_SimpleType(self) -> None:
		"""'preservingstring' is named in the compartments and drawn nowhere - it has nothing to show."""
		self.assertIn("Description : preservingstring", self._dot)
		self.assertNotIn('"preservingstring"', self._dot)

	def test_Stable(self) -> None:
		"""A rebuilt page is only comparable to the one before it when the drawing doesn't reshuffle."""
		self.assertEqual(self._dot, XSDSchemaGraph._RenderGraph(getResourceFile(Resources, "TestReport-v0.1.xsd")))


class XSDSchemaGraphDetails(Testcase):
	"""The parts of an XML schema graph that the shipped schema doesn't exercise."""

	_SCHEMA = dedent("""\
		<?xml version="1.0" encoding="UTF-8"?>
		<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
			<xs:simpleType name="charlie">
				<xs:restriction base="xs:string"><xs:enumeration value="c"/></xs:restriction>
			</xs:simpleType>
			<xs:simpleType name="alpha">
				<xs:restriction base="xs:string"><xs:enumeration value="a"/></xs:restriction>
			</xs:simpleType>
			<xs:simpleType name="bravo">
				<xs:restriction base="xs:string"><xs:enumeration value="b"/></xs:restriction>
			</xs:simpleType>
			<xs:complexType name="root">
				<xs:sequence>
					<xs:element name="One" type="alpha"/>
					<xs:element name="Two" type="bravo" maxOccurs="unbounded"/>
					<xs:element name="Three" type="charlie"/>
					<xs:element name="Any"/>
					<xs:element name="Inline">
						<xs:complexType><xs:attribute name="x" type="xs:string"/></xs:complexType>
					</xs:element>
				</xs:sequence>
			</xs:complexType>
			<xs:element name="Root" type="root"/>
		</xs:schema>
		""")

	def _Render(self) -> str:
		"""
		Write the schema above into a temporary directory and render it.

		:returns: The graph in the DOT language.
		"""
		with TemporaryDirectory() as directory:
			schema = Path(directory) / "Details.xsd"
			schema.write_text(self._SCHEMA, encoding="utf-8")

			return XSDSchemaGraph._RenderGraph(schema)

	def test_Enumeration_Order(self) -> None:
		"""They are collected in a set, whose iteration order varies between interpreter runs unless it is sorted."""
		dot = self._Render()
		positions = [dot.index(f'"{name}" [style="filled"') for name in ("alpha", "bravo", "charlie")]

		self.assertListEqual(sorted(positions), positions)

	def test_Unbounded(self) -> None:
		self.assertIn("Two : bravo [1..*]", self._Render())

	def test_TypeWithoutRecord(self) -> None:
		"""A complex type without a record - a builtin or an anonymous one - is drawn as a plain node."""
		dot = self._Render()

		self.assertIn('  "xsd:anyType";\n', dot)
		self.assertIn('  "(anonymous)";\n', dot)
		self.assertIn('"root" -> "xsd:anyType" [label="Any [1..1]"];', dot)
		self.assertIn('"root" -> "(anonymous)" [label="Inline [1..1]"];', dot)


class TypeNames(Testcase):
	"""What a type is called in a record, which is not always what it is called in the schema."""

	class _Type:
		"""A stand-in for an 'xmlschema' type, which only has to answer for its name."""

		def __init__(self, name: Nullable[str]) -> None:
			self.name = name

	def test_Builtin(self) -> None:
		"""The namespace a builtin type is spelled with is 40 characters that say nothing in a diagram."""
		builtin = self._Type("{http://www.w3.org/2001/XMLSchema}string")

		self.assertEqual("xsd:string", XSDSchemaGraph._TypeName(builtin))

	def test_Named(self) -> None:
		self.assertEqual("status", XSDSchemaGraph._TypeName(self._Type("status")))

	def test_Anonymous(self) -> None:
		"""An inline type has no name, and an empty label would be read as a missing one."""
		self.assertEqual("(anonymous)", XSDSchemaGraph._TypeName(self._Type(None)))


class Cardinalities(Testcase):
	"""How often an element may occur, as a record row states it."""

	class _Element:
		"""A stand-in for an 'xmlschema' element, which only has to answer for its occurrence."""

		def __init__(self, lower: int, upper: Nullable[int]) -> None:
			self.occurs = (lower, upper)

	def test_Bounded(self) -> None:
		self.assertEqual("0..1", XSDSchemaGraph._Cardinality(self._Element(0, 1)))

	def test_Unbounded(self) -> None:
		"""'None' is what 'unbounded' arrives as, and it has no number to print."""
		self.assertEqual("1..*", XSDSchemaGraph._Cardinality(self._Element(1, None)))
