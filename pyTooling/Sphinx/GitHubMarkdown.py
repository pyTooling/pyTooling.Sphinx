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
A converter of GitHub-flavoured Markdown into docutils nodes.

The Markdown is e.g. the notes of a GitHub release. :class:`GitHubMarkdown` parses it with markdown-it-py and the
GFM plugin of mdit-py-plugins - CommonMark plus tables, strikethrough, task lists, alerts, autolinks and footnotes -,
and :class:`~pyTooling.Sphinx.Markdown.MarkdownTranslator` translates the tokens into the nodes a directive
returns:

.. code-block:: Python

   converter = GitHubMarkdown("pyTooling", "pyTooling")
   return converter.Convert(markdown, self.state.document, location=self.get_location())

.. rubric:: GitHub's references

GitHub links what Markdown leaves as text: ``#123``, ``GH-123`` and ``owner/name#123`` to an issue or a pull request,
``@user`` to a user, a commit's hash (7 to 40 hexadecimal digits) to the commit, and ``:tada:`` is an emoji. The
converter does the same in text outside of code and links (see :meth:`GitHubMarkdown.Parse`). GitHub links a
hash only if the commit exists; the converter can't ask, so it links a word of hexadecimal digits holding a digit and a
letter.

.. rubric:: Emoji

The emoji, their characters and shortcodes, are GitHub's own list: the table :data:`EMOJI_FILE` is generated from
github/gemoji's :file:`db/emoji.json`, which GitHub, Inc. distributes under the MIT license; the table's header names
the version and holds the license text. A custom GitHub emoji, e.g. ``:octocat:``, is an image without characters, and
isn't in the list.

.. rubric:: Headings and raw HTML

A heading becomes a topic or a rubric, never a section, and raw HTML is translated element by element, as
:mod:`~pyTooling.Sphinx.Markdown` describes.

.. rubric:: LaTeX

An emoji is a node of its own (:class:`~pyTooling.Sphinx.Node.Emoji`), whose characters LaTeX writes as they are, for
LuaLaTeX and an emoji font.

LaTeX can't include an SVG image, e.g. a badge. :class:`RasterizeShieldsBadges` fetches a shields.io badge as PNG;
every other SVG image is converted by Sphinx' ImageMagick converter, :mod:`sphinx.ext.imgconverter`, which
pyTooling.Sphinx loads. Without ImageMagick, Sphinx warns, and LaTeX stops at the image with "Unknown graphics
extension: .svg".

.. attention::

   Packages ``markdown_it`` and ``mdit_py_plugins`` are imported when a :class:`GitHubMarkdown` is created, not when
   this module is imported. They are installed with the extra ``markdown``.
"""
from __future__                        import annotations

from re                                import compile as re_compile, escape as re_escape
from typing                            import TYPE_CHECKING, Any, ClassVar, Optional as Nullable, Pattern
from urllib.parse                      import urlsplit

from docutils                          import nodes
from sphinx.transforms.post_transforms import SphinxPostTransform

from pyTooling.Common                  import getFullyQualifiedName, readResourceFile
from pyTooling.Decorators              import export, readonly
from pyTooling.Exceptions              import MissingDependencyError
from pyTooling.MetaClasses             import ExtendedType
from pyTooling.Sphinx                  import Resources as SphinxResources
from pyTooling.Sphinx.Markdown         import IMAGE_CLASS, MarkdownTranslator
from pyTooling.Sphinx.Node             import Emoji
from pyTooling.Sphinx.Shields          import SHIELDS_SERVICE_PNG, SHIELDS_SERVICE_SVG

if TYPE_CHECKING:  # pragma: no cover
	from markdown_it                     import MarkdownIt


__all__ = ["EMOJI_FILE", "OWNER_PATTERN", "REPOSITORY_NAME_PATTERN", "REPOSITORY_PATTERN", "REFERENCE_PATTERN"]

#: Name of the emoji table in :mod:`pyTooling.Sphinx.Resources`: a line per emoji, its code points and its shortcodes,
#: generated from github/gemoji (MIT license, Copyright (c) 2019 GitHub, Inc.).
EMOJI_FILE = "GitHubEmoji.txt"

#: A GitHub owner - a user or an organization: ASCII letters, digits and single hyphens, not starting with a hyphen.
OWNER_PATTERN = re_compile(r"[A-Za-z0-9](?:-?[A-Za-z0-9])*")

#: A GitHub repository's name: ASCII letters, digits, ``.``, ``_`` and ``-``.
REPOSITORY_NAME_PATTERN = re_compile(r"[A-Za-z0-9._-]+")

#: A GitHub repository with its owner, as a reference writes it: ``<owner>/<name>``.
REPOSITORY_PATTERN = re_compile(rf"{OWNER_PATTERN.pattern}/{REPOSITORY_NAME_PATTERN.pattern}")

_BEFORE = r"(?<![\w/@#.-])"
"""What can't precede a reference: a word character, or a character continuing a path, a reference or a URL."""

#: An emoji's shortcode, or one of GitHub's references: an issue or pull request, a commit, or a user.
REFERENCE_PATTERN = re_compile(
	r":(?P<shortcode>[a-z0-9_+-]+):"
	rf"|{_BEFORE}(?:(?P<issueRepository>{REPOSITORY_PATTERN.pattern})#|GH-|#)(?P<issue>[0-9]+)(?![\w-])"
	rf"|{_BEFORE}(?:(?P<commitRepository>{REPOSITORY_PATTERN.pattern})@)?(?P<sha>[0-9a-f]{{7,40}})(?![\w-])"
	rf"|{_BEFORE}@(?P<user>{OWNER_PATTERN.pattern})(?![\w/-])"
)


@export
class GitHubMarkdown(metaclass=ExtendedType, slots=True):
	"""
	A converter of GitHub-flavoured Markdown into docutils nodes, which links GitHub's references in a repository's
	context.

	The owner and the repository are the ones ``#123`` refers to, and the server URL the one every link starts with.
	:meth:`Convert` converts a Markdown document into docutils nodes, :meth:`Parse` parses a text without Markdown for
	GitHub's references and emoji.

	GitHub writes a line break of an issue, a comment or a release's notes as a line break, not as a space:
	:attr:`LineBreaks` selects which.
	"""

	_emojis:       ClassVar[Nullable[dict[str, str]]] = None  #: The emoji's characters by shortcode, once read.
	_shortcodes:   ClassVar[Nullable[dict[str, str]]] = None  #: A shortcode per emoji, by its characters without U+FE0F.
	_emojiPattern: ClassVar[Nullable[Pattern[str]]]   = None  #: The pattern finding emoji written as characters.

	_owner:      str         #: The owner of the repository references refer to, a user or an organization.
	_repository: str         #: The name of the repository references refer to.
	_serverURL:  str         #: The URL of the GitHub server, without a trailing ``/``.
	_lineBreaks: bool        #: Whether a line break in a paragraph is written as a line break.
	_parser:     MarkdownIt  #: The Markdown parser.

	def __init__(
		self,
		owner: str,
		repository: str,
		serverURL: str = "https://github.com",
		lineBreaks: bool = True
	) -> None:
		"""
		Initializes a converter for the Markdown of a repository.

		:param owner:                   The owner of the repository references refer to, a user or an organization.
		:param repository:              The name of the repository references refer to.
		:param serverURL:               Optional, URL of the GitHub server. Default: ``"https://github.com"``.
		:param lineBreaks:              Optional, whether a line break in a paragraph is written as a line break, as
		                                GitHub does in a release's notes. Default: ``True``.
		:raises ValueError:             If parameter ``owner`` is ``None``.
		:raises TypeError:              If parameter ``owner`` isn't of type :class:`str`.
		:raises ValueError:             If parameter ``owner`` isn't a GitHub user's or organization's name.
		:raises ValueError:             If parameter ``repository`` is ``None``.
		:raises TypeError:              If parameter ``repository`` isn't of type :class:`str`.
		:raises ValueError:             If parameter ``repository`` isn't a GitHub repository's name.
		:raises ValueError:             If parameter ``serverURL`` is ``None``.
		:raises TypeError:              If parameter ``serverURL`` isn't of type :class:`str`.
		:raises ValueError:             If parameter ``serverURL`` isn't an HTTP or HTTPS URL.
		:raises ValueError:             If parameter ``lineBreaks`` is ``None``.
		:raises TypeError:              If parameter ``lineBreaks`` isn't of type :class:`bool`.
		:raises MissingDependencyError: If the extra ``markdown`` isn't installed.
		"""
		if owner is None:
			raise ValueError("Parameter 'owner' is None.")
		elif not isinstance(owner, str):
			ex = TypeError("Parameter 'owner' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(owner)}'.")
			raise ex
		elif OWNER_PATTERN.fullmatch(owner) is None:
			ex = ValueError("Parameter 'owner' is not a GitHub user's or organization's name.")
			ex.add_note(f"Got value '{owner}'.")
			raise ex

		if repository is None:
			raise ValueError("Parameter 'repository' is None.")
		elif not isinstance(repository, str):
			ex = TypeError("Parameter 'repository' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(repository)}'.")
			raise ex
		elif REPOSITORY_NAME_PATTERN.fullmatch(repository) is None:
			ex = ValueError("Parameter 'repository' is not a GitHub repository's name.")
			ex.add_note(f"Got value '{repository}'.")
			raise ex

		if serverURL is None:
			raise ValueError("Parameter 'serverURL' is None.")
		elif not isinstance(serverURL, str):
			ex = TypeError("Parameter 'serverURL' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(serverURL)}'.")
			raise ex
		elif urlsplit(serverURL).scheme not in ("https", "http") or urlsplit(serverURL).netloc == "":
			ex = ValueError("Parameter 'serverURL' is not an HTTP or HTTPS URL.")
			ex.add_note(f"Got value '{serverURL}'.")
			raise ex

		if lineBreaks is None:
			raise ValueError("Parameter 'lineBreaks' is None.")
		elif not isinstance(lineBreaks, bool):
			ex = TypeError("Parameter 'lineBreaks' is not of type 'bool'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(lineBreaks)}'.")
			raise ex

		try:
			from markdown_it         import MarkdownIt
		except ImportError as ex:
			raise MissingDependencyError(dependency="markdown-it-py", extra="markdown") from ex

		try:
			from mdit_py_plugins.gfm import gfm_plugin
		except ImportError as ex:
			raise MissingDependencyError(dependency="mdit-py-plugins", extra="markdown") from ex

		self._owner =      owner
		self._repository = repository
		self._serverURL =  serverURL.rstrip("/")
		self._lineBreaks = lineBreaks
		# 'text_join' would merge an escaped character into the text around it, e.g. '\#12' into a reference
		self._parser =     MarkdownIt("commonmark", {"html": True}).use(gfm_plugin).disable("text_join")

		if GitHubMarkdown._emojis is None:
			emojis: dict[str, str] =     {}
			shortcodes: dict[str, str] = {}
			for line in readResourceFile(SphinxResources, EMOJI_FILE).splitlines():
				if line.startswith("#") or line.strip() == "":
					continue

				codePoints, *names = line.split()
				characters = "".join(chr(int(codePoint, 16)) for codePoint in codePoints.split("-"))
				shortcodes[characters.replace("\ufe0f", "")] = names[0]
				for name in names:
					emojis[name] = characters

			GitHubMarkdown._emojiPattern = self._EmojiPattern(shortcodes)
			GitHubMarkdown._shortcodes =   shortcodes
			GitHubMarkdown._emojis =       emojis

	@staticmethod
	def _EmojiPattern(shortcodes: dict[str, str]) -> Pattern[str]:
		"""
		Build the pattern finding the emoji written as characters in a text: a trie of their characters, each optionally
		followed by variation selector 16 (U+FE0F).

		A single character below U+2190 - e.g. the copyright sign - is an emoji only if followed by U+FE0F; else it is
		a character of the text font.

		:param shortcodes: The emoji's characters without U+FE0F.
		:returns:          The pattern.
		"""
		trie: dict[str, Any] = {}
		for characters in shortcodes:
			level = trie
			for character in characters:
				level = level.setdefault(character, {})
			level[""] = {}

		def alternatives(level: dict[str, Any], depth: int) -> str:
			"""
			Nested function for recursion.

			:param level: A level of the trie, by character; key ``""`` marks the end of an emoji.
			:param depth: The level's depth, ``0`` for the first character.
			:returns:     The level's pattern.
			"""
			branches = []
			for character, nextLevel in sorted(level.items()):
				if character == "":
					continue

				selector = "\ufe0f" if depth == 0 and ord(character) < 0x2190 and list(nextLevel) == [""] else "\ufe0f?"
				branches.append(f"{re_escape(character)}{selector}{alternatives(nextLevel, depth + 1)}")

			if len(branches) == 0:
				return ""

			optional = "?" if "" in level else ""
			return f"(?:{'|'.join(branches)}){optional}"

		return re_compile(alternatives(trie, 0))

	@readonly
	def Owner(self) -> str:
		"""
		Read-only property to access the owner of the repository references refer to (:attr:`_owner`).

		:returns: The owner, a user or an organization.
		"""
		return self._owner

	@readonly
	def Repository(self) -> str:
		"""
		Read-only property to access the name of the repository references refer to (:attr:`_repository`).

		:returns: The repository's name.
		"""
		return self._repository

	@readonly
	def ServerURL(self) -> str:
		"""
		Read-only property to access the URL of the GitHub server (:attr:`_serverURL`).

		:returns: The URL, without a trailing ``/``.
		"""
		return self._serverURL

	@readonly
	def LineBreaks(self) -> bool:
		"""
		Read-only property to access whether a line break in a paragraph is written as a line break (:attr:`_lineBreaks`).

		:returns: ``True``, if a line break is written as a line break; ``False``, if as a space.
		"""
		return self._lineBreaks

	def Convert(
		self,
		markdown: str,
		document: nodes.document,
		repeatedTitle: str = "",
		location: Nullable[str] = None
	) -> list[nodes.Node]:
		"""
		Convert a Markdown document into docutils nodes.

		The nodes are body elements a directive returns; headings become topics and rubrics (see the module's
		description). A footnote's ID is unique in the document.

		The first heading of the Markdown can repeat the title, which the nodes are put under, e.g. ``# GHDL 5.0.1`` in
		the notes of a release titled so. Given as ``repeatedTitle``, such a heading is skipped, so the headings after it
		become the topics.

		:param markdown:      The Markdown.
		:param document:      The document the nodes are put into.
		:param repeatedTitle: Optional, the title the first heading is skipped for; compared without surrounding and
		                      repeated whitespace. Default: ``""``, no heading is skipped.
		:param location:      Optional, location the warnings are reported at, e.g. ``index.rst:12``. Default: ``None``.
		:returns:             The nodes.
		:raises ValueError:   If parameter ``markdown`` is ``None``.
		:raises TypeError:    If parameter ``markdown`` isn't of type :class:`str`.
		:raises ValueError:   If parameter ``document`` is ``None``.
		:raises TypeError:    If parameter ``document`` isn't of type :class:`~docutils.nodes.document`.
		:raises ValueError:   If parameter ``repeatedTitle`` is ``None``.
		:raises TypeError:    If parameter ``repeatedTitle`` isn't of type :class:`str`.
		:raises TypeError:    If parameter ``location`` isn't of type :class:`str`.
		"""
		if markdown is None:
			raise ValueError("Parameter 'markdown' is None.")
		elif not isinstance(markdown, str):
			ex = TypeError("Parameter 'markdown' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(markdown)}'.")
			raise ex

		if document is None:
			raise ValueError("Parameter 'document' is None.")
		elif not isinstance(document, nodes.document):
			ex = TypeError("Parameter 'document' is not of type 'docutils.nodes.document'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(document)}'.")
			raise ex

		if repeatedTitle is None:
			raise ValueError("Parameter 'repeatedTitle' is None.")
		elif not isinstance(repeatedTitle, str):
			ex = TypeError("Parameter 'repeatedTitle' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(repeatedTitle)}'.")
			raise ex

		if location is not None and not isinstance(location, str):
			ex = TypeError("Parameter 'location' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(location)}'.")
			raise ex

		tokens = self._parser.parse(markdown)
		if repeatedTitle != "":
			for index, token in enumerate(tokens):
				if token.type == "heading_open" and token.level == 0:
					if " ".join(tokens[index + 1].content.split()) == " ".join(repeatedTitle.split()):
						del tokens[index:index + 3]
					break

		return MarkdownTranslator(self, document, location).Translate(tokens)

	def Parse(self, text: str, references: bool = True) -> list[nodes.Node]:
		"""
		Parse a text for GitHub's references and emoji into docutils nodes, linking the references and writing emoji as
		:class:`~pyTooling.Sphinx.Node.Emoji` nodes.

		An emoji is written as its shortcode, e.g. ``:tada:``, or as its characters. A shortcode GitHub doesn't know
		stays text, as does a custom GitHub emoji, which has no characters, e.g. ``:octocat:``.

		:param text:        The text, without Markdown.
		:param references:  Optional, whether GitHub's references are linked; ``False`` e.g. for a link's text. Default:
		                    ``True``.
		:returns:           The text, references and emoji.
		:raises ValueError: If parameter ``text`` is ``None``.
		:raises TypeError:  If parameter ``text`` isn't of type :class:`str`.
		"""
		if text is None:
			raise ValueError("Parameter 'text' is None.")
		elif not isinstance(text, str):
			ex = TypeError("Parameter 'text' is not of type 'str'.")
			ex.add_note(f"Got type '{getFullyQualifiedName(text)}'.")
			raise ex

		result: list[nodes.Node] = []
		ownRepository = f"{self._owner}/{self._repository}"
		position = 0
		for match in REFERENCE_PATTERN.finditer(text):
			written = match[0]
			if (shortcode := match["shortcode"]) is not None:
				if (characters := self._emojis.get(shortcode)) is None:
					continue

				node: nodes.Node = Emoji(characters, characters, shortcode=shortcode)
			elif not references:
				continue
			elif (issue := match["issue"]) is not None:
				repository = ownRepository if match["issueRepository"] is None else match["issueRepository"]
				node = nodes.reference(
					written, written, refuri=f"{self._serverURL}/{repository}/issues/{issue}", classes=["github-issue"]
				)
			elif (sha := match["sha"]) is not None:
				if sha.isdigit() or not any(character.isdigit() for character in sha):
					continue

				repository = ownRepository if match["commitRepository"] is None else match["commitRepository"]
				node = nodes.reference(
					written, "", refuri=f"{self._serverURL}/{repository}/commit/{sha}", classes=["github-commit"]
				)
				if match["commitRepository"] is not None:
					node += nodes.Text(f"{repository}@")
				node += nodes.literal(sha[:7], sha[:7])
			else:
				node = nodes.reference(
					written, written, refuri=f"{self._serverURL}/{match['user']}", classes=["github-user"]
				)

			result.extend(self._ConvertEmojiCharacters(text[position:match.start()]))
			result.append(node)
			position = match.end()

		result.extend(self._ConvertEmojiCharacters(text[position:]))
		return result

	def _ConvertEmojiCharacters(self, text: str) -> list[nodes.Node]:
		"""
		Convert a text into text and :class:`~pyTooling.Sphinx.Node.Emoji` nodes for the emoji written as characters.

		:param text: The text.
		:returns:    The text and the emoji; nothing for an empty text.
		"""
		result: list[nodes.Node] = []
		position = 0
		for match in self._emojiPattern.finditer(text):
			if match.end() == match.start():
				continue

			if match.start() > position:
				result.append(nodes.Text(text[position:match.start()]))

			characters = match[0]
			result.append(Emoji(characters, characters, shortcode=self._shortcodes[characters.replace("\ufe0f", "")]))
			position = match.end()

		if position < len(text):
			result.append(nodes.Text(text[position:]))

		return result


@export
class RasterizeShieldsBadges(SphinxPostTransform):
	"""
	A post-transform fetching the shields.io badges of converted Markdown as PNG in LaTeX, which can't include SVG.

	A badge's URI is moved to :data:`~pyTooling.Sphinx.Shields.SHIELDS_SERVICE_PNG`, without a suffix ``.svg``. Every
	other SVG image is left to :mod:`sphinx.ext.imgconverter`, which pyTooling.Sphinx loads and which converts it with
	ImageMagick.
	"""

	default_priority = 50           #: Priority among the post-transforms: before Sphinx downloads remote images.
	formats =          ("latex", )  #: Output formats the transform runs for.

	def run(self, **kwargs: Any) -> None:
		"""
		Move the shields.io badges of converted Markdown to the service rasterizing them.

		The images of converted Markdown have class :data:`~pyTooling.Sphinx.Markdown.IMAGE_CLASS`.

		:param kwargs: Keyword arguments Sphinx passes to a post-transform; none is used.
		"""
		for image in self.document.findall(nodes.image):
			if IMAGE_CLASS not in image["classes"]:
				continue

			uri = urlsplit(image["uri"])
			if f"{uri.scheme}://{uri.netloc}" == SHIELDS_SERVICE_SVG:
				raster = urlsplit(SHIELDS_SERVICE_PNG)._replace(path=uri.path.removesuffix(".svg"), query=uri.query)
				image["uri"] =        raster.geturl()
				image["candidates"] = {"?": image["uri"]}
