---
title: "On Built Module Interface Compatibility"
subtitle: "or, Testing a bunch of build systems<br>which claim to support modules"
mediaTitle: "BMI Compatibility: Testing Build System C++ Modules Support"
description: "Discussing the problem of built module interface compatibility in
C++ build systems, and testing which popular build systems do and do not support
BMI compatibility calculation."
epigraph: "Translating from one language to another, unless it is from Greek
and Latin, the queens of all languages, is like looking at Flemish tapestries
from the wrong side, for although the figures are visible, they are covered by
threads that obscure them, and cannot be seen with the smoothness and color of
the right side."
epigraphAuthor: "Cervantes, Don Quixote"
preEpigraph: "In this post we'll cover a common problem among build systems which
claim to \"support modules\". If you want to jump into the technical stuff
and not me waxing philosophical,
<a href=\"#an-introduction-to-built-module-interfaces\">skip to the
first heading.</a>"
image: "social-media"
date: 2026-05-31T8:00:00-04:00
draft: false
---

Domain expertise is a funny thing. Before developing some expertise in a
domain, we often judge tools from that domain based on their ease-of-use. Think
of the controls of a consumer road car compared to a Formula One race car. The
consumer car is "better" because it's intuitive to use, teenagers get the hang
of it in a few weeks. If all you need is to commute from one place to another,
these controls and the machine they're attached to are perfectly servicable.

However, once domain expertise has been established, we often stop thinking in
terms of ease-of-use and begin thinking in terms of _capabilities_. The Formula
One car is "better" because it enables behavior the road car can't achieve. A
non-expert driver can't get the car around a single corner, but that's not what
the domain expert is concerned with.

{{< collapse label="Boring Disclaimer: I don't speak for my employer" >}}

I have never needed to write one of these before, but because this is directly
adjacent to my day job: this is just me talking. I'm not speaking on behalf of
anyone or any organization beside myself. I am definitely ***not*** establishing
an official opinion for my employer or any of their partners or clients.

{{< /collapse >}}

I work on build systems all day. Developing them, writing build scripts for
projects, porting projects from one to the other, so on and so forth. For better
or worse, I have domain expertise in build systems. I'm chiefly concerned with
what they *can* do, and how much code is required to make them do it, not with
how simple or intuitive their interfaces are. **I want to talk about something
some build systems can do, and others can't.** Not the interface, the
capability.

{{<
  img2 src="horses-banner.png"
  style="margin: 1rem auto; border-radius: 7% / 20%;"
  darkmode="img-fill"
>}}

The hot new capability in C++ build systems is **modules**. It is an easy way
for new entrants and mavericks to distinguish themselves from the old guard.
"... and we support C++20 modules!" is in almost every `ReadMe.md` for these
kinds of build systems.

However, there's a reason modules took so long to be adopted by the build
systems of yesteryear; they're difficult to implement, and shortcuts break
builds. Many build systems are taking shortcuts with modules. In this post we
explore a common way shortcuts break: Built Module Interface Compatibility.

## An Introduction to Built Module Interfaces

In pre-modules C++ we had headers and implementation files. These combined to
form translation units (TUs), which the compiler chunked through to produce
object files. Object files are hardy mechanisms; their formats are standardized
by platform vendors, and anything not controlled by the vendors is dictated by
ABI standards. They are broadly interchangeable, object files produced by one
compiler can be combined with object files from another by a linker.[^1]

[^1]: This remains true unless we're dealing link-time optimization, where the
compiler uses object files as a carrier for compiler-specific IR. Exceptions
abound in toolchain engineering.

{{<
  img2 src="horse-vetting.png"
  style="width:30%; float: right; margin: 0% 0% 0% 1%; border-radius: 10% 10% 0% 0%;"
  darkmode="img-fill"
>}}

Modules complicate this story. Modules ship as collections of **module units**,
each of which is a TU in and of itself.[^2] Every module unit needs to be built,
every module unit produces an object file. Some module units represent
_interfaces_. Like the headers of yore, these contain declarations which other
TUs want to use.

[^2]: After preprocessing. It's still possible to combine module units with
headers.

We cannot access these declarations via plain text inclusion, like with
headers, nor do the object files contain the information we need.[^3] Instead
the compiler produces a sidecar when building these module units which describes
the unit's interface. This is the **Built Module Interface**, or BMI.

[^3]: This should be self-evident, consider template declarations which
otherwise make no appearance in object files.

{{<fleuron>}}

A build system will pass these BMIs to the compiler whenever it is building
a TU which needs the declarations they contain. Achieving this alone is a bit of
work for the build system and language machinery, because naïvely neither is
aware of which declarations are produced by a given TU, or which TUs want to
consume those declarations. Succeeding at this is the bar most build systems
set for "supporting modules".[^4]

[^4]: All future references to "scanning" and "collation" (also known as
"aggregation") are about this step. The build system and the compiler collude
to figure out which TUs provide which modules, and which TUs want
to `import` those providers.

The subtlety comes from the BMIs themselves. Where object files are hardy, BMIs
are extremely sensitive. Compatibility between compilers is out of the question.
Compatibility between different builds of the same compiler is dubious at best.
And here's the kicker: **compatibility between different invocations of the same
build of the same compiler is not guaranteed**, it's not even particularly
likely.

A guaranteed way to break BMI compatibility is to change language standards.
If the producer of a BMI is compiled with C++23, and the consumer wants to
use C++26, that's a build failure. To correctly build the project the build
system needs to recognize these incompatibilities and reconstruct BMIs
under flags compatible with consumers. **In my opinion, this is the bar for
"supporting modules".**

## The Test

In order to judge build system support for managing BMI compatibility, we need
some common project under which we will define said support. Our example will be
four build system targets, a provider and three consumers. The provider builds
under C++23, one consumer also builds under C++23, and the remaining two build
under C++26. This will test three things:

* Does the build system handle BMI compatibility at all?

* Can the build system reuse BMIs between providers and compatible consumers?

* Can the build system reuse BMIs between consumers which are incompatible
with the provider, but compatible amongst themselves?

{{< collapse label="A Note On Header Units" >}}

We're not going to talk about header units in depth. However, any build system
which fails this test also can't support header units, at least not efficiently.

Header units are BMI-providers without an associated translation unit. They
must be rebuilt some minimum number of times based on BMI compatibility of all
the translation units which consume them.

{{< /collapse >}}

We don't need anything fancy here on the language side, two files will do it.
One will export a C++ module, the other will import it. The importing file can
be reused for all three consumers. For completeness, the code is:

<div style="display: flex; justify-content: space-around; margin-bottom: 1rem">

```cpp
// provider.cppm
export module provider;

// consumer.cpp
import provider;
```

{{<
  img2 src="windmill.png"
  style="width:30%; border-radius: 50%; align-self: center;"
  darkmode="img-fill"
>}}

</div>

The tested build systems will be the major cross-platform players which claim
any level of modules support: [Bazel](https://bazel.build/),
[CMake](https://cmake.org/), and [Xmake](https://xmake.io/). As well as some
mavericks and brand-new build systems which claim the same:
[build2](https://build2.org/),[^5] [Qbs](https://qbs.io/),
[pcons](https://pcons.org/), and
[cppbuild](https://codeberg.org/mccakit/cppbuild). I'll be using the
latest-at-time-of-writing trunk for each.[^6]

[^5]: Please debate in your forum of choice if {{< rb >}}build2{{< /rb >}} is a maverick or a major
build system.

[^6]: Tested under {{< rb >}}GCC 16.1{{< /rb >}} and {{< rb >}}Clang 22.1{{< /rb >}}, for all systems except
{{< rb >}}cppbuild{{< /rb >}} which documents only {{< rb >}}Clang{{< /rb >}} support.

The complete code [is available here.](https://github.com/nickelpro/bmi-compatibility-tests)

## The Quixotic Attempts

Unsurprisingly, all the mavericks and newcomers failed the test, being unable to
produce a successful build. Surprisingly, so did {{< rb >}}Bazel{{< /rb >}}, and it fails _hard_.
{{< rb >}}Bazel{{< /rb >}}'s module support is experimental, so this isn't a slight against it.
We'll dispatch with analyzing the others first and then come back to {{< rb >}}Bazel{{< /rb >}}.

{{< rb >}}build2{{< /rb >}} was an expected failure. It's known not to support BMI compatibility
and [has a comment where the BMI compatibility check would go noting this.](https://github.com/build2/build2/blob/708bfbc1df971339452a73194f7261ef2364d3fd/libbuild2/cc/compile-rule.cxx#L5984-L5987)
While I would like to see this pothole more clearly sign-posted in the
documentation (rather than being arcana for build engineers who read
implementation code), there's nothing wrong with `TODO`-based implementation.

{{< rb >}}Qbs{{< /rb >}}'s module support is documented as experimental, so no harm in failing.
The only differentiator being I can't find any infrastructure in the code where
compatibility would even be implemented, no stubs, no `TODO`s.

{{< rb >}}pcons{{< /rb >}} is so new it still has the new-build-system-smell. It is the only
candidate which is openly vibe-coded. If you're wondering if AI can save you
from BMI-compatibility, the answer is No. Like {{< rb >}}Qbs{{< /rb >}}, there doesn't appear to
be any notion of compatibility at all.[^7] {{< rb >}}pcons{{< /rb >}} is also the only system
considered which performs collation only once at configure time,[^8] but it's
brand new so we'll forgive it.

[^7]: This was my first time using {{< rb >}}pcons{{< /rb >}} and I learned it has the unfortunate
behavior of assuming if the same source file appears in multiple targets, it can
reuse the resulting object file. This is obviously wrong, as I may have compiled
it under different flags.\
\
If the author happens to read this: Hey, don't do that. It's a bad habit.

[^8]: Meaning we can break the build by editing existing files to a different
valid shape then rerunning {{< rb >}}Ninja{{< /rb >}}. This is pretty catastrophic by build system
standards. It leads to "just nuke the build folder and it starts working for
some reason" bugs.

Calling {{< rb >}}cppbuild{{< /rb >}} _new_ would be unfair, new implies complete, it's
under construction. However the author has been dragging modules work forward by
pushing for the libraries {{< rb >}}cppbuild{{< /rb >}} relies on to provide module units, so it
gets a shout out. Unfortunately it doesn't handle BMI compatibility yet, but
I'm sure it will soon.

{{<
  img2 src="fire-engine.png"
  style="border-radius: 7% / 20%; margin: 1rem auto;"
  darkmode="img-fill"
>}}

So, {{< rb >}}Bazel{{< /rb >}}. Again, module support is experimental which means there's no
commitment to this stuff working. It fails the BMI compatibility test, but the
bigger problem is _it doesn't even support GCC_. [This is due to a broken
template in `rules_cc`](https://github.com/bazelbuild/rules_cc/blob/72430b92dbb20279638ead93cbdc662a64ad5e4f/cc/private/toolchain/gcc_deps_scanner_wrapper.sh.tpl)
which hasn't been meaningfully changed since it was written in 2024 and I don't
believe ever worked. It sends the preprocessor output to the dependency file
path it wants, and writes the dependency file output to a temp file which is
discarded.

This is a trivial-to-fix bug, but it means no one is testing Bazel's module
support on GCC. This thing breaks on {{< rb  blue>}}Hello World{{< /rb >}}.
Comprehensive testing of modules support is absolutely essential for production
build systems, so there remains work to be done before moving out of
experimental.

## The Victors?

{{< rb >}}CMake{{< /rb >}} and {{< rb >}}Xmake{{< /rb >}} both produce
successful builds for the test, but neither passes on all the listed criteria.
{{< rb >}}CMake{{< /rb >}} rebuilds the BMI for every single consumer, and
{{< rb >}}Xmake{{< /rb >}} rebuilds the BMI for each incompatible consumer. This
is more work than needs to be done.

{{<
  img2 src="chevalier.png"
  style="width:30%; float: left; margin: 0% 1% 0% 0%;"
  darkmode="img-fill"
>}}

{{< rb >}}CMake{{< /rb >}}'s behavior is due to [a stubbed out calculation for BMI compatibility](https://gitlab.kitware.com/cmake/cmake/-/blob/936afa9823c9a592ba9406236dd95dbfe1179a10/Source/cmCxxModuleUsageEffects.cxx#L11-14)
which uses the consumer's name as a compatibility hash instead of anything
having to do with standard versions or flags. This is fixed [in a pending MR
for {{< rb >}}CMake 4.4{{< /rb >}}](https://gitlab.kitware.com/cmake/cmake/-/merge_requests/12116)
and with that MR applied {{< rb >}}CMake{{< /rb >}} passes on all criteria.[^9]

[^9]: Full disclosure, it's my MR.

{{< rb >}}Xmake{{< /rb >}} doesn't maintain a cache of available BMIs the way {{< rb >}}CMake{{< /rb >}} does, each
consumer asks a binary question: [Is this consumer compatible with the provider?](https://github.com/xmake-io/xmake/blob/c2dd4195391125636743b9ebb70a794349a6f7ce/xmake/rules/c%2B%2B/modules/scanner.lua#L385-L405)
If not, the BMI is rebuilt by the consumer asking the question. {{< rb >}}Xmake{{< /rb >}} also
doesn't reuse scans, each target scans and collates its entire graph. This is
simple and easy to debug, but wasteful. Rescanning behavior is unique to
{{< rb >}}Xmake{{< /rb >}}, none of the other build systems considered rescan module units.

Another interesting behavior of {{< rb >}}Xmake{{< /rb >}} is the `discriminate_on_defines` policy.
This policy determines if definition flags are considered for the purposes of
BMI compatibility calculation. This is something of a strange question, what
does it matter if the provider and consumer have different compile definitions?

It matters because...

## Nobody Knows How to Rebuild BMIs

I've lied to you reader. **No build system handles BMI compatibility correctly,
because there is no generally agreed correct way to rebuild BMIs.** There are
several very serious toolchain engineers who hold that C++ modules require all
code involved in an entire application, including any dynamic libraries it
uses, be built under precisely identical compile flags.[^10] That the very
question of BMI compatibility is ill-formed. I do not agree with them, but the
problem is hard.

[^10]: I had a snarky joke here, but I've decided to replace it with: toolchain
work is thankless drudgery which everyone hates you for doing. That this pile
of chewing gum and ducktape works at all is a minor miracle. Next time you run
into a compiler engineer, linker guru, or stdlib maintainer, buy them a beer.


Consider the following `provider`:

<div style="display: flex; justify-content: space-around; margin-bottom: 1rem">


```cpp
// provider.cppm
module;

#include <private_header.hpp>

export module provider;
```

{{<
  img2 src="chevalier2.png"
  style="width:30%; border-radius: 5%; align-self: center;"
  darkmode="img-fill"
>}}

</div>

We have a private header, a header which is meant to only be accessible to the
`provider` target. If a consumer needs to rebuild the BMI for this module unit,
how does it get access to this header? More generally, when we rebuild a BMI,
which flags get swapped out in order to make the rebuilt BMI compatible with the
consumer, and which flags remain the same?

Our two victors disagree on the answer:

* {{< rb >}}Xmake{{< /rb >}} swaps out flags wholesale when BMIs are incompatible. All includes,
all compile definitions, all compile options, everything. This is why it cares
about compile definitions for the purpose of BMI compatibility.

* {{< rb >}}CMake{{< /rb >}} swaps out compile options and language features,[^11] but keeps
includes and definitions as they were in the provider.

[^11]: {{< rb >}}CMake{{< /rb >}}-speak for the language version standard.

So the above example builds fine on {{< rb >}}CMake{{< /rb >}}, and fails on {{< rb >}}Xmake{{< /rb >}}. However,
{{< rb >}}Xmake{{< /rb >}} isn't wrong, they had a motivated reason for this behavior: shared
library exports. [The {{< rb >}}Xmake{{< /rb >}} bug covering this issue](https://github.com/xmake-io/xmake/issues/7436)
explicitly uses changing the compile definitions between the provider and
consumer as a way to control symbol visibility, and they manifest "changing"
by not propagating private includes and definitions to the consumer's rebuild
of the BMI.

[The {{< rb >}}CMake{{< /rb >}} bug covering the same issue](https://gitlab.kitware.com/cmake/cmake/-/work_items/25539)
is unresolved, and currently unsolvable within {{< rb >}}CMake{{< /rb >}} outside truly heinous
hacks like compile defintion smuggling. Personally, I believe a dedicated
mechanism for this problem is better than {{< rb >}}Xmake{{< /rb >}}'s "solution" of failing to
rebuild BMIs with private headers.[^12]

[^12]: I should note here, this fully precludes "everything builds under the
same flags always". We must provide some mechanism for consumers to receive
different flags than providers. The only place "same flags everywhere all the
time" works is the MSVC toolchain, which "magically" translates
`__declspec(dllexport)` into `__declspec(dllimport)` when consuming BMIs,
presumably because they too didn't want to solve this problem.\
\
However, [this causes other problems](https://developercommunity.visualstudio.com/t/C20-Modules-Spurious-warning-LNK4217/10892880), prompting the invention of
the wonderfully obscure `/dxifcSuppressDllImportTransform` flag. I like to
think of the ISDIT flag as a secret handshake among build system people.

## Coda

I don't know man. Modules are really hard. An irrelevant microfraction of the
C++ community seems to understand that, and even among toolchain people the
problems are discounted. C++ implementers can solve hard problems. Two-phase
lookup is hard, vague-linkage is hard, lots of things are hard, but worth it.

I think modules are really cool, I think these problems are totally solvable
and will eventually result in a really good mechanism for the language. However,
I also think the era of pretending the language is the only part of C++ which
requires guidance and standardization is over.

We will not solve BMI compatibility and other problems like it while every build
system is freestyling on the semantics of what "supporting modules" means. The
two major working module implementations on the build system side have
irreconcilable differences regarding how modules work. There must be
guidance from the top or things will only get worse as implementations become
more mature, and more ossified in that maturity.

**#ReviveTheEcosystemIS**
