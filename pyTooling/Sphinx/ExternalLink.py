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
Icons behind the external links of a document in HTML, each chosen by the link's target.

A link to GitHub gets GitHub's mark, an e-mail address an envelope, and a link to a host without an icon of its own a
square with an arrow pointing out of it.

Two post-transforms mark the links, for HTML only: :class:`MarkExternalLinks` before Sphinx resolves the references,
so it sees the links written with their URI - also those of a :mod:`sphinx.ext.extlinks` role -, and
:class:`MarkIntersphinxLinks` after, so it sees the links Sphinx resolved to another project's documentation - e.g. by
:mod:`sphinx.ext.intersphinx`. A marked link gets a CSS class naming its icon, which the stylesheet draws, and opens
in a new browser tab - unless configuration value ``pyTooling_ExternalLink_NewTab`` is ``False``, or the link is an
e-mail address.

A third post-transform, :class:`MarkDownloadLinks`, gives the links of Sphinx' ``:download:`` role a download icon. A
link to an archive - a file name ending in an extension of :data:`ARCHIVE_FORMATS`, e.g. ``.zip`` or ``.tar.gz`` - gets
the archive icon instead, also a link written with its URI.

A fourth post-transform, :class:`AddDownloadSizes`, writes the size of a download's file behind its link, and an
archive's format, e.g. ``(ZIP, 1.2 MiB)``. The size of a file of the documentation is read from the file system; the
size of another site's file is asked with an HTTP ``HEAD`` request, only if its URI matches a pattern of configuration
value ``pyTooling_ExternalLink_RemoteSizes``. An archive, whose size isn't known, gets its format only, e.g. ``(ZIP)``.

.. code-block:: Python

   # doc/conf.py
   pyTooling_ExternalLink_Icons =             "all"
   pyTooling_ExternalLink_NewTab =            True
   pyTooling_ExternalLink_Hosts =             {
     "gitlab.example.org": "gitlab",
   }
   pyTooling_ExternalLink_DownloadSizes =     True
   pyTooling_ExternalLink_RemoteSizes =       [
     "https://github.com/pyTooling/*/releases/download/*",
   ]
   pyTooling_ExternalLink_RemoteSizeTimeout = 5.0

.. seealso::

   :ref:`LINK/External`
      |rarr| The icons, the configuration values and the stylesheet's custom properties, with rendered examples.
"""
from fnmatch                           import fnmatchcase
from math                              import isfinite
from pathlib                           import Path
from typing                            import Any, ClassVar, Literal, Mapping, Self, Sequence
from urllib.parse                      import urlsplit
from weakref                           import WeakKeyDictionary

from docutils                          import nodes
from requests.exceptions               import HTTPError, RequestException, Timeout
from sphinx.addnodes                   import download_reference
from sphinx.application                import Sphinx
from sphinx.config                     import Config
from sphinx.environment                import BuildEnvironment
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util.logging               import getLogger
from sphinx.util.requests              import head

from pyTooling.Common                  import StringEnum, getFullyQualifiedName, getTypeName
from pyTooling.Decorators              import export
from pyTooling.Sphinx                  import SphinxExtensionError


__all__ = ["CONFIG_PREFIX", "HOST_ICONS", "ARCHIVE_FORMATS"]

CONFIG_PREFIX = "pyTooling_ExternalLink"
"""Prefix of the configuration values, e.g. ``pyTooling_ExternalLink_Icons``."""


@export
class ExternalLinkIcons(StringEnum):
	"""
	Which external links get an icon, as configuration value ``pyTooling_ExternalLink_Icons`` states it.
	"""

	Disabled = "none"      #: No link.
	Explicit = "explicit"  #: Links written with their URI, also those of a :mod:`sphinx.ext.extlinks` role.
	All =      "all"       #: These, and links resolved to another project's documentation.

	DEFAULT =  Explicit    #: Without a configuration value, the links written with their URI get an icon.


@export
class LinkIcon(StringEnum):
	"""
	The icon drawn behind an external link; the link gets the CSS class ``pytooling-link-icon-<value>``.
	"""

	External =    "external"     #: A square with an arrow pointing out of it.
	Mail =        "mail"         #: An envelope.
	GitHub =      "github"       #: GitHub's mark.
	GitLab =      "gitlab"       #: GitLab's tanuki.
	Python =      "python"       #: Python's logo.
	NumPy =       "numpy"        #: NumPy's logo.
	PyPy =        "pypy"         #: PyPy's logo.
	Pytest =      "pytest"       #: pytest's logo.
	Pydantic =    "pydantic"     #: Pydantic's logo.
	ReadTheDocs = "readthedocs"  #: Read the Docs' logo.
	Sphinx =      "sphinx"       #: Sphinx' logo.
	Download =    "download"     #: An arrow pointing down into a tray; the icon of a download link.
	Archive =     "archive"      #: A file with a zipper; the icon of a link to an archive.

	DEFAULT =     External       #: A host without an icon of its own gets the square with the arrow.

	@classmethod
	def FromURI(cls, uri: str, hosts: Mapping[str, Self]) -> Self:
		"""
		Choose the icon of a link by its target.

		A ``mailto:`` URI gets :attr:`Mail`, a URI whose path ends in an archive's extension :attr:`Archive` - see
		:func:`getArchiveExtension`. Any other URI gets the icon of its host, which is looked up in ``hosts`` with its full
		domain name first, then without its first label, and so on: ``docs.python.org`` is found as ``python.org``. A URI
		without a host, or with a host not found, gets :attr:`DEFAULT`.

		:param uri:   The link's target.
		:param hosts: The icons, keyed by domain name in lower case.
		:returns:     The link's icon.
		"""
		target = urlsplit(uri)
		if target.scheme == "mailto":
			return cls.Mail
		elif getArchiveExtension(uri) != "":
			return cls.Archive
		elif (host := target.hostname) is None:
			return cls.DEFAULT

		labels = host.split(".")
		for index in range(len(labels)):
			if (domainName := ".".join(labels[index:])) in hosts:
				return hosts[domainName]

		return cls.DEFAULT


HOST_ICONS: dict[str, LinkIcon] = {
	"github.com":      LinkIcon.GitHub,
	"gitlab.com":      LinkIcon.GitLab,
	"python.org":      LinkIcon.Python,
	"pypi.org":        LinkIcon.Python,
	"numpy.org":       LinkIcon.NumPy,
	"pypy.org":        LinkIcon.PyPy,
	"pytest.org":      LinkIcon.Pytest,
	"pydantic.dev":    LinkIcon.Pydantic,
	"readthedocs.io":  LinkIcon.ReadTheDocs,
	"readthedocs.org": LinkIcon.ReadTheDocs,
	"rtfd.io":         LinkIcon.ReadTheDocs,
	"sphinx-doc.org":  LinkIcon.Sphinx,
}
"""
The icon of a link to a host or to one of its subdomains, keyed by the host's domain name in lower case.

A project adds hosts, or replaces an icon, with configuration value ``pyTooling_ExternalLink_Hosts``.
"""

ARCHIVE_FORMATS: dict[str, str] = {
	"zip":     "ZIP",
	"tar.gz":  "tar.gz",
	"tgz":     "tar.gz",
	"tar.bz2": "tar.bz2",
	"tar.xz":  "tar.xz",
	"tar.zst": "tar.zst",
	"7z":      "7z",
}
"""
The formats of archives, keyed by their file name extension in lower case, as the label a download's size names.

A link to a file with one of these extensions gets the icon :attr:`LinkIcon.Archive`.
"""


@export
def getArchiveExtension(uri: str) -> str:
	"""
	Return the extension of the archive a link targets, as key of :data:`ARCHIVE_FORMATS`.

	The extensions are compared with the end of the URI's path, ignoring case; a query and a fragment are ignored. A
	local file name is a URI without a scheme: ``files/Archive.ZIP`` ends in ``zip``.

	:param uri: The link's target.
	:returns:   The extension, or an empty string if the path doesn't end in an archive's extension.
	"""
	path = urlsplit(uri).path.lower()
	for extension in ARCHIVE_FORMATS:
		if path.endswith(f".{extension}"):
			return extension

	return ""


@export
def checkExternalLinkConfiguration(sphinx: Sphinx, config: Config) -> None:
	"""
	Call-back for Sphinx' ``config-inited`` event, reading the configuration values of the external links' icons.

	``pyTooling_ExternalLink_Icons`` is replaced by the member of :class:`ExternalLinkIcons` it names,
	``pyTooling_ExternalLink_Hosts`` by a dictionary of the members of :class:`LinkIcon` its values name, keyed by its
	hosts in lower case, ``pyTooling_ExternalLink_RemoteSizes`` by a tuple of its patterns, and
	``pyTooling_ExternalLink_RemoteSizeTimeout`` by a :class:`float`.

	:param sphinx:                The Sphinx application.
	:param config:                The configuration, after :file:`conf.py` was read.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_Icons`` is not a string.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_Icons`` names no member of :class:`ExternalLinkIcons`.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_NewTab`` is not a boolean.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_Hosts`` is not a dictionary.
	:raises SphinxExtensionError: If a host of ``pyTooling_ExternalLink_Hosts`` is not a string.
	:raises SphinxExtensionError: If a host of ``pyTooling_ExternalLink_Hosts`` is empty.
	:raises SphinxExtensionError: If an icon of ``pyTooling_ExternalLink_Hosts`` is not a string.
	:raises SphinxExtensionError: If an icon of ``pyTooling_ExternalLink_Hosts`` names no member of :class:`LinkIcon`.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_DownloadSizes`` is not a boolean.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_RemoteSizes`` is not a list.
	:raises SphinxExtensionError: If a pattern of ``pyTooling_ExternalLink_RemoteSizes`` is not a string.
	:raises SphinxExtensionError: If a pattern of ``pyTooling_ExternalLink_RemoteSizes`` is empty.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_RemoteSizeTimeout`` is not a number.
	:raises SphinxExtensionError: If ``pyTooling_ExternalLink_RemoteSizeTimeout`` is not a positive, finite number.
	"""
	icons = config[f"{CONFIG_PREFIX}_Icons"]
	if icons is not None and not isinstance(icons, str):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Icons: Value is not of type 'str'.")
		ex.add_note(f"Got type '{getFullyQualifiedName(icons)}'.")
		raise ex

	try:
		config[f"{CONFIG_PREFIX}_Icons"] = ExternalLinkIcons.Parse(icons)
	except ValueError as cause:
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Icons: '{icons}' is not a selection of links.")
		ex.add_note(f"Allowed values: {', '.join(ExternalLinkIcons)}.")
		raise ex from cause

	if not isinstance(newTab := config[f"{CONFIG_PREFIX}_NewTab"], bool):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_NewTab: Value is not of type 'bool'.")
		ex.add_note(f"Got type '{getFullyQualifiedName(newTab)}'.")
		raise ex

	hosts = config[f"{CONFIG_PREFIX}_Hosts"]
	if not isinstance(hosts, Mapping):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: Value is not a dictionary.")
		ex.add_note(f"Got type '{getFullyQualifiedName(hosts)}'.")
		raise ex

	hostIcons: dict[str, LinkIcon] = {}
	for host, icon in hosts.items():
		if not isinstance(host, str):
			ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: Host '{host}' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(host)}'.")
			raise ex
		elif host == "":
			raise SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: Host is empty.")

		if icon is not None and not isinstance(icon, str):
			ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: Icon of host '{host}' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(icon)}'.")
			raise ex

		try:
			hostIcons[host.lower()] = LinkIcon.Parse(icon)
		except ValueError as cause:
			ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_Hosts: Icon '{icon}' of host '{host}' is not an icon.")
			ex.add_note(f"Allowed values: {', '.join(LinkIcon)}.")
			raise ex from cause

	config[f"{CONFIG_PREFIX}_Hosts"] = hostIcons

	if not isinstance(downloadSizes := config[f"{CONFIG_PREFIX}_DownloadSizes"], bool):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_DownloadSizes: Value is not of type 'bool'.")
		ex.add_note(f"Got type '{getFullyQualifiedName(downloadSizes)}'.")
		raise ex

	remoteSizes = config[f"{CONFIG_PREFIX}_RemoteSizes"]
	if isinstance(remoteSizes, str) or not isinstance(remoteSizes, Sequence):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_RemoteSizes: Value is not a list.")
		ex.add_note(f"Got type '{getFullyQualifiedName(remoteSizes)}'.")
		raise ex

	for pattern in remoteSizes:
		if not isinstance(pattern, str):
			ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_RemoteSizes: Pattern '{pattern}' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(pattern)}'.")
			raise ex
		elif pattern == "":
			raise SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_RemoteSizes: Pattern is empty.")

	config[f"{CONFIG_PREFIX}_RemoteSizes"] = tuple(remoteSizes)

	timeout = config[f"{CONFIG_PREFIX}_RemoteSizeTimeout"]
	if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_RemoteSizeTimeout: Value is not of type 'float'.")
		ex.add_note(f"Got type '{getFullyQualifiedName(timeout)}'.")
		raise ex
	elif not (timeout > 0 and isfinite(timeout)):
		ex = SphinxExtensionError(f"conf.py: {CONFIG_PREFIX}_RemoteSizeTimeout: Value is not a positive, finite number.")
		ex.add_note(f"Got value '{timeout}'.")
		raise ex

	config[f"{CONFIG_PREFIX}_RemoteSizeTimeout"] = float(timeout)


@export
class BaseExternalLinkTransform(SphinxPostTransform):
	"""
	Base-class of the post-transforms marking external links in HTML, so the stylesheet draws an icon behind each.

	A marked link gets the CSS class :attr:`linkClass`, and the CSS class ``pytooling-link-icon-<icon>`` naming the icon
	:meth:`LinkIcon.FromURI` chooses for it; a link to an archive also gets the CSS class
	``pytooling-archive-<extension>``, e.g. ``pytooling-archive-tar-gz``, naming its format. A link holding an image -
	e.g. a badge - isn't marked, nor is a download link: :class:`MarkDownloadLinks` marks those.

	If ``pyTooling_ExternalLink_NewTab`` is ``True``, a marked link opens in a new browser tab: it gets the attributes
	``target="_blank"`` and ``rel="noopener noreferrer"``, which Sphinx' HTML writer copies into the ``<a>`` element. An
	e-mail address doesn't, as a browser would open an empty tab beside the mail program.
	"""

	formats =   ("html", )                               #: Output formats the transform runs for.
	linkClass:  ClassVar[str]                            #: CSS class of a link the transform marks.
	selections: ClassVar[tuple[ExternalLinkIcons, ...]]  #: Values of ``pyTooling_ExternalLink_Icons`` it runs for.

	#: The configuration values of the external links' icons, as ``name: (default, rebuild, types)``. Each is
	#: registered with :data:`CONFIG_PREFIX` as prefix, e.g. ``pyTooling_ExternalLink_Icons``.
	#:
	#: ``Icons`` names a member of :class:`ExternalLinkIcons`; ``None`` is its ``DEFAULT``. ``NewTab`` states whether a
	#: marked link opens in a new browser tab. ``Hosts`` maps a host's domain name to the name of a member of
	#: :class:`LinkIcon`, adding to :data:`HOST_ICONS` or replacing its icon. ``DownloadSizes`` states whether
	#: :class:`AddDownloadSizes` writes the downloads' sizes, ``RemoteSizes`` lists the patterns of the URIs whose size it
	#: asks for, and ``RemoteSizeTimeout`` is the seconds it waits for a response. All are ``"html"``-rebuilt: the marks
	#: and sizes are written into the pages, never into the environment.
	configValues: ClassVar[dict[str, tuple[Any, Literal["html"], Any]]] = {
		"Icons":             (None, "html", (str, ExternalLinkIcons)),
		"NewTab":            (True, "html", bool),
		"Hosts":             ({},   "html", dict),
		"DownloadSizes":     (True, "html", bool),
		"RemoteSizes":       ([],   "html", (list, tuple)),
		"RemoteSizeTimeout": (5.0,  "html", (int, float)),
	}

	def run(self, **kwargs: Any) -> None:
		"""
		Mark every link :meth:`_Selects` selects, if ``pyTooling_ExternalLink_Icons`` is one of :attr:`selections`.

		:param kwargs: Keyword arguments Sphinx passes to a post-transform; none is used.
		"""
		if self.config[f"{CONFIG_PREFIX}_Icons"] not in self.selections:
			return

		hosts = HOST_ICONS.copy()
		hosts.update(self.config[f"{CONFIG_PREFIX}_Hosts"])
		newTab = self.config[f"{CONFIG_PREFIX}_NewTab"]
		for reference in self.document.findall(nodes.reference):
			if isinstance(reference, download_reference) or "refuri" not in reference or not self._Selects(reference):
				continue
			elif next(reference.findall(nodes.image), None) is not None:
				continue

			icon = LinkIcon.FromURI(reference["refuri"], hosts)
			reference["classes"] += [self.linkClass, f"pytooling-link-icon-{icon}"]
			if icon is LinkIcon.Archive:
				extension = getArchiveExtension(reference["refuri"])
				reference["classes"].append(f"pytooling-archive-{extension.replace('.', '-')}")

			if newTab and icon is not LinkIcon.Mail:
				reference["target"] = "_blank"
				reference["rel"] =    "noopener noreferrer"

	def _Selects(self, reference: nodes.reference) -> bool:
		"""
		Decide whether a link with a URI is marked.

		:param reference: The link.
		:returns:         ``True`` if the link is marked.
		"""
		raise NotImplementedError(f"Method '{getTypeName(self)}._Selects' is abstract.")


@export
class MarkExternalLinks(BaseExternalLinkTransform):
	"""
	A post-transform marking the links written with an absolute URI, before Sphinx resolves the references.

	A link of a :mod:`sphinx.ext.extlinks` role, e.g. ``:gh:``, is one of them.
	"""

	default_priority = 5                                                    #: Before Sphinx' ``ReferencesResolver`` (10).
	linkClass =        "pytooling-external-link"                            #: CSS class of a marked link.
	selections =       (ExternalLinkIcons.Explicit, ExternalLinkIcons.All)  #: Values it runs for.

	def _Selects(self, reference: nodes.reference) -> bool:
		"""
		Select a link to an absolute URI of scheme ``http``, ``https``, ``ftp`` or ``mailto``.

		:param reference: The link.
		:returns:         ``True`` if the link isn't internal and its URI has one of these schemes.
		"""
		return not reference.get("internal", False) and urlsplit(reference["refuri"]).scheme in (
			"http", "https", "ftp", "mailto"
		)


@export
class MarkIntersphinxLinks(BaseExternalLinkTransform):
	"""
	A post-transform marking the links Sphinx resolved to another project's documentation.

	Such a link - e.g. one of :mod:`sphinx.ext.intersphinx` - is one :class:`MarkExternalLinks` didn't mark, which its
	resolver declared not ``internal``. Its URI may be relative, for a project whose inventory is a local file; then it
	gets the icon :attr:`LinkIcon.External`.
	"""

	default_priority = 20                            #: After Sphinx' ``ReferencesResolver`` (10).
	linkClass =        "pytooling-intersphinx-link"  #: CSS class of a marked link.
	selections =       (ExternalLinkIcons.All, )     #: Values it runs for.

	def _Selects(self, reference: nodes.reference) -> bool:
		"""
		Select a link declared not ``internal`` by its resolver, which :class:`MarkExternalLinks` didn't mark.

		:param reference: The link.
		:returns:         ``True`` if the link's attribute ``internal`` is ``False`` and the link isn't marked yet.
		"""
		return reference.get("internal", None) is False and MarkExternalLinks.linkClass not in reference["classes"]


@export
class MarkDownloadLinks(SphinxPostTransform):
	"""
	A post-transform marking the links of Sphinx' ``:download:`` role in HTML, so the stylesheet draws a download icon
	behind each.

	A marked link gets the CSS classes ``pytooling-download-link`` and ``pytooling-link-icon-download``, whether the file
	is part of the documentation or another site's. A link to an archive gets ``pytooling-link-icon-archive`` instead,
	and ``pytooling-archive-<extension>`` naming its format - see :func:`getArchiveExtension`. A marked link stays in the
	browser's tab, as the browser saves the file. A link holding an image isn't marked.
	"""

	default_priority = 5                                                    #: Before Sphinx' ``ReferencesResolver`` (10).
	formats =          ("html", )                                           #: Output formats the transform runs for.
	linkClass =        "pytooling-download-link"                            #: CSS class of a marked link.
	selections =       (ExternalLinkIcons.Explicit, ExternalLinkIcons.All)  #: Values it runs for.

	def run(self, **kwargs: Any) -> None:
		"""
		Mark every download link, if ``pyTooling_ExternalLink_Icons`` is one of :attr:`selections`.

		:param kwargs: Keyword arguments Sphinx passes to a post-transform; none is used.
		"""
		if self.config[f"{CONFIG_PREFIX}_Icons"] not in self.selections:
			return

		for reference in self.document.findall(download_reference):
			if next(reference.findall(nodes.image), None) is not None:
				continue
			elif (extension := getArchiveExtension(reference["reftarget"])) == "":
				reference["classes"] += [self.linkClass, f"pytooling-link-icon-{LinkIcon.Download}"]
			else:
				reference["classes"] += [
					self.linkClass, f"pytooling-link-icon-{LinkIcon.Archive}", f"pytooling-archive-{extension.replace('.', '-')}"
				]


@export
class DownloadSizeError(SphinxExtensionError):
	"""
	The size of a download's file is unknown: the file can't be read, or a server didn't tell it.
	"""


@export
class AddDownloadSizes(SphinxPostTransform):
	"""
	A post-transform writing the size of a download's file behind its link in HTML, and the format of an archive.

	A download is a link of Sphinx' ``:download:`` role, or a link written with an ``http`` or ``https`` URI whose path
	ends in an archive's extension - see :func:`getArchiveExtension`. Its size follows the link as an inline node of CSS
	class :attr:`sizeClass`, e.g. ``(340.0 kiB)``, for an archive with its format's label of :data:`ARCHIVE_FORMATS`,
	e.g. ``(ZIP, 1.2 MiB)``. A link holding an image gets none.

	The size of a file of the documentation is read from the file system. The size of another site's file is asked with
	an HTTP ``HEAD`` request, following redirections, only if its URI is of scheme ``http`` or ``https`` and matches a
	pattern of ``pyTooling_ExternalLink_RemoteSizes``; each URI is asked once per build. If the size is unknown - e.g. a
	file Sphinx didn't find, no response within ``pyTooling_ExternalLink_RemoteSizeTimeout`` seconds, an HTTP error, or a
	response without a ``Content-Length`` -, Sphinx warns at the link with the warning type ``pyTooling.download_size``.
	A download, whose size isn't known, gets no size; an archive gets its format only, e.g. ``(ZIP)``. No download gets
	a size or a format, if ``pyTooling_ExternalLink_DownloadSizes`` is ``False``.
	"""

	default_priority = 25                         #: After the post-transforms marking the links.
	formats =          ("html", )                 #: Output formats the transform runs for.
	sizeClass =        "pytooling-download-size"  #: CSS class of the size behind a link.

	#: The sizes of the remote files asked for, per build environment - i.e. per build -, in bytes, keyed by URI.
	_remoteSizes:    ClassVar[WeakKeyDictionary[BuildEnvironment, dict[str, int]]] =               WeakKeyDictionary()
	#: Why the sizes of remote files asked for are unknown, per build environment, keyed by URI.
	_remoteFailures: ClassVar[WeakKeyDictionary[BuildEnvironment, dict[str, DownloadSizeError]]] = WeakKeyDictionary()

	def run(self, **kwargs: Any) -> None:
		"""
		Write the size behind every download, if ``pyTooling_ExternalLink_DownloadSizes`` is ``True``.

		:param kwargs: Keyword arguments Sphinx passes to a post-transform; none is used.
		"""
		if not self.config[f"{CONFIG_PREFIX}_DownloadSizes"]:
			return

		patterns = self.config[f"{CONFIG_PREFIX}_RemoteSizes"]
		timeout =  self.config[f"{CONFIG_PREFIX}_RemoteSizeTimeout"]
		sizes =    self._remoteSizes.setdefault(self.env, {})
		failures = self._remoteFailures.setdefault(self.env, {})
		for reference in list(self.document.findall(nodes.reference)):
			isDownload = isinstance(reference, download_reference)
			if next(reference.findall(nodes.image), None) is not None:
				continue
			elif isDownload and "refuri" not in reference:
				if "filename" not in reference:
					continue

				uri = reference["reftarget"]
				try:
					sizeText = self._FormatSize(Path(self.env.relfn2path(uri, self.env.docname)[1]).stat().st_size)
				except OSError as ex:
					self._WarnUnknownSize(reference, uri, f"{ex.strerror}.")
					sizeText = ""
			elif urlsplit(uri := reference.get("refuri", "")).scheme not in ("http", "https"):
				continue
			elif not isDownload and getArchiveExtension(uri) == "":
				continue
			elif not any(fnmatchcase(uri, pattern) for pattern in patterns):
				sizeText = ""
			elif uri in sizes:
				sizeText = self._FormatSize(sizes[uri])
			elif uri in failures:
				self._WarnUnknownSize(reference, uri, failures[uri])
				sizeText = ""
			else:
				try:
					sizes[uri] = self._RequestSize(uri, timeout, self.config)
				except DownloadSizeError as ex:
					failures[uri] = ex
					self._WarnUnknownSize(reference, uri, ex)
					sizeText = ""
				else:
					sizeText = self._FormatSize(sizes[uri])

			extension = getArchiveExtension(uri)
			if extension == "" and sizeText == "":
				continue
			elif extension == "":
				text = f"({sizeText})"
			elif sizeText == "":
				text = f"({ARCHIVE_FORMATS[extension]})"
			else:
				text = f"({ARCHIVE_FORMATS[extension]}, {sizeText})"

			reference.parent.insert(
				reference.parent.index(reference) + 1, [nodes.Text(" "), nodes.inline("", text, classes=[self.sizeClass])]
			)

	@staticmethod
	def _WarnUnknownSize(reference: nodes.reference, uri: str, reason: object) -> None:
		"""
		Warn at a download's link, that its file's size is unknown.

		The warning's type is ``pyTooling.download_size``, so a project can suppress it.

		:param reference: The download's link.
		:param uri:       The file's URI, or its path as written in the document.
		:param reason:    Why the size is unknown.
		"""
		getLogger(__name__).warning(
			f"Size of download '{uri}' is unknown. {reason}", location=reference, type="pyTooling", subtype="download_size"
		)

	@staticmethod
	def _RequestSize(uri: str, timeout: float, config: Config) -> int:
		"""
		Ask a server for the size of a file, with an HTTP ``HEAD`` request.

		The request is sent by :mod:`sphinx.util.requests`, so it follows Sphinx' configuration values ``user_agent``,
		``tls_verify`` and ``tls_cacerts``. It follows redirections, e.g. of a GitHub release's asset to its storage.

		:param uri:                The file's URI.
		:param timeout:            Seconds to wait for a response.
		:param config:             Sphinx' configuration.
		:returns:                  The file's size in bytes, as the response's ``Content-Length`` states it.
		:raises DownloadSizeError: If the server doesn't respond within ``timeout`` seconds, responds with an HTTP error, or
		                           the request fails otherwise.
		:raises DownloadSizeError: If the response has no ``Content-Length``, or one that is no number.
		"""
		try:
			response = head(
				uri, allow_redirects=True, timeout=timeout, _user_agent=config.user_agent,
				_tls_info=(config.tls_verify, config.tls_cacerts)
			)
			response.raise_for_status()
		except Timeout as ex:
			raise DownloadSizeError(f"No response within {timeout} seconds.") from ex
		except HTTPError as ex:
			raise DownloadSizeError(f"Server responded {ex.response.status_code} {ex.response.reason}.") from ex
		except RequestException as ex:
			raise DownloadSizeError(f"Request failed: {ex}") from ex

		length = response.headers.get("Content-Length", "")
		if length == "":
			raise DownloadSizeError("Response has no 'Content-Length'.")
		elif not length.isdecimal():
			raise DownloadSizeError(f"Response's 'Content-Length' '{length}' is no number.")

		return int(length)

	@staticmethod
	def _FormatSize(size: int) -> str:
		"""
		Format a file's size in binary units.

		A size below 1024 bytes is written in bytes, e.g. ``1023 B``; a larger one in the largest unit of kiB, MiB and GiB
		it reaches, with one decimal, e.g. ``1.0 kiB``.

		:param size: The size in bytes.
		:returns:    The size and its unit.
		"""
		if size < 1024:
			return f"{size} B"

		for exponent, unit in (
			(1, "kiB"),
			(2, "MiB")
		):
			if (value := round(size / 1024 ** exponent, 1)) < 1024:
				return f"{value:.1f} {unit}"

		return f"{size / 1024 ** 3:.1f} GiB"
