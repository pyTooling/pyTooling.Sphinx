**Release created on: 09.11.2024 - 23:13:26**

# New Features

* Reworked semantic and calendar version classes:
  * Moved common implementations to `Version` base-type.
    * Moved major, minor, micro, build, post, dev, release level, release number, hash, prefix, postfix parts to the base-type.
    * Moved implementations of comparison operators to the base-type: `__eq__`, `__ne__`, `__lt__`, `__le__`, `__gt__`, `__ge__`.
    * Implemented minimum comparison operator using `__rshift__` (`>>`) for PIP's `~=` operator.
    * Implemented a formatting helper method `_format`.
  * Reworked `SemanticVersion`.
    * Additionally allow comparisons with string and integer types.
    * Enhanced `SemanticVersion.Parse()` class-method:
      * Raise exceptions on invalid inputs.
      * Use a regular expression to check and split the input.
  * Implemented `CalendarVersion` (previously a dummy).
    * Added `CalendarVersion.Parse()` class-method: raise exceptions on invalid inputs.
    * Implemented comparison operators.
  * Added validator classes `WordSizeValidator` and `MaxValueValidator`.
  * Added doc-strings.
  * Improved `__str__()` method to return only used version parts.
  * Added `__format__()` for user defined formatting specifications.

# Changes

* Bumped dependencies.
* Renamed `SemanticVersion.Patch` to `SemanticVersion.Micro`.  
  `SemanticVersion.Patch` is still available as an alias.
* Moved `pyTooling.Platform.PythonVersion` to `pyTooling.Versioning.PythonVersion`.

# Bug Fixes

* Added support for Python 3.12 on MSYS2 environments (MinGW64, UCRT64, Clang64).
* Internally used type `PythonVersion` used a buggy constructor.  
  The problem only occurred with PyPy, but it proved a general bug in that type.  
  Creating an instance now needs the class-method `PythonVersion.FromSysVersionInfo()`

# Documentation

* Updated versioning and stopwatch examples on the landing page.
* Added doc-strings to all version classes.
* Improved Versioning documentation page.
* Improved Stopwatch documentation page.

# Unit Tests

* Added unit tests for `SemanticVersion` and `CalendarVersion`.


# Related Issues
* fixes #12
* fixes #107
* fixes #169
* fixes #170
* fixes #174