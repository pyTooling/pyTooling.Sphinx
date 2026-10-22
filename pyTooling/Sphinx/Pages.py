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
Pages generated from a model: a document per object of the model - a testsuite, a testcase, a source file, a VHDL
entity, ... - built without a source file, in the navigation below the directive showing the model's summary.

:class:`GeneratedPages` holds what doesn't depend on the model or the domain: the document names, the registration and
generation of the documents, and the tables of contents. :class:`ReportPages` adds the objects of domain ``report``:
an entry per page, which a role of :data:`~pyTooling.Sphinx.REPORT_ROLES` refers to. Another domain - e.g. a VHDL
domain - derives from :class:`GeneratedPages`, names the type of its objects as the type argument
(``GeneratedPages[Library | DesignUnit]``), names its domain in :attr:`GeneratedPages._DOMAIN`, and registers its
objects in :meth:`GeneratedPages._Registered`; a page may also be written as reStructuredText, see
:meth:`GeneratedPages._Fill`.

A report declared with the key ``pages`` gets a document per object, named below that key's document name by the
names of the objects from the report's root down, e.g. ``<pages>/<testsuite>/<testcase>``. A name's characters other
than letters, digits, ``_``, ``-`` and ``.`` - e.g. the brackets of a parametrized pytest testcase - are replaced by
``_``, and a name colliding with a sibling's (also when differing only in case) gets the suffix ``-2``, ``-3``, ...

The pages are built as docutils node trees and handed to Sphinx as if they were read from a file: their names are
registered when the builder is initialized and again before the documents are read -
:meth:`sphinx.project.Project.discover` forgets them in between -, and the file Sphinx sees as their source is the
report - or a file a derived class names per page, e.g. a module's source -, so a changed report rebuilds them.
A page carries the metadata ``:orphan:``. A page with children lists them in a hidden table of contents, as the
directive showing the report's summary lists the top-level pages, so the pages are in the navigation below that
directive's document; a page's own sections aren't listed there. Every object with a page is an object of domain
``report``, referred to by a role of :data:`~pyTooling.Sphinx.REPORT_ROLES`.

.. seealso::

   :mod:`pyTooling.Sphinx.UnittestPages`
      |rarr| The pages of a unit test report: a page per testsuite and testcase.
"""
from __future__                     import annotations

from pathlib                        import Path
from re                             import compile as re_compile
from time                           import time_ns
from typing                         import Any, ClassVar, Generic, Iterable, Optional as Nullable, TypeVar

from docutils                       import nodes
from docutils.frontend              import get_default_settings
from docutils.readers.standalone    import Reader
from docutils.transforms.references import DanglingReferences
from docutils.utils                 import DependencyList
from sphinx                         import addnodes
from sphinx.addnodes                import pending_xref
from sphinx.application             import Sphinx
from sphinx.domains                 import Domain
from sphinx.environment             import BuildEnvironment
from sphinx.transforms              import DoctreeReadEvent, SphinxTransformer
from sphinx.util.docutils           import new_document, sphinx_domains
from sphinx.util.logging            import getLogger

from pyTooling.Common               import getFullyQualifiedName
from pyTooling.Decorators           import export, readonly
from pyTooling.MetaClasses          import ExtendedType, abstractmethod

from pyTooling.Sphinx               import ReportDomain, ReportEntry, ReportExtensionError


__all__ = ["UNSAFE_CHARACTERS", "EntityType"]

#: Characters of an object's name, which are replaced in its document name.
UNSAFE_CHARACTERS = re_compile(r"[^A-Za-z0-9_.\-]+")

EntityType = TypeVar("EntityType")  #: The type of the objects a model's pages are generated for.


@export
class GeneratedPages(Generic[EntityType], metaclass=ExtendedType, slots=True):
	"""
	Base-class of the pages generated for one model - a report, a design, ...: a document name per object.

	The document names are computed once, when the pages are created, so a summary, the roles and the pages agree on
	them. A derived class names the type of the model's objects as the type argument :data:`EntityType`, names an
	object, lists its children, builds its page, and names the domain of the pages' objects in :attr:`_DOMAIN`; it
	declares its own class variable :attr:`_pages`, the registry of its models' pages.
	"""

	_DOMAIN:    ClassVar[str]                                  #: Name of the domain, which the pages' objects belong to.
	_pages:     ClassVar[dict[str, GeneratedPages[Any]]] = {}  #: The pages of every model of this kind, by pages ID.
	_separator: ClassVar[str] = "."                            #: Separator of the names in an object's qualified name.

	_pagesID:   str                                #: Identifier of the pages, e.g. a report's identifier.
	_source:    Path                               #: The file Sphinx regards as the pages' source, e.g. the report file.
	_paths:     dict[int, tuple[str, ...]]         #: Names from the model's root down to an object, by its ``id()``.
	_docNames:  dict[int, str]                     #: Document names, by the ``id()`` of their object.
	_documents: dict[str, tuple[str, EntityType]]  #: Role name and object, by document name.
	_topLevel:  list[str]                          #: Document names of the top-level objects' pages.

	def __init__(self, pagesID: str, prefix: str, source: Path, topLevel: Iterable[tuple[str, EntityType]]) -> None:
		"""
		Compute the document names of a model's objects.

		An object whose qualified name is already taken by another of the same kind gets no page; this is logged as a
		warning.

		:param pagesID:  Identifier of the pages, e.g. a report's identifier.
		:param prefix:   Document name the pages are generated below.
		:param source:   The file Sphinx regards as the pages' source, e.g. the report file.
		:param topLevel: The top-level objects as ``(role name, object)`` pairs, in the order of their pages.
		"""
		self._pagesID =   pagesID
		self._source =    source.resolve()
		self._paths =     {}
		self._docNames =  {}
		self._documents = {}

		qualifiedNames: dict[str, set[str]] = {}

		def addPages(children: Iterable[tuple[str, EntityType]], path: tuple[str, ...], directory: str) -> list[str]:
			"""
			Nested function adding a document name and entry per object, recursing into the objects' children.

			:param children:  The objects of one parent as ``(role name, object)`` pairs.
			:param path:      The parent's path below the report's root.
			:param directory: The parent's document name, the directory of its children's documents.
			:returns:         The document names of the objects, which got a page.
			"""
			siblings: set[str] = set()
			docNames: list[str] = []
			for roleName, child in children:
				name = self._Name(child)
				childPath = (*path, *self._PathElements(name))
				qualifiedName = self._separator.join(childPath)
				if qualifiedName in (names := qualifiedNames.setdefault(roleName, set())):
					getLogger(__name__).warning(
						f"Pages '{pagesID}': the qualified name '{qualifiedName}' is not unique, so the second one gets no page."
					)
					continue

				names.add(qualifiedName)

				baseName = UNSAFE_CHARACTERS.sub("_", name).strip("_.") or "_"
				fileName, counter = baseName, 1
				while fileName.lower() in siblings:
					counter += 1
					fileName = f"{baseName}-{counter}"
				siblings.add(fileName.lower())

				docName = f"{directory}/{fileName}"
				self._paths[id(child)] =    childPath
				self._docNames[id(child)] = docName
				self._documents[docName] =  (roleName, child)
				docNames.append(docName)

				addPages(self._Children(roleName, child), childPath, docName)

			return docNames

		self._topLevel = addPages(topLevel, (), prefix)

	@staticmethod
	def CheckPagesConfiguration(configurationName: str, pages: Any) -> str:
		"""
		Check the document name a report's pages are generated below - the value of a report's key ``pages`` -, and
		normalize it.

		:param configurationName:     Name of the report's configuration, as an error message names it.
		:param pages:                 The value of key ``pages``.
		:returns:                     The document name without leading and trailing ``/``.
		:raises ReportExtensionError: If ``pages`` isn't a string.
		:raises ReportExtensionError: If ``pages`` isn't a relative document name. |br|
		                              Use a name like 'unittests/src', separated by '/', without '.' or '..'.
		"""
		if not isinstance(pages, str):
			ex = ReportExtensionError(f"{configurationName}.pages: Document name is not a string.")
			ex.add_note(f"Got type '{getFullyQualifiedName(pages)}'.")
			raise ex

		parts = pages.strip("/").split("/")
		if "\\" in pages or any(part in ("", ".", "..") for part in parts):
			ex = ReportExtensionError(f"{configurationName}.pages: '{pages}' is not a relative document name.")
			ex.add_note("Use a name like 'unittests/src', separated by '/', without '.' or '..'.")
			raise ex

		return "/".join(parts)

	@classmethod
	def HasPages(cls, pagesID: str) -> bool:
		"""
		Check if a model has pages.

		:param pagesID: Identifier of the pages, e.g. a report's identifier.
		:returns:       ``True``, if the model was declared with pages, e.g. a report with the key ``pages``.
		"""
		return pagesID in cls._pages

	@classmethod
	def GetPages(cls, pagesID: str) -> GeneratedPages[Any]:
		"""
		Return the pages of a model.

		:param pagesID:   Identifier of the pages, e.g. a report's identifier.
		:returns:         The model's pages.
		:raises KeyError: If the model has no pages.
		"""
		try:
			return cls._pages[pagesID]
		except KeyError as ex:
			raise KeyError(f"'{pagesID}' has no pages.") from ex

	@classmethod
	def GenerateAll(cls, sphinxApplication: Sphinx, env: BuildEnvironment, docnames: list[str]) -> None:
		"""
		Call-back for Sphinx' ``env-before-read-docs`` event: generate the pages of every model of this kind.

		:param sphinxApplication: Sphinx application instance.
		:param env:               The build environment.
		:param docnames:          The documents to read, from which the generated pages are removed.
		"""
		for pages in cls._pages.values():
			pages.Generate(sphinxApplication)

			docnames[:] = [docname for docname in docnames if docname not in pages._documents]

	@classmethod
	def HideSource(
		cls,
		sphinxApplication: Sphinx,
		pagename: str,
		templatename: str,
		context: dict[str, object],
		doctree: Nullable[nodes.document]
	) -> None:
		"""
		Call-back for Sphinx' ``html-page-context`` event: a generated page has no source to copy or link.

		Without it, the HTML builder would copy the pages' source - e.g. the report file - per page.

		:param sphinxApplication: Sphinx application instance.
		:param pagename:          Name of the page.
		:param templatename:      Name of the page's template.
		:param context:           The template's context.
		:param doctree:           The page's doctree.
		"""
		if any(pagename in pages._documents for pages in cls._pages.values()):
			context["sourcename"] = ""

	@readonly
	def PagesID(self) -> str:
		"""
		Read-only property to access the pages' identifier (:attr:`_pagesID`).

		:returns: The identifier of the pages, e.g. a report's identifier.
		"""
		return self._pagesID

	@readonly
	def DocNames(self) -> tuple[str, ...]:
		"""
		Read-only property to return the names of the generated documents.

		:returns: The document names, an object before its children.
		"""
		return tuple(self._documents)

	def DocName(self, entity: EntityType) -> Nullable[str]:
		"""
		Return the name of an object's document.

		:param entity: The object.
		:returns:      The document name, or ``None`` if the object has no page.
		"""
		return self._docNames.get(id(entity), None)

	def Register(self, env: BuildEnvironment) -> None:
		"""
		Register the document names, each with its source (see :meth:`_Source`).

		:param env: The build environment.
		"""
		for docName, (_, entity) in self._documents.items():
			env.project.docnames.add(docName)
			env.project._docname_to_path[docName] = self._Source(entity)

	def Generate(self, sphinxApplication: Sphinx) -> None:
		"""
		Build the doctree of every page, have the environment collect it, and store it as if it was read.

		The page's content is added by :meth:`_Fill`, while the page is the environment's current document - so a
		directive of a page written as reStructuredText registers its objects for that page. The event ``doctree-read``
		is emitted per page, so the environment's collectors record its title, table of contents and metadata.
		Afterwards, the page's table of contents keeps the pages it lists, and loses its sections, so the navigation shows
		the model's objects only. Each object is then registered in its domain, see :meth:`_Registered`.

		:param sphinxApplication: Sphinx application instance.
		"""
		env = sphinxApplication.env
		domain = env.domains[self._DOMAIN]

		self.Register(env)
		for docName, (roleName, entity) in self._documents.items():
			document = new_document(str(self._Source(entity)))
			document.settings.env = env
			document.settings.record_dependencies = DependencyList()
			document += nodes.docinfo("", nodes.field("", nodes.field_name("", "orphan"), nodes.field_body()))

			env.prepare_settings(docName)
			try:
				self._Fill(sphinxApplication, document, docName, roleName, entity)
				sphinxApplication.events.emit("doctree-read", document)
			finally:
				env.prepare_settings("")
				env.ref_context.clear()

			pageEntry = env.tocs[docName][0]
			for entries in pageEntry[1:]:
				entries[:] = [entry for entry in entries if isinstance(entry, addnodes.toctree)]
				if len(entries) == 0:
					pageEntry.remove(entries)

			env.all_docs[docName] = time_ns() // 1_000
			self._Registered(domain, docName, roleName, entity)
			sphinxApplication.builder.write_doctree(docName, document)

	def TableOfContents(self, docName: str) -> nodes.compound:
		"""
		Create the hidden table of contents of the model's top-level pages, for the document showing its summary.

		The pages are then below that document in the navigation.

		:param docName: Name of the document showing the report's summary.
		:returns:       The table of contents.
		"""
		return self._TableOfContents(docName, self._topLevel)

	@staticmethod
	def _TableOfContents(docName: str, children: list[str]) -> nodes.compound:
		"""
		Create a hidden table of contents listing pages.

		:param docName:  Name of the document holding the table of contents.
		:param children: Names of the listed pages' documents.
		:returns:        The table of contents.
		"""
		toctree = addnodes.toctree(
			parent=docName, entries=[(None, child) for child in children], includefiles=children, maxdepth=1,
			caption=None, glob=False, hidden=True, includehidden=False, titlesonly=True, numbered=0
		)
		return nodes.compound("", toctree, classes=["toctree-wrapper"])

	@staticmethod
	def _Field(fieldList: nodes.field_list, name: str, *content: nodes.Node) -> None:
		"""
		Add a field to a page's summary.

		:param fieldList: The summary's field list.
		:param name:      The field's name.
		:param content:   The field's value.
		"""
		fieldList += nodes.field("", nodes.field_name(name, name), nodes.field_body("", nodes.paragraph("", "", *content)))

	@staticmethod
	def _Table(columns: list[tuple[str, int]], classes: list[str]) -> tuple[nodes.table, nodes.tbody]:
		"""
		Create a table with a header row.

		:param columns: One ``(title, width)`` pair per column.
		:param classes: CSS classes of the table.
		:returns:       The table, and its body the rows are added to.
		"""
		table = nodes.table("", classes=classes)
		table += (tableGroup := nodes.tgroup(cols=len(columns)))
		for _, width in columns:
			tableGroup += nodes.colspec(colwidth=width)

		tableGroup += (tableHeader := nodes.thead())
		tableHeader += (headerRow := nodes.row())
		for columnTitle, _ in columns:
			headerRow += nodes.entry("", nodes.paragraph(columnTitle, columnTitle))

		tableGroup += (tableBody := nodes.tbody())
		return table, tableBody

	@abstractmethod
	def _Name(self, entity: EntityType) -> str:
		"""
		Return an object's name, the last element of its path.

		:param entity: The object.
		:returns:      The name.
		"""

	def _PathElements(self, name: str) -> tuple[str, ...]:
		"""
		Return the elements an object's name adds to its path: the name itself, unless a derived class splits it.

		:param name: The object's name.
		:returns:    The path elements.
		"""
		return (name, )

	def _Source(self, entity: EntityType) -> Path:
		"""
		Return the file Sphinx regards as the source of an object's page: the pages' source, unless a derived class names
		another one.

		:param entity: The object.
		:returns:      The page's source file.
		"""
		return self._source

	@abstractmethod
	def _Children(self, roleName: str, entity: EntityType) -> Iterable[tuple[str, EntityType]]:
		"""
		Return an object's children, in the order of their pages.

		:param roleName: The role referring to the object.
		:param entity:   The object.
		:returns:        The children as ``(role name, object)`` pairs.
		"""

	def _Fill(
		self,
		sphinxApplication: Sphinx,
		document:          nodes.document,
		docName:           str,
		roleName:          str,
		entity:            EntityType
	) -> None:
		"""
		Add an object's page to its document: the top section built by :meth:`_Page`.

		A derived class writing its pages as reStructuredText overrides it, and parses the text into the document by
		:meth:`_ParseReST` - the page is the environment's current document then, so its directives register their
		objects for the page.

		:param sphinxApplication: Sphinx application instance.
		:param document:          The page's document, holding the metadata ``:orphan:``.
		:param docName:           Name of the page's document.
		:param roleName:          The role referring to the object.
		:param entity:            The object.
		"""
		document += self._Page(docName, roleName, entity)

	@staticmethod
	def _ParseReST(sphinxApplication: Sphinx, document: nodes.document, text: str) -> None:
		"""
		Parse reStructuredText into a page's document, as Sphinx reads a source file: with the directives and roles of
		every domain.

		The document gets the parser's default settings it lacks, and the settings Sphinx reads a source file with. The
		transforms of Sphinx' reading are applied - e.g. a label is attached to its section -, except the one emitting
		``doctree-read``, which :meth:`Generate` emits.

		:param sphinxApplication: Sphinx application instance.
		:param document:          The page's document, which the parsed nodes are appended to.
		:param text:              The reStructuredText.
		"""
		parser = sphinxApplication.registry.create_source_parser(
			"restructuredtext", config=sphinxApplication.config, env=sphinxApplication.env
		)

		settings = document.settings
		for name, value in vars(get_default_settings(parser)).items():
			if not hasattr(settings, name):
				setattr(settings, name, value)

		for name, value in sphinxApplication.env.settings.items():
			setattr(settings, name, value)

		transformer = SphinxTransformer(document)
		transformer.set_environment(sphinxApplication.env)
		transformer.add_transforms(
			[transform for transform in Reader().get_transforms() if transform is not DanglingReferences]
		)
		transformer.add_transforms(parser.get_transforms())
		transformer.add_transforms(
			[transform for transform in sphinxApplication.registry.get_transforms() if transform is not DoctreeReadEvent]
		)

		with sphinx_domains(sphinxApplication.env):
			parser.parse(text, document)
			transformer.apply_transforms()

	@abstractmethod
	def _Page(self, docName: str, roleName: str, entity: EntityType) -> nodes.section:
		"""
		Build an object's page.

		:param docName:  Name of the page's document.
		:param roleName: The role referring to the object.
		:param entity:   The object.
		:returns:        The page's top section.
		"""

	def _Registered(self, domain: Domain, docName: str, roleName: str, entity: EntityType) -> None:
		"""
		Register an object's page in the pages' domain, after the page was generated.

		Nothing by default: a page written as reStructuredText registers its objects by its directives.

		:param domain:   The domain named by :attr:`_DOMAIN`.
		:param docName:  Name of the page's document.
		:param roleName: The role referring to the object.
		:param entity:   The object.
		"""


@export
class ReportPages(GeneratedPages[EntityType]):
	"""
	Base-class of the pages of one report: a document name and an entry of domain ``report`` per object.

	A derived class names an object, writes its title, lists its children, and builds its page; it declares its own
	class variable :attr:`~GeneratedPages._pages`, the registry of its reports' pages.
	"""

	_DOMAIN: ClassVar[str] = ReportDomain.name  #: The pages' objects belong to domain ``report``.

	_entries: dict[int, ReportEntry]  #: The entries, by the ``id()`` of their object.

	def __init__(self, reportID: str, prefix: str, reportFile: Path, topLevel: Iterable[tuple[str, EntityType]]) -> None:
		"""
		Compute the document names and entries of a report's objects.

		An object whose qualified name is already taken by another of the same kind gets no page; this is logged as a
		warning.

		:param reportID:   Identifier of the report.
		:param prefix:     Document name the pages are generated below.
		:param reportFile: The report file, the pages' source for Sphinx.
		:param topLevel:   The top-level objects as ``(role name, object)`` pairs, in the order of their pages.
		"""
		super().__init__(reportID, prefix, reportFile, topLevel)

		self._entries = {
			id(entity): ReportEntry(docName, reportID, self._paths[id(entity)], self._separator, self._Title(entity))
			for docName, (_, entity) in self._documents.items()
		}

	@classmethod
	def CreateReference(cls, roleName: str, entry: ReportEntry, docname: str, text: Nullable[str] = None) -> pending_xref:
		"""
		Create a reference to an object's page, showing its name or a text.

		:param roleName: The role referring to the object, e.g. ``tc`` for a testcase.
		:param entry:    The object.
		:param docname:  Name of the document holding the reference.
		:param text:     Optional, the text shown instead of the object's name. Default: ``None``.
		:returns:        The reference, resolved by domain ``report``.
		"""
		reference = pending_xref(
			"", refdomain=cls._DOMAIN, reftype=roleName, reftarget=f"{entry.reportID}:{entry.QualifiedName}",
			refexplicit=text is not None, refwarn=True, refdoc=docname
		)
		text = entry.Name if text is None else text
		classes = ["xref", cls._DOMAIN, f"{cls._DOMAIN}-{roleName}"]
		reference += nodes.inline(text, text, classes=classes)

		return reference

	@readonly
	def ReportID(self) -> str:
		"""
		Read-only property to access the report's identifier (:attr:`~GeneratedPages._pagesID`).

		:returns: The identifier of the report.
		"""
		return self._pagesID

	def Entry(self, entity: EntityType) -> Nullable[ReportEntry]:
		"""
		Return the entry of an object of this report.

		:param entity: The object.
		:returns:      Its entry, or ``None`` if it has no page.
		"""
		return self._entries.get(id(entity), None)

	def _Reference(self, roleName: str, entity: EntityType, docName: str) -> nodes.Node:
		"""
		Create a reference to an object's page, or its name if it has no page.

		:param roleName: The role referring to the object.
		:param entity:   The object.
		:param docName:  Name of the document holding the reference.
		:returns:        The reference, or the name as text.
		"""
		if (entry := self.Entry(entity)) is None:
			return nodes.Text(self._Name(entity))

		return self.CreateReference(roleName, entry, docName)

	@abstractmethod
	def _Title(self, entity: EntityType) -> Nullable[str]:
		"""
		Return an object's title written for a reader, if it differs from its name.

		:param entity: The object.
		:returns:      The title, or ``None``.
		"""

	def _Registered(self, domain: Domain, docName: str, roleName: str, entity: EntityType) -> None:
		"""
		Register an object's entry in domain ``report``, after its page was generated.

		:param domain:   Domain ``report``.
		:param docName:  Name of the page's document.
		:param roleName: The role referring to the object, e.g. ``tc`` for a testcase.
		:param entity:   The object.
		"""
		domain.AddEntry(roleName, self._entries[id(entity)])  # type: ignore[attr-defined]
