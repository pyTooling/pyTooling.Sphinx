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
Unit tests for the schema graphs: :class:`~pyTooling.Sphinx.SchemaGraph.DotGraph` and the ``xmlschema-graph``
directive's rendering in :class:`~pyTooling.Sphinx.XMLSchemaGraph.XMLSchemaGraph`.
"""
from pathlib                         import Path
from tempfile                        import TemporaryDirectory
from textwrap                        import dedent
from typing                          import Optional as Nullable

from pyTooling                       import Resources
from pyTooling.Common                import getResourceFile
from pyTooling.Sphinx.SchemaGraph    import DotGraph
from pyTooling.Sphinx.XMLSchemaGraph import XMLSchemaGraph
from pyTooling.Testing               import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("Schema graph")
class Graphs(Testcase):
	"""The graph every schema graph is drawn as."""

	@testcase("Shared look")
	def SharedAttributes(self) -> None:
		"""
		An empty schema graph carries the attributes every schema graph shares.

		Renders an empty DotGraph and compares it with the expected DOT: left to right, the node separation, record nodes
		and the fonts of nodes and edges.
		"""
		self.assertEqual(dedent("""\
			digraph "schema" {
			  rankdir="LR";
			  nodesep=0.4;
			  node [shape="record", fontname="sans-serif", fontsize=10];
			  edge [fontname="sans-serif", fontsize=9];
			}
			"""), str(DotGraph()))

	@testcase("Graph identifier")
	def Identifier(self) -> None:
		"""
		A schema graph is written under the identifier it is given.

		Renders a DotGraph named 'other' and checks the DOT text starts with that identifier.
		"""
		self.assertTrue(str(DotGraph("other")).startswith('digraph "other" {'))

	@testcase("Identifier checks")
	def Identifier_Parameters(self) -> None:
		"""
		A missing or non-string identifier is rejected.

		Creates a DotGraph with None and with an integer, and checks the ValueError and TypeError and their messages.
		"""
		for identifier, exceptionType, message in (
			(None, ValueError, "Parameter 'identifier' is None."),
			(1,    TypeError,  "Parameter 'identifier' is not of type 'str'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					DotGraph(identifier)
				self.assertEqual(message, str(context.exception))

	@testcase("Record node")
	def Record(self) -> None:
		"""
		A record is its title in guillemets, followed by one compartment per sequence of rows.

		Adds a record with a title holding a '|', a compartment of two rows, an empty compartment and an attribute, and
		checks the node is returned, the title is escaped, the rows are left-aligned and the empty compartment is a space.
		"""
		graph = DotGraph()
		node = graph.AddRecord("t", "t|1", (("a", "b"), ()), {"style": "filled"})

		self.assertIs(node, graph.GetNode("t"))
		self.assertIn('  "t" [style="filled", label="{«t\\|1»|a\\lb\\l| }"];\n', str(graph))

	@testcase("Record title checks")
	def Record_Parameters(self) -> None:
		"""
		A missing or non-string record title is rejected.

		Adds a record with None and with an integer as title, and checks the ValueError and TypeError and their messages.
		"""
		graph = DotGraph()
		for title, exceptionType, message in (
			(None, ValueError, "Parameter 'title' is None."),
			(1,    TypeError,  "Parameter 'title' is not of type 'str'."),
		):
			with self.subTest(message=message):
				with self.assertRaises(exceptionType) as context:
					graph.AddRecord("t", title)
				self.assertEqual(message, str(context.exception))

	@testcase("Node on demand")
	def GetOrAddNode(self) -> None:
		"""
		An edge's target without a record of its own becomes a plain node, once.

		Asks for an existing record and gets it back; asks twice for 'xsd:anyType' and gets the same new node, which is
		written as a plain node.
		"""
		graph = DotGraph()
		record = graph.AddRecord("t", "t")

		self.assertIs(record, graph.GetOrAddNode("t"))
		plain = graph.GetOrAddNode("xsd:anyType")
		self.assertIs(plain, graph.GetOrAddNode("xsd:anyType"))
		self.assertIn('  "xsd:anyType";\n', str(graph))


@testsuite("Shipped XML schema")
class XMLSchemaGraphs(Testcase):
	"""The XML schema pyTooling ships, drawn as the 'xmlschema-graph' directive draws it."""

	_dot: str  #: The rendered schema, shared by the testcases.

	@classmethod
	def setUpClass(cls) -> None:
		"""Render the schema once for all testcases of this class."""
		cls._dot = XMLSchemaGraph._RenderGraph(getResourceFile(Resources, "TestReport-v0.1.xsd"))

	@testcase("Complex types as records")
	def ComplexType(self) -> None:
		"""
		Every complex type of the schema is a record.

		Checks the rendered test-report schema has a record titled 'testreport', 'testsuite' and 'testcase'.
		"""
		for typeIdentifier in ("testreport", "testsuite", "testcase"):
			with self.subTest(typeIdentifier=typeIdentifier):
				self.assertIn(f'"{typeIdentifier}" [label="{{«{typeIdentifier}»|', self._dot)

	@testcase("Attribute with its type")
	def Attribute(self) -> None:
		"""
		An attribute is written with its type, a builtin type with the 'xsd:' prefix.

		Checks the rendered schema contains the row 'duration : xsd:float'.
		"""
		self.assertIn("duration : xsd:float", self._dot)

	@testcase("Containment as an edge")
	def Containment(self) -> None:
		"""
		A complex-typed child element is an edge carrying the element's name and cardinality.

		Checks the rendered schema has the edge from 'testreport' to 'testsuite' labelled 'Testsuite [0..*]'.
		"""
		self.assertIn('"testreport" -> "testsuite" [label="Testsuite [0..*]"];', self._dot)

	@testcase("Recursive containment")
	def Containment_Recursive(self) -> None:
		"""
		A type containing itself is an edge to itself.

		Checks the rendered schema has the edge from 'testsuite' to 'testsuite'.
		"""
		self.assertIn('"testsuite" -> "testsuite" [label="Testsuite [0..*]"];', self._dot)

	@testcase("Root element")
	def RootElement(self) -> None:
		"""
		A root element is a double circle pointing to its type.

		Checks the rendered schema has the node '<TestReport>' with its attributes and an edge labelled 'root' to
		'testreport'.
		"""
		root = '"<TestReport>" [shape="doublecircle", style="filled", fillcolor="#e8e8ff", label="TestReport"];'
		self.assertIn(root, self._dot)
		self.assertIn('"<TestReport>" -> "testreport" [label="root"];', self._dot)

	@testcase("Enumeration node")
	def Enumeration(self) -> None:
		"""
		An enumeration is a filled record of its values, used by a dashed edge.

		Checks the rendered schema has the record 'status' with its values, and the dashed, non-constraining edge from
		'testcase' to it.
		"""
		self.assertIn('"status" [style="filled", fillcolor="#f0f0f0", label="{«status»|passed\\lfailed\\l', self._dot)
		self.assertIn('"testcase" -> "status" [style="dashed", arrowhead="open", constraint=false];', self._dot)

	@testcase("Simple type without node")
	def SimpleType(self) -> None:
		"""
		A simple type that is no enumeration is only named, not drawn.

		Checks 'preservingstring' appears in a compartment row and nowhere as a node.
		"""
		self.assertIn("Description : preservingstring", self._dot)
		self.assertNotIn('"preservingstring"', self._dot)

	@testcase("Stable output")
	def Stable(self) -> None:
		"""
		The same schema is always rendered to the same text.

		Renders the schema a second time and compares it with the first rendering.
		"""
		self.assertEqual(self._dot, XMLSchemaGraph._RenderGraph(getResourceFile(Resources, "TestReport-v0.1.xsd")))


@testsuite("XML schema details")
class XMLSchemaGraphDetails(Testcase):
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

			return XMLSchemaGraph._RenderGraph(schema)

	@testcase("Enumeration order")
	def Enumeration_Order(self) -> None:
		"""
		Enumerations are written in the order of their names.

		Renders a schema declaring 'charlie', 'alpha' and 'bravo', and checks their records appear alphabetically.
		"""
		dot = self._Render()
		positions = [dot.index(f'"{name}" [style="filled"') for name in ("alpha", "bravo", "charlie")]

		self.assertListEqual(sorted(positions), positions)

	@testcase("Unbounded occurrence")
	def Unbounded(self) -> None:
		"""
		An element with 'maxOccurs="unbounded"' has a '*' as upper limit.

		Renders a schema with such an element and checks its row ends with '[1..*]'.
		"""
		self.assertIn("Two : bravo [1..*]", self._Render())

	@testcase("Types without a record")
	def TypeWithoutRecord(self) -> None:
		"""
		A complex type without a record - a builtin or an anonymous one - is a plain node.

		Renders a schema with an untyped element and an inline complex type, and checks the plain nodes 'xsd:anyType' and
		'(anonymous)' and the edges to them.
		"""
		dot = self._Render()

		self.assertIn('  "xsd:anyType";\n', dot)
		self.assertIn('  "(anonymous)";\n', dot)
		self.assertIn('"root" -> "xsd:anyType" [label="Any [1..1]"];', dot)
		self.assertIn('"root" -> "(anonymous)" [label="Inline [1..1]"];', dot)


@testsuite("Type names")
class TypeNames(Testcase):
	"""What a type is called in a record, which is not always what it is called in the schema."""

	class _Type:
		"""A stand-in for an 'xmlschema' type, which only has to answer for its name."""

		def __init__(self, name: Nullable[str]) -> None:
			self.name = name

	@testcase("Builtin type")
	def Builtin(self) -> None:
		"""
		A builtin type is named with the 'xsd:' prefix instead of its namespace.

		Names a stand-in type in the XML Schema namespace and checks it becomes 'xsd:string'.
		"""
		builtin = self._Type("{http://www.w3.org/2001/XMLSchema}string")

		self.assertEqual("xsd:string", XMLSchemaGraph._TypeName(builtin))

	@testcase("Named type")
	def Named(self) -> None:
		"""
		A type declared by the schema keeps its name.

		Names a stand-in type 'status' and checks the name is unchanged.
		"""
		self.assertEqual("status", XMLSchemaGraph._TypeName(self._Type("status")))

	@testcase("Anonymous type")
	def Anonymous(self) -> None:
		"""
		A type without a name is named '(anonymous)'.

		Names a stand-in type whose name is None.
		"""
		self.assertEqual("(anonymous)", XMLSchemaGraph._TypeName(self._Type(None)))


@testsuite("Cardinalities")
class Cardinalities(Testcase):
	"""How often an element may occur, as a record row states it."""

	class _Element:
		"""A stand-in for an 'xmlschema' element, which only has to answer for its occurrence."""

		def __init__(self, lower: int, upper: Nullable[int]) -> None:
			self.occurs = (lower, upper)

	@testcase("Bounded occurrence")
	def Bounded(self) -> None:
		"""
		A bounded occurrence is written as its two numbers.

		Formats a stand-in element occurring 0 to 1 times and checks '0..1'.
		"""
		self.assertEqual("0..1", XMLSchemaGraph._Cardinality(self._Element(0, 1)))

	@testcase("Unbounded occurrence")
	def Unbounded(self) -> None:
		"""
		An unbounded occurrence has a '*' as upper limit.

		Formats a stand-in element whose upper limit is None and checks '1..*'.
		"""
		self.assertEqual("1..*", XMLSchemaGraph._Cardinality(self._Element(1, None)))
