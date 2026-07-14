---
title: "On Building Shared Libraries from Modules"
subtitle: "The Interface Unit Symbol Ownership Problem"
subsubtitle: "or, One man's struggle to get 5 lines<br>of code to link correctly"
mediaTitle: "Building Shared Libraries from Modules: The Interface Unit Symbol Ownership Problem"
description: "Discussing the problem of creating shared libraries when using
C++20 modules."
epigraph: "For it is plain, that every word we speak is, in some degree, a
diminution of our lunge by corrosion, and, consequently, contributes to the
shortening of our lives. An expedient was therefore offered, \"that since words
are only names for things, it would be more convenient for all men to carry
about them such things as were necessary to express a particular business they
are to discourse on.\""
epigraphAuthor: "Jonathan Swift, Gulliver's Travels"
preEpigraph: "This post is going to cover some well-known C++ semantics. If
you're already familiar with the basics of vague linkage and shared library
symbol visibility,
<a href=\"#whos-symbol-is-it-anyway\">you can skip the preliminaries.</a>"
image: "social-media"
date: 2026-07-09T8:00:00-04:00
draft: true
---

Shared libraries are not found anywhere in the ISO {{< rb >}}C++{{< /rb >}}
standard. Nor, for that matter, are static libraries. Or really libraries of any
kind.{{< sn hdr-only >}} However, it's incorrect to claim the standard has
nothing at all to say about source code translation and linking,
{{< rb >}}[\[basic.link\]](https://eel.is/c++draft/basic.link){{< /rb >}} is
dedicated to the subject. The requirements laid out there describe what
capabilities must be implemented, although not how.{{< sn dyn-link >}}

{{< sidenote ident=hdr-only >}}
Are header-only libraries addressed by the standard? In a sense, I suppose, to
the degree headers are addressed at all.
{{< /sidenote >}}

{{< sidenote ident=dyn-link side=left >}}
From the perspective of the standard, library binaries represent a kind of
deferred, partial, program construction.
{{< /sidenote >}}

This is academic, and boring. We don't care precisely where the implementation
decisions stop and the standard begins, so long as everything works. Problems
arise when toolchains disagree on implementation decisions in ways visible
to the programmer. Unfortunately, {{< rb >}}C++{{< /rb >}} modules are making
these implementation decisions visible.

{{<banner
  src="acqueduct"
  alt="An illustration of a ruined acqueduct"
  darkmode="img-fill"
  style="border-radius: 5% / 20%;"
  width="40%"
/>}}

[In a previous post](/posts/bmi-compatibility) we discussed how the
{{< rb blue >}}built module interface{{< /rb >}}, or BMI, constructed from a
module unit is a fragile, compiler-invocation specific artifact. This is mostly
the build system's problem, and can be ignored by users unless something goes
wrong.

We handwaved what information ends up in the BMI, leaving it at
"declarations".{{< sn template-defs >}} This works nicely for describing BMIs
as a kind of "serialized header". But of course, headers contain more than
declarations, they also contain `inline` definitions. In this post we'll explore
why these `inline` definitions create a thorny problem for modules, especially
when combined with shared libraries.

{{< sidenote ident=template-defs >}}
I didn't explicitly include template definitions in that explanation. So I'll
do so here: BMIs contain template definitions. The proof is left as an exercise
for the reader.
{{< /sidenote >}}

## Vague Linkage Primer

{{< rb blue >}}Vague Linkage{{< /rb >}} is a headline feature of
{{< rb >}}C++{{< /rb >}}. It is one of the major departures of the language
from its progenitor, plain {{< rb >}}C{{< /rb >}}. The `inline` keyword is the
usual entry point to discussing {{< rb blue >}}vague linkage{{< /rb >}}
and I personally find it useful to discuss the version of the keyword that
{{< rb >}}C{{< /rb >}} later adopted before introducing how the mechanics work
in {{< rb >}}C++{{< /rb >}}.{{< sn inline-keyword >}}

{{< sidenote ident=inline-keyword side=left >}}
The `inline` keyword goes all the way back to Stroustrup's original
{{< rb >}}C with Classes{{< /rb >}}. The {{< rb >}}C{{< /rb >}} language
wouldn't adopt it until the 1999.
{{< /sidenote >}}

Consider the following example:

{{<
  collapse label="Figure 1: Inline in C"
  preamble="If you want to explore this concept for yourself, click the godbolt link."
  godbolt="https://godbolt.org/z/nqj3j8158"
>}}
```c
// main.c
#include <impl.h>

int main() {
  return f(5);
}

// impl.h
inline int f(int num) {
  return num * num;
}

// impl.c
int f(int num) {
  return num + num;
}
```
Try changing the optimization level by switching `‑DCMAKE_BUILD_TYPE=Debug` to
`‑DCMAKE_BUILD_TYPE=Release`.
{{< /collapse >}}

The mechanics here are simple. There is one canonical,
external,{{< sidenote >}}i.e. not `inline`{{< /sidenote >}}
definition of `f()`, provided by `impl.c`. At low optimization levels, the code
in `impl.h` is treated only as a declaration of `f()`, and the linker resolves
the call in `main()` to the canonical definition. Thus the program returns `10`.

{{< marginalia side=left
  src="stahlstadt"
  alt="An illustration of two men repelling into Stahlstadt"
  style="margin: -3rem;"
  imgstyle="height:25rem; width:auto; border-radius: 20% 20% 50% 50% / 5% 5% 10% 10%;"
  darkmode="img-fill"
/>}}

The compiler is allowed to treat the implementation of `f()` provided by
`impl.h` as an "inline definition" available for inlining directly into
`main()`, and at higher optimization levels it does so; the program returns
`25`.

So, the code for `f()` is always either:

  * Inlined directly from the header, no call site, no manifestation of `f()` in
    the `main.c` translation unit (TU).

  * A call site which resolves to the definition of `f()` provided by `impl.c`.

If we remove `impl.c`, [we get a link error at low optimization levels](https://godbolt.org/z/Tf5jnzhrr),
because no external definition of `f()` exists.

These semantics makes the toolchain's job very easy; there is always one
canonical, external, definition of `f()`, with possibly an inline definition
available to use at the compiler's discretion. Multiple TUs providing external
definitions of the same function is ill-formed.{{< sidenote >}}And `inline`
variables do not exist. They're much less useful in {{< rb >}}C{{< /rb >}}.{{< /sidenote >}}

{{< fleuron >}}

If we [setup a similar situation](https://godbolt.org/z/GxeEdv86P) in
{{< rb >}}C++{{< /rb >}}, we do not see a link error. If we inspect the
resulting compiler output for `main.cpp`:

<div style="display: flex; justify-content: space-around; align-items: center; margin-bottom: 1rem">

```asm
main:
 # ...
 call <f(int)>

f(int):
 # ...
```

{{<
  img2 src="kailasa"
  alt="An illustration of Kailasa temple, part of the Ellora cave complex"
  style="width:50%; border-radius: 15%;"
  darkmode="img-fill"
>}}

</div>

We find `f()` has somehow manifested an external definition into `main.cpp`'s
TU. And in fact, `f()` will act as an external definition in every TU in which
it appears. Normally this would be a
{{< rb blue >}}One Definition Rule{{< /rb >}}{{< sn odr>}} violation, but this
is allowed via {{< rb >}}[\[basic.def.odr\]](https://eel.is/c%2B%2Bdraft/basic.def.odr#16){{< /rb >}}.
The behavior is best explained by the note in
{{< rb >}}[\[dcl.inline\]](https://eel.is/c%2B%2Bdraft/basic.def.odr#16){{< /rb >}}:

> An inline function or variable with external or module linkage can be defined
> in multiple translation units ([basic.def.odr]), but is one entity with one
> address.

{{< sidenote ident=odr side=left >}}
{{< rb blue >}}ODR{{< /rb >}} is exactly what it sounds like, a well-formed
program is allowed at-most one definition of most kinds of variables and
functions.
{{< /sidenote >}}

{{< rb blue >}}Vague linkage{{< /rb >}} is this cross-TU linkage behavior:
multiple external definitions, one logical entity. The "how" is beyond the
standard.{{< sn maskray>}} The important point is the definition manifests in
all TUs where it is needed, and the toolchain sorts out the mess later.

{{< sidenote ident=maskray >}}
The definitive author on all things linkage related is
{{< rb >}}Fangrui Song{{< /rb >}}, better known as {{< rb >}}MaskRay{{< /rb >}}.
For a deep-dive in how {{< rb blue >}}vague linkage{{< /rb >}} is implemented,
you can start with his post on [COMDAT and section group](https://maskray.me/blog/2021-07-25-comdat-and-section-group).
{{< /sidenote >}}

## Symbol Visibility and Shared Libraries

Completely outside the {{< rb >}}C++{{< /rb >}} language concept of
visibility,{{< sn visibility >}} there exists the toolchain notion of
{{< rb blue >}}symbol visibility{{< /rb >}}. These do not meaningfully
intersect, which is a source of endless confusion. {{< rb blue >}}Symbol
visibility{{< /rb >}} describes the availability of a function or variable
definition from a linked binary, such as a shared library.{{< sn sym-vs-def >}}
We describe available definitions as **visible** or **exported**, and
unavailable definitions as **hidden** or **unexported**.

{{< sidenote ident=visibility side=left >}}
Formally I think the standard calls this: *can be found by name lookup*, but I
have literally never heard it referred to as anything other than visibility;
usually in discussions of visibility versus reachability.
{{< /sidenote >}}

{{< sidenote ident=sym-vs-def >}}
Symbols and definitions are not the same thing. The former is a toolchain
mechanism and the latter a language concept. However, they're close enough to
use interchangeably for our purposes.
{{< /sidenote >}}

Because we've used the magic words *shared library* the standard no longer wants
anything to do with us. Everything from this point on is between the programmer
and the compiler.

{{<img2
  src="soltaniyeh"
  alt="An illustration of Soltaniyeh, featuring the mausoleum of Öljaitü"
  darkmode="img-fill"
  style="margin: 1rem auto; border-radius: 7% / 20%;"
>}}

One might guess that, without any intervention or use of compiler-specific
behavior, shared libraries act like normal {{< rb >}}C++{{< /rb >}} code does in
all other contexts. Definitions are normally visible and
available, and you must invoke some special magic to make
them hidden. On {{< rb >}}Unix{{< /rb >}}-like platforms you would be correct,
but it turns out this can have a disasterous impact on performance and binary
size.{{< sn visibility-perf >}}

{{< sidenote ident=visibility-perf side=left >}}
See {{< rb >}}Niall Douglas{{< /rb >}}'s [write-up on the GNU wiki](https://gcc.gnu.org/wiki/Visibility) for more details.
{{< /sidenote >}}

The impact is so severe that the general recommendation is to always override
the default,{{< sn vis-default >}} making all definitions hidden, and then
expose only those which are actually a part of your library's public API. The
{{< rb >}}Windows{{< /rb >}} \/ {{< rb >}}MSVC{{< /rb >}} universe made this
the default semantic from the start.

{{< sidenote ident=vis-default >}}
Controlled by the `‑fvisibility` family of compiler flags.
{{< /sidenote >}}

Making a definition visible from within a shared library requires annotating it
with a compiler-specific keyword or attribute. We don't need to go further than
this to understand the problem shared libraries are going to cause with modules.
The core point is: **without deliberate action, definitions become hidden when
they are linked into shared libraries.**

For completeness, exporting an `inline` function looks something like this:

{{<
  collapse label="Figure 2: Exporting an Inline Function"
>}}
```cpp
// func.h
#if defined(_WIN32)

#if defined(BUILDING_LIBRARY)
#    define API_PUBLIC __declspec(dllexport)
#  else
#    define API_PUBLIC __declspec(dllimport)
#  endif

// On Windows symbols are always hidden by default
#  define API_PRIVATE

#else

#  define API_PUBLIC [[gnu::visibility("default")]]

// Unnecessary if always building with -fvisibility=hidden
#  define API_PRIVATE [[gnu::visibility("hidden")]]

#endif

API_PUBLIC
inline void public_func() {
  // ...
}

API_PRIVATE
inline void private_func() {
  // ...
}
```
{{< /collapse >}}

At runtime, the address of `public_func` will be the same across all shared
libraries and the executable which uses this header. They will all share the
same copy. `private_func` will be local to each linked binary, each will get
and use its own manifestation of the function.

The `BUILDING_LIBRARY` definition and `__declspec(dllimport)` usage is necessary
on Windows platforms. These platforms make a distinction between declarations
and definitions intended to be fufilled locally, and those which are intended to
be imported from a shared library. When building the library the definition is
local, when using the library the definition is imported.{{< sn sym-vis-more >}}

{{< sidenote ident=sym-vis-more >}}
This is just scratching the surface of {{< rb blue >}}symbol visibility{{< /rb >}}.
A great deal more information is available in compiler manuals.
{{< /sidenote >}}

## Who's Symbol is it Anyway?

Ok, so the good news is there are only three compilers worth talking about
when it comes to {{< rb >}}C++{{< /rb >}} modules: {{< rb >}}GCC{{< /rb >}},
{{< rb >}}Clang{{< /rb >}}, and {{< rb >}}MSVC{{< /rb >}}.{{< sn suncc >}} The
even better news is that for {{< rb >}}GCC{{< /rb >}} and
{{< rb >}}Clang{{< /rb >}}, there's nothing to talk about; all the machinery
surrounding {{< rb blue >}}vague linkage{{< /rb >}} and {{< rb blue >}}symbol
visibility{{< /rb >}} works exactly the same as it does with headers.{{< sn mod-init >}}

{{< sidenote ident=suncc side=left >}}
We need not engage in every library maintainer's favorite hobby of pretending to
care about {{< rb >}}SunCC{{< /rb >}} or whatever.
{{< /sidenote >}}

{{< sidenote ident=mod-init >}}
There are some rough edges around the visibility controls for module-specific
constructs like module initializers, [see GCC Bug 105397](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=105397).
{{< /sidenote >}}

The bad news is {{< rb >}}MSVC{{< /rb >}} does something different.

Before we talk about modules, let's establish baseline behavior without them.
We will construct a simulacrum of a module interface unit from a header and
an implementation file, then check that behavior against the real deal.

{{<
  collapse label="Figure 3: We Have Modules at Home"
  godbolt="https://godbolt.org/z/4vqv8xd81"
>}}
```cpp
// provider_interface.hpp
inline int value = 5;

// provider_translation_unit.cpp
#include <provider_interface.hpp>

// consumer.cpp
#include <provider_interface.hpp>

int main() {
  return value;
}
```
{{< /collapse >}}

If we inspect the symbol tables of the object files for the two translation
units, we find that a definition of `value` has manifested in `consumer.cpp`,
and no definition of `value` appears in `provider_translation_unit.cpp`. This
is typical compiler behavior, inline definitions do not manifest in translation
units which don't use them.

Modules allow programmers to collapse the concept of an interface header and a
seperate translation unit into a single file, the interface unit. Translating
**Figure 3** into actual module usage results in **Figure 4**.

{{<
  collapse label="Figure 4: A Module"
  godbolt="https://godbolt.org/z/9dx11P916"
>}}
```cpp
// provider.cppm
export module provider;
export inline int value = 5;

// consumer.cpp
import provider;

int main() {
  return value;
}
```
{{< /collapse >}}

Again we inspect the symbol tables of the object files for the two translation
units. Under {{< rb >}}Clang{{< /rb >}} and {{< rb >}}GCC{{< /rb >}} the results
are the same as before. `provider.cppm` has no definition for `value`,
`consumer.cpp` does.

Under {{< rb >}}MSVC{{< /rb >}} **the result is reversed**, `provider.cppm`
contains the definition for `value`, and `consumer.cpp` instead contains an
undefined reference to the same. This behavior isn't proscribed by the standard,
but it is surprising. Under {{< rb >}}MSVC{{< /rb >}}, the sole owner of some
inline definitions is the module unit which originated them.{{< sn msvc-list >}}

{{< sidenote ident=msvc-list side=left >}}
As far as I can tell, nothing in the MSVC or Win64 ABI documentation discusses
exactly which definitions this applies to. It is maybe possible to work
backwards from [the IFC specification](https://github.com/microsoft/ifc) to
discover some of the rules, but curious readers are better off reverse
engineering this behavior the usual way.
{{< /sidenote >}}

This change in behavior is the root of the {{< rb blue >}}Interface Unit
Symbol Ownership Problem{{< /rb >}}.

## A Quick Digression About Static Library ABI

Static libraries are bundles of object files. So long as two compilers agree
on what the presence, names, and properties of the symbols contained within
those object files should be, the compilers are ABI compatible and can use
objects and static libraries produced by the other.

{{< rb >}}Clang{{< /rb >}} and {{< rb >}}MSVC{{< /rb >}} no longer agree on the
*presence* component of their ABI.{{< sn name-mangling >}}

{{< sidenote ident=name-mangling >}}
They don't agree on the *names* component either, but this is recognized as
a {{< rb >}}Clang{{< /rb >}} bug. See
[Clang Issue #89781](https://github.com/llvm/llvm-project/issues/89781).
{{< /sidenote >}}

{{< tabula
  caption="ABI Compatibility Producer vs. Consumer"
  matrix=true
>}}
  {{< tabula-head >}}
    {{< tabula-row >}}
      {{< tabula-th >}}.{{< /tabula-th >}}
      {{< tabula-th >}}Clang{{< /tabula-th >}}
      {{< tabula-th >}}MSVC{{< /tabula-th >}}
    {{< /tabula-row >}}
  {{< /tabula-head >}}
  {{< tabula-body >}}
    {{< tabula-row >}}
      {{< tabula-th scope="row" >}}Clang{{< /tabula-th >}}
      {{< tabula-td outcome="yes" >}}Links{{< /tabula-td >}}
      {{< tabula-td outcome="yes" >}}Links{{< /tabula-td >}}
    {{< /tabula-row >}}
    {{< tabula-row >}}
      {{< tabula-th scope="row" >}}MSVC{{< /tabula-th >}}
      {{< tabula-td outcome="no" >}}Fails{{< /tabula-td >}}
      {{< tabula-td outcome="yes" >}}Links{{< /tabula-td >}}
    {{< /tabula-row >}}
  {{< /tabula-body >}}
{{< /tabula >}}

## The Problem

## Coda
