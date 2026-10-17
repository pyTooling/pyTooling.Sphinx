# New Features

* `pyTooling.Testing` is a new module: enhanced classes for writing unit tests with Python's `unittest` framework,
  which pytest runs as well.
  * `ApplicationTestcase` starts the installed program the way a user does, so a test covers the
    `console_scripts` entry point, the argument parsing and the exit code - none of which importing the code can
    reach. `RunEntrypoint()` runs the console script, `RunModule()` runs `python -m <module>`, and
    `assertExitCode()` reports the exit code with `stdout` and `stderr` attached.
  * `Testcase` is the base class every pyTooling testcase derives from: `unittest.TestCase` plus the assertions
    Python gained later than the oldest supported interpreter - `assertHasAttr()` and `assertNotHasAttr()` on
    Python 3.11-3.13, the standard library's own implementations from 3.14 on.
  * `stripANSIColorCodes()` makes colored output comparable to an expectation.
  * `TestingException` is the module's exception, derived from `ToolingException`.
* `pyTooling.Versioning.VersionValidatorException`, derived from `ToolingException`, carries the rejected version
  in its `Version` property.
* `pyTooling.MetaClasses.abstractclass` marks a class as *abstract* although it has no abstract method - a
  base-class collecting shared infrastructure could not say so before, because abstractness was only inferred
  from `@abstractmethod`. The marker is not inherited, so a derived class is instantiable unless it is decorated
  itself, and the raised `AbstractClassError` says *needs to be derived* where the inferred case names the
  methods to override.

  ```python
  @abstractclass
  class Base(metaclass=ExtendedType):
    '''This class needs to be inherited.'''
  ```

* `pyTooling.Exceptions.MissingDependencyError` ([#299](https://github.com/pyTooling/pyTooling/pull/299)) replaces
  the six `raise Exception("Optional dependency '...' not installed.")` at import time (`Packaging`,
  `Dependency.Python` x3, `Configuration.YAML`, `TerminalUI`). It derives from `ImportError`, which is what a
  caller guarding an optional import catches, carries the missing package and the extra as `Dependency` and
  `Extra`, and attaches the install hint as a note: *"Either install pyTooling with extra 'pyTooling[yaml]' or
  install 'ruamel.yaml' directly."*
* `pyTooling.Warning.EscalatedWarningException` ([#299](https://github.com/pyTooling/pyTooling/pull/299)) is raised
  where a `WarningCollector`'s handler asks for a warning to be raised instead of collected - that was a bare
  `Exception` before, so a caller had no way to catch it specifically.
* `pyTooling.Graph.DuplicateVertexError` and `DuplicateEdgeError` carry the offending `vertexID`/`edgeID`, so a
  handler doesn't have to parse the message to learn which identifier collided.
* `pyTooling.Decorators`:
  * `InheritDocString` can **merge** the two doc-strings instead of replacing one with the other, so a derived
    entity documents what is specific to it without repeating its base-class. New keyword parameters `merge`,
    `order`, `prefix`, `interfix` and `postfix`; the merged text is assembled as
    `prefix + first + interfix + second + postfix`.
  * `DocStringMergeOrder` is a new enumeration selecting which doc-string comes first: `BaseFirst` (the default)
    or `DerivedFirst`.

  ```python
  @InheritDocString(BaseClass, merge=True, order=DocStringMergeOrder.DerivedFirst)
  class Derived(BaseClass):
    """What this class adds."""
  ```

  `baseClass` remains the first parameter, so existing calls are unaffected.

# Breaking Changes

* ⚠️ `pyTooling.Warning.SupervisedThreadException` takes `(message, /, *, threadName=None, cause=None)` where it
  took `(threadName, message, /, cause=None)`. The message is positional-only and the attached objects are
  keyword-only - the shape `AttributeError(msg, *, name=, obj=)`, `NameError` and `ImportError` use. Callers
  passing the thread name positionally have to name it:

  ```python
  SupervisedThreadException(threadName, f"Thread '{threadName}' failed.")              # before
  SupervisedThreadException(f"Thread '{threadName}' failed.", threadName=threadName)   # now
  ```

* ⚠️ `pyTooling.TerminalUI.TerminalBaseApplication.CheckPythonVersion()` **and** the exit code
  `PYTHON_VERSION_CHECK_FAILED_EXIT_CODE` (254) are removed. A package's `python_requires` metadata makes the check
  unnecessary - the installer refuses the package before a single line of it is imported. Applications calling it
  delete that one line; two of ours do (`pyVersioning`, `pyGHDL`).
* ⚠️ `pyTooling.Warning.UnhandledWarningException` is removed, as v9.0.0 was announced to do. Nothing raised it
  any more since the warning protocol handles an unhandled warning itself.
* ⚠️ **34 base-classes in `pyTooling.CLIAbstraction` raise `AbstractClassError` instead of `TypeError`** when they
  are instantiated directly ([#303](https://github.com/pyTooling/pyTooling/pull/303)). They were guarded by 34
  hand-written `__init__` pairs raising `TypeError`; they are `@abstractclass` now, which is the same intent said
  once. A test asserting `TypeError` on such an instantiation has to be updated - `AbstractClassError` derives from
  `ExtendedTypeError`, not from `TypeError`.
* ⚠️ **A configuration is read-only** ([#305](https://github.com/pyTooling/pyTooling/pull/305)). No file format
  implements writing - both backends documented *"Writing a configuration is not supported by this
  implementation"* - so `Node.__setitem__` and `Sequence.__setitem__` say so with one message instead of four
  stubs: `NotImplementedError: Currently, the configuration is read-only. Writing isn't implemented.` The two
  backend overrides are gone; they inherit it.
* ⚠️ **`CalendarVersion` no longer invents parts that were never given**
  ([#311](https://github.com/pyTooling/pyTooling/pull/311)). `CalendarVersion.Parse("2024")` rendered `'2024.0'`
  where `CalendarVersion(2024)` rendered `'2024'`, and the two-part classes passed a literal `0` as the micro part,
  so **every** year-month, year-week and year-release version rendered three: `YearMonthVersion(2024, 10)` was
  `'2024.10.0'`. Equality, ordering and hashing are unchanged - only the rendering, so a caller comparing
  `str(version)` against a stored string sees the shorter form now.
* ⚠️ **`pyTooling.GenericPath.URL.Protocols` is a `Flag` whose secured schemes are combinations**
  ([#316](https://github.com/pyTooling/pyTooling/pull/316)). `HTTPS` and `FTPS` had their own bits, so
  `Protocols.HTTPS & Protocols.TLS` was `0` and a URL could not be asked whether it is encrypted. They are named
  composites now - `HTTPS = TLS | HTTP`, `FTPS = TLS | FTP` - which makes `Protocols.TLS in url.Scheme` the check
  for a TLS secured scheme, without knowing the list of secured schemes. A named composite is a full member, so
  lookup by name, lookup by value and `.name` are unchanged and `URL.Parse()` and `str(url)` are unaffected; the
  base class is plain `Flag`, because nothing compares a scheme to an integer. **The numeric values change**
  (`HTTPS` 4 → 5, `FTPS` 16 → 9, `FILE` 32 → 2), which affects code that persisted them as integers.
  `URL._scheme`, its constructor parameter and `URL.Scheme` are `Nullable[Protocols]`, which is what the
  constructor has always accepted.
* ⚠️ **The four `pyTooling.Configuration.Node` stubs that every backend implements are `@abstractmethod`**
  ([#304](https://github.com/pyTooling/pyTooling/pull/304)): `__len__`, `__getitem__`, `__iter__` and `QueryPath`.
  A backend that forgets one is rejected at class-creation time instead of raising `NotImplementedError` somewhere
  in a call chain.
* ⚠️ Neither `SupervisedThreadException` nor the new `VersionValidatorException` has a default message. An
  exception without text says nothing to whoever catches it.

  See *Bug Fixes*: the one call site inside pyTooling that already used the new order was broken by the old
  signature.

* ⚠️ **Annotations in 26 modules are no longer evaluated at definition time**
  ([#315](https://github.com/pyTooling/pyTooling/pull/315),
  [#318](https://github.com/pyTooling/pyTooling/pull/318)). Those modules carry
  `from __future__ import annotations`, so on Python 3.11-3.13 `SomeClass.__annotations__` yields **strings** where
  it previously yielded type objects; on Python 3.14 ([PEP 649](https://peps.python.org/pep-0649/)) they are
  computed lazily and read as before. Code introspecting pyTooling classes at runtime has to resolve them itself:

  ```python
  from typing import get_type_hints

  get_type_hints(SomeClass)     # works on every supported version
  SomeClass.__annotations__     # strings on 3.11-3.13
  ```

# Changes

* `pyTooling.MetaClasses.ExtendedType` forwards **any further class keyword argument** to
  `__init_subclass__`, the way `type` does ([#303](https://github.com/pyTooling/pyTooling/pull/303)). Without it a
  class using `ExtendedType` could not accept its own class keywords - which is what blocked `@abstractclass` on
  the classes that needed it most.
* The 34 hand-written abstract guards in `pyTooling.CLIAbstraction` are replaced by `@abstractclass`
  ([#303](https://github.com/pyTooling/pyTooling/pull/303)): **559 lines deleted, 160 added** across 9 modules, and
  68 `# TODO:` comments with them.
* The workarounds for Python versions before 3.11 are gone - `setup.py` and the pipeline have required 3.11 since
  v8.0: `ParamSpec` is imported from `typing` unconditionally, `AttributeError.name` is read instead of parsing
  the message, and `__ilshift__`/`__iand__`/`__ior__`/`__ixor__` return `typing.Self`.
* **A `@readonly` property hands out the getter's type instead of `Any`**
  ([#317](https://github.com/pyTooling/pyTooling/pull/317)). `readonly` is a `property` subclass, which costs it the
  special-casing a type checker applies to `property` itself: every read of such a property was `Any`, and that
  spreads - a comparison of two of them, or a method returning one, became `Any` as well. It is generic in the
  getter's return type now and declares `__get__`, so downstream code gets a real type. `readonly.getter()` returns
  a `readonly` as well, rather than the plain `property` the type stubs promise.
* **`from __future__ import annotations` is usable in a class built by `ExtendedType`**
  ([#309](https://github.com/pyTooling/pyTooling/pull/309)). [PEP 563](https://peps.python.org/pep-0563/) turns every annotation in a module into a
  string, and the meta-class inspects annotations to compute `__slots__` and to tell a `ClassVar` from a field - so
  it used to make a slot out of a class variable and a slot named after a string. It resolves postponed
  annotations before inspecting them now, with a textual `ClassVar` fallback for the annotation it cannot
  evaluate. The pay-off is that a forward reference no longer needs quotes:
  `Nullable[TerminalApplication]` instead of `Nullable["TerminalApplication"]`.
  **`pyTooling.TerminalUI` was the first module switched over**
  ([#315](https://github.com/pyTooling/pyTooling/pull/315)) and
  [#318](https://github.com/pyTooling/pyTooling/pull/318) finished the job: the 25 remaining modules carry the
  future import, and all 316 of their string annotations are plain annotations. 308 of them were genuine forward
  references - a class referring to itself or to a class defined further down - which is why the future import is
  required rather than cosmetic: Python 3.11-3.13 evaluate annotations eagerly and would raise `NameError` at
  import time without it. The same pull-request groups every import section into future, standard library,
  third-party and own-package imports.


# Bug Fixes

* `pyTooling.Warning`:
  * ⚠️ **`ThreadSupervisor.ReRaise()` raised `TypeError` whenever two or more threads had failed.** It built its
    `ExceptionGroup` with `SupervisedThreadException(f"Thread ... failed.", cause=ex)` - one positional argument
    against a signature requiring two - so the caller got
    `TypeError: __init__() missing 1 required positional argument: 'message'` instead of the group. Nothing
    covered `ThreadSupervisor`, which is how it survived.
  * `SupervisedWarningCollector.__init__` documented two of its five parameters.
* `pyTooling.MetaClasses`:
  * ⚠️ **An `@abstractmethod` reached through a normal base-class *and* a mixin raised
    `TypeError: Method 'X' is used by multiple classes`** ([#300](https://github.com/pyTooling/pyTooling/pull/300)).
    Two defects in one shape: the class' own method was overwritten while collecting the inherited ones, and
    `functools.wraps` copied `__classobj__` onto the wrapper, so the wrapper claimed to belong to the base-class.
    A concrete method in the same diamond was fine, which is why it looked like an `@abstractmethod` problem. This
    is what blocked the abstract stubs in `Configuration.Node` and `Filesystem.Base`.
* `pyTooling.CLIAbstraction`, `pyTooling.Dependency`, `pyTooling.LinkedList`:
  * **Nine exceptions were raised with no message at all**
    ([#302](https://github.com/pyTooling/pyTooling/pull/302)) - a caller got a traceback and nothing else. Each says
    now what was expected and what arrived. One `LinkedList` guard turned out to be unreachable in the shape it was
    written and is corrected rather than described.
* `pyTooling.Graph` ([#298](https://github.com/pyTooling/pyTooling/pull/298)):
  * ⚠️ **`Vertex.Delete()` and `Link.Delete()` raised `NameError` - always.** Both ended in
    `assert getrefcount(self) == 1`, and `getrefcount` was never imported, so deleting a vertex or a link was
    impossible. The assertion is removed rather than repaired: a reference count of 1 cannot be guaranteed once a
    caller holds the object.
  * ⚠️ **A deleted vertex left its edges and links behind in the graph's registries.** `Delete()` unlinked the
    vertices but never removed the edge from `_edgesWithID` / `_edgesWithoutID`, so the graph still counted and
    iterated objects that no longer existed. `Edge._Unregister()` and `Link._Unregister()` do it in one place now,
    including the subgraph case and a link crossing a subgraph boundary, which is registered on both.
  * ⚠️ **`Base.Delete()` dropped the attribute dictionary** (`self._dict = None`) instead of clearing it, so every
    later `len()` or `in` on the element raised `TypeError: 'NoneType' object is not subscriptable`.
  * ⚠️ **`Link.Reverse()` had never worked**: it removed the link from `_outboundEdges` / `_inboundEdges`, where a
    link is never registered, so every call raised `ValueError: list.remove(x): x not in list`.
* `pyTooling.Versioning`:
  * A validator rejecting a parsed version raised a bare `ValueError`, indistinguishable from *this string is not
    a version at all*. `SemanticVersion.Parse` and `CalendarVersion.Parse` raise `VersionValidatorException` now,
    which carries the rejected version. The finding listed one site; `CalendarVersion.Parse` was a second.


# Documentation

**Every module, class, class field, method, dunder method and nested function in the package now has a doc-string.**
That was eleven pull-requests of work and it is what most of this release is:

* **Modules** ([#282](https://github.com/pyTooling/pyTooling/pull/282)) - 10 modules in the package had none, and 88
  testsuite modules carried a wrong copy of somebody else's (the git tests were titled `mkdir`, `SizeOf` claimed to be
  `isnestedclass`).
* **Classes** ([#280](https://github.com/pyTooling/pyTooling/pull/280)) - 47 classes.
* **Class fields** ([#279](https://github.com/pyTooling/pyTooling/pull/279)) - 127 fields across 21 modules got a
  trailing `#:` comment, so Sphinx documents them.
* **Methods** - the methods that had none, one module scope per pull-request so each stayed reviewable:

  * [#284](https://github.com/pyTooling/pyTooling/pull/284) - `pyTooling.Graph.GraphML`, the element methods (17).
  * [#285](https://github.com/pyTooling/pyTooling/pull/285) - `pyTooling.Graph.GraphML`, the graph and document
    methods (28).
  * [#286](https://github.com/pyTooling/pyTooling/pull/286) - `pyTooling.Filesystem` and its `Docker` module (18).
  * [#287](https://github.com/pyTooling/pyTooling/pull/287) - `pyTooling.Configuration.JSON`,
    `pyTooling.Configuration.YAML` and `pyTooling.Dependency.Python` (21).
  * [#288](https://github.com/pyTooling/pyTooling/pull/288) - the long tail: `pyTooling.MetaClasses`,
    `pyTooling.Attributes.ArgParse`, `pyTooling.Warning`, `pyTooling.CLIAbstraction`, `pyTooling.Cartesian2D`,
    `pyTooling.Cartesian3D`, `pyTooling.GenericPath.URL`, `pyTooling.LinkedList`, `pyTooling.Tracing`,
    `pyTooling.Tree` and `pyTooling.Versioning` (23 across 12 files).
  * [#289](https://github.com/pyTooling/pyTooling/pull/289) - `pyTooling.Graph`, the deletion and traversal
    methods (12).
  * [#290](https://github.com/pyTooling/pyTooling/pull/290) - the 33 **nested functions**, across 12 modules. They
    are invisible to the rendered documentation, but they are what a reader of the source hits first.
* **Dunder methods** ([#281](https://github.com/pyTooling/pyTooling/pull/281)) - 109 of them.
* **Field lists** ([#283](https://github.com/pyTooling/pyTooling/pull/283)) - 134 `:param:`, 89 `:returns:` and 27
  `:raises:` entries that were missing, wrong or named a parameter that doesn't exist.

Two sweeps closed what the doc-strings then referenced:

* **41 cross-references pointed nowhere** ([#301](https://github.com/pyTooling/pyTooling/pull/301)) - Sphinx reports
  these only under `nitpicky`, so they had accumulated, including the plain typo `pyTooling.Metaclasses.ExtendedType`.
  Together with 4 mixed-format `.. seealso::` blocks, 2 duplicated entries and 3 misaligned `import` blocks, that
  check is at zero.
* **Neighbouring modules cross-reference each other** ([#295](https://github.com/pyTooling/pyTooling/pull/295)) - 27
  module-level `.. seealso::` blocks, so a reader landing on `CallByRef` finds `Attributes` and `Common` without
  going back to the index.

Three conventions were settled and applied package-wide while doing it:

* ⚠️ **A property setter carries no doc-string** ([#278](https://github.com/pyTooling/pyTooling/pull/278)). Sphinx
  renders the getter's, so a setter's text was never displayed. The nine in `pyTooling.CLIAbstraction` are folded into
  their getters, and two getters that claimed to be read-only were corrected.
* **A `.. seealso::` block is a definition list** ([#291](https://github.com/pyTooling/pyTooling/pull/291)) - the target
  as the term, a `|rarr|` one-liner as its description. 13 blocks still used bullets.
* **An exception's advisory `add_note()` is repeated in its `:raises:` description**
  ([#294](https://github.com/pyTooling/pyTooling/pull/294), [#296](https://github.com/pyTooling/pyTooling/pull/296)) -
  a caller reading the documentation gets the same hint as a caller reading the traceback.

Pages:

* `doc/Testing.rst` is new: what application testing is, the mixin in use, the assertion and the ANSI helper.
* `doc/Decorators.rst` describes merging and the order enumeration.
* `doc/Dependency.rst` is new - the module was referenced from the index page and had no page of its own.
* `doc/MetaClasses.rst` documents `abstractclass` next to `abstractmethod` and `mustoverride`, and the
  `.. seealso::` blocks of the four decorators point at each other.
* ⚠️ `doc/Terminal/index.rst` ([#276](https://github.com/pyTooling/pyTooling/pull/276)) documented two classes that no
  longer exist and nothing that does. Page and tutorial are rewritten.
* **The terminal application tutorial's examples are files, and they are executed**
  ([#319](https://github.com/pyTooling/pyTooling/pull/319)). Step 6 documented a `help` command handler reading
  `args.Command` without declaring the argument - the program in the tutorial raised
  `AttributeError: 'Namespace' object has no attribute 'Command'` when it was run. It declares a `StringArgument`
  now. The examples live in `tests/example/TerminalApplication` as complete, runnable programs, are pulled into the
  page with `literalinclude`, and each step is laid out as a two-column grid like the landing page: description on
  the left, code on the right.

# Unit Tests

* `tests/unit/Warning/Supervisor.py` is new: all four paths of `ThreadSupervisor.ReRaise()`. That class had no
  tests at all.
* `tests/unit/Versioning/Validators.py` is new: six testcases for the validator exception.
* `tests/unit/Testing/` covers the new module with 12 testcases, using the Python interpreter itself as the
  program under test so they need nothing beyond the standard library.
* `tests/unit/Decorators/Decorators.py` covers merging, both orders, the affixes, and a doc-string that is missing
  on either side.
* `tests/unit/MetaClasses/Abstract.py` covers the declared-abstract class: the marker, the message, that it is not
  inherited, a decorated class derived from a decorated class, and a class without the meta-class.
* `tests/unit/Graph/__init__.py` checks that both duplicate-identifier errors carry their ID.
* `tests/unit/Documentation.py` is new: it imports every tutorial example, parses `help version` and `help`
  through the parser of step 6 to prove the `help` command's argument exists and is optional, and runs the testcase
  the tutorial prints - 6 testcases, 12 subtests.
* **The whole suite derives from `pyTooling.Testing.Testcase`** instead of `unittest.TestCase` - 68 modules,
  including `tests/performance`.

# GitHub Pipeline

* Tag pipelines are named after the tag, via `run-name`.
* ⚠️ **GitHub Pages is no longer published from a development branch**
  ([#297](https://github.com/pyTooling/pyTooling/pull/297)). The `github-pages` environment admits `dev` and `main`
  only, so the deploy job on any other branch was failed by GitHub before a runner was assigned - 2 s, no steps, no
  log. Every `claude/*` pull-request therefore showed a red pipeline that had nothing to do with its changes, which
  is exactly how a real failure gets overlooked. One `if:` on the reusable-workflow call.

----------
# Related Issues and Pull-Requests

**Merged into `dev` for this release** (all merged as of 2026-08-20):

| | |
|---|---|
| [#266](https://github.com/pyTooling/pyTooling/pull/266), [#268](https://github.com/pyTooling/pyTooling/pull/268), [#270](https://github.com/pyTooling/pyTooling/pull/270) | `pyTooling.Testing`, its documentation page and the `Testcase` base-class |
| [#269](https://github.com/pyTooling/pyTooling/pull/269) | the validator exception, the constructor convention and the `ThreadSupervisor` fix - **this is what makes v9.0.0 a breaking release** |
| [#271](https://github.com/pyTooling/pyTooling/pull/271) | removing `UnhandledWarningException` |
| [#272](https://github.com/pyTooling/pyTooling/pull/272) | the `pyTooling.Dependency` documentation page |
| [#273](https://github.com/pyTooling/pyTooling/pull/273) | the duplicate-identifier errors |
| [#274](https://github.com/pyTooling/pyTooling/pull/274) | `abstractclass`, and the test suite moving to `Testcase` |
| [#275](https://github.com/pyTooling/pyTooling/pull/275) | the integer-key stash and two test stubs |
| [#276](https://github.com/pyTooling/pyTooling/pull/276) | `pyTooling.TerminalUI` documented, `CheckPythonVersion()` removed |
| [#277](https://github.com/pyTooling/pyTooling/pull/277) | the Python < 3.11 workarounds |
| [#278](https://github.com/pyTooling/pyTooling/pull/278)-[#296](https://github.com/pyTooling/pyTooling/pull/296) | the documentation campaign, see *Documentation* - including [#281](https://github.com/pyTooling/pyTooling/pull/281) (dunder doc-strings) and [#295](https://github.com/pyTooling/pyTooling/pull/295) (cross references), both merged 2026-08-19 |
| [#292](https://github.com/pyTooling/pyTooling/pull/292) | `getFullyQualifiedName()` in 28 exception messages |
| [#293](https://github.com/pyTooling/pyTooling/pull/293) | the JSON and YAML nodes inherit their doc-strings |
| [#297](https://github.com/pyTooling/pyTooling/pull/297) | GitHub Pages is not published from a development branch |
| [#298](https://github.com/pyTooling/pyTooling/pull/298) | `Delete()` unregisters where it registered, and `Link.Reverse()` works at all |
| [#299](https://github.com/pyTooling/pyTooling/pull/299) | the eight bare `Exception` raises get a type |
| [#300](https://github.com/pyTooling/pyTooling/pull/300) | the abstract method reached through a mixin as well |
| [#301](https://github.com/pyTooling/pyTooling/pull/301) | 41 cross-references that pointed nowhere |
| [#302](https://github.com/pyTooling/pyTooling/pull/302) | nine exceptions that said nothing |
| [#303](https://github.com/pyTooling/pyTooling/pull/303) | one decorator instead of 34 hand-written abstract guards |
| [#304](https://github.com/pyTooling/pyTooling/pull/304) | the four `Configuration.Node` stubs every backend implements are abstract |
| [#305](https://github.com/pyTooling/pyTooling/pull/305) | a configuration is read-only |
| [#306](https://github.com/pyTooling/pyTooling/pull/306) | written-out type names instead of links to base types |
| [#307](https://github.com/pyTooling/pyTooling/pull/307) | the missing-dependency report, its exit code and the rename to `MissingDependencyException` |
| [#308](https://github.com/pyTooling/pyTooling/pull/308) | every optional parameter says so, in one form |
| [#310](https://github.com/pyTooling/pyTooling/pull/310) | the built-in generics replace the `typing` aliases |
| [#311](https://github.com/pyTooling/pyTooling/pull/311) | an absent version part stays absent |
| [#309](https://github.com/pyTooling/pyTooling/pull/309) | `ExtendedType` understands postponed annotations (PEP 563), so `from __future__ import annotations` is usable - see *Changes* |
| [#315](https://github.com/pyTooling/pyTooling/pull/315), [#317](https://github.com/pyTooling/pyTooling/pull/317) | the first module using `from __future__ import annotations`, and `@readonly` handing out the getter's type |
| [#312](https://github.com/pyTooling/pyTooling/pull/312), [#313](https://github.com/pyTooling/pyTooling/pull/313), [#314](https://github.com/pyTooling/pyTooling/pull/314), [#316](https://github.com/pyTooling/pyTooling/pull/316) | static typing: mypy **931 → 824**, grouped by error code, one code per pull-request. #316 is the one that found defects: `LinkedList.Node.InsertNodeBefore()`/`InsertNodeAfter()` on a node belonging to no list raised `AttributeError` deep inside instead of reporting the misuse || [#318](https://github.com/pyTooling/pyTooling/pull/318) | the remaining 25 modules switched to postponed annotations, 316 string annotations unquoted |
| [#319](https://github.com/pyTooling/pyTooling/pull/319) | the tutorial's examples moved into executed files, and its `help` command fixed |

**Consumed by** [edaa-org/pyEDAA.Reports#168](https://github.com/edaa-org/pyEDAA.Reports/pull/168), which needs this
release on PyPI.


--------
Published from [Pipeline](https://github.com/pyTooling/pyTooling/actions/runs/32421979053) workflow triggered by github-actions[bot] on 2026-08-20 22:05:15 UTC.

This automatic release was created by [pyTooling/Actions](http://github.com/pyTooling/Actions)::Release.yml
