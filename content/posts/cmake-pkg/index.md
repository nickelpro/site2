---
title: "Modern CMake Packaging: A Guide"
display: "Modern CMake Packaging: A&nbspGuide"
subtitle: "Or, A Candle in the Dark"
date: 2022-12-19T17:00:00-04:00
image: "social-media"
draft: false
description: "A conversational guide to modern CMake packaging for C++"
epigraph: "Pretty sure I just failed my Calc III final.<br>I hate calculus, but
I love CMake. Let's talk about CMake."
---
There is
[a five year old `CMake` bug](https://gitlab.kitware.com/cmake/cmake/-/issues/17282)
describing the need for a "cookbook" to walk users through
effective packaging of `CMake` projects. As with so many corners of `CMake`
usage, the technical documentation extensively describes _how_ everything works,
but gives no hints to _which_ components of the extensive `CMake` ecosystem
should be used. Inevitably, projects end up cobbling together code copied from
other sources and gently massaged into a "works for me" state.

Due to other immense obstacles in the C/C++ package ecosystem, this has not been
seen as the most pressing issue. However, with the rise of package managers like
`conan` and especially `vcpkg` (which makes `CMake` central to its
architecture), ensuring that C/C++ libraries have functional packaging routines
has grown in importance.

{{< img src="candle" darkmode="filter" style="width:80%; margin-left:auto; margin-right:auto;"
imgstyle="border-top-left-radius:50%; border-top-right-radius:50%" />}}

Absent an official cookbook, widespread community consensus, a qualified expert,
or well-liked town fool to provide guidance; I provide my dim, flickering
advice for how to best take advantage of the `CMake` packaging facilities.

{{< collapse >}}
Don't like reading? _Don't like me?_

Got you covered, [example repo is here](https://github.com/nickelpro/NavidsonExample)

Usage demonstration of that repo [is here](https://github.com/nickelpro/AshTreeExample)

Happy packaging!
{{< /collapse >}}

## Package? Never heard of her.

Part of the problem is the term "packaging" doesn't have a formal definition in
the C/C++ ecosystem in the same way that it does for other languages. The quick
definition is this: packaging is the process of generating and populating a
directory structure that contains everything a third-party project will need to
use your code. We'll also need some other definitions:

* **Source Tree:** File system location of the project source code

* **Build Tree:** File system location where the actual building and linking of
code happens

* **Install Tree:** File system location where the aforementioned packaging
happens. Typically files will be moved out of the build tree into the install
tree

* **Package:** Collective name for the contents of the install tree. This
includes artifacts from the build process as well as version information and
other metadata files

* **Target:** A named, distinct collection of build artifacts, headers, or other
products of the codebase placed into the install tree

{{< collapse >}}
"Target", I hear you say, "I know that one." Yep, packaging targets and
"target-driven" modern `CMake` are closely related. If you're familiar with the
latter learning the former won't be so bad.

Unfortunately, there is some friction between project-native targets and
`IMPORTED` targets from other sources. We'll get there.
{{< /collapse >}}

## Packaging Starts at Home

Before we get to packaging specific commands we need to briefly talk about how
`CMake` targets interact with one another. Consider the library example from
**Figure 1**.

{{< collapse label="Figure 1" >}}
```CMake
cmake_minimum_required(VERSION 3.25)

project(NavidsonRecord LANGUAGES CXX VERSION 1.5.97)

add_library(house SHARED)
target_sources(house PRIVATE hallway.cpp)
target_sources(house PUBLIC
  FILE_SET HEADERS
  BASE_DIRS include
  FILES include/labyrinth.hpp
)
```

`FILE_SET`s are cool, and you should be using them, but that's not the only
reason I include them here. By using a `FILE_SET` we dodge a difficult
discussion about `BUILD_INTERFACE` and `INSTALL_INTERFACE` generator
expressions. Use `FILE_SET` to add headers to your targets, it Just Works™.
{{< /collapse >}}

Here we have a project called `NavidsonRecord`. We pause just long enough to
note that the `project` directive is used to annotate the current version and
that this will be important later.

{{< img src="machine" resize="300x q90" darkmode="diff" imgstyle="border-radius:50%;" style="shape-outside: circle(); width:40%; float: right; margin: 0.5rem 0 0.5rem 0.5rem;" />}}

The project consists of a single shared library named `house` which is itself
composed of a single compilation unit named _hallway.cpp_, and some number of
headers stored in the source tree under the _include_ folder. One of these,
_labyrinth.hpp_, is listed as a source file. While any files inside the
`BASE_DIRS` will be visible for inclusion during the build process, only files
listed under the `FILES` parameter will be installed.

Now let's address the scope keywords: `PUBLIC`, `PRIVATE`, and `INTERFACE`.

When using directives from the `target_` family, such as `target_sources`, we
use a scope keyword to describe how the associated resources should be used.
`PRIVATE` resources will be used only by the associated target, `INTERFACE`
resources will be used only by dependents of the associated target, and
`PUBLIC` resources will be used by both.


## Keep the Goal in Mind

Let's talk about what files we need to produce:[^1]

* **package-config-version.cmake:**[^2] The version file allows `CMake` to discover
version information without fully invoking or loading your package

* **package-config.cmake:**[^3] The configuration file is responsible for loading
dependencies and making targets available to the current build session

* **package.pc:** The package config file is the format understood by the
venerable `pkg-config` program and serves as a pidgin used by build tools to
talk to one another about dependencies. Package config is a bad format, but it's
the least common denominator. If a consumer of your library doesn't use `CMake`
they'll need this file.

[^1]: **package** is a placeholder name in these examples
[^2]: The naming convention **PackageConfigVersion.cmake** is also supported,
but I like lower case letters
[^3]: Ditto

These files, along with all files associated with the package's targets, need
to be placed inside the install tree. At that point our job is done. What
eventually happens to the install tree depends on how the end-user is consuming
our package. It's entirely possible the "install tree" _is_ the user's program
or `/usr` directory.

## The 5½ Minute CMake

Best practice for packaging involves two helper scripts,
`CMakePackageConfigHelpers` and `GNUInstallDirs`.

`GNUInstallDirs` provides the `CMAKE_INSTALL_` family of variables, which
provide standard path information for the install tree. `CMakePackageConfigHelpers` provides the `write_basic_package_version_file`
macro, which we'll use to generate the **package-config-version.cmake** file.

{{< collapse >}}
`CMakePackageConfigHelpers` provides one other macro,
`configure_package_config_file`, which can be used to generate the
**package-config.cmake** file. This macro supports an older style of `CMake`
packaging which would `set()` variables with necessary package information. It
ensures such variables are "relocatable", meaning they correctly point to
wherever the install location happens to be rather than use a hardcoded path.

We're not going to need this macro because we're not going to be "generating"
the config file at all, and instead of variables we'll be using `CMake` targets
to communicate dependencies.
{{< /collapse >}}

In **Figure 2** we use these macros and variables to generate and install the
version file for the `NavidsonRecord` project.

{{< collapse label="Figure 2" >}}
```CMake
write_basic_package_version_file(
  ${CMAKE_CURRENT_BINARY_DIR}/navidson-config-version.cmake
  COMPATIBILITY AnyNewerVersion
)

install(FILES
  ${CMAKE_CURRENT_BINARY_DIR}/navidson-config-version.cmake
  DESTINATION ${CMAKE_INSTALL_DATADIR}/navidson
)
```
{{< /collapse >}}

Quick notes:
* Whatever name is used for the folder and file names, in this example
"navidson", _is the package name_. This is the name that will be used with
`find_package()` by dependencies to load your project. The project name is
irrelevant here

* The project version we noted above will be used for the purpose of determining
compatibility. It can be overridden using the `VERSION` parameter

* Header-only libraries and other projects that don't involve compilation should
pass the `ARCH_INDEPENDENT` parameter to avoid checking architecture
compatibility

Next let's address the `pkg-config` file, for this we need to write an input
template such as **Figure 3**.

{{< collapse label="Figure 3" >}}
```
# navidson.pc.in

prefix=${pcfiledir}/../..
exec_prefix=${prefix}
includedir=${prefix}/@CMAKE_INSTALL_INCLUDEDIR@
libdir=${exec_prefix}/@CMAKE_INSTALL_LIBDIR@

Name: navidson
Description: My dear Zampanò, who did you lose?
Version: @PROJECT_VERSION@
Libs: -L${libdir} -lhouse
Cflags: -I${includedir}
```
The `pkg-config` format is a subject unto itself, and I cannot hope to cover it
completely here. The approach presented is reasonable but provided without
further comment, I would probably just get it wrong.

I will briefly mention that it sometimes appropriate to use the
`CMAKE_INSTALL_FULL_` family of variables to achieve "relocatability" instead of
trying to architect the `pkg-config` file itself to be relocatable.
{{< /collapse >}}


In **Figure 4** we fill in the `@` variables using the `configure_file`
directive, then install the resulting generated file in the same way as the
version file.


{{< collapse label="Figure 4" >}}
```CMake
configure_file(
  ${CMAKE_CURRENT_SOURCE_DIR}/cmake/navidson.pc.in
  ${CMAKE_CURRENT_BINARY_DIR}/navidson.pc
)

install(
  FILES ${CMAKE_CURRENT_BINARY_DIR}/navidson.pc
  DESTINATION ${CMAKE_INSTALL_LIBDIR}/pkgconfig
)
```
{{< /collapse >}}

## Heading \#5

We're now ready for the meat, the `install(TARGETS)` and `install(EXPORT)`
directives. These, like `pkg-config`, are complex commands with many different
knobs and buttons. While we'll explore a reasonable usage, the important take
away is that you _should be using_ `install(EXPORT)` instead of older styles
of installing and exporting targets.

{{< collapse >}}

A specific callout, `install(EXPORT)` and `export()` are very different
directives. The latter supports exporting targets from the build tree, and thus
is orthogonal to a discussion of "packaging".

My personal hot take: you shouldn't use `export()` under effectively any
circumstances. It can lead only to confusion. The only valid example for
`export()` given by the `CMake` docs is incredibly niche:

>  This is useful during cross-compiling to build utility executables that can
> run on the host platform in one project and then import them into another
> project being compiled for the target platform.

Which I'm forced to concede is somewhat valid, but I've never seen `export()`
used for this in the wild. I've only experienced it being misused. So my
blanket advice is: just don't.

{{< /collapse >}}

Enough foreplay, **Figure 5** is the code we need to install our `house` target.

{{< collapse label="Figure 5" >}}
```CMake
install(
  TARGETS house
  EXPORT navidsonTargets
  FILE_SET HEADERS
)

install(
  EXPORT navidsonTargets
  NAMESPACE nvr::
  DESTINATION ${CMAKE_INSTALL_DATADIR}/navidson
)
```

Oh ya, that's the stuff
{{< /collapse >}}


Alright, brace yourself for some overloaded terms. The first `install(TARGETS)`
directive takes a list of one or more **targets** and associates them with what
`CMake` calls an **export**. In **Figure 5** the export is named
`navidsonTargets`, which is a typical naming scheme.

{{< img src="pump" darkmode="diff" imgstyle="border-radius:20%;" resize="x350 q90" style="shape-outside: margin-box; border-radius: 20%; width:30%; float: left; margin: 1rem 1rem 0 0;" />}}

An **export** is a different _type_ than `CMake` variables or targets, but it
works on a similar principle. In the same way _files_ get associated with
targets, the `install(TARGETS)` directive associates targets with an export.
And just like how we can call `target_sources` repeatedly to add files to a
given target, we can call `install(TARGETS)` repeatedly to add targets to a
given export.

The `install(EXPORT)` directive generates a cmake file for a given export
directly into the install tree with the name "\[exportName\].cmake", so in this case
"navidsonTargets.cmake". This file does all the necessary legwork to
setup our targets in the parent project. In the parent project our targets
will have their names prefixed by the `NAMESPACE`, so `house` will be known as
`nvr::house`.[^4]

[^4]: Convention is to use the package name as the namespace, so a good citizen
would use `navidson::house`. [See this discussion on Reddit](https://www.reddit.com/r/cpp/comments/zq5er9/modern_cmake_packaging_a_guide/j0wnqj2/?context=2)

## The End

"But wait!" you cry, "You said we needed three files, where is
_navidson-config.cmake_?"

Good, you're paying attention. You'll find it in **Figure 6**, try not to be
disappointed.

{{< collapse label="Figure 6" >}}
```CMake
# navidson-config.cmake
# find_package(RandomDependency CONFIG REQUIRED)
include(${CMAKE_CURRENT_LIST_DIR}/navidsonTargets.cmake)
```

We'll need to install this file into the install tree, we can add it to the
install directive from Figure 2.

```CMake
install(FILES
  ${CMAKE_CURRENT_SOURCE_DIR}/cmake/navidson-config.cmake
  ${CMAKE_CURRENT_BINARY_DIR}/navidson-config-version.cmake
  DESTINATION ${CMAKE_INSTALL_DATADIR}/navidson
)
```
{{< /collapse >}}

If our library had any dependencies we would add the code to find them here (as
well as in our _CMakeLists.txt_ file). In this example we don't, so
**navidson-config.cmake** is a single line of code, which includes the generated
export file. The only thing left to do is make sure it gets installed alongside
the version file and we're done.

Effectively zero projects I've look at do this in the "modern" way so I'd like
to briefly address silly things you shouldn't be doing in the config file:

* **Ad hoc include guards:** First off, `CMake` already has an `include_guard`
directive. Second off, they're unnecessary, the export targets already protect
against double inclusion in a far more comprehensive fashion than you will come
up with.

* **@PACKAGE_INIT@:** This is a substitution that comes from
`CMakePackageConfigHelpers` and as far as I can tell it's obsolete in an
**export**/`find_package` based workflow. It doesn't do anything except define
macros you shouldn't be using anyway.

* **set_and_check():** Macro provided by the above substitution. The generated
export targets already do everything you would have previously used this macro
for.

* **check_required_components():** Also from the above substitution. Superceded
by `find_package(REQUIRED)`.

* **@PACKAGE_NAME@ and other such silliness:** How often are you changing the
name of your entire package? How hard is find+replace? I never say this, but
**YAGNI**.

There are very few reasons for your project config file to consist of anything
other than `find_package()` and `include()` directives. While there are some
reasons to split out targets into separate exports (for example, if you have
optional dependencies that enable/disable certain targets), most projects will
get away with a set of zero or more calls to `find_package()` followed by a
single `include()` of their export file.

## Afterword

And that's it. Example repo is available [here](https://github.com/nickelpro/NavidsonExample).
Example of using that example repo is [here](https://github.com/nickelpro/AshTreeExample),
to prove I'm not a crank. I'm going to go be sad about Calculus III. If I fail
it next semester too I'll write more about `CMake`.
