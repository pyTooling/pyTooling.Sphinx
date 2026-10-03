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
Unit tests for :mod:`pyTooling.Sphinx.DependencyTable`: the entrypoints, the version constraints and formats, and the
report of unresolved licenses.
"""
from pathlib                          import Path
from sys                              import platform as sys_platform
from tempfile                         import TemporaryDirectory
from textwrap                         import dedent
from typing                           import Optional as Nullable

from packaging.specifiers             import SpecifierSet
from pytest                           import mark

from pyTooling.Sphinx                 import SphinxExtensionError
from pyTooling.Sphinx.DependencyTable import DependencyFormat, DependencyTable, VersionFormat, formatUnresolvedLicenses
from pyTooling.Sphinx.DependencyTable import readEntrypoints
from pyTooling.Testing                import Testcase, testsuite, testcase


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("Dependency entrypoints")
class Entrypoints(Testcase):
	"""``pyTooling_Dependency_Requirements`` is read while :file:`conf.py` is processed, so its errors end the build."""

	@staticmethod
	def _write(directory: Path, name: str, content: str) -> Path:
		path = directory / name
		path.write_text(dedent(content).lstrip(), encoding="utf-8")

		return path

	@testcase("Requirements file")
	def File(self) -> None:
		"""
		A file entrypoint is read when the configuration is read, not when a table is built.

		Writes a requirements file of two packages, reads the entrypoint, and checks both requirements and the file path
		are known right away.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "requirements.txt", """
				pytest ~= 9.1
				colorama ~= 0.4.6
			""")

			entrypoints = readEntrypoints({"unittest": {"file": "requirements.txt"}}, root)

		self.assertEqual({"colorama", "pytest"}, set(entrypoints["unittest"].Requirements))
		self.assertEqual((root / "requirements.txt",), entrypoints["unittest"].Files)

	@testcase("Included requirements file")
	def File_Included(self) -> None:
		"""
		A file included with '-r' is listed with the file including it.

		Writes a file including 'base.txt', reads the entrypoint, and checks both paths are listed, the including one
		first.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "base.txt", "colorama ~= 0.4.6\n")
			self._write(root, "requirements.txt", """
				-r base.txt
				pytest ~= 9.1
			""")

			entrypoints = readEntrypoints({"unittest": {"file": "requirements.txt"}}, root)

		self.assertEqual([root / "requirements.txt", root / "base.txt"], list(entrypoints["unittest"].Files))

	@testcase("Path spelled one way")
	@mark.skipif(sys_platform == "win32", reason="Creating a symbolic link needs a privilege Windows doesn't grant.")
	def File_SymbolicLink(self) -> None:
		"""
		A file and its includes are listed under one spelling of their directory.

		Reads the entrypoint through a symbolic link to the directory, as macOS' '/var' and Windows' short names hand a
		build, and checks both files are listed under the real path. Skipped on Windows, where a link needs a privilege.
		"""
		with TemporaryDirectory() as directory:
			real = Path(directory).resolve() / "real"
			real.mkdir()
			self._write(real, "base.txt", "colorama ~= 0.4.6\n")
			self._write(real, "requirements.txt", """
				-r base.txt
				pytest ~= 9.1
			""")

			link = Path(directory).resolve() / "link"
			link.symlink_to(real)

			files = readEntrypoints({"unittest": {"file": "requirements.txt"}}, link)["unittest"].Files

		self.assertEqual([real / "requirements.txt", real / "base.txt"], list(files))

	@testcase("Package entrypoint")
	def Package(self) -> None:
		"""
		A package entrypoint keeps its name and extra and is resolved later.

		Reads 'pyTooling[yaml]' and checks the package is ('pyTooling', 'yaml') and no requirements are known yet.
		"""
		entrypoints = readEntrypoints({"yaml": {"package": "pyTooling[yaml]"}}, Path("."))

		self.assertEqual((("pyTooling", "yaml"),), entrypoints["yaml"].Packages)
		self.assertIsNone(entrypoints["yaml"].Requirements)

	@testcase("Package without extra")
	def Package_WithoutExtra(self) -> None:
		"""
		A package without an extra has None as its extra.

		Reads 'pyTooling' and checks the package is ('pyTooling', None).
		"""
		entrypoints = readEntrypoints({"package": {"package": "pyTooling"}}, Path("."))

		self.assertEqual((("pyTooling", None),), entrypoints["package"].Packages)

	@testcase("Several packages")
	def Packages(self) -> None:
		"""
		The plural field 'packages' declares several packages.

		Reads a tuple of two packages and a list of one, and checks both declarations.
		"""
		entrypoints = readEntrypoints({
			"tuple": {"packages": ("pyTooling[yaml]", "pyTooling[terminal]")},
			"list":  {"packages": ["pyTooling", ]}
		}, Path("."))

		self.assertEqual((("pyTooling", "yaml"), ("pyTooling", "terminal")), entrypoints["tuple"].Packages)
		self.assertEqual((("pyTooling", None),), entrypoints["list"].Packages)

	@testcase("Packages from any iterable")
	def Packages_Iterable(self) -> None:
		"""
		The plural field takes any iterable, not only a tuple or list.

		Reads the packages from a generator and from a set, and checks both declarations.
		"""
		entrypoints = readEntrypoints({
			"generator": {"packages": (name for name in ("pyTooling[yaml]", "pyTooling[terminal]"))},
			"set":       {"packages": {"pyTooling"}}
		}, Path("."))

		self.assertEqual((("pyTooling", "yaml"), ("pyTooling", "terminal")), entrypoints["generator"].Packages)
		self.assertEqual((("pyTooling", None),), entrypoints["set"].Packages)

	@testcase("Several files")
	def Files(self) -> None:
		"""
		The plural field 'files' reads several files in order; a later statement wins.

		Writes two files constraining 'pytest' differently, reads both, and checks the union of packages, the second
		file's constraint and the order of the paths.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "first.txt", "pytest ~= 8.0\ncolorama ~= 0.4.6\n")
			self._write(root, "second.txt", "pytest ~= 9.1\n")

			entrypoints = readEntrypoints({"both": {"files": ["first.txt", "second.txt"]}}, root)

		requirements = entrypoints["both"].Requirements
		self.assertEqual({"colorama", "pytest"}, set(requirements))
		self.assertEqual("~=9.1", str(requirements["pytest"].specifier))
		self.assertEqual([root / "first.txt", root / "second.txt"], list(entrypoints["both"].Files))

	@testcase("Plural field with a string")
	def Files_String(self) -> None:
		"""
		The plural field rejects a bare string, which would otherwise be read as one path per character.

		Declares 'files' as a string and checks the error suggests 'file'.
		"""
		with self.assertRaises(SphinxExtensionError) as exceptionCapture:
			readEntrypoints({"unittest": {"files": "requirements.txt"}}, Path("."))

		self.assertIn("Use 'file'", str(exceptionCapture.exception))

	@testcase("Singular field with a list")
	def File_Iterable(self) -> None:
		"""
		The singular field rejects an iterable.

		Declares 'file' as a list and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": {"file": ["requirements.txt"]}}, Path("."))

	@testcase("Missing requirements file")
	def File_Missing(self) -> None:
		"""
		A missing file is reported with the entrypoint's identifier.

		Declares a file that doesn't exist and checks the error names '[unittest]'.
		"""
		with TemporaryDirectory() as directory:
			with self.assertRaises(SphinxExtensionError) as exceptionCapture:
				readEntrypoints({"unittest": {"file": "nothing.txt"}}, Path(directory))

		self.assertIn("[unittest]", str(exceptionCapture.exception))

	@testcase("Neither file nor package")
	def NoField(self) -> None:
		"""
		A declaration without a field is rejected.

		Declares an empty dictionary and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": {}}, Path("."))

	@testcase("Both file and package")
	def FileAndPackage(self) -> None:
		"""
		A declaration with a file and a package is rejected.

		Declares both fields and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": {"file": "requirements.txt", "package": "pyTooling"}}, Path("."))

	@testcase("Singular and plural field")
	def FileAndFiles(self) -> None:
		"""
		A declaration with a singular field and its plural is rejected.

		Declares 'file' and 'files' and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": {"file": "a.txt", "files": ["b.txt"]}}, Path("."))

	@testcase("Unknown field")
	def UnknownField(self) -> None:
		"""
		A misspelt field is reported, not ignored.

		Declares the misspelt field 'fiel' and checks the error names it as unknown.
		"""
		with self.assertRaises(SphinxExtensionError) as exceptionCapture:
			readEntrypoints({"unittest": {"files": "requirements.txt"}}, Path("."))

		self.assertIn("files", str(exceptionCapture.exception))

	@testcase("Declaration not a dictionary")
	def Declaration_NoDictionary(self) -> None:
		"""
		A declaration that is no dictionary is rejected.

		Declares an entrypoint as a string and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": "requirements.txt"}, Path("."))

	@testcase("Configuration not a dictionary")
	def Configuration_NoDictionary(self) -> None:
		"""
		A configuration value that is no dictionary is rejected.

		Passes a list as the configuration and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints(["requirements.txt"], Path("."))


@testsuite("Version constraints")
class VersionConstraints(Testcase):
	"""A dependency table prints a constraint for a reader, not for an installer."""

	@staticmethod
	def _format(specifier: str, simplify: bool = True, versionFormat: Nullable["VersionFormat"] = None) -> str:
		if versionFormat is None:
			versionFormat = VersionFormat.All

		return DependencyTable._FormatSpecifier(SpecifierSet(specifier), simplify, versionFormat)

	@testcase("No constraint")
	def Any(self) -> None:
		"""
		A requirement without a constraint is printed as 'any'.

		Formats an empty specifier set.
		"""
		self.assertEqual("any", self._format(""))

	@testcase("Operator symbols")
	def Operators(self) -> None:
		"""
		Comparison operators are printed as their typographic symbols.

		Formats '>=', '<=', '!=' and '==' and checks '≥', '≤', '≠' and '='.
		"""
		self.assertEqual("≥3.12", self._format(">=3.12"))
		self.assertEqual("≤2.0", self._format("<=2.0", simplify=False))
		self.assertEqual("≠2.0", self._format("!=2.0", simplify=False))
		self.assertEqual("=1.2.3", self._format("==1.2.3"))

	@testcase("Compatible release")
	def CompatibleRelease(self) -> None:
		"""
		A compatible release '~=' is printed as its lower bound.

		Formats '~=0.4.6' and checks '≥0.4.6'.
		"""
		self.assertEqual("≥0.4.6", self._format("~=0.4.6"))

	@testcase("Upper bound dropped")
	def UpperBound(self) -> None:
		"""
		Simplifying drops an upper bound next to a lower bound.

		Formats '<4.0,>=3.0' and checks '≥3.0'.
		"""
		self.assertEqual("≥3.0", self._format("<4.0,>=3.0"))

	@testcase("Exclusion dropped")
	def Exclusion(self) -> None:
		"""
		Simplifying drops an excluded version.

		Formats '!=2.0,>=1.0' and checks '≥1.0'.
		"""
		self.assertEqual("≥1.0", self._format("!=2.0,>=1.0"))

	@testcase("Upper bound alone")
	def UpperBound_Alone(self) -> None:
		"""
		An upper bound without a lower bound is kept.

		Formats '<4.0' and checks it isn't simplified away.
		"""
		self.assertEqual("<4.0", self._format("<4.0"))

	@testcase("Full constraint")
	def Full(self) -> None:
		"""
		Without simplifying, every part of a constraint is printed.

		Formats '<4.0,>=3.0' and '~=0.4.6' unsimplified and checks both parts and the '~=' are kept.
		"""
		self.assertEqual("≥3.0, <4.0", self._format("<4.0,>=3.0", simplify=False))
		self.assertEqual("~=0.4.6", self._format("~=0.4.6", simplify=False))


@testsuite("Version formats")
class VersionFormats(Testcase):
	"""A dependency table prints as much of a version as a reader needs, which is rarely all of it."""

	@staticmethod
	def _format(specifier: str, versionFormat: "VersionFormat") -> str:
		return DependencyTable._FormatSpecifier(SpecifierSet(specifier), True, versionFormat)

	@testcase("Default version format")
	def Default(self) -> None:
		"""
		The default version format is 'MajorMinor'.

		Compares DEFAULT_VERSION_FORMAT with the enumeration member.
		"""
		from pyTooling.Sphinx.DependencyTable import DEFAULT_VERSION_FORMAT

		self.assertIs(VersionFormat.MajorMinor, DEFAULT_VERSION_FORMAT)

	@testcase("Version parts per format")
	def Formats(self) -> None:
		"""
		Each version format keeps its number of parts.

		Formats '~=0.4.6' with every format and checks '≥0', '≥0.4' and twice '≥0.4.6'.
		"""
		self.assertEqual("≥0", self._format("~=0.4.6", VersionFormat.Major))
		self.assertEqual("≥0.4", self._format("~=0.4.6", VersionFormat.MajorMinor))
		self.assertEqual("≥0.4.6", self._format("~=0.4.6", VersionFormat.MajorMinorPatch))
		self.assertEqual("≥0.4.6", self._format("~=0.4.6", VersionFormat.All))

	@testcase("All parts")
	def All(self) -> None:
		"""
		'All' keeps the pre- and dev-release parts the other formats drop.

		Formats '==9.1.2.dev3' with 'All' and with 'MajorMinorPatch'.
		"""
		self.assertEqual("=9.1.2.dev3", self._format("==9.1.2.dev3", VersionFormat.All))
		self.assertEqual("=9.1.2", self._format("==9.1.2.dev3", VersionFormat.MajorMinorPatch))

	@testcase("Short version not padded")
	def ShortVersion(self) -> None:
		"""
		A version shorter than the format isn't padded with zeros.

		Formats '>=9' with 'MajorMinorPatch' and checks '≥9'.
		"""
		self.assertEqual("≥9", self._format(">=9", VersionFormat.MajorMinorPatch))

	@testcase("No duplicate statements")
	def Duplicates(self) -> None:
		"""
		Two constraints that become equal when shortened are printed once.

		Formats '>=1.2.3,>=1.2.9' with 'MajorMinor' and checks '≥1.2'.
		"""
		self.assertEqual("≥1.2", self._format(">=1.2.3,>=1.2.9", VersionFormat.MajorMinor))


@testsuite("Dependency formats")
class DependencyFormats(Testcase):
	"""What a line of a dependency tree states is the document's choice."""

	@testcase("Default dependency format")
	def Default(self) -> None:
		"""
		The default dependency format states package, version and license.

		Compares DEFAULT_DEPENDENCY_FORMAT with the enumeration member.
		"""
		from pyTooling.Sphinx.DependencyTable import DEFAULT_DEPENDENCY_FORMAT

		self.assertIs(DependencyFormat.PackageVersionLicense, DEFAULT_DEPENDENCY_FORMAT)

	@testcase("Content per format")
	def Formats(self) -> None:
		"""
		Each dependency format says whether it shows the version and the license.

		Checks 'ShowsVersion' and 'ShowsLicense' of all four members.
		"""
		self.assertEqual(
			[(False, False), (True, False), (False, True), (True, True)],
			[(member.ShowsVersion, member.ShowsLicense) for member in DependencyFormat]
		)

	@testcase("Spelling of members")
	def Spelling(self) -> None:
		"""
		A member is written as it is spelled in a document.

		Converts members of DependencyFormat and VersionFormat to strings and checks their names.
		"""
		self.assertEqual("PackageVersionLicense", str(DependencyFormat.PackageVersionLicense))
		self.assertEqual("MajorMinor", str(VersionFormat.MajorMinor))


@testsuite("Unresolved license report")
class UnresolvedLicenseReport(Testcase):
	"""A package needing a license override is reported with what the index published, because that is the reason."""

	@testcase("One package")
	def Package(self) -> None:
		"""
		The report of one package names the package and what the index published.

		Formats one package with a 'license' field and checks the count, the field and the package's name.
		"""
		message = formatUnresolvedLicenses({"multidict": ("license: Apache License 2.0",)})

		self.assertIn("1 package(s) need a license override", message)
		self.assertIn("license: Apache License 2.0", message)
		self.assertIn("multidict", message)

	@testcase("Packages grouped by reason")
	def Group(self) -> None:
		"""
		Packages with the same published information are reported as one group.

		Formats three packages sharing a classifier and checks the classifier appears once, followed by the packages.
		"""
		classifier = "classifier: License :: OSI Approved :: BSD License"
		message = formatUnresolvedLicenses({"Jinja2": (classifier,), "alabaster": (classifier,), "colorama": (classifier,)})

		self.assertEqual(1, message.count(classifier))
		self.assertIn("Jinja2, alabaster, colorama", message)

	@testcase("Biggest group first")
	def Group_Order(self) -> None:
		"""
		The group with the most packages comes first.

		Formats a group of two packages and a single one and checks the order of the lines.
		"""
		classifier = "classifier: License :: OSI Approved :: BSD License"
		message = formatUnresolvedLicenses({
			"multidict": ("license: Apache License 2.0",),
			"Jinja2":    (classifier,),
			"alabaster": (classifier,),
		})
		lines = message.splitlines()

		self.assertEqual(f"  {classifier}", lines[1])
		self.assertEqual("    Jinja2, alabaster", lines[2])
		self.assertEqual("  license: Apache License 2.0", lines[3])

	@testcase("No license information")
	def NoInformation(self) -> None:
		"""
		A package without any published license information says so.

		Formats a package with no fields and checks the message.
		"""
		message = formatUnresolvedLicenses({"mystery": ()})

		self.assertIn("the index published no license information", message)

	@testcase("Several published fields")
	def Fields(self) -> None:
		"""
		Several published fields of one package are joined into one reason.

		Formats a package with a 'license' field and a classifier and checks both, separated by ';'.
		"""
		message = formatUnresolvedLicenses({
			"sphinxcontrib-jsmath": ("license: BSD", "classifier: License :: OSI Approved :: BSD License")
		})

		self.assertIn("license: BSD; classifier: License :: OSI Approved :: BSD License", message)
