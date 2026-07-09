---
title: "Upside Down Polymorphic Inheritance"
display: "Upside Down Polymorphic&nbspInheritance"
subtitle: "Leveraging P2162 for&nbspFun&nbsp&&nbspProfit"
description: "Discussion and examples of using P2162 to build polymorphic types in C++"
image: "social-media"
date: 2022-07-17T06:00:00-04:00
draft: false
---

The [visitor pattern](https://en.wikipedia.org/wiki/Visitor_pattern) is an
esoteric programming pattern that has never been widely popular. No one
seems to be totally certain on what it's good for, as demonstrated by the
diversity of opinions [found on StackOverflow](https://stackoverflow.com/questions/255214/when-should-i-use-the-visitor-design-pattern).
One notable quote [from the software engineering StackExchange](https://softwareengineering.stackexchange.com/a/48825)
sums up the vibe:

> Visitor pattern has the most narrow use and almost never will the added complexity be justified

{{< collapse >}}
My brother's assessment of the visitor pattern was even less generous:

> btw when you get a chance
>
> I'm reading this article series
>
> On like clean OOP
>
> in it he suggests the 'visitor' pattern
>
> I had to read up on it more
>
> Because I didn't really get it
>
> And this pattern seems insane?

{{< /collapse >}}

The pattern was canonized in C++ with `std::variant` and `std::visit`
in C++17. The reception was less than warm; in an influential post Mark Kline
convincingly argued that, ["`std::visit` is everything wrong with C++"](https://bitbashing.io/std-visit.html).

{{< img src="rat-header" resize="700x webp q90" darkmode="diff" imgstyle="border-radius:5em;" />}}

I'm partial to this argument. Plainly, we want pattern matching syntax, we want
it now, and the longer it is delayed the more horrendous crust builds up in the
gutters. Yet, pattern matching isn't here and the crumbs down in the gutter look
mighty tasty. Perhaps a little nibble wouldn't be so bad...

In this post we'll discuss how to use `std::variant` and `std::visit` as
replacements for polymorphic inheritance, allowing the use of value semantics
with a polymorphic type. No pointers, smart or otherwise.

## If it Quacks Like a Duck

Kline argued that the usage of `std::visit` is overly verbose, requires
expert-level C++ knowledge, or both. This remains indisputable, but the example
used was crafted to show `std::visit` in the worst light.

Kline wanted to print a fundamental type's name, thus every type needed to be
matched exactly, but what if we weren't dealing with fundamental types? Let's
consider **Figure 1**.

{{<collapse
  label="Figure 1"
  godbolt="https://godbolt.org/z/dbPoceW98"
>}}
```cpp
#include <print>
#include <string_view>
#include <variant>

using namespace std;
using namespace std::literals;

struct Alice {
  string_view name() {
    return "Alice"sv;
  }
};

struct Bob {
  string_view name() {
    return "Bob"sv;
  }
};

using Person = variant<Alice, Bob>;

void print_name(Person& p) {
  visit([](auto& inner) {
    print("Name: {}\n", inner.name());
  }, p);
}
```
{{< /collapse >}}

{{< img src="duck" resize="210x webp q90" darkmode="diff" imgstyle="border-radius:50%;" style="shape-outside: circle(); width:30%; float: left; margin: 0.5rem;" />}}

We don't care if the type we're dealing with is specifically `Alice` or `Bob`, we
only care that the type is vaguely person-shaped, that it's got a `name()`.

The question becomes, what happens if we're dealing with a type that _doesn't_
quack the way we need it to? Here we get in deep with "advanced" C++, though
it looks a little different now than when Kline wrote his post.


{{<collapse
  label="Figure 2"
  preamble="Duplicate code from previous figures will be excluded."
  godbolt="https://godbolt.org/z/o1oYevs6W"
>}}
```cpp
#include <concepts>

struct Stranger {};

using Person = variant<Alice, Bob, Stranger>;

template <typename T>
concept IsNamed = requires(T p) {
  { p.name() } -> convertible_to<string_view>;
};

void print_name(Person& p) {
  visit([](auto& inner) {
    if constexpr(IsNamed<decltype(inner)>)
      print("Name: {}\n", inner.name());
    else
      print("This is a stranger!\n");
  }, p);
}
```
My sophomore CS students would not like this code.
{{< /collapse >}}

Concepts, requires expressions, and constexpr-if are not beginner friendly, but
**Figure 2**'s approach remains compact. We needn't match every possible type,
we need only identify if a given type conforms to our requirements via a
`concept`.

Ok, we can `std::visit` with concise, if complex, code, that's polymorphism
covered. What's this got to do with _inheritance_?

## Tree of Types

The only type specified to work with `std::visit` is, naturally, `std::variant`.
[P2162](http://wg21.link/p2162) allows for one other [kind](https://en.wikipedia.org/wiki/Kind_(type_theory)):

> [Types] that publicly and unambiguously inherit from a specialization of std::variant

The proposal discusses two advantages: recursive variant types, and the ability
to "extend functionality" of `std::variant`. It's this extension of
functionality which provides a new angle on inheritance.

First an illustrative use case; consider a serialization protocol implemented
with a virtual base class as in **Figure 3**. If you're familiar with how this
would be done using traditional polymorphic inheritance, skip down to
**Figure 5** for the good stuff.

{{<collapse
  label="Figure 3"
  preamble="If you want a more complete exploration of how this would work, click the godbolt link."
  godbolt="https://godbolt.org/z/3nsnfG14h"
>}}
```cpp
#include <cstdint>
#include <iostream>

struct Packet {
  uint8_t id_val;

  virtual void encode(ostream& os) const = 0;
  virtual void decode(istream& is) = 0;
};

struct Request : Packet {
  static constexpr uint8_t id_num {1};
  uint8_t req_val;

  void encode(ostream& os) const {
    os.put(req_val);
  }

  void decode(istream& is) {
    req_val = is.get();
  }
};

struct Affirmative : Packet {
  static constexpr uint8_t id_num {2};
  uint8_t resp_val;

  // encode/decode very similar to Request
};

struct Failure : Packet {
  static constexpr uint8_t id_num {3};
  uint8_t resp_val;

  // encode/decode very similar to Request
};
```
{{< /collapse >}}

Ignoring the problems that come from minimizing code length for example
purposes, the fundamental struggle with virtual interfaces is the need to
explicitly juggle heap allocations. The networking code interfacing with
these classes would look something like **Figure 4**.

{{<collapse
  label="Figure 4"
  preamble="[Thanks to /u/tisti for fixing this example](https://www.reddit.com/r/cpp/comments/w1f3ph/upside_down_polymorphic_inheritance_leveraging/igk0kr4/)"
  godbolt="https://godbolt.org/z/Gfa6z93xG"
>}}
```cpp
#include <memory>

void encode_packet(const Packet& p, ostream& os) {
  os.put(p.id_val);
  p.encode(os);
}

unique_ptr<Packet> decode_packet(istream& is) {
  uint8_t id = is.get();

  auto p = [id]() -> unique_ptr<Packet> {
    switch (id) {
      case Request::id_num:
        return std::make_unique<Request>();
      case Affirmative::id_num:
        return std::make_unique<Affirmative>();
      case Failure::id_num:
        return std::make_unique<Failure>();
    }
  }();
  p->id_val = id;
  p->decode(is);
  return p;
}
```
Yuck.
{{< /collapse >}}

By modern C++ standards this is _OK_, but we've abandoned value semantics for
the notational soup of smart pointers. P2162 provides an alternative approach.

{{< img src="tree-header" resize="700x webp q90" darkmode="filter"/>}}

**Figure 5** lays out our packets as individual classes with no base class to
derive from. The code is included here for completeness, but there's nothing
surprising in it.

{{<collapse
  label="Figure 5"
  godbolt="https://godbolt.org/z/zvGfvc9Ez"
>}}
```cpp
struct Request {
  static constexpr uint8_t id_num {1};
  uint8_t req_val;

  void encode(ostream& os) const {
    os.put(req_val);
  }

  void decode(istream& is) {
    req_val = is.get();
  }
};

struct Affirmative {
  static constexpr uint8_t id_num {2};
  uint8_t resp_val;

  // encode/decode very similar to Request
};

struct Failure {
  static constexpr uint8_t id_num {3};
  uint8_t resp_val;

  // encode/decode very similar to Request
};

```
{{< /collapse >}}

**Figure 6** brings the pieces together, we build a `std::variant`
specialization of the "derived" classes from **Figure 5** and _inherit_ that
specialization in our `Packet` "base class" (upside down!). Finally,
`std::visit` implements the behavior of virtual functions.

{{<collapse
  label="Figure 6"
  godbolt="https://godbolt.org/z/rqYeY5r1f"
>}}
```cpp
struct Packet : variant<Request, Affirmative, Failure> {
  using variant::variant;

  Packet(uint8_t id) : variant {from_id(id)} {}

  Packet(istream& is) {
    decode(is);
  }

  void encode(ostream& os) const {
    visit([&](const auto& inner){
      os.put(inner.id_num);
      inner.encode(os);
    }, *this);
  }

  void decode(istream& is) {
    *this = from_id(is.get());
    visit([&](auto& inner){ inner.decode(is); }, *this);
  }

private:
  static Packet from_id(uint8_t id) {
    switch(id) {
      case Request::id_num:
        return Request {};
      case Affirmative::id_num:
        return Affirmative {};
      case Failure::id_num:
        return Failure {};
    }
  }
};
```
{{< /collapse >}}

Our networking code is now trivial (included as **Figure 7** for completeness).
We will probably ditch free-standing functions entirely and use the `Packet`
interface directly. The major advantage is we can use value semantics while
generically handling packets.

{{<collapse
  label="Figure 7"
  godbolt="https://godbolt.org/z/ovbM9994r"
>}}
```cpp
void encode_packet(const Packet& p, ostream& os) {
  p.encode(os);
}

Packet decode_packet(istream& is) {
  return Packet {is};
}
```
{{< /collapse >}}

We've also ditched the `id_val` variable which served as our
[sum-type tag](https://en.wikipedia.org/wiki/Tagged_union). This is now tracked
implicitly by `std::variant` and won't become a source of bugs.

## Performance Gremlins

{{< img src="jester.webp" resize="210x webp q90" darkmode="filter" imgstyle="border-bottom-left-radius:50%; border-bottom-right-radius:50%" style="shape-outside: circle(); width:30%; float: right; margin: 0.5rem;" />}}

Before you go and turn your entire codebase upside down you should be aware that
GCC [has two](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=86912)
[infamous bugs](https://gcc.gnu.org/bugzilla/show_bug.cgi?id=80603) which
may impact the performance of `std::variant` and `std::visit`. As long as your
total number of contained types is small,
[less than 11 elements](https://gcc.gnu.org/git/gitweb.cgi?p=gcc.git;h=cfb582f62791dfadc243d97d37f0b83ef77cf480),
you'll get a fast path thanks to a libstdc++ optimization. For larger type
collections you'll want to benchmark and see how much `std::variant` is going to
cost you on GCC or switch to [an alternative implementation](https://github.com/mpark/variant)
such as `mpark::variant`

## Final Thoughts

Ultimately I think this approach, while interesting for today's software, is a
hack. The true missing links here are
[Unified Call Syntax](http://wg21.link/n4474), with which we could extend
`std::variant` types without the need to inherit from them, and
[Pattern Matching](http://wg21.link/p2392), which would replace calls to
`std::visit` and their constexpr-if trees with a sensible syntax.

The idea that Haskell, a language where "whitespace doesn't matter except for
when it does" and strong claimant to the more-cryptic-than-template-metaprogramming throne,
can express these concepts much more clearly than C++ is embarassing.
