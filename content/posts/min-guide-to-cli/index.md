---
title: "Command Line Flags in C++"
subtitle: "A Minimalist's Guide"
date: 2022-02-07T02:11:00-04:00
image: "social-media"
draft: false
---

You are programming a tool in C++. Not a huge tool, not a tool where you care
enough about performance to say, use faster data structures than those provided
by the standard library, but one where you feel compelled to add some useful
options. After a brief and uninspiring survery of the field you settle on the
old standard for implementing program settings, you're going to parse `argv`.

{{< img src="beelzebub" darkmode="light" imgstyle="border-radius:5em;" />}}

Parsing command line options falls into the nightmare zone of complexity. It is
not so trivial that there's a single obvious approach, nor is it difficult
enough to be solely the domain of white papers published by subject matter
experts. Rather it's an approachable problem that everyone likes to take a
swing at it, and following that swing run to write a blog post about their
clever little solution; completely flooding search results with endless
mediocre code.

{{< collapse >}}
This is a common problem. My little brother recently tried to research
solutions to the [multiway number partitioning](https://en.wikipedia.org/wiki/Multiway_number_partitioning)
problem, for which the best algorithms are already well known to academia. To
his dismay, he found plenty of Stack Overflow posts describing completely
broken solutions to the problem that don't even implement the known algorithms.
{{< /collapse >}}

With that in mind, here is my clever little solution.

## A Little Cleverness

The requirements for my `argv` handler were thus:
  * Vaguely declarative
  * Produces a [POD](https://en.wikipedia.org/wiki/Passive_data_structure) struct
  * No outside dependencies
  * Trivial to add and remove settings

Since I want a POD struct at the end of this, that's as good a place to start
as any:

{{< collapse label="Figure 1">}}
```cpp
// These are the headers we'll be using in this post
#include <functional>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <string>
#include <unordered_map>

// For example code only; only heathens do this in real life
using namespace std;

struct MySettings {
  bool help {false};
  bool verbose {false};
  optional<string> infile;
  optional<string> outfile;
  optional<int> value;
};
```
{{< /collapse >}}

Some interesting notes about **Figure 1**:
* `help` and `verbose` are bools, to be controlled with simple toggle flags
* `outfile` requires a parameter and cannot be handled by a toggle flag
* `infile` is intended to flagless, set when a parameter is not a recognized flag
* `value` is neither string or bool, so some sort of conversion will need to
be done

My preferred way to switch on strings is to use a map to `std::function`:

{{< collapse label="Figure 2">}}
```cpp
typedef function<void(MySettings&)> NoArgHandle;

/**
 * We can also use a function pointer here, ie:
 * typedef void (*NoArgHandle)(MySettings&);
 *
 * If we're only ever going to use plain functions
 * or capture-less lambdas as handles, the plain
 * function pointer is good and marginally more performant.
 */

const unordered_map<string, NoArgHandle> NoArgs {
  {"--help", [](MySettings& s) { s.help = true; }},
  {"-h", [](MySettings& s) { s.help = true; }},

  {"--verbose", [](MySettings& s) { s.verbose = true; }},
  {"-v", [](MySettings& s) { s.verbose = true; }},

  {"--quiet", [](MySettings& s) { s.verbose = false; }},
};
```
{{< /collapse >}}

In **Figure 2** we have an unordered map that when passed a string will
produce a lambda (or other `std::function` thingy) which can perform the
applicable modification to `MySettings`. If this seems extremely obvious and
simple to you, that's because it is.

As a point of style, it may be appropriate to use a macro here to minimize
repetition and make the code more declarative:

{{< collapse label="Figure 3">}}
```cpp
typedef function<void(MySettings&)> NoArgHandle;

#define S(str, f, v) {str, [](MySettings& s) {s.f = v;}}
const unordered_map<string, NoArgHandle> NoArgs {
  S("--help", help, true),
  S("-h", help, true),

  S("--verbose", verbose, true),
  S("-v", verbose, true),

  S("--quiet", verbose, false),
};
#undef S
```
{{< /collapse >}}

{{< img src="curse" darkmode="light" imgstyle="border-radius:50%;" style="width:30%; float: right; margin: 0 0 1rem;" />}}

Of course, there are legitimate schools of thought which teach that the C
preprocessor is of the devil. My immortal soul is worth little and less to me
personally, so I like the macro.

For the single argument parameters we simply iterate on this approach. Our
lambdas will now take two arguments, the first being the `MySettings` struct
and the second being the string argument:

{{< collapse label="Figure 4">}}
```cpp
typedef function<void(MySettings&, const string&)> OneArgHandle;

#define S(str, f, v) \
  {str, [](MySettings& s, const string& arg) { s.f = v; }}

const unordered_map<string, OneArgHandle> OneArgs {
  // Writing out the whole lambda
  {"-o", [](MySettings& s, const string& arg) {
    s.outfile = arg;
  }},

  // Using the macro
  S("--output", outfile, arg),

  // Performing string -> int conversion
  S("--value", value, stoi(arg)),
};
#undef S
```
{{< /collapse >}}

It should be clear from this point that this approach can be further iterated
to support flags with arbitrary numbers of arguments and parsing complexity.
All that's left to do is put the pieces together and actually parse `argv`.

## Putting the Pieces Together

We're going to need a function that does four things in the following order:
1. Check if a string from `argv` is a NoArg option, and if so invoke the
  appropriate handler
2. Check if the string is a OneArg option, and if so collect the string
  argument (throwing if no such argument exists), then invoke the appropriate
  handler
3. Check if `infile` has been set, and if not set it with the string
4. Warn if `infile` has already been set and the flag is unrecognized

Let's do it:


{{< collapse label="Figure 5">}}
```cpp
MySettings parse_settings(int argc, const char* argv[]) {
  MySettings settings;

  // argv[0] is traditionally the program name, so start at 1
  for(int i {1}; i < argc; i++) {
    string opt {argv[i]};

    // Is this a NoArg?
    if(auto j {NoArgs.find(opt)}; j != NoArgs.end())
      j->second(settings); // Yes, handle it!

    // No, how about a OneArg?
    else if(auto k {OneArgs.find(opt)}; k != OneArgs.end())
      // Yes, do we have a parameter?
      if(++i < argc)
        // Yes, handle it!
        k->second(settings, {argv[i]});
      else
        // No, and we cannot continue, throw an error
        throw std::runtime_error {"missing param after " + opt};

    // No, has infile been set yet?
    else if(!settings.infile)
      // No, use this as the input file
      settings.infile = argv[i];

    // Yes, possibly throw here, or just print an error
    else
      cerr << "unrecognized command-line option " << opt << endl;
  }

  return settings;
}
```
It's minus 50dkp if you don't handle it!
{{< /collapse >}}

## Final Thoughts

Parsing `argv` is not a hard problem and I make no pretence that the solution
presented here is innovative or ground breaking. Yet if the internet is to be
believed handling these humble flags requires at least one operating system
specific framework or a single header file copied from Dr. Dobbs circa 2003.

Dependencies are not necessarily bad things, but C++ is not Javascript.
There's no need to pull in outside frameworks to solve a problem we can hack in
a few dozens lines of code ourselves.

See also: [*Addendum: Handling Positional Arguments*](/posts/min-guide-to-cli-addenda)
