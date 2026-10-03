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
The language-neutral half of drawing a schema as a Graphviz graph in a Sphinx document.

:class:`DotGraph` is a :class:`pyTooling.Graph.GraphViz.Graph` with the look every schema graph shares, and
:class:`SchemaGraph` is the directive's base-class: its argument becomes a path, the file becomes a build dependency,
and the DOT is handed to :mod:`sphinx.ext.graphviz`. A schema language adds a module reading its schemas into a
:class:`DotGraph`, and a subclass naming the directive.

.. seealso::

   :mod:`pyTooling.Sphinx.XMLSchemaGraph`
      |rarr| The ``xmlschema-graph`` directive, drawing an XML schema.
   :mod:`pyTooling.Graph.GraphViz`
      |rarr| The DOT model :class:`DotGraph` is built on.
   :mod:`pyTooling.Sphinx`
      |rarr| The extension this belongs to, and what else it brings.
"""
from __future__               import annotations

from pathlib                  import Path
from typing                   import Any, Mapping, Optional as Nullable, Sequence

from docutils                 import nodes
from sphinx.ext.graphviz      import figure_wrapper, graphviz

from pyTooling.Common         import getFullyQualifiedName
from pyTooling.Decorators     import export
from pyTooling.Graph.GraphViz import AttributeValue, Graph, Node, RecordField, RecordLabel
from pyTooling.Sphinx         import BaseDirective, strip


@export
class DotGraph(Graph):
	"""
	A Graphviz graph of a schema, with the look every schema graph shares.

	It flows from left to right, its nodes are records, and its nodes and edges use the same fonts, so two diagrams in
	one document look alike. A renderer adds records, nodes and edges as to any :class:`~pyTooling.Graph.GraphViz.Graph`.
	"""

	def __init__(self, identifier: str = "schema") -> None:
		"""
		Initialize an empty graph carrying the shared attributes.

		:param identifier:  Optional, the graph's identifier. Default: ``schema``.
		:raises ValueError: If parameter 'identifier' is None.
		:raises TypeError:  If parameter 'identifier' is not a string.
		"""
		super().__init__(identifier, attributes={"rankdir": "LR", "nodesep": 0.4})

		if identifier is None:
			raise ValueError("Parameter 'identifier' is None.")

		self._nodeDefaults["shape"]    = "record"
		self._nodeDefaults["fontname"] = "sans-serif"
		self._nodeDefaults["fontsize"] = 10
		self._edgeDefaults["fontname"] = "sans-serif"
		self._edgeDefaults["fontsize"] = 9

	def AddRecord(
		self,
		identifier: str,
		title: str,
		compartments: Sequence[Sequence[str]] = (),
		attributes: Nullable[Mapping[str, AttributeValue]] = None
	) -> Node:
		"""
		Add a record node: a titled box divided into compartments, one below the other.

		:param identifier:   Identifier of the node, which an edge names it by.
		:param title:        The record's title, written in guillemets.
		:param compartments: Optional, the rows of each compartment below the title.
		:param attributes:   Optional, further attributes of the node, by name.
		:returns:            The added node.
		:raises ValueError:  If parameter 'title' is None.
		:raises TypeError:   If parameter 'title' is not a string.
		"""
		if title is None:
			raise ValueError("Parameter 'title' is None.")
		elif not isinstance(title, str):
			ex = TypeError("Parameter 'title' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(title)}'.")
			raise ex

		fields: list[RecordField] = [f"«{title}»"]
		fields.extend(compartments)

		return self.AddNode(Node(identifier, RecordLabel(fields, flipped=True), attributes))

	def GetOrAddNode(self, identifier: str) -> Node:
		"""
		Return the node with the given identifier, adding a plain node first if there is none.

		An edge can point to a type the renderer has no record for, like a builtin or an anonymous type. Graphviz would
		create such a node implicitly; here it is added explicitly and drawn with the node defaults.

		:param identifier:  Identifier of the node.
		:returns:           The node with that identifier.
		:raises ValueError: If parameter 'identifier' is None.
		:raises TypeError:  If parameter 'identifier' is not a string.
		"""
		if self.HasNode(identifier):
			return self.GetNode(identifier)

		return self.AddNode(Node(identifier))


@export
class SchemaGraph(BaseDirective):
	"""
	Base-class of the directives drawing the schema file given as their argument.

	It holds everything that isn't the schema's language: the path is resolved against the document using the
	directive and registered as a dependency - so editing the schema rebuilds the page holding its diagram - and
	whatever :meth:`_RenderGraph` returns is handed to :mod:`sphinx.ext.graphviz`, wrapped in a figure when a caption
	was given. A derived class sets :attr:`~pyTooling.Sphinx.BaseDirective.directiveName` and
	overrides :meth:`_RenderGraph`.
	"""

	has_content =               False  #: A boolean; ``True`` if content is allowed.
	required_arguments =        1      #: Number of required directive arguments: the schema's path.
	optional_arguments =        0      #: Number of optional arguments after the required ones.
	final_argument_whitespace = False  #: A boolean; ``True`` if the last argument may contain spaces.
	# docutils declares 'option_spec' on 'Directive' and 'BaseDirective' assigns it, so mypy calls every
	# spelling of this override a conflict with one of them
	#: Mapping of option names to validator functions.
	option_spec: dict[str, Any] = {  # type: ignore[misc]
		"caption": strip,
	}

	def run(self) -> list[nodes.Node]:
		"""
		Read the schema and hand its graph to :mod:`sphinx.ext.graphviz` for rendering.

		:returns: A ``graphviz`` node, wrapped in a figure when a caption was given, or the message of whatever went
		          wrong while reading the schema.
		"""
		relativePath, absolutePath = self.env.relfn2path(self.arguments[0])
		self.env.note_dependency(relativePath)
		schemaFile = Path(absolutePath)

		try:
			code = self._RenderGraph(schemaFile)
		except Exception as ex:
			return self._internalError(
				nodes.container(),
				__name__,
				f"{self.directiveName}: Couldn't draw schema '{schemaFile}'.",
				ex
			)

		node = graphviz()
		node["code"] = code
		node["options"] = {"docname": self.env.docname}
		node["alt"] = f"Diagram of {schemaFile.name}"

		if (caption := self.options.get("caption", None)) is not None:
			return [figure_wrapper(self, node, caption)]

		return [node]

	@classmethod
	def _RenderGraph(cls, schemaFile: Path) -> str:
		"""
		Render the schema as a graph.

		:param schemaFile:           Path of the schema to render.
		:returns:                    The graph in the DOT language.
		:raises NotImplementedError: If a derived class doesn't override it.
		"""
		raise NotImplementedError(f"{cls.directiveName}: '_RenderGraph' is not implemented.")
