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
A list of abbreviations, and roles referring to an abbreviation in the form they name.

The directive ``abbreviations`` holds the list - a definition list of abbreviations, each with its long form and,
optionally, a description like a glossary's:

.. code-block:: ReST

   .. abbreviations::

      FSM
         :long:        finite-state machine
         :long-plural: finite-state machines

         A machine in exactly one of a finite number of states at a time.

      HDL
         :long: hardware description language

A role refers to an abbreviation from any document, in the form it names, as LaTeX' ``acro`` package does:
``:acs:`FSM``` writes *FSM*, ``:acl:`FSM``` *finite-state machine*, ``:acf:`FSM``` *finite-state machine (FSM)*,
and ``:acsp:``, ``:aclp:`` and ``:acfp:`` the plurals. ``:ac:`` and ``:acp:`` are ``:acs:`` and ``:acsp:``: a reader
doesn't read a page linearly, so there is no first use spelling an abbreviation out. A text written as the role's
title, ``:acs:`FSM's <FSM>```, replaces the form. Every reference links to the abbreviation in the list; in HTML, a
short form shows its long form in a box on hover.

.. seealso::

   :ref:`DIR/Abbreviations`
      |rarr| The directive and the roles, with rendered examples.
   :mod:`pyTooling.Sphinx`
      |rarr| The extension this belongs to, and what else it brings.
"""
from typing                import Any, Iterable, Iterator, NamedTuple, Optional as Nullable

from docutils              import nodes
from sphinx.addnodes       import pending_xref
from sphinx.builders       import Builder
from sphinx.domains        import Domain, ObjType
from sphinx.environment    import BuildEnvironment
from sphinx.roles          import XRefRole
from sphinx.util.logging   import getLogger
from sphinx.util.nodes     import make_id, make_refnode

from pyTooling.Decorators  import export, readonly
from pyTooling.Sphinx      import BaseDirective, SphinxExtensionError, strip
from pyTooling.Sphinx.Node import Abbreviation


__all__ = ["DOMAIN_NAME", "ROLES", "FIELDS"]

#: Name of the domain collecting the abbreviations of all documents.
DOMAIN_NAME = "abbreviation"

#: The roles, mapping a role's name to the form it writes and whether it is the plural.
ROLES = {
	"ac":   ("short", False),
	"acs":  ("short", False),
	"acl":  ("long",  False),
	"acf":  ("full",  False),
	"acp":  ("short", True),
	"acsp": ("short", True),
	"aclp": ("long",  True),
	"acfp": ("full",  True),
}

#: The fields an abbreviation states its forms in, and whether one is required.
FIELDS = {
	"long":        True,
	"plural":      False,
	"long-plural": False,
}


@export
class AbbreviationEntry(NamedTuple):
	"""An abbreviation of the list: where it is written, and its forms as plain text."""

	docName:    str  #: Name of the document holding the list.
	anchor:     str  #: Identifier of the abbreviation's entry in that document.
	short:      str  #: The abbreviation itself, e.g. ``FSM``.
	long:       str  #: The long form, e.g. ``finite-state machine``.
	plural:     str  #: The plural of the short form, e.g. ``FSMs``.
	longPlural: str  #: The plural of the long form, e.g. ``finite-state machines``.

	def Form(self, form: str, plural: bool) -> str:
		"""
		Return one form of the abbreviation as plain text.

		:param form:   ``short``, ``long`` or ``full``, the long form followed by the short one in parentheses.
		:param plural: Whether the plural is asked for.
		:returns:      The form's text.
		"""
		short = self.plural if plural else self.short
		long = self.longPlural if plural else self.long
		if form == "short":
			return short
		elif form == "long":
			return long

		return f"{long} ({short})"


@export
class AbbreviationRole(XRefRole):
	"""
	A role referring to an abbreviation in the domain :data:`DOMAIN_NAME`, whatever name it is registered by.

	Sphinx registers a role outside a domain without one, so the reference would be resolved by nobody; this role puts
	its own domain on the reference, and uses its name as the reference's type.
	"""

	def run(self) -> tuple[list[nodes.Node], list[nodes.system_message]]:
		"""
		Create the reference, or only the text if the role is written with ``!``.

		:returns: The nodes and messages a role returns.
		"""
		self.refdomain = DOMAIN_NAME
		self.reftype = self.name.rpartition(":")[2]
		self.classes = ["xref", DOMAIN_NAME, f"{DOMAIN_NAME}-{self.reftype}"]

		if self.disabled:
			return self.create_non_xref_node()

		return self.create_xref_node()


@export
class AbbreviationDomain(Domain):
	"""
	The domain collecting the abbreviations of all documents, and resolving the references to them.

	An abbreviation is registered once in the whole documentation; it gets no entry in the general index.
	"""

	name =  DOMAIN_NAME     #: Name of the domain.
	label = "Abbreviation"  #: Name of the domain shown to a reader.

	object_types = {"abbreviation": ObjType("abbreviation", *ROLES)}  #: The one kind of object, referred to by every role.
	initial_data: dict[str, Any] = {"abbreviations": {}}              #: The data of an empty documentation: no abbreviation.
	roles = {
		roleName: AbbreviationRole(innernodeclass=nodes.inline, warn_dangling=True) for roleName in ROLES
	}  #: The roles, also as ``:abbreviation:<role>:``.
	dangling_warnings = {
		roleName: "abbreviation '%(target)s' isn't in a list of abbreviations" for roleName in ROLES
	}  #: The warning for a reference to an unknown abbreviation, per role.

	@readonly
	def Abbreviations(self) -> dict[str, AbbreviationEntry]:
		"""
		Read-only property to return the abbreviations of all documents, from the domain's data.

		:returns: The abbreviations, keyed by their short form.
		"""
		return self.data["abbreviations"]

	def Register(self, entry: AbbreviationEntry, location: nodes.Node) -> None:
		"""
		Register an abbreviation, or warn that it is registered in a list already.

		:param entry:    The abbreviation.
		:param location: Node the warning points to.
		"""
		if (registered := self.Abbreviations.get(entry.short)) is not None:
			getLogger(__name__).warning(
				f"abbreviation '{entry.short}' is in the list of document '{registered.docName}' already",
				location=location
			)
			return

		self.Abbreviations[entry.short] = entry

	def clear_doc(self, docname: str) -> None:
		"""
		Forget the abbreviations of a document, before it is read again.

		:param docname: Name of the document.
		"""
		for short in [short for short, entry in self.Abbreviations.items() if entry.docName == docname]:
			del self.Abbreviations[short]

	def merge_domaindata(self, docnames: Iterable[str], otherdata: dict[str, Any]) -> None:
		"""
		Take over the abbreviations a parallel reader collected for its documents.

		:param docnames:  Names of the documents the other reader read.
		:param otherdata: The other reader's domain data.
		"""
		documents = set(docnames)
		for short, entry in otherdata["abbreviations"].items():
			if entry.docName in documents:
				self.Abbreviations[short] = entry

	def resolve_xref(
		self,
		env: BuildEnvironment,
		fromdocname: str,
		builder: Builder,
		typ: str,
		target: str,
		node: pending_xref,
		contnode: nodes.Element
	) -> Nullable[nodes.reference]:
		"""
		Resolve a reference to an abbreviation into a link to its entry, showing the form the role names.

		A short form is an :class:`~pyTooling.Sphinx.Node.Abbreviation`, so HTML explains it on hover; a full form holds
		one. A title written in the role replaces the form's text; the box still explains the abbreviation.

		:param env:         The build environment.
		:param fromdocname: Name of the document holding the reference.
		:param builder:     The builder writing the documents.
		:param typ:         The role's name.
		:param target:      The abbreviation referred to.
		:param node:        The reference.
		:param contnode:    The reference's text.
		:returns:           The link, or ``None`` if the abbreviation isn't in a list.
		"""
		if (entry := self.Abbreviations.get(target)) is None:
			return None

		form, plural = ROLES[typ]
		short, long = entry.Form("short", plural), entry.Form("long", plural)
		if node.get("refexplicit", False):
			text = contnode.astext()
			content: list[nodes.Node] = [
				Abbreviation(text, text, short=short, long=long) if form == "short" else nodes.Text(text)
			]
		elif form == "short":
			content = [Abbreviation(short, short, short=short, long=long)]
		elif form == "long":
			content = [nodes.Text(long)]
		else:
			content = [nodes.Text(f"{long} ("), Abbreviation(short, short, short=short, long=long), nodes.Text(")")]

		inline = nodes.inline("", "", *content, classes=contnode["classes"])
		return make_refnode(builder, fromdocname, entry.docName, entry.anchor, inline)

	def resolve_any_xref(
		self,
		env: BuildEnvironment,
		fromdocname: str,
		builder: Builder,
		target: str,
		node: pending_xref,
		contnode: nodes.Element
	) -> list[tuple[str, nodes.reference]]:
		"""
		Resolve a reference of role ``:any:`` to an abbreviation, which shows its short form.

		:param env:         The build environment.
		:param fromdocname: Name of the document holding the reference.
		:param builder:     The builder writing the documents.
		:param target:      The text referred to.
		:param node:        The reference.
		:param contnode:    The reference's text.
		:returns:           The role and link, if the text is an abbreviation; otherwise nothing.
		"""
		if (reference := self.resolve_xref(env, fromdocname, builder, "acs", target, node, contnode)) is None:
			return []

		return [(f"{DOMAIN_NAME}:acs", reference)]

	def get_objects(self) -> Iterator[tuple[str, str, str, str, str, int]]:
		"""
		Name the abbreviations, for the search and for other documentations referring to them.

		:returns: A tuple per abbreviation: name, display name, type, document, anchor and search priority.
		"""
		for short, entry in self.Abbreviations.items():
			yield short, short, "abbreviation", entry.docName, entry.anchor, 1


@export
class Abbreviations(BaseDirective):
	"""
	The ``abbreviations`` directive: a list of abbreviations, which the roles in :data:`ROLES` refer to.

	The content is a definition list. A term is an abbreviation; its definition starts with a field list stating the
	forms - :data:`FIELDS` - and may continue with a description. ``:class:`` puts additional CSS classes on the list.
	"""

	directiveName: str = "abbreviations"  #: Name the directive is invoked by.

	has_content =               True   #: A boolean; ``True`` if content is allowed.
	required_arguments =        0      #: Number of required directive arguments.
	optional_arguments =        0      #: Number of optional arguments after the required ones.
	final_argument_whitespace = False  #: A boolean; ``True`` if the last argument may contain spaces.
	# docutils declares 'option_spec' on 'Directive' and 'BaseDirective' assigns it, so mypy calls every
	# spelling of this override a conflict with one of them
	#: Mapping of option names to validator functions.
	option_spec: dict[str, Any] = {  # type: ignore[misc]
		"class": strip,
	}

	def run(self) -> list[nodes.Node]:
		"""
		Render the list, and register its abbreviations in the domain.

		:returns: The list as a definition list, or the message of whatever the content got wrong.
		"""
		container = nodes.container()
		self.state.nested_parse(self.content, self.content_offset, container)

		try:
			definitionList = self._DefinitionList(container)
			entries = [self._ReadItem(item) for item in definitionList.children]
		except SphinxExtensionError as ex:
			return [self.state.document.reporter.error(f"{self.directiveName}: {ex}", line=self.lineno)]

		domain: AbbreviationDomain = self.env.get_domain(DOMAIN_NAME)  # type: ignore[assignment]
		for item, (short, forms, description) in zip(definitionList.children, entries):
			anchor = make_id(self.env, self.state.document, "abbreviation", short)
			term = item[0]
			term["ids"].append(anchor)
			self.state.document.note_explicit_target(term)

			long, plural, longPlural = forms["long"], forms.get("plural"), forms.get("long-plural")
			entry = AbbreviationEntry(
				docName=self.env.docname,
				anchor=anchor,
				short=short,
				long=long.astext(),
				plural=f"{short}s" if plural is None else plural.astext(),
				longPlural=f"{long.astext()}s" if longPlural is None else longPlural.astext()
			)
			domain.Register(entry, item)

			definition = nodes.definition()
			definition += nodes.paragraph("", "", *long.children, classes=["abbreviation-long"])
			definition += description
			item.replace(item[1], definition)

		definitionList["classes"] += ["pytooling-abbreviations"] + self.options.get("class", "").split()

		return [definitionList]

	@staticmethod
	def _DefinitionList(container: nodes.Element) -> nodes.definition_list:
		"""
		Return the definition list the content has to consist of.

		:param container:             The parsed content.
		:returns:                     The definition list.
		:raises SphinxExtensionError: If the content is anything but one definition list.
		"""
		if len(container.children) != 1 or not isinstance(container[0], nodes.definition_list):
			raise SphinxExtensionError("The directive's content isn't a definition list of abbreviations.")

		return container[0]

	@staticmethod
	def _ReadItem(item: nodes.definition_list_item) -> tuple[str, dict[str, nodes.paragraph], list[nodes.Node]]:
		"""
		Read an abbreviation: its term, the fields stating its forms, and the description following them.

		:param item:                  An item of the definition list.
		:returns:                     The abbreviation, its forms keyed by field name, and the description.
		:raises SphinxExtensionError: If the term has a classifier.
		:raises SphinxExtensionError: If the definition doesn't start with a field list.
		:raises SphinxExtensionError: If a field is unknown, given twice, or not a single paragraph.
		:raises SphinxExtensionError: If a required field is missing.
		"""
		term, definition = item[0], item[-1]
		short = term.astext().strip()
		if len(item.children) != 2:
			raise SphinxExtensionError(f"Abbreviation '{short}' has a classifier, which isn't supported.")

		if len(definition.children) == 0 or not isinstance(definition[0], nodes.field_list):
			raise SphinxExtensionError(f"Abbreviation '{short}' doesn't start with a field list, e.g. ':long:'.")

		forms: dict[str, nodes.paragraph] = {}
		for field in definition[0].children:
			name = field[0].astext().strip()
			body = field[1]
			if name not in FIELDS:
				ex = SphinxExtensionError(f"Abbreviation '{short}' has an unknown field ':{name}:'.")
				ex.add_note(f"Known fields: {', '.join(f':{field}:' for field in FIELDS)}")
				raise ex
			elif name in forms:
				raise SphinxExtensionError(f"Abbreviation '{short}' states field ':{name}:' twice.")
			elif len(body.children) != 1 or not isinstance(body[0], nodes.paragraph):
				raise SphinxExtensionError(f"Field ':{name}:' of abbreviation '{short}' isn't a single paragraph.")

			forms[name] = body[0]

		for name in (name for name, required in FIELDS.items() if required and name not in forms):
			raise SphinxExtensionError(f"Abbreviation '{short}' has no field ':{name}:'.")

		return short, forms, list(definition.children[1:])
