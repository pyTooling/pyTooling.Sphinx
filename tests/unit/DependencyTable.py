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
from sys                              import intern as sys_intern, platform as sys_platform
from tempfile                         import TemporaryDirectory
from textwrap                         import dedent
from types                            import SimpleNamespace
from typing                           import Optional as Nullable
from unittest.mock                    import patch

from docutils                         import nodes
from docutils.utils                   import new_document
from packaging.requirements           import Requirement
from packaging.specifiers             import SpecifierSet
from pytest                           import mark

from pyTooling.Dependency             import BrokenRequirementWarning, UnknownLicenseWarning, UnsupportedVersionWarning
from pyTooling.Dependency.Python      import LicenseOverrides
from pyTooling.Dependency.Resolver    import ResolutionStatus
from pyTooling.Exceptions             import MissingDependencyError
from pyTooling.Versioning             import SemanticVersion
from pyTooling.Sphinx                 import SphinxExtensionError
from pyTooling.Sphinx.DependencyTable import DependencyFormat, DependencyTable, VersionFormat, \
                                             formatUnresolvedLicenses, DependencyCollector, prepareEntrypoints, \
                                             readEntrypoints, DuplicateFormat, DuplicateMatch, \
                                             ReplaceFoldedDependencies, DEFAULT_DEPENDENCY_FORMAT, \
                                             DEFAULT_VERSION_FORMAT, _COLLECTORS, _MergeRequirements
from pyTooling.Sphinx.Node            import FoldedDependencies
from pyTooling.Testing                import Testcase, testsuite, testcase


#: Name of the logger :mod:`pyTooling.Sphinx.DependencyTable` reports through, as Sphinx prefixes it.
LOGGER_NAME = "sphinx.pyTooling.Sphinx.DependencyTable"


if __name__ == "__main__":  # pragma: no cover
	print("ERROR: you called a testcase declaration file as an executable module.")
	print("Use: 'python -m unittest <testcase module>'")
	exit(1)


@testsuite("License override file")
class PackageOverrides(Testcase):
	"""``pyTooling_Dependency_PackageOverrides`` is read while :file:`conf.py` is processed; its errors end the build."""

	@testcase("YAML extra missing")
	def YAMLExtraMissing(self) -> None:
		"""
		An override file without pyTooling's 'yaml' extra ends the build with a message naming the extra.

		Lets reading the override file raise the MissingDependencyError pyTooling raises without ruamel.yaml and checks the
		SphinxExtensionError's message and cause.
		"""
		sphinx = SimpleNamespace(confdir=".")
		config = SimpleNamespace(
			pyTooling_Dependency_Requirements={"unittest": {"file": "requirements.txt"}},
			pyTooling_Dependency_PackageOverrides="Dependency.PackageOverrides.yaml"
		)
		missing = MissingDependencyError(dependency="ruamel.yaml", extra="yaml")

		with patch.object(LicenseOverrides, "FromFile", side_effect=missing):
			with self.assertRaises(SphinxExtensionError) as context:
				prepareEntrypoints(sphinx, config)

		self.assertEqual(
			"conf.py: pyTooling_Dependency_PackageOverrides: Reading the override file needs the 'yaml' extra: "
			"pip install pyTooling[yaml]",
			str(context.exception)
		)
		self.assertIs(missing, context.exception.__cause__)


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

			entrypoints = readEntrypoints({"unittest": {"file": "requirements.txt"}}, root, root)

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

			entrypoints = readEntrypoints({"unittest": {"file": "requirements.txt"}}, root, root)

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

			files = readEntrypoints({"unittest": {"file": "requirements.txt"}}, link, link)["unittest"].Files

		self.assertEqual([real / "requirements.txt", real / "base.txt"], list(files))

	@testcase("Broken requirement line")
	def File_BrokenRequirement(self) -> None:
		"""
		A line that can't be parsed is reported as a Sphinx warning; the other requirements are read.

		Writes a file of two packages with a broken line between them, reads the entrypoint, and checks the warning
		names the entrypoint, the file and the line, and both packages are known.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "requirements.txt", """
				pytest ~= 9.1
				not a requirement
				colorama ~= 0.4.6
			""")

			with self.assertLogs(LOGGER_NAME, level="WARNING") as logCapture:
				entrypoints = readEntrypoints({"unittest": {"file": "requirements.txt"}}, root, root)

		self.assertEqual(1, len(logCapture.records))
		message = logCapture.records[0].getMessage()
		self.assertIn("[unittest].file:", message)
		self.assertIn(f"Requirement 'not a requirement' in '{root / 'requirements.txt'}' line 2", message)
		self.assertEqual({"colorama", "pytest"}, set(entrypoints["unittest"].Requirements))

	@testcase("Broken requirement line in an included file")
	def File_Included_BrokenRequirement(self) -> None:
		"""
		A broken line in a file included with '-r' is reported with the included file's path.

		Writes 'base.txt' with a broken line, includes it, and checks the warning names 'base.txt' and the package
		before the broken line is known.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "base.txt", "colorama ~= 0.4.6\nnot a requirement\n")
			self._write(root, "requirements.txt", """
				-r base.txt
				pytest ~= 9.1
			""")

			with self.assertLogs(LOGGER_NAME, level="WARNING") as logCapture:
				entrypoints = readEntrypoints({"unittest": {"file": "requirements.txt"}}, root, root)

		self.assertEqual(1, len(logCapture.records))
		self.assertIn(f"in '{root / 'base.txt'}' line 2", logCapture.records[0].getMessage())
		self.assertEqual({"colorama", "pytest"}, set(entrypoints["unittest"].Requirements))

	@testcase("Package entrypoint")
	def Package(self) -> None:
		"""
		A package entrypoint keeps its name and extra and is resolved later.

		Reads 'pyTooling[yaml]' and checks the package is ('pyTooling', 'yaml') and no requirements are known yet.
		"""
		entrypoints = readEntrypoints({"yaml": {"package": "pyTooling[yaml]"}}, Path("."), Path("."))

		self.assertEqual((("pyTooling", "yaml"),), entrypoints["yaml"].Packages)
		self.assertIsNone(entrypoints["yaml"].Requirements)

	@testcase("Package without extra")
	def Package_WithoutExtra(self) -> None:
		"""
		A package without an extra has None as its extra.

		Reads 'pyTooling' and checks the package is ('pyTooling', None).
		"""
		entrypoints = readEntrypoints({"package": {"package": "pyTooling"}}, Path("."), Path("."))

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
		}, Path("."), Path("."))

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
		}, Path("."), Path("."))

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

			entrypoints = readEntrypoints({"both": {"files": ["first.txt", "second.txt"]}}, root, root)

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
			readEntrypoints({"unittest": {"files": "requirements.txt"}}, Path("."), Path("."))

		self.assertIn("Use 'file'", str(exceptionCapture.exception))

	@testcase("Singular field with a list")
	def File_Iterable(self) -> None:
		"""
		The singular field rejects an iterable.

		Declares 'file' as a list and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": {"file": ["requirements.txt"]}}, Path("."), Path("."))

	@testcase("Missing requirements file")
	def File_Missing(self) -> None:
		"""
		A missing file is reported with the entrypoint's identifier.

		Declares a file that doesn't exist and checks the error names '[unittest]'.
		"""
		with TemporaryDirectory() as directory:
			with self.assertRaises(SphinxExtensionError) as exceptionCapture:
				readEntrypoints({"unittest": {"file": "nothing.txt"}}, Path(directory), Path(directory))

		self.assertIn("[unittest]", str(exceptionCapture.exception))

	@testcase("pyproject.toml file")
	def PyProject(self) -> None:
		"""
		A pyproject entrypoint is read when the configuration is read: the build requirements and the file path.

		Writes a 'pyproject.toml' file with two build requirements, reads the entrypoint, and checks both requirements by
		their canonical name and the file path are known right away.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "pyproject.toml", """
				[build-system]
				requires = [
				  "setuptools >= 84.2.1",
				  "pyTooling >= 10.1.0, < 11.0"
				]
				build-backend = "setuptools.build_meta"
			""")

			entrypoints = readEntrypoints({"packaging": {"pyproject": "pyproject.toml"}}, root, root)

		requirements = entrypoints["packaging"].Requirements
		self.assertEqual({"pytooling", "setuptools"}, set(requirements))
		self.assertEqual("<11.0,>=10.1.0", str(requirements["pytooling"].specifier))
		self.assertEqual((root / "pyproject.toml",), entrypoints["packaging"].Files)
		self.assertEqual((), entrypoints["packaging"].Packages)

	@testcase("pyproject.toml file without build-system table")
	def PyProject_NoBuildSystem(self) -> None:
		"""
		A 'pyproject.toml' file without a '[build-system]' table has no build requirements.

		Writes a file with a '[tool.pytest]' table only, reads the entrypoint, and checks its requirements are empty.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "pyproject.toml", """
				[tool.pytest]
				junit_xml = "report/unit/unittest.xml"
			""")

			entrypoints = readEntrypoints({"packaging": {"pyproject": "pyproject.toml"}}, root, root)

		self.assertEqual({}, entrypoints["packaging"].Requirements)

	@testcase("Unparsable build requirement")
	def PyProject_UnparsableRequirement(self) -> None:
		"""
		A build requirement that can't be parsed is reported as a Sphinx warning; the other requirements are read.

		Writes a file of two build requirements with a broken one between them, reads the entrypoint, and checks the
		warning names the entrypoint, the requirement and the file, and both packages are known.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "pyproject.toml", """
				[build-system]
				requires = ["setuptools >= 84.2.1", "not a requirement", "pyTooling >= 10.1.0"]
			""")

			with self.assertLogs(LOGGER_NAME, level="WARNING") as logCapture:
				entrypoints = readEntrypoints({"packaging": {"pyproject": "pyproject.toml"}}, root, root)

		self.assertEqual(1, len(logCapture.records))
		message = logCapture.records[0].getMessage()
		self.assertIn("[packaging].pyproject:", message)
		self.assertIn(f"Build requirement 'not a requirement' in '{root / 'pyproject.toml'}' can't be parsed.", message)
		self.assertEqual({"pytooling", "setuptools"}, set(entrypoints["packaging"].Requirements))

	@testcase("Missing pyproject.toml file")
	def PyProject_Missing(self) -> None:
		"""
		A missing 'pyproject.toml' file is reported with the entrypoint's identifier and the path.

		Declares a file that doesn't exist and checks the error names '[packaging].pyproject' and the path, and is caused
		by pyTooling's PyProjectFileNotFoundError.
		"""
		from pyTooling.Dependency import PyProjectFileNotFoundError

		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			with self.assertRaises(SphinxExtensionError) as exceptionCapture:
				readEntrypoints({"packaging": {"pyproject": "pyproject.toml"}}, root, root)

		message = str(exceptionCapture.exception)
		self.assertIn("[packaging].pyproject: Project file", message)
		self.assertIn(str(root / "pyproject.toml"), message)
		self.assertIsInstance(exceptionCapture.exception.__cause__, PyProjectFileNotFoundError)

	@testcase("Invalid pyproject.toml file")
	def PyProject_InvalidTOML(self) -> None:
		"""
		A 'pyproject.toml' file that isn't valid TOML ends the build with a message naming the entrypoint.

		Writes a file with an unterminated table header and checks the SphinxExtensionError names '[packaging]'.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "pyproject.toml", "[build-system\n")

			with self.assertRaises(SphinxExtensionError) as exceptionCapture:
				readEntrypoints({"packaging": {"pyproject": "pyproject.toml"}}, root, root)

		self.assertIn("[packaging].pyproject:", str(exceptionCapture.exception))
		self.assertIn("is not valid TOML.", str(exceptionCapture.exception))

	@testcase("build-system table without requires")
	def PyProject_NoRequires(self) -> None:
		"""
		A '[build-system]' table without the key 'requires' ends the build, as PEP 518 makes the key mandatory.

		Writes a table with 'build-backend' only and checks the SphinxExtensionError names the missing key.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			self._write(root, "pyproject.toml", """
				[build-system]
				build-backend = "setuptools.build_meta"
			""")

			with self.assertRaises(SphinxExtensionError) as exceptionCapture:
				readEntrypoints({"packaging": {"pyproject": "pyproject.toml"}}, root, root)

		self.assertIn("has no key 'requires'.", str(exceptionCapture.exception))

	@testcase("pyproject field with a list")
	def PyProject_Iterable(self) -> None:
		"""
		The field 'pyproject' takes one path; it has no plural form and rejects an iterable.

		Declares 'pyproject' as a list and checks the error names what is expected.
		"""
		with self.assertRaises(SphinxExtensionError) as exceptionCapture:
			readEntrypoints({"packaging": {"pyproject": ["pyproject.toml"]}}, Path("."), Path("."))

		self.assertEqual(
			"conf.py: pyTooling_Dependency_Requirements:[packaging].pyproject: Expected None, True or a string, got "
			"'list'.",
			str(exceptionCapture.exception)
		)

	@testcase("pyproject.toml file in the project root")
	def PyProject_True(self) -> None:
		"""
		True reads 'pyproject.toml' in the project's root directory, not next to conf.py.

		Writes a file into the project root and none into the conf.py directory 'doc', reads the entrypoint with True,
		and checks the root's file was read.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			(root / "doc").mkdir()
			self._write(root, "pyproject.toml", """
				[build-system]
				requires = ["setuptools >= 84.2.1"]
			""")

			entrypoints = readEntrypoints({"packaging": {"pyproject": True}}, root / "doc", root)

		self.assertEqual({"setuptools"}, set(entrypoints["packaging"].Requirements))
		self.assertEqual((root / "pyproject.toml",), entrypoints["packaging"].Files)

	@testcase("pyproject.toml file below the project root")
	def PyProject_Subdirectory(self) -> None:
		"""
		A relative path is relative to the project's root directory.

		Writes 'package/pyproject.toml', reads it as 'package/pyproject.toml' with conf.py in 'doc', and checks the file
		below the root was read.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			(root / "doc").mkdir()
			(root / "package").mkdir()
			self._write(root / "package", "pyproject.toml", """
				[build-system]
				requires = ["hatchling"]
			""")

			entrypoints = readEntrypoints({"packaging": {"pyproject": "package/pyproject.toml"}}, root / "doc", root)

		self.assertEqual({"hatchling"}, set(entrypoints["packaging"].Requirements))
		self.assertEqual((root / "package" / "pyproject.toml",), entrypoints["packaging"].Files)

	@testcase("Absolute path of a pyproject.toml file")
	def PyProject_Absolute(self) -> None:
		"""
		An absolute path is read as it is, whatever the project root.

		Writes a file into a directory and declares its absolute path with an unrelated project root, and checks the
		file was read.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			file = self._write(root, "pyproject.toml", """
				[build-system]
				requires = ["setuptools >= 84.2.1"]
			""")

			entrypoints = readEntrypoints({"packaging": {"pyproject": str(file)}}, Path("."), root / "elsewhere")

		self.assertEqual((file,), entrypoints["packaging"].Files)

	@testcase("Project without pyproject.toml file")
	def PyProject_None(self) -> None:
		"""
		None declares a project without a 'pyproject.toml' file: nothing is read, and there are no build requirements.

		Reads the entrypoint with None in a directory without any file and checks it has no requirements and no files.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			entrypoints = readEntrypoints({"packaging": {"pyproject": None}}, root, root)

		self.assertEqual({}, entrypoints["packaging"].Requirements)
		self.assertEqual((), entrypoints["packaging"].Files)

	@testcase("pyproject field set to False")
	def PyProject_False(self) -> None:
		"""
		False is no allowed value; a project without the file declares None.

		Declares 'pyproject' as False and checks the error names what is expected.
		"""
		with self.assertRaises(SphinxExtensionError) as exceptionCapture:
			readEntrypoints({"packaging": {"pyproject": False}}, Path("."), Path("."))

		self.assertIn("Expected None, True or a string, got 'bool'.", str(exceptionCapture.exception))

	@testcase("pyproject field with an empty path")
	def PyProject_Empty(self) -> None:
		"""
		An empty path is rejected instead of naming the project root directory.

		Declares 'pyproject' as an empty string and checks the error suggests True.
		"""
		with self.assertRaises(SphinxExtensionError) as exceptionCapture:
			readEntrypoints({"packaging": {"pyproject": ""}}, Path("."), Path("."))

		self.assertEqual(
			"conf.py: pyTooling_Dependency_Requirements:[packaging].pyproject: Path is empty. Use True for the project "
			"root's file.",
			str(exceptionCapture.exception)
		)

	@testcase("Neither file nor package")
	def NoField(self) -> None:
		"""
		A declaration without a field is rejected.

		Declares an empty dictionary and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": {}}, Path("."), Path("."))

	@testcase("Both file and package")
	def FileAndPackage(self) -> None:
		"""
		A declaration with a file and a package is rejected.

		Declares both fields and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": {"file": "requirements.txt", "package": "pyTooling"}}, Path("."), Path("."))

	@testcase("Singular and plural field")
	def FileAndFiles(self) -> None:
		"""
		A declaration with a singular field and its plural is rejected.

		Declares 'file' and 'files' and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": {"file": "a.txt", "files": ["b.txt"]}}, Path("."), Path("."))

	@testcase("Unknown field")
	def UnknownField(self) -> None:
		"""
		A misspelt field is reported, not ignored.

		Declares the misspelt field 'fiel' and checks the error names it as unknown.
		"""
		with self.assertRaises(SphinxExtensionError) as exceptionCapture:
			readEntrypoints({"unittest": {"fiel": "requirements.txt"}}, Path("."), Path("."))

		self.assertIn("Unknown field(s): fiel.", str(exceptionCapture.exception))

	@testcase("Declaration not a dictionary")
	def Declaration_NoDictionary(self) -> None:
		"""
		A declaration that is no dictionary is rejected.

		Declares an entrypoint as a string and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints({"unittest": "requirements.txt"}, Path("."), Path("."))

	@testcase("Configuration not a dictionary")
	def Configuration_NoDictionary(self) -> None:
		"""
		A configuration value that is no dictionary is rejected.

		Passes a list as the configuration and checks the SphinxExtensionError.
		"""
		with self.assertRaises(SphinxExtensionError):
			readEntrypoints(["requirements.txt"], Path("."), Path("."))


@testsuite("Project root")
class ProjectRoot(Testcase):
	"""``pyTooling_ProjectRoot`` says where a ``pyproject`` entrypoint's path starts; unset, it's conf.py's parent."""

	@staticmethod
	def _Files(confDirectory: Path, projectRoot: Nullable[str]) -> tuple[Path, ...]:
		sphinx = SimpleNamespace(confdir=str(confDirectory))
		config = SimpleNamespace(pyTooling_Dependency_Requirements={"packaging": {"pyproject": True}})
		if projectRoot is not None:
			config.pyTooling_ProjectRoot = projectRoot

		prepareEntrypoints(sphinx, config)

		return _COLLECTORS.pop(id(sphinx)).Entrypoints["packaging"].Files

	@testcase("Default project root")
	def Default(self) -> None:
		"""
		Without pyTooling_ProjectRoot, the project root is the parent of conf.py's directory.

		Writes 'pyproject.toml' next to 'doc', prepares the entrypoints with conf.py in 'doc', and checks the file in the
		parent directory was read.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			(root / "doc").mkdir()
			(root / "pyproject.toml").write_text("[build-system]\nrequires = []\n", encoding="utf-8")

			files = self._Files(root / "doc", None)

		self.assertEqual((root / "pyproject.toml",), files)

	@testcase("Project root set")
	def Set(self) -> None:
		"""
		pyTooling_ProjectRoot is relative to conf.py's directory.

		Writes 'pyproject.toml' two levels above 'docs/sphinx', sets the root to '../..', and checks that file was read.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			(root / "docs" / "sphinx").mkdir(parents=True)
			(root / "pyproject.toml").write_text("[build-system]\nrequires = []\n", encoding="utf-8")

			files = self._Files(root / "docs" / "sphinx", "../..")

		self.assertEqual((root / "docs" / "sphinx" / ".." / ".." / "pyproject.toml",), files)


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


class _Resolved:
	"""
	A requirement as the resolver hands it over: the index doesn't know the project, and the package's name - or the
	name given as release - stands in for its release, interned, so two lines of the same release share one object.
	"""

	def __init__(
		self,
		name: str,
		status: ResolutionStatus,
		*dependencies: "_Resolved",
		release: Nullable[str] = None
	) -> None:
		self.Requirement =  Requirement(name)
		self.Status =       status
		self.Project =      None
		self.Release =      sys_intern(self.Requirement.name if release is None else release)
		self.Dependencies = dependencies


class _TreeTable(DependencyTable):
	"""A table rendering a package as its name, with its extras."""

	def __init__(
		self,
		duplicateFormat: DuplicateFormat = DuplicateFormat.Expanded,
		duplicateMatch: DuplicateMatch = DuplicateMatch.Subset
	) -> None:
		self._duplicateFormat =   duplicateFormat
		self._duplicateMatch =    duplicateMatch
		self._duplicateOf =       {}
		self._originals =         set()
		self._anchors =           {}
		self._pendingReferences = []
		self.state =              SimpleNamespace(document=new_document("<test>"))

	def _RequirementParagraph(self, requirement: Requirement, project: None, release: str) -> nodes.paragraph:
		return nodes.paragraph(text=f"{requirement.name}{self._ExtrasText(requirement)}")


@testsuite("Dependency trees")
class DependencyTrees(Testcase):
	"""
	A dependency tree is rendered as the resolver resolved it, and says where the depth limit cut it off.

	The trees are 'a -> b -> c, d; c -> e -> a', as the resolver returns them for each limit.
	"""

	@staticmethod
	def _render(root: _Resolved) -> list[str]:
		bulletList = _TreeTable()._CreateBulletList([root])

		return [node.astext() for node in bulletList.findall(nodes.paragraph)]

	@testcase("Unlimited")
	def Unlimited(self) -> None:
		"""
		Without a limit, a tree is rendered until it ends; a cycle ends at a package already on the path.

		Renders a tree whose 'a' below 'e' closes a cycle and checks every package is listed once and nothing is marked.
		"""
		tree = _Resolved("a", ResolutionStatus.Resolved,
			_Resolved("b", ResolutionStatus.Resolved,
				_Resolved("c", ResolutionStatus.Resolved,
					_Resolved("e", ResolutionStatus.Resolved, _Resolved("a", ResolutionStatus.Cycle))
				),
				_Resolved("d", ResolutionStatus.Resolved)
			)
		)

		self.assertEqual(["a", "b", "c", "e", "d"], self._render(tree))

	@testcase("Limited")
	def Limited(self) -> None:
		"""
		A package whose dependencies the limit cuts off says how many weren't expanded.

		Renders a tree whose dependencies of 'b' reached the limit and checks 'b' is followed by the marker for its two.
		"""
		tree = _Resolved("a", ResolutionStatus.Resolved,
			_Resolved("b", ResolutionStatus.Resolved,
				_Resolved("c", ResolutionStatus.LimitReached),
				_Resolved("d", ResolutionStatus.LimitReached)
			)
		)

		self.assertEqual(["a", "b", "… 2 more dependencies not expanded"], self._render(tree))

	@testcase("Limited, one dependency")
	def Limited_One(self) -> None:
		"""
		The marker counts a single dependency in the singular.

		Renders a tree whose 'e' below 'c' reached the limit and checks the marker of 'c'.
		"""
		tree = _Resolved("a", ResolutionStatus.Resolved,
			_Resolved("b", ResolutionStatus.Resolved,
				_Resolved("c", ResolutionStatus.Resolved, _Resolved("e", ResolutionStatus.LimitReached)),
				_Resolved("d", ResolutionStatus.Resolved)
			)
		)

		self.assertEqual(["a", "b", "c", "… 1 more dependency not expanded", "d"], self._render(tree))

	@testcase("Limited, leaf")
	def Limited_Leaf(self) -> None:
		"""
		A package without dependencies gets no marker, even at the limit; neither does a cycle back into the path.

		Renders a tree whose 'e' requires only 'a', which closes a cycle, and checks 'e' and 'd' are unmarked.
		"""
		tree = _Resolved("a", ResolutionStatus.Resolved,
			_Resolved("b", ResolutionStatus.Resolved,
				_Resolved("c", ResolutionStatus.Resolved,
					_Resolved("e", ResolutionStatus.Resolved, _Resolved("a", ResolutionStatus.Cycle))
				),
				_Resolved("d", ResolutionStatus.Resolved)
			)
		)

		self.assertEqual(["a", "b", "c", "e", "d"], self._render(tree))

	@testcase("Not resolved")
	def NotResolved(self) -> None:
		"""
		A row whose package wasn't resolved to a release says its dependencies weren't evaluated.

		Renders the dependencies entry of a package the index doesn't know and checks the text.
		"""
		entry = _TreeTable()._DependenciesEntry(_Resolved("ghost", ResolutionStatus.UnknownProject))

		self.assertEqual("not evaluated", entry.astext())


@testsuite("Duplicate dependencies")
class Duplicates(Testcase):
	"""
	A line whose dependencies an earlier line of the table shows is a duplicate.

	Its dependencies are folded or replaced by a link to that line. Every first-level row is an original before any
	line of a tree.
	"""

	@staticmethod
	def _Table(
		rows: tuple[_Resolved, ...],
		duplicateFormat: DuplicateFormat = DuplicateFormat.Collapsed,
		duplicateMatch: DuplicateMatch = DuplicateMatch.Subset
	) -> _TreeTable:
		table = _TreeTable(duplicateFormat, duplicateMatch)
		table._duplicateOf = table._FindDuplicates(SimpleNamespace(Requirements=rows))
		table._originals =   set(table._duplicateOf.values())

		return table

	@staticmethod
	def _Lines(table: _TreeTable, row: _Resolved) -> list[str]:
		bulletList = table._CreateBulletList(list(row.Dependencies))

		return [node.astext() for node in bulletList.findall(nodes.paragraph)]

	@staticmethod
	def _Sphinx() -> tuple[_Resolved, _Resolved]:
		"""The rows 'autodoc -> sphinx -> docutils' and 'sphinx -> docutils', as the resolver returns them."""
		return (
			_Resolved("autodoc", ResolutionStatus.Resolved,
				_Resolved("sphinx", ResolutionStatus.Resolved, _Resolved("docutils", ResolutionStatus.Resolved))
			),
			_Resolved("sphinx", ResolutionStatus.Resolved, _Resolved("docutils", ResolutionStatus.Resolved))
		)

	@testcase("Defaults")
	def Defaults(self) -> None:
		"""
		Duplicates are collapsed and matched by subset when the document doesn't say.

		Parses both options without a value and checks the members.
		"""
		self.assertIs(DuplicateFormat.Collapsed, DuplicateFormat.Parse(None))
		self.assertIs(DuplicateMatch.Subset, DuplicateMatch.Parse(None))

	@testcase("Option values")
	def Values(self) -> None:
		"""
		The options take their members' values; another value is rejected with the values allowed.

		Parses 'reference' and 'name', and checks 'Collapsed' is rejected, as values are lower case.
		"""
		self.assertIs(DuplicateFormat.Reference, DuplicateFormat.Parse("reference"))
		self.assertIs(DuplicateMatch.Name, DuplicateMatch.Parse("name"))
		with self.assertRaises(ValueError) as exceptionCapture:
			DuplicateFormat.Parse("Collapsed")

		self.assertEqual(["Allowed values: expanded, collapsed, reference."], exceptionCapture.exception.__notes__)

	@testcase("Compact lists")
	def Compact(self) -> None:
		"""
		Every list of a tree is compact, also one holding folded dependencies, so HTML spaces its lines alike.

		Renders the tree of 'autodoc' collapsed and checks every bullet list carries the class 'compact'.
		"""
		rows = self._Sphinx()
		bulletList = self._Table(rows)._CreateBulletList(list(rows[0].Dependencies))

		self.assertTrue(all("compact" in node["classes"] for node in bulletList.findall(nodes.bullet_list)))

	@testcase("Expanded")
	def Expanded(self) -> None:
		"""
		Expanded duplicates are no duplicates: every tree is shown in full.

		Finds the duplicates of the 'sphinx' rows with 'Expanded' and checks there are none and the tree is complete.
		"""
		rows = self._Sphinx()
		table = self._Table(rows, DuplicateFormat.Expanded)

		self.assertEqual({}, table._duplicateOf)
		self.assertEqual(["sphinx", "docutils"], self._Lines(table, rows[0]))

	@testcase("Collapsed duplicate of a row")
	def Collapsed(self) -> None:
		"""
		A dependency the table lists in a row of its own is a duplicate of that row, even if the row is further down.

		Renders the tree of 'autodoc', whose 'sphinx' is a row below it, and checks the marker follows 'sphinx' and the
		folded 'docutils' is still there, inside a FoldedDependencies node.
		"""
		rows = self._Sphinx()
		table = self._Table(rows)

		self.assertIs(rows[1], table._duplicateOf[rows[0].Dependencies[0]])
		self.assertEqual(["sphinx", "… 1 dependency, listed at sphinx", "docutils"], self._Lines(table, rows[0]))
		bulletList = table._CreateBulletList(list(rows[0].Dependencies))
		self.assertEqual(1, len(list(bulletList.findall(FoldedDependencies))))

	@testcase("Referenced duplicate of a row")
	def Reference(self) -> None:
		"""
		A referenced duplicate gets the marker alone; its dependencies aren't rendered.

		Renders the tree of 'autodoc' with 'Reference' and checks 'docutils' is missing and nothing is folded.
		"""
		rows = self._Sphinx()
		table = self._Table(rows, DuplicateFormat.Reference)

		self.assertEqual(["sphinx", "… 1 dependency, listed at sphinx"], self._Lines(table, rows[0]))
		bulletList = table._CreateBulletList(list(rows[0].Dependencies))
		self.assertEqual(0, len(list(bulletList.findall(FoldedDependencies))))

	@testcase("Shared dependency of two trees")
	def Shared(self) -> None:
		"""
		A package two trees share is shown at its first line; the second line links to it.

		Builds rows 'a -> x -> pydantic -> core' and 'b -> y -> pydantic -> core', renders both trees, and checks the
		first 'pydantic' is shown, the second links to it, and the link's target is the first line's ID.
		"""
		first =  _Resolved("pydantic", ResolutionStatus.Resolved, _Resolved("core", ResolutionStatus.Resolved))
		second = _Resolved("pydantic", ResolutionStatus.Resolved, _Resolved("core", ResolutionStatus.Resolved))
		rows = (
			_Resolved("a", ResolutionStatus.Resolved, _Resolved("x", ResolutionStatus.Resolved, first)),
			_Resolved("b", ResolutionStatus.Resolved, _Resolved("y", ResolutionStatus.Resolved, second))
		)
		table = self._Table(rows, DuplicateFormat.Reference)

		self.assertEqual({second: first}, table._duplicateOf)
		self.assertEqual(["x", "pydantic", "core"], self._Lines(table, rows[0]))
		self.assertEqual(["y", "pydantic", "… 1 dependency, listed at pydantic"], self._Lines(table, rows[1]))

		[(reference, original)] = table._pendingReferences
		self.assertIs(first, original)
		self.assertIn(table._anchors[first], table.state.document.ids)

	@testcase("Subset of the extras")
	def Subset(self) -> None:
		"""
		With 'Subset', a line requiring the original's extras or fewer is a duplicate; one requiring more is not.

		Builds the row 'pyTooling[dependencies]' and the tree 'reports -> pyTooling, pyTooling[yaml]', and checks plain
		'pyTooling' is a duplicate of the row, 'pyTooling[yaml]' is not.
		"""
		resolved = ResolutionStatus.Resolved
		plain =    _Resolved("pyTooling", resolved, _Resolved("colorama", resolved))
		yaml =     _Resolved("pyTooling[yaml]", resolved, _Resolved("ruamel.yaml", resolved))
		row =      _Resolved("pyTooling[dependencies]", resolved, _Resolved("aiohttp", resolved))
		table =    self._Table((_Resolved("reports", resolved, plain, yaml), row))

		self.assertEqual({plain: row}, table._duplicateOf)

	@testcase("Exact extras")
	def Exact(self) -> None:
		"""
		With 'Exact', a line is a duplicate only with the original's extras.

		Builds the row 'pyTooling[dependencies]' and the tree 'reports -> pyTooling, pyTooling[dependencies]', and checks
		only the line with the same extra is a duplicate.
		"""
		resolved = ResolutionStatus.Resolved
		plain =    _Resolved("pyTooling", resolved, _Resolved("colorama", resolved))
		same =     _Resolved("pyTooling[dependencies]", resolved, _Resolved("aiohttp", resolved))
		row =      _Resolved("pyTooling[dependencies]", resolved, _Resolved("aiohttp", resolved))
		table =    self._Table((_Resolved("reports", resolved, plain, same), row), duplicateMatch=DuplicateMatch.Exact)

		self.assertEqual({same: row}, table._duplicateOf)

	@testcase("Other release")
	def OtherRelease(self) -> None:
		"""
		A line of another release is no duplicate, unless duplicates are matched by name.

		Builds the row 'sphinx' and the tree 'autodoc -> sphinx' of another release, and checks it is a duplicate with
		'Name' only.
		"""
		resolved = ResolutionStatus.Resolved
		older =    _Resolved("sphinx", resolved, _Resolved("docutils", resolved), release="8.2")
		rows = (
			_Resolved("autodoc", resolved, older),
			_Resolved("sphinx", resolved, _Resolved("docutils", resolved), release="9.1")
		)

		self.assertEqual({}, self._Table(rows)._duplicateOf)
		self.assertEqual({older: rows[1]}, self._Table(rows, duplicateMatch=DuplicateMatch.Name)._duplicateOf)

	@testcase("Original cut off by the depth limit")
	def Limited(self) -> None:
		"""
		A line whose dependencies the depth limit cut off is no original; the next full line is.

		Builds 'a -> x -> pydantic (limit reached)', 'b -> pydantic -> core' and 'c -> pydantic -> core', and checks the
		line below 'b' is the original of the one below 'c', not the cut-off line below 'a'.
		"""
		cut =    _Resolved("pydantic", ResolutionStatus.Resolved, _Resolved("core", ResolutionStatus.LimitReached))
		full =   _Resolved("pydantic", ResolutionStatus.Resolved, _Resolved("core", ResolutionStatus.Resolved))
		second = _Resolved("pydantic", ResolutionStatus.Resolved, _Resolved("core", ResolutionStatus.Resolved))
		rows = (
			_Resolved("a", ResolutionStatus.Resolved, _Resolved("x", ResolutionStatus.Resolved, cut)),
			_Resolved("b", ResolutionStatus.Resolved, full),
			_Resolved("c", ResolutionStatus.Resolved, second)
		)

		self.assertEqual({second: full}, self._Table(rows)._duplicateOf)

	@testcase("Without dependencies")
	def Leaf(self) -> None:
		"""
		A line without dependencies is never a duplicate: there is nothing to fold.

		Builds the row 'docutils' and the tree 'sphinx -> docutils', and checks no duplicate is found.
		"""
		rows = (
			_Resolved("sphinx", ResolutionStatus.Resolved, _Resolved("docutils", ResolutionStatus.Resolved)),
			_Resolved("docutils", ResolutionStatus.Resolved)
		)

		self.assertEqual({}, self._Table(rows)._duplicateOf)

	@testcase("Output formats without folding")
	def NoFolding(self) -> None:
		"""
		LaTeX, text, manual pages and Texinfo get the marker alone, its link as text.

		Renders the tree of 'autodoc' collapsed into a document, runs ReplaceFoldedDependencies, and checks nothing is
		folded, 'docutils' is gone, and the marker holds no reference.
		"""
		rows = self._Sphinx()
		table = self._Table(rows)
		document = table.state.document
		document += table._CreateBulletList(list(rows[0].Dependencies))

		ReplaceFoldedDependencies(document).run()

		self.assertEqual(0, len(list(document.findall(FoldedDependencies))))
		self.assertEqual(0, len(list(document.findall(nodes.reference))))
		self.assertEqual(
			["sphinx", "… 1 dependency, listed at sphinx"],
			[node.astext() for node in document.findall(nodes.paragraph)]
		)
		self.assertEqual(("latex", "text", "man", "texinfo"), ReplaceFoldedDependencies.formats)


@testsuite("Extras")
class Extras(Testcase):
	"""A requirement's extras are shown behind the package's name, and several statements of a package merge them."""

	@testcase("No extras")
	def None_(self) -> None:
		"""
		A requirement without extras adds nothing to the name.

		Checks the text of 'pyTooling >= 10.1' is empty.
		"""
		self.assertEqual("", DependencyTable._ExtrasText(Requirement("pyTooling >= 10.1")))

	@testcase("Sorted extras")
	def Sorted(self) -> None:
		"""
		Several extras are shown sorted, in one pair of brackets.

		Checks the text of 'pyTooling[yaml,packaging,console]'.
		"""
		requirement = Requirement("pyTooling[yaml,packaging,console]")

		self.assertEqual("[console,packaging,yaml]", DependencyTable._ExtrasText(requirement))

	@testcase("Later statement keeps earlier extras")
	def Merge(self) -> None:
		"""
		A later statement of a package wins, with the extras of the earlier one added; the given requirements stay as
		they are.

		Merges 'pyTooling[yaml] >= 9.0' and 'pyTooling >= 10.1', and checks the result and both inputs.
		"""
		earlier = Requirement("pyTooling[yaml] >= 9.0")
		later =   Requirement("pyTooling >= 10.1")

		merged = _MergeRequirements([earlier, later])

		self.assertEqual("pyTooling[yaml]>=10.1", str(merged["pytooling"]))
		self.assertEqual(set(), later.extras)
		self.assertEqual("pyTooling[yaml]>=9.0", str(earlier))

	@testcase("Later statement with all extras")
	def Merge_Contained(self) -> None:
		"""
		A later statement naming the earlier extras already is taken as it is.

		Merges 'pyTooling[yaml]' and 'pyTooling[dependencies,yaml]', and checks the second statement is the result.
		"""
		later = Requirement("pyTooling[dependencies,yaml]")

		self.assertIs(later, _MergeRequirements([Requirement("pyTooling[yaml]"), later])["pytooling"])

	@testcase("Extras across requirements files")
	def Files(self) -> None:
		"""
		A file entrypoint of several files merges the extras of a package stated in two of them.

		Writes 'pyTooling[yaml]' into the first file and 'pyTooling ~= 10.1' into the second, reads both, and checks the
		merged requirement.
		"""
		with TemporaryDirectory() as directory:
			root = Path(directory).resolve()
			(root / "first.txt").write_text("pyTooling[yaml] >= 9.0\n", encoding="utf-8")
			(root / "second.txt").write_text("pyTooling ~= 10.1\n", encoding="utf-8")

			entrypoints = readEntrypoints({"both": {"files": ["first.txt", "second.txt"]}}, root, root)

		self.assertEqual("pyTooling[yaml]~=10.1", str(entrypoints["both"].Requirements["pytooling"]))


def _licenseWarning(name: str) -> UnknownLicenseWarning:
	warning = UnknownLicenseWarning(
		f"License of '{name}' 1.0 couldn't be resolved.",
		projectName=name,
		version=SemanticVersion(1, 0)
	)
	warning.add_note("license: BSD")

	return warning


@testsuite("Collecting unresolved licenses")
class UnresolvedLicenseCollection(Testcase):
	"""A package whose license the index couldn't answer for is recorded once, by the override file's spelling."""

	@testcase("Two spellings, one entry")
	def TwoSpellings(self) -> None:
		"""
		A package required under two spellings is recorded once, by its canonical name.

		Reports two warnings about an unknown license, naming 'Sphinx_RTD_Theme' and 'sphinx-rtd-theme', and checks
		that one entry remains, keyed 'sphinx-rtd-theme'.
		"""
		collector = DependencyCollector({}, "https://pypi.org", "https://pypi.org/pypi", None)

		with self.assertNoLogs(LOGGER_NAME, level="WARNING"):
			collector._ReportWarnings([_licenseWarning("Sphinx_RTD_Theme"), _licenseWarning("sphinx-rtd-theme")])

		self.assertEqual({"sphinx-rtd-theme": ("license: BSD",)}, collector.UnresolvedLicenses)


@testsuite("Reporting warnings")
class WarningReport(Testcase):
	"""A warning reported while resolving is reported as a Sphinx warning, not raised and not recorded as a license."""

	@testcase("Broken requirement")
	def BrokenRequirement(self) -> None:
		"""
		A warning about a broken requirement is logged with its note.

		Reports a warning about a requirement naming an undeclared extra and checks the warning and its note are logged
		and no unresolved license is recorded.
		"""
		collector = DependencyCollector({}, "https://pypi.org", "https://pypi.org/pypi", None)
		warning = BrokenRequirementWarning(
			"Requirement 'pyTooling[terminal]' names extra 'terminal', which release '1.0' of package 'pyTooling' doesn't "
			"declare."
		)
		warning.add_note("Known extras: yaml")

		with self.assertLogs(LOGGER_NAME, level="WARNING") as logCapture:
			collector._ReportWarnings([warning])

		self.assertEqual(1, len(logCapture.records))
		message = logCapture.records[0].getMessage()
		self.assertIn("[dependency-table] Requirement 'pyTooling[terminal]' names extra 'terminal'", message)
		self.assertIn("\n  Known extras: yaml", message)
		self.assertEqual({}, collector.UnresolvedLicenses)

	@testcase("Critical warning")
	def Critical(self) -> None:
		"""
		A critical warning, as pyTooling reports for a release whose version can't be parsed, is logged once.

		Reports a critical warning and checks it is logged.
		"""
		collector = DependencyCollector({}, "https://pypi.org", "https://pypi.org/pypi", None)

		with self.assertLogs(LOGGER_NAME, level="WARNING") as logCapture:
			collector._ReportWarnings([
				UnsupportedVersionWarning(
					"Skipping release '2004d' of package 'pytz'.",
					projectName="pytz",
					version="2004d"
				)
			])

		self.assertEqual(1, len(logCapture.records))
		self.assertEqual(
			"[dependency-table] Skipping release '2004d' of package 'pytz'.",
			logCapture.records[0].getMessage()
		)


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
