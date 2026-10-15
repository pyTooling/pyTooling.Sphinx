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
Unit tests for the downloads of :mod:`pyTooling.Sphinx.ExternalLink`: the archive icon, and the size behind a download's
link.
"""
from http.server                   import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading                     import Thread
from time                          import sleep
from unittest.mock                 import patch

from pyTooling.Sphinx              import SphinxExtensionError
from pyTooling.Sphinx.ExternalLink import ARCHIVE_FORMATS, HOST_ICONS, AddDownloadSizes, LinkIcon, getArchiveExtension
from pyTooling.Sphinx.ExternalLink import checkExternalLinkConfiguration
from pyTooling.Testing             import Testcase, testsuite, testcase

from tests.unit.Extension          import Project


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("Archive detection")
class ArchiveDetection(Testcase):
	"""A link's target is an archive, if its path ends in an extension of ARCHIVE_FORMATS."""

	@testcase("Archives")
	def Archives(self) -> None:
		"""
		Every extension is found, in any case, in a local file name and in a URI; a query and a fragment are ignored.

		Looks up the extension of each target and checks it, and that it has a label.
		"""
		for uri, extension in (
			("pkg.zip",                                     "zip"),
			("pkg-1.0.tar.gz",                              "tar.gz"),
			("pkg-1.0.tgz",                                 "tgz"),
			("pkg-1.0.tar.bz2",                             "tar.bz2"),
			("pkg-1.0.tar.xz",                              "tar.xz"),
			("pkg-1.0.tar.zst",                             "tar.zst"),
			("pkg-1.0.7z",                                  "7z"),
			("files/Archive.ZIP",                           "zip"),
			("https://example.org/PKG-1.0.Tar.Gz",          "tar.gz"),
			("https://example.org/pkg.zip?raw=true",        "zip"),
			("https://example.org/pkg.tar.xz#sha256=00ff",  "tar.xz"),
		):
			with self.subTest(uri=uri):
				self.assertEqual(extension, getArchiveExtension(uri))
				self.assertIn(extension, ARCHIVE_FORMATS)

	@testcase("Other files")
	def OtherFiles(self) -> None:
		"""
		A path ending in another extension, in an archive's extension without a dot, or with a host named like an archive
		isn't an archive; neither is a query naming one.

		Looks up the extension of each target and checks it's empty.
		"""
		for uri in (
			"report.pdf",
			"pkg-1.0.gz",
			"pkg-1.0.tar",
			"pkg.zip.html",
			"https://example.org/zip",
			"https://example.zip/",
			"https://example.org/download?file=pkg.zip",
		):
			with self.subTest(uri=uri):
				self.assertEqual("", getArchiveExtension(uri))

	@testcase("Labels")
	def Labels(self) -> None:
		"""
		Both extensions of a gzip-compressed tar archive name the same format.

		Checks the labels of 'zip', 'tar.gz' and 'tgz'.
		"""
		self.assertEqual("ZIP", ARCHIVE_FORMATS["zip"])
		self.assertEqual("tar.gz", ARCHIVE_FORMATS["tar.gz"])
		self.assertEqual("tar.gz", ARCHIVE_FORMATS["tgz"])

	@testcase("Icon")
	def Icon(self) -> None:
		"""
		An archive gets the archive icon, whatever its host's icon; an e-mail address on a domain named like an archive
		stays an e-mail address.

		Chooses the icon for a GitHub release's asset, a GitLab archive, a host without icon, and two e-mail addresses.
		"""
		for uri, icon in (
			("https://github.com/pyTooling/pyTooling/releases/download/v1.0.0/pkg-1.0.0.zip", LinkIcon.Archive),
			("https://gitlab.com/group/project/-/archive/v1.0/project-v1.0.tar.gz",           LinkIcon.Archive),
			("https://example.org/pkg.7z",                                                    LinkIcon.Archive),
			("https://github.com/pyTooling/pyTooling/releases",                               LinkIcon.GitHub),
			("https://example.zip/",                                                          LinkIcon.External),
			("mailto:someone@example.zip",                                                    LinkIcon.Mail),
		):
			with self.subTest(uri=uri):
				self.assertIs(icon, LinkIcon.FromURI(uri, HOST_ICONS))


@testsuite("Download size format")
class SizeFormat(Testcase):
	"""A download's size, in binary units."""

	@testcase("Units")
	def Units(self) -> None:
		"""
		Bytes as integer below 1024, then kiB, MiB and GiB with one decimal; a value rounding to 1024 takes the next unit.

		Formats sizes at and around each unit's boundary and checks the text.
		"""
		for size, text in (
			(0,                  "0 B"),
			(1023,               "1023 B"),
			(1024,               "1.0 kiB"),
			(1536,               "1.5 kiB"),
			(1024 ** 2 - 52,     "1023.9 kiB"),
			(1024 ** 2 - 1,      "1.0 MiB"),
			(1024 ** 2,          "1.0 MiB"),
			(1234567,            "1.2 MiB"),
			(1024 ** 3 - 1,      "1.0 GiB"),
			(1024 ** 3,          "1.0 GiB"),
			(5 * 1024 ** 4,      "5120.0 GiB"),
		):
			with self.subTest(size=size):
				self.assertEqual(text, AddDownloadSizes._FormatSize(size))


@testsuite("Download size configuration")
class SizeConfiguration(Testcase):
	"""
	Reading the configuration values 'pyTooling_ExternalLink_DownloadSizes', '..._RemoteSizes' and
	'..._RemoteSizeTimeout'.
	"""

	@staticmethod
	def _Config(downloadSizes: object, remoteSizes: object, timeout: object) -> dict[str, object]:
		"""
		Return a configuration with the download size values given, and the defaults of the others.

		:param downloadSizes: Value of 'pyTooling_ExternalLink_DownloadSizes'.
		:param remoteSizes:   Value of 'pyTooling_ExternalLink_RemoteSizes'.
		:param timeout:       Value of 'pyTooling_ExternalLink_RemoteSizeTimeout'.
		:returns:             The configuration.
		"""
		return {
			"pyTooling_ExternalLink_Icons":             None,
			"pyTooling_ExternalLink_NewTab":            True,
			"pyTooling_ExternalLink_Hosts":             {},
			"pyTooling_ExternalLink_DownloadSizes":     downloadSizes,
			"pyTooling_ExternalLink_RemoteSizes":       remoteSizes,
			"pyTooling_ExternalLink_RemoteSizeTimeout": timeout,
		}

	@testcase("Values read")
	def Values(self) -> None:
		"""
		The patterns become a tuple, the timeout a float.

		Checks a configuration without sizes, with a list of patterns and an integer timeout.
		"""
		config = self._Config(False, ["https://github.com/pyTooling/*/releases/download/*"], 2)
		checkExternalLinkConfiguration(None, config)

		self.assertFalse(config["pyTooling_ExternalLink_DownloadSizes"])
		self.assertEqual(
			("https://github.com/pyTooling/*/releases/download/*", ), config["pyTooling_ExternalLink_RemoteSizes"]
		)
		self.assertIsInstance(config["pyTooling_ExternalLink_RemoteSizeTimeout"], float)
		self.assertEqual(2.0, config["pyTooling_ExternalLink_RemoteSizeTimeout"])

	@testcase("Errors")
	def Errors(self) -> None:
		"""
		A malformed value is rejected with a message naming the configuration value, and a note.

		Checks the message and the notes per malformed value.
		"""
		for downloadSizes, remoteSizes, timeout, name, error, notes in (
			("yes", [],       5.0,          "DownloadSizes",     "Value is not of type 'bool'.",      ["Got type 'str'."]),
			(True,  "*.zip",  5.0,          "RemoteSizes",       "Value is not a list.",              ["Got type 'str'."]),
			(True,  {"a": 1}, 5.0,          "RemoteSizes",       "Value is not a list.",              ["Got type 'dict'."]),
			(True,  [1],      5.0,          "RemoteSizes",       "Pattern '1' is not of type 'str'.", ["Got type 'int'."]),
			(True,  [""],     5.0,          "RemoteSizes",       "A pattern is empty.",               []),
			(True,  [],       "5",          "RemoteSizeTimeout", "Value is not of type 'float'.",     ["Got type 'str'."]),
			(True,  [],       True,         "RemoteSizeTimeout", "Value is not of type 'float'.",     ["Got type 'bool'."]),
			(True,  [],       0,            "RemoteSizeTimeout", "Value is not a positive, finite number.",
			 ["Got value '0'."]),
			(True,  [],       -1.0,         "RemoteSizeTimeout", "Value is not a positive, finite number.",
			 ["Got value '-1.0'."]),
			(True,  [],       float("inf"), "RemoteSizeTimeout", "Value is not a positive, finite number.",
			 ["Got value 'inf'."]),
			(True,  [],       float("nan"), "RemoteSizeTimeout", "Value is not a positive, finite number.",
			 ["Got value 'nan'."]),
		):
			with self.subTest(name=name, error=error, notes=notes):
				with self.assertRaises(SphinxExtensionError) as context:
					checkExternalLinkConfiguration(None, self._Config(downloadSizes, remoteSizes, timeout))

				self.assertEqual(f"conf.py: pyTooling_ExternalLink_{name}: {error}", str(context.exception))
				self.assertEqual(notes, getattr(context.exception, "__notes__", []))


@testsuite("Downloads in a document")
class Rendering(Project):
	"""The archive icon and the sizes of the downloads of the documentation, in a built page."""

	_document = (
		"Index\n#####\n\n"
		"* report :download:`report <report.pdf>`\n"
		"* zip :download:`Archive.ZIP`\n"
		"* sources :download:`sources <files/pkg-1.0.tar.gz>`\n"
		"* remote :download:`release <https://example.org/pkg-1.0.zip>`\n"
		"* explicit `release <https://github.com/pyTooling/pyTooling/releases/download/v1.0/pkg-1.0.tar.gz>`__\n"
	)

	def _buildDownloads(self, **config: object) -> str:
		"""
		Write three files of 1023, 1536 and 2048 bytes, and build the document.

		:param config: Configuration values overriding the defaults.
		:returns:      The page's HTML.
		"""
		(self._path / "src" / "files").mkdir()
		(self._path / "src" / "report.pdf").write_bytes(b"x" * 1023)
		(self._path / "src" / "Archive.ZIP").write_bytes(b"x" * 1536)
		(self._path / "src" / "files" / "pkg-1.0.tar.gz").write_bytes(b"x" * 2048)
		self._build(self._document, **config)

		return self._html("index")

	@testcase("Icons and sizes")
	def IconsAndSizes(self) -> None:
		"""
		A download link gets the download icon and its size; a link to an archive the archive icon, its format and size.

		A remote file without a pattern of 'pyTooling_ExternalLink_RemoteSizes' gets no size, and isn't asked for. Builds
		the document and checks every link's classes and the text behind it.
		"""
		html = self._buildDownloads()

		self.assertEqual([], self._warningLines())
		for link in (
			'<a class="pytooling-download-link pytooling-link-icon-download reference download internal" download="" '
			'href="_downloads/',
			'<span class="pre">report</span></code></a> <span class="pytooling-download-size">(1023 B)</span>',
			'<a class="pytooling-download-link pytooling-link-icon-archive pytooling-archive-zip reference download '
			'internal" download="" href="_downloads/',
			'<span class="pre">Archive.ZIP</span></code></a> <span class="pytooling-download-size">(ZIP, 1.5 kiB)</span>',
			'<a class="pytooling-download-link pytooling-link-icon-archive pytooling-archive-tar-gz reference download '
			'internal" download="" href="_downloads/',
			'<span class="pre">sources</span></code></a> <span class="pytooling-download-size">(tar.gz, 2.0 kiB)</span>',
			'<a class="pytooling-download-link pytooling-link-icon-archive pytooling-archive-zip reference download '
			'external" download="" href="https://example.org/pkg-1.0.zip"><code class="xref download docutils literal '
			'notranslate"><span class="pre">release</span></code></a></p></li>',
			'<a class="pytooling-external-link pytooling-link-icon-archive pytooling-archive-tar-gz reference external" '
			'href="https://github.com/pyTooling/pyTooling/releases/download/v1.0/pkg-1.0.tar.gz" rel="noopener noreferrer" '
			'target="_blank">release</a></p></li>',
		):
			with self.subTest(link=link):
				self.assertIn(link, html)

		self.assertEqual(3, html.count("pytooling-download-size"))

	@testcase("Sizes off")
	def SizesOff(self) -> None:
		"""
		With 'pyTooling_ExternalLink_DownloadSizes' set to False, no download gets a size; the icons stay.

		Builds the document and checks no size is on the page.
		"""
		html = self._buildDownloads(pyTooling_ExternalLink_DownloadSizes=False)

		self.assertEqual([], self._warningLines())
		self.assertNotIn("pytooling-download-size", html)
		self.assertIn("pytooling-link-icon-archive", html)

	@testcase("Sizes without icons")
	def SizesWithoutIcons(self) -> None:
		"""
		With 'pyTooling_ExternalLink_Icons' set to 'none', the downloads keep their sizes.

		Builds the document and checks no link is marked, and the sizes are on the page.
		"""
		html = self._buildDownloads(pyTooling_ExternalLink_Icons="none")

		self.assertEqual([], self._warningLines())
		self.assertNotIn("pytooling-link-icon", html)
		self.assertNotIn("pytooling-archive", html)
		self.assertIn('</a> <span class="pytooling-download-size">(ZIP, 1.5 kiB)</span>', html)

	@testcase("Missing file")
	def MissingFile(self) -> None:
		"""
		A file Sphinx doesn't find gets no size, and only Sphinx' own warning.

		Builds a document with a download of a file that doesn't exist, and checks the warning and the page.
		"""
		self._build("Index\n#####\n\n:download:`missing.zip`\n")

		warnings = self._warningLines()
		self.assertEqual(1, len(warnings))
		self.assertIn("download file not readable", warnings[0])
		self.assertNotIn("pytooling-download-size", self._html("index"))

	@testcase("Theme's download glyph")
	def ThemeGlyph(self) -> None:
		"""
		The stylesheet replaces sphinx_rtd_theme's glyph before a marked download link's text, and writes the text as any
		link's.

		Builds an empty project and checks the stylesheet's rules for the first <span> of a marked download link.
		"""
		self._build("Index\n#####\n")

		stylesheet = next((self._path / "build" / "html" / "_static").glob("pyTooling.*.css")).read_text(encoding="utf-8")
		self.assertIn(
			"a.pytooling-download-link code.download span:first-child::before {\n  content: none;\n", stylesheet
		)
		self.assertIn(
			"a.pytooling-download-link code.download span:first-child {\n  display: inline;\n  margin: 0;\n"
			"  font: inherit;\n",
			stylesheet
		)

	@testcase("Parallel build")
	def Parallel(self) -> None:
		"""
		In a parallel build, the documents are post-transformed in the main process, so a remote file is asked for once.

		Builds seven documents with two processes, with the request replaced by a mock. Sphinx writes the first document,
		'doc0', before it starts the processes, so only the others link the remote file. Checks every page's size and the
		requests.
		"""
		uri = "https://example.org/pkg.zip"
		documents = {"doc0": "Document 0\n##########\n"}
		for number in range(1, 6):
			documents[f"doc{number}"] = f"Document {number}\n##########\n\n:download:`{uri}`\n"

		with patch.object(AddDownloadSizes, "_RequestSize", return_value=1536) as requestSize:
			self._build(
				f"Index\n#####\n\n:download:`{uri}`\n",
				documents=documents,
				parallel=2,
				pyTooling_ExternalLink_RemoteSizes=[uri]
			)

		self.assertEqual([], self._warningLines())
		for name in ("index", "doc1", "doc2", "doc3", "doc4", "doc5"):
			with self.subTest(name=name):
				self.assertIn('<span class="pytooling-download-size">(ZIP, 1.5 kiB)</span>', self._html(name))

		requestSize.assert_called_once_with(uri, 5.0)


class Server(ThreadingHTTPServer):
	"""A local HTTP server answering HEAD requests, which records each request's path."""

	daemon_threads = True  #: A slow answer doesn't hold the server's shutdown.
	requests: list[str]    #: The requested paths, in order.


class Handler(BaseHTTPRequestHandler):
	"""Answer a HEAD request per path: a size, a redirection, no size, a slow answer, or 404."""

	server: Server

	def do_HEAD(self) -> None:
		"""
		Answer a HEAD request.
		"""
		self.server.requests.append(self.path)
		if self.path == "/pkg.zip":
			self.send_response(200)
			self.send_header("Content-Length", "1536")
		elif self.path == "/redirect.tar.gz":
			self.send_response(302)
			self.send_header("Location", "/pkg-2.0.tar.gz")
		elif self.path == "/pkg-2.0.tar.gz":
			self.send_response(200)
			self.send_header("Content-Length", f"{3 * 1024 ** 2}")
		elif self.path == "/nolength.zip":
			self.send_response(200)
		elif self.path == "/slow.zip":
			sleep(1.0)
			self.send_response(200)
			self.send_header("Content-Length", "1")
		else:
			self.send_response(404)

		self.end_headers()

	def log_message(self, format: str, *args: object) -> None:
		"""
		Write no log.

		:param format: Format of the log message.
		:param args:   Values of the log message.
		"""


@testsuite("Remote download sizes")
class RemoteSizes(Project):
	"""The sizes of other sites' files, asked from a local HTTP server."""

	_server: Server
	_thread: Thread
	_base:   str

	def setUp(self) -> None:
		super().setUp()
		self._server = Server(("127.0.0.1", 0), Handler)
		self._server.requests = []
		self._thread = Thread(target=self._server.serve_forever, daemon=True)
		self._thread.start()
		self._base = f"http://127.0.0.1:{self._server.server_address[1]}"

		environment = patch.dict("os.environ", {"no_proxy": "127.0.0.1", "NO_PROXY": "127.0.0.1"})
		environment.start()
		self.addCleanup(environment.stop)

	def tearDown(self) -> None:
		self._server.shutdown()
		self._server.server_close()
		self._thread.join()
		super().tearDown()

	@testcase("Sizes")
	def Sizes(self) -> None:
		"""
		A remote file matching a pattern gets its size, also through a redirection; each URI is asked once.

		A link written with its URI gets a size if it targets an archive. A file matching no pattern isn't asked for.
		Builds a document with two links to the same file, a redirected archive and a file without pattern, and checks
		the sizes and the requests.
		"""
		self._build(
			"Index\n#####\n\n"
			f"* :download:`first <{self._base}/pkg.zip>`\n"
			f"* :download:`second <{self._base}/pkg.zip>`\n"
			f"* `redirected <{self._base}/redirect.tar.gz>`__\n"
			f"* :download:`other <{self._base}/other.zip>`\n",
			pyTooling_ExternalLink_RemoteSizes=[f"{self._base}/pkg.*", f"{self._base}/redirect.*"]
		)

		self.assertEqual([], self._warningLines())
		html = self._html("index")
		for name in ("first", "second"):
			with self.subTest(name=name):
				self.assertIn(
					f'<span class="pre">{name}</span></code></a> <span class="pytooling-download-size">(ZIP, 1.5 kiB)</span>',
					html
				)

		self.assertIn('>redirected</a> <span class="pytooling-download-size">(tar.gz, 3.0 MiB)</span>', html)
		self.assertIn('<span class="pre">other</span></code></a></p></li>', html)
		self.assertEqual(["/pkg.zip", "/redirect.tar.gz", "/pkg-2.0.tar.gz"], self._server.requests)

	@testcase("No pattern")
	def NoPattern(self) -> None:
		"""
		By default, no remote file is asked for.

		Builds a document with a remote download and checks there was no request and no size.
		"""
		self._build(f"Index\n#####\n\n:download:`release <{self._base}/pkg.zip>`\n")

		self.assertEqual([], self._warningLines())
		self.assertEqual([], self._server.requests)
		self.assertNotIn("pytooling-download-size", self._html("index"))

	@testcase("Unknown sizes")
	def Unknown(self) -> None:
		"""
		An answer without size, an HTTP error, and no answer within the timeout leave the link without size, and warn.

		Builds a document with three such downloads and a timeout of 0.1 seconds, and checks the warnings and the page.
		"""
		self._build(
			"Index\n#####\n\n"
			f"* :download:`no length <{self._base}/nolength.zip>`\n"
			f"* :download:`missing <{self._base}/missing.zip>`\n"
			f"* :download:`slow <{self._base}/slow.zip>`\n",
			pyTooling_ExternalLink_RemoteSizes=[f"{self._base}/*"],
			pyTooling_ExternalLink_RemoteSizeTimeout=0.1
		)

		self.assertEqual(
			[
				f"src/index.rst:4: WARNING: size of download '{self._base}/nolength.zip' unknown: the answer has no "
				f"'Content-Length' [pyTooling.download_size]",
				f"src/index.rst:5: WARNING: size of download '{self._base}/missing.zip' unknown: the server answered 404 Not "
				f"Found [pyTooling.download_size]",
				f"src/index.rst:6: WARNING: size of download '{self._base}/slow.zip' unknown: no answer within 0.1 seconds "
				f"[pyTooling.download_size]",
			],
			self._warningLines()
		)
		self.assertNotIn("pytooling-download-size", self._html("index"))

	@testcase("Suppressed warnings")
	def Suppressed(self) -> None:
		"""
		The warning's type lets a project suppress it.

		Builds a document with a download without size, with 'pyTooling.download_size' in 'suppress_warnings', and checks
		there is no warning.
		"""
		self._build(
			f"Index\n#####\n\n:download:`no length <{self._base}/nolength.zip>`\n",
			pyTooling_ExternalLink_RemoteSizes=[f"{self._base}/*"],
			suppress_warnings=["pyTooling.download_size"]
		)

		self.assertEqual([], self._warningLines())
		self.assertEqual(["/nolength.zip"], self._server.requests)
