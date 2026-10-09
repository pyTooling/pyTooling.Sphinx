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
Pages generated from a report: a document per object of the report - a testsuite, a testcase, a source file, ... -
built without a source file, in the navigation below the directive showing the report's summary.

A report declared with the key ``pages`` gets a document per object, named below that key's document name by the
names of the objects from the report's root down, e.g. ``<pages>/<testsuite>/<testcase>``. A name's characters other
than letters, digits, ``_``, ``-`` and ``.`` - e.g. the brackets of a parametrized pytest testcase - are replaced by
``_``, and a name colliding with a sibling's (also when differing only in case) gets the suffix ``-2``, ``-3``, ...

The pages are built as docutils node trees and handed to Sphinx as if they were read from a file: their names are
registered when the builder is initialized and again before the documents are read -
:meth:`sphinx.project.Project.discover` forgets them in between -, and the file Sphinx sees as their source is the
report, so a changed report rebuilds them.
A page carries the metadata ``:orphan:``. A page with children lists them in a hidden table of contents, as the
directive showing the report's summary lists the top-level pages, so the pages are in the navigation below that
directive's document; a page's own sections aren't listed there. Every object with a page is an object of domain
``report``, referred to by a role of :data:`~pyTooling.Sphinx.REPORT_ROLES`.

.. seealso::

   :mod:`pyTooling.Sphinx.UnittestPages`
      |rarr| The pages of a unit test report: a page per testsuite and testcase.
"""
from __future__                 import annotations

from pathlib                    import Path
from re                         import compile as re_compile
from time                       import time_ns
from typing                     import Any, ClassVar, Iterable, Optional as Nullable

from docutils                   import nodes
from docutils.utils             import DependencyList
from sphinx                     import addnodes
from sphinx.addnodes            import pending_xref
from sphinx.application         import Sphinx
from sphinx.environment         import BuildEnvironment
from sphinx.util.docutils       import new_document
from sphinx.util.logging        import getLogger

from pyTooling.Common           import getFullyQualifiedName
from pyTooling.Decorators       import export, readonly
from pyTooling.MetaClasses      import ExtendedType, abstractmethod

from pyTooling.Sphinx           import ReportDomain, ReportEntry, ReportExtensionError


__all__ = ["UNSAFE_CHARACTERS"]

#: Characters of an object's name, which are replaced in its document name.
UNSAFE_CHARACTERS = re_compile(r"[^A-Za-z0-9_.\-]+")


@export
class ReportPages(metaclass=ExtendedType, slots=True):
	"""
	Base-class of the pages of one report: a document name and an entry of domain ``report`` per object.

	The document names are computed once, when the report's pages are created, so the summary table, the roles and the
	pages agree on them. A derived class names an object, lists its children, and builds its page; it declares its own
	class variable :attr:`_reportPages`, the registry of its reports' pages.
	"""

	_reportPages: ClassVar[dict[str, ReportPages]] = {}  #: The pages of every report of this kind, by report ID.
	_separator:   ClassVar[str] = "."                    #: Separator of the names in an object's qualified name.

	_reportID:   str                             #: Identifier of the report.
	_reportFile: Path                            #: The report file, the pages' source for Sphinx.
	_entries:    dict[int, ReportEntry]          #: The entries, by the ``id()`` of their object.
	_documents:  dict[str, tuple[str, Any]]      #: Role name and object, by document name.
	_topLevel:   list[str]                       #: Document names of the top-level objects' pages.

	def __init__(self, reportID: str, prefix: str, reportFile: Path, topLevel: Iterable[tuple[str, Any]]) -> None:
		"""
		Compute the document names and entries of a report's objects.

		An object whose qualified name is already taken by another of the same kind gets no page; this is logged as a
		warning.

		:param reportID:   Identifier of the report.
		:param prefix:     Document name the pages are generated below.
		:param reportFile: The report file.
		:param topLevel:   The top-level objects as ``(role name, object)`` pairs, in the order of their pages.
		"""
		self._reportID =   reportID
		self._reportFile = reportFile.resolve()
		self._entries =    {}
		self._documents =  {}

		qualifiedNames: dict[str, set[str]] = {}

		def addPages(children: Iterable[tuple[str, Any]], path: tuple[str, ...], directory: str) -> list[str]:
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
				childPath = (*path, name)
				qualifiedName = self._separator.join(childPath)
				if qualifiedName in (names := qualifiedNames.setdefault(roleName, set())):
					getLogger(__name__).warning(
						f"Report '{reportID}': the qualified name '{qualifiedName}' is not unique, "
						f"so the second one gets no page."
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
				self._entries[id(child)] = ReportEntry(docName, reportID, childPath, self._separator, self._Title(child))
				self._documents[docName] = (roleName, child)
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
	def HasPages(cls, reportID: str) -> bool:
		"""
		Check if a report has pages.

		:param reportID: Identifier of the report.
		:returns:        ``True``, if the report was declared with the key ``pages``.
		"""
		return reportID in cls._reportPages

	@classmethod
	def GetPages(cls, reportID: str) -> ReportPages:
		"""
		Return the pages of a report.

		:param reportID:  Identifier of the report.
		:returns:         The report's pages.
		:raises KeyError: If the report has no pages.
		"""
		try:
			return cls._reportPages[reportID]
		except KeyError as ex:
			raise KeyError(f"Report '{reportID}' has no pages.") from ex

	@classmethod
	def GenerateAll(cls, sphinxApplication: Sphinx, env: BuildEnvironment, docnames: list[str]) -> None:
		"""
		Call-back for Sphinx' ``env-before-read-docs`` event: generate the pages of every report of this kind.

		:param sphinxApplication: Sphinx application instance.
		:param env:               The build environment.
		:param docnames:          The documents to read, from which the generated pages are removed.
		"""
		for pages in cls._reportPages.values():
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

		Without it, the HTML builder would copy the report file - the page's source for Sphinx - per page.

		:param sphinxApplication: Sphinx application instance.
		:param pagename:          Name of the page.
		:param templatename:      Name of the page's template.
		:param context:           The template's context.
		:param doctree:           The page's doctree.
		"""
		if any(pagename in pages._documents for pages in cls._reportPages.values()):
			context["sourcename"] = ""

	@staticmethod
	def CreateReference(roleName: str, entry: ReportEntry, docname: str) -> pending_xref:
		"""
		Create a reference to an object's page, showing its name.

		:param roleName: The role referring to the object, e.g. ``tc`` for a testcase.
		:param entry:    The object.
		:param docname:  Name of the document holding the reference.
		:returns:        The reference, resolved by domain ``report``.
		"""
		reference = pending_xref(
			"", refdomain=ReportDomain.name, reftype=roleName, reftarget=f"{entry.reportID}:{entry.QualifiedName}",
			refexplicit=False, refwarn=True, refdoc=docname
		)
		classes = ["xref", ReportDomain.name, f"{ReportDomain.name}-{roleName}"]
		reference += nodes.inline(entry.Name, entry.Name, classes=classes)

		return reference

	@readonly
	def ReportID(self) -> str:
		"""
		Read-only property to access the report's identifier (:attr:`_reportID`).

		:returns: The identifier of the report.
		"""
		return self._reportID

	@readonly
	def DocNames(self) -> tuple[str, ...]:
		"""
		Read-only property to return the names of the generated documents.

		:returns: The document names, an object before its children.
		"""
		return tuple(self._documents)

	def Entry(self, entity: Any) -> Nullable[ReportEntry]:
		"""
		Return the entry of an object of this report.

		:param entity: The object.
		:returns:      Its entry, or ``None`` if it has no page.
		"""
		return self._entries.get(id(entity), None)

	def Register(self, env: BuildEnvironment) -> None:
		"""
		Register the document names, with the report file as their source.

		:param env: The build environment.
		"""
		for docName in self._documents:
			env.project.docnames.add(docName)
			env.project._docname_to_path[docName] = self._reportFile

	def Generate(self, sphinxApplication: Sphinx) -> None:
		"""
		Build the doctree of every page, have the environment collect it, and store it as if it was read.

		The event ``doctree-read`` is emitted per page, so the environment's collectors record its title, table of
		contents and metadata. Afterwards, the page's table of contents keeps the pages it lists, and loses its sections,
		so the navigation shows the report's objects only.

		:param sphinxApplication: Sphinx application instance.
		"""
		env = sphinxApplication.env
		domain: ReportDomain = env.domains[ReportDomain.name]  # type: ignore[assignment]

		self.Register(env)
		for docName, (roleName, entity) in self._documents.items():
			document = new_document(str(self._reportFile))
			document.settings.env = env
			document.settings.record_dependencies = DependencyList()
			document += nodes.docinfo("", nodes.field("", nodes.field_name("", "orphan"), nodes.field_body()))
			document += self._Page(docName, roleName, entity)

			env.prepare_settings(docName)
			try:
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
			domain.AddEntry(roleName, self._entries[id(entity)])
			sphinxApplication.builder.write_doctree(docName, document)

	def TableOfContents(self, docName: str) -> nodes.compound:
		"""
		Create the hidden table of contents of the report's top-level pages, for the document showing its summary.

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

	def _Reference(self, roleName: str, entity: Any, docName: str) -> nodes.Node:
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
	def _Name(self, entity: Any) -> str:
		"""
		Return an object's name, the last element of its path.

		:param entity: The object.
		:returns:      The name.
		"""

	@abstractmethod
	def _Title(self, entity: Any) -> Nullable[str]:
		"""
		Return an object's title written for a reader, if it differs from its name.

		:param entity: The object.
		:returns:      The title, or ``None``.
		"""

	@abstractmethod
	def _Children(self, roleName: str, entity: Any) -> Iterable[tuple[str, Any]]:
		"""
		Return an object's children, in the order of their pages.

		:param roleName: The role referring to the object.
		:param entity:   The object.
		:returns:        The children as ``(role name, object)`` pairs.
		"""

	@abstractmethod
	def _Page(self, docName: str, roleName: str, entity: Any) -> nodes.section:
		"""
		Build an object's page.

		:param docName:  Name of the page's document.
		:param roleName: The role referring to the object.
		:param entity:   The object.
		:returns:        The page's top section.
		"""
