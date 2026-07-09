---
title: "The Undocumented SWIG"
subtitle: "Building High Performance Integrated Python Extensions"
description: "Deep dive into using SWIG to extend Python, Part 1 of 3"
image: "social-media"
date: 2020-08-26T13:46:15-04:00
draft: false
---

For those who have never ventured into the dark underworld of the Python
C&#8209;Extension API, you may believe that it is as fluid and rewarding as
the rest of the Python ecosystem. I regret to inform you that this is not the
case. Line 13 of [*The Zen of Python*](https://www.python.org/dev/peps/pep-0020/)
says:

> There should be one -- and preferably only one -- obvious way to do it.

The C&#8209;Extension API is an excellent example of what happens when one
completely ignores that advice. There are two (incompatible) ways to export a
module, a half-dozen *documented* ways to parse an argument list, and no less
than nine options for calling a method. The documentation for this mess is
excellent by C Library standards, but falls woefully short of the gold standard
set by the rest of the Python docs.

{{< collapse >}}
The simplest, fastest, and most efficient way to write a function in C that can
be called as a Python method is to use the *barely documented* `METH_FASTCALL`
signature and the *completely undocumented* `_PyArg_ParseStack` parser.

A simple print function looks like this:
```C
#define PY_SSIZE_T_CLEAN
#include <Python.h>

static PyObject *print_func(PyObject *self,
    PyObject *const *args, Py_ssize_t nargs) {
  const char *str;
  if(!_PyArg_ParseStack(args, nargs, "s", &str))
    return NULL;
  puts(str);
  Py_RETURN_NONE;
}

static PyMethodDef CPrintMethods[] = {
  {"print_func", (PyCFunction) print_func, METH_FASTCALL},
  {0}
};

static struct PyModuleDef CPrintModule = {
  .m_base = PyModuleDef_HEAD_INIT,
  .m_name = "CPrint",
  .m_size = -1,
  .m_methods = CPrintMethods,
};

PyMODINIT_FUNC PyInit_CPrint(void) {
  return PyModule_Create(&CPrintModule);
}
```

Which is actually quite reasonable considering the amount of heavy lifting the
API is doing under the hood. Unfortunately, the per-function overhead is still
much too high to be maintainable for most applications, and it doesn't even
begin to address C++ codebases which will have to first build a C wrapper.
{{< /collapse >}}

Thankfully there is a better way, the excellent *Simplified Wrapper and
Interface Generator*, better known as [SWIG](http://www.swig.org/). In this
three part series we'll take a crash course in typical SWIG usage, discuss some
advanced features like typemaps, templates, and ownership semantics, and then
do a deep dive into using the SWIG runtime header to allow for tight, seamless
integration of C/C++ code written specifically to accelerate Python modules.

## Introducing SWIG

<!--- *If you're already familiar with SWIG, feel free to skip to
Part 2* -->

SWIG is the 8th Wonder of the Software World, it takes an incredibly
complicated job and makes it a transparent part of your build process. SWIG
cleanly integrates C and C++ routines into any of a dozen target languages
using their native ABIs and foreign function interfaces. For many real-world
use cases, not trivial example code, SWIG can do this out-of-the-box with
barely any configuration whatsoever.

Unlike the C&#8209;Extension API, SWIG has top-notch documentation full of
example code and extensive reference material. This post is not a substitute
for that documentation, it's here to rapidly get the reader up to speed with
the bare-minimum required to follow along with the other posts in the series.
With that said, let's begin our journey.

{{< img src="walk" resize="1200x webp q75" darkmode="filter" style="width: 65%; margin: 0 auto 1rem;" />}}

Figure 1 contains two files. The first is a simple C++ header containing a
[POD](https://en.wikipedia.org/wiki/Passive_data_structure) struct. All
C&#8209;esque code for these examples will be C++, but the exact same
principles hold when working with pure C. The second file is called the
*interface* file, and it's how we're going to instruct SWIG to build all the
necessary code to interact with Python.

*All code examples can also be found in
[this companion repository](https://github.com/nickelpro/Undocumented-SWIG),
along with build files.*

{{< collapse label="Figure 1">}}
All names are strictly for flavor.
```C++
// Agent.hpp
#include <cstdint>
#include <string>

struct AgentUpdate {
  int id;
  std::string call_sign;
  float health;
  std::uint64_t secret;
};
```

We'll explore this interface file in more detail in the next section.

```C++
// Agent.i
%module CAgent
%{
#include "Agent.hpp"
%}

%include <stdint.i>
%include <std_string.i>

%include "Agent.hpp"
```
{{< /collapse >}}

Before we explore the interface file further, try building these files to see
what happens. For Python the SWIG command to use is:

`swig -c++ -python -py3 Agent.i`

The switches here do what you expect, configuring SWIG to accept C++ as input
(instead of C), and produce a Python Extension (specifically Python 3) as
output. The extensions consists of two files, *CAgent.py* and *Agent_wrap.cxx*.

If you start Python and try to `import CAgent` right now, you'll get an import
error for a module called *_CAgent*. *CAgent.py* is a proxy for the actual
extension, *Agent_wrap.cxx*, which we still need to build. How you choose to
build this is up to you and your workflow, the following command will build the
extension if you're using the CMakeLists.txt included with the companion repo:

`cmake . && cmake --build .`

{{< collapse >}}
There are _many_ ways to build C/C++ projects and Python extensions, the
companion repo uses cmake and it's my preferred workflow. Python's distutils is
the official recommended path for building extensions.

Whatever you choose, the build must produce a shared library named:

`_[module_name].[ext]`

Where "[module_name]" is the same as the module name specified in the interface
file, and "[ext]" is "pyd" on Windows and "so" on other platforms.
{{< /collapse >}}

Now open a Python REPL in the same folder that you've built the extension and
`import CAgent`. You can create an `AgentUpdate` object and play with it, just
like a native Python class. Do `AgentUpdate` objects act the way you expect them
to? What are the differences from a normal Python object? *Hint: Check out the
\_\_dict\_\_*.

## Interrogating the Interface

Now we'll explore that interface file in more depth. SWIG interface files are
typically quite trivial, and our interface file is barely going to change at
all in this entire series, but that doesn't mean they're not powerful. Rather,
SWIG itself is so powerful that we rarely need to leverage the many
capabilities of interface files very much.

Starting with the first line:

```C++
%module CAgent
```

The module directive gives the resulting Python module it's name. I typically
prefix SWIG-generated modules with "C" to make them easy to tell apart at a
glance and easy to add to *.gitignore*.

```C++
%{
#include "Agent.hpp"
%}
```
All code between `%{` and `%}` directives is included literally in the
generated wrapper. This is typically used to include headers necessary to build
the wrapper, which we do here.

```C++
%include <stdint.i>
%include <std_string.i>
```

The `%include` directive in SWIG works the same way `#include` does in C/C++,
the preprocessor places a copy of the include'd file into the unit. Here
we're including standard SWIG [typemaps](http://www.swig.org/Doc4.0/Typemaps.html)
for interacting C++ strings and the standard integer types.

{{<  img src="cog.png" resize="500x webp q75" darkmode="filter" style="width:30%; float: right; margin: 0 0 0 0.2rem;"/>}}

This raises the awkward question of "What is a typemap?" For now, I'm going to
quote SWIG's documentation:

> Let's start with a short disclaimer that "typemaps" are an advanced
customization feature that provide direct access to SWIG's low-level code
generator. Not only that, they are an integral part of the SWIG C++ type system
(a non-trivial topic of its own).

Suffice to say the concept of typemaps is outside the scope of this crash
course. We need these two includes because they allow us to transparently
interact with standard integers and C++ strings, but that's as much as *this
post* is going to explore them.

```C++
%include "Agent.hpp"
```

The final `%include` takes all the declarations from *Agent.hpp* and places
them in our interface file. SWIG parses these declarations and generates
wrapper code based on them.

{{< collapse >}}
The curious reader might wonder, if we're just going to `%include` the header
file in the interface, do we really need the interface file at all? If SWIG can
parse C/C++ header files, why not just run it on the header directly?

The answer is, you can! SWIG even defines a macro, `#define SWIG`, so you can
place SWIG directives directly in the header file that will be ignored by your
compiler's preprocessor but recognized by SWIG's. We separate these directives
into their own file as a matter of good practice, not necessity.
{{< /collapse >}}

As mentioned earlier, there are far more powerful directives available than the
ones explored here. Additionally, SWIG has a library of support files that
build yet more advanced functionality on top of those directives. Rather than
trying to learn all of SWIG in one fell swoop, it's best to just learn on the
go.

## Getting Classy

{{<  img src="king" resize="700x q75 webp" darkmode="filter" style="width:40%; float: left; margin: 1.5rem 0.2rem 1rem 0;"/>}}

Normally this is the part of the tutorial where we add a second layer of
complexity to the material introduced in the first couple sections. But thanks
to SWIG, there is no additional complexity. Classes, methods, and functions all
work identically to the basic POD we're already familiar with.

Figure 2 creates a proper class with a method; it also adds an implementation
file, *Agent.cpp*, as a matter of good C++ practice but not necessity. SWIG
only needs to see declarations, not definitions, so it doesn't care about this
file. The result builds and acts the way you expect it to **without any changes
to the interface file**.

{{< collapse label="Figure 2" >}}
*Agent.i is unchanged, and not listed here*
```C++
// Agent.hpp
#include <cstdint>
#include <string>
#include <random>

struct AgentUpdate {
  int id;
  std::string call_sign;
  float health;
  std::uint64_t secret;
};

class SecretAgent {
public:
  std::string call_sign {"Spy"};

  SecretAgent(int id);
  AgentUpdate generate_update();

private:
  const int id;
  float health {100.0};
  std::default_random_engine random_engine {std::random_device{}()};
  std::uniform_int_distribution<std::uint64_t> secret_generator;
};
```

Note in *Agent.cpp* we're using a C++20 aggregate initializer, if your workflow
doesn't support C++20 yet you can rework `generate_update()` to initialize the
`AgentUpdate` using individual assignments instead.

```C++
// Agent.cpp
#include "Agent.hpp"

SecretAgent::SecretAgent(const int id) : id(id) {}

AgentUpdate SecretAgent::generate_update() {
  return AgentUpdate {
    .id = id,
    .call_sign = call_sign,
    .health = health,
    .secret = secret_generator(random_engine)
  };
}
```

From here on out the CMakeLists.txt files in the companion repo will run the
entire build process. SWIG is fully integrated with cmake, no need to run any
commands by hand. You can also use the CMakeLists.txt in the root directory to
build individual Figures without working in their respective subdirectories.

Also included is a simple *RunAgent.py* script which will construct a
`SecretAgent` and generate an update, in case you're tired of typing things
into the REPL.
{{< /collapse >}}

Again I encourage you to play with the resulting CAgent module, or even to
modify the `SecretAgent`'s C++ source code. For code that only wants to *call
into* C/C++, and does not need to *call back into* Python, this is as
complicated as SWIG gets for most use cases.

As a fun exercise, Figure 3 uses these same techniques to add a combat function
to the `SecretAgent` class, with an enum return type.

{{< collapse label="Figure 3" >}}
*Still no changes needed for Agent.i*
```C++
// Agent.hpp
#include <cstdint>
#include <string>
#include <random>

struct AgentUpdate {
  int id;
  std::string call_sign;
  float health;
  std::uint64_t secret;
};

class SecretAgent {
public:
  std::string call_sign {"Spy"};

  SecretAgent(int id);
  SecretAgent(int id, const std::string& call_sign);

  AgentUpdate generate_update();
  enum combat_result {
    COMBAT_DEFEAT,
    COMBAT_VICTORY,
    COMBAT_TIE,
  };
  combat_result combat(SecretAgent& other);

private:
  const int id;
  float health {100.0};
  std::default_random_engine random_engine {std::random_device{}()};
  std::uniform_int_distribution<std::uint64_t> secret_generator;
  std::uniform_real_distribution<float> combat_generator {0, 100};
};
```

SWIG doesn't usually differentiate between pass-by-value, reference, and
pointer. SWIG's docs explore this more fully, but as a rule of thumb these
things Just Work™.

```C++
// Agent.cpp
#include "Agent.hpp"

SecretAgent::SecretAgent(const int id) : id(id) {}

SecretAgent::SecretAgent(const int id, const std::string& call_sign) :
    call_sign(call_sign), id(id) {}

AgentUpdate SecretAgent::generate_update() {
  return AgentUpdate {
    .id = id,
    .call_sign = call_sign,
    .health = health,
    .secret = secret_generator(random_engine)
  };
}

SecretAgent::combat_result SecretAgent::combat(SecretAgent& other) {
  other.health -= combat_generator(random_engine);
  if(other.health > 0)
    health -= combat_generator(random_engine);
  else
    return SecretAgent::COMBAT_VICTORY;
  if(health > 0)
    return SecretAgent::COMBAT_TIE;
  return SecretAgent::COMBAT_DEFEAT;
}
```

*RunAgencySim.py* is a fun script in the companion repo that illustrates the
usage of the capabilities added here.
{{< /collapse >}}

Of note, the `combat_result` member enum is translated to a set of member
variables for the Python class, which are mapped to globals defined in the
underlying shared library. This means they're accessed almost identically to
the enum members in C++.

## What's Next

None of the techniques discussed in this post are Python specific, they can be
applied to any of the target languages that SWIG supports. In the next part
we'll talk a little more about typemaps and using them to interact with more
complex types than integers and strings. This involves calling `Python.h`
specific functions, and will begin our descent into the less traveled corners
of SWIG usage.


*The images used in this post are public domain, made available thanks to the
invaluable work of Liam Quin at [fromoldbooks.org](https://www.fromoldbooks.org/)*
