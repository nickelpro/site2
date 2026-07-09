---
title: "The Realm of Confusion: Object Kinds in SystemVerilog"
display: "The Realm of Confusion:<br>Object Kinds in SystemVerilog"
subtitle: "Or, a short treatise on the subject of nets and variables"
description: "Discussion of the differences between System Verilog data object kinds"
epigraph: "Computers are like Old Testament gods; lots of rules and no mercy"
epigraphAuthor: "Joseph Campbell"
image: "social-media"
date: 2023-02-26T20:00:00-04:00
draft: false
---

SystemVerilog is a strange language. Students of computer science frequently
struggle when they first encounter it, because if you squint and turn your head
_just so_ it looks like a programming language. However, the parts of the
language commonly known as "the synthesizable subset" have very little to do
with programming.

SystemVerilog does exactly what it says on the tin, it's a
_hardware description language_. It describes a physical object, a heathen rock
which we have imbued with great and terrible power.

{{< img src="magnus-header" darkmode="filter" style="width:80%; margin-left:auto; margin-right:auto;" />}}

In keeping with its nature as not-a-programming-language, SystemVerilog has a
somewhat strange relationship with the concept of _types_. In this post we'll
briefly explore the difference between the two major groups of data objects,
`nets` and `variables`, and how they (don't) relate to SystemVerilog "data
types". Along the way we will touch on all the parts of a basic scalar
declaration, noting how parts are implicitly declared when omitted from said
declaration.

If you have ever wondered what, exactly, the difference between `var`,
`logic`, and `reg` is, or what parts of a port list are _actually_ required,
this post is for you.

{{< collapse label="A Brief Note on Standards" >}}

The SystemVerilog standard (formally known as the _Language Reference Manual_ or
LRM), **IEEE Std 1800-2017**, is a supremely readable document. If you're used
to and have developed a healthy fear of standardese due to certain programming
languages (_cough_ C++ _cough_ _cough_), you have no reason to fear the
SystemVerilog LRM. If you can get access to it, you should read it to find the
correct answers to any questions you might have.

That said, getting access to IEEE standards isn't an option for everybody. This
guide is provided in hopes it is useful to those who go standard-less.

{{< /collapse >}}

## Definitions and Notations

A **scalar** is a data object which describes a single _bit_ of information.
We're using the term _bit_ here rather loosely, as the student of computer
science will assert that a bit is an object that assumes one of two possible
states. But we are not computer scientists, we are masons, carving
trans-resistive elements into the devil's stones.

Our bits are not restricted to merely **on** or **off**, most of our bits will
have _at least_ four states. These are:

* **0**: a logic zero or a false condition
* **1**: a logic one or a true condition
* **x**: an unknown logic value
* **z**: a high-impedance state

{{< collapse label="Examples of Scalar Declarations" >}}

The following are examples of scalar declarations in SystemVerilog:

```verilog
wire alpha;
logic beta;
var gamma;
reg delta;
```

{{< /collapse >}}

An array is a data object which encompasses one or more bits of information.
Arrays come in two flavors, **packed arrays**, which are also known as
**vectors**, and **unpacked arrays**. When the unqualified term **array** is
used, we're usually talking about unpacked arrays.

{{< collapse label="Examples of Array and Vector Declarations" >}}

The following are examples of array and vector declarations in SystemVerilog:

```verilog
wire [3:0] alpha;       // Four bit vector
logic beta [3:0];       // Four element array of scalars
var gamma [4];          // Four element array of scalars
reg [1:0] delta [4:0];  // Five element array of two bit vectors
```

{{< /collapse >}}

Arrays and vectors are a subject all their own, for the remainder of this post
we'll deal with scalars. We bring them up only to mention that everything we
discuss with regards to scalars will also apply to arrays and vectors.

## What's in a declaration?

A basic declaration of a scalar contains three elements, in order they are: the
**object kind**, the **data type**, and the **identifier**.

Working backwards:

* **identifier** is the name by which we will refer to our
  freshly declared scalar

* **data type** defines the range of values our scalar can assume

* **object kind** describes the behavior of our scalar, chiefly the mechanisms
  by which it can be assigned and hold values


{{< collapse label="Object Kinds Don't Exist" >}}

It's true, I invented the term ***object kind***. It does not come from the LRM,
but the LRM is simply being unreasonable. The LRM has no name for the category
of thing I am addressing as "object kind".

Instead, everytime the LRM must address this unnameable, unspoken, thing, it
instead enumerates the two options. So instead of saying "object kind" it will
instead say "variable or net". Thus the alternative title to this piece.

The closest the LRM comes to admitting there is a categorical relationship
between these two terms is section 6.5:

> There are two main groups of data objects: variables and nets. These two
> groups differ in the way in which they are assigned and hold values.

And, specifically in the context of port declarations, section 23.2.2.3:

> Within this subclause, the term **port kind** is used to mean any of the net
> type keywords, or the keyword `var`, which are used to explicitly declare a
> port of one of these kinds.

Combining these two phrases, "groups of data objects" and "port kind", I arrived
at _object kind_. I look forward to being credited in the next edition of the
LRM.

{{< /collapse >}}

So for example, in the following scalar declaration:

```verilog
var logic omega;
```

`var` is the object kind, `logic` is the data type, and `omega` is the
identifier.

## Descriptions of Data

There are two important built-in data types:

* `logic` can assume any of the four basic value states

* `bit` can assume only the true and false value states


Notably, `logic` is the default data type for _everything_ in SystemVerilog. If
the data type of our example scalar declaration is omitted, the `logic` keyword
is implicit. This also holds for port declarations.

{{<  img src="beccafumi" resize="205x q75 webp" darkmode="filter" imgstyle="border-radius:20%;" style="shape-outside: margin-box; border-radius: 20%; width:30%; float: left; margin: 1rem 1rem 0 0;"/>}}

There exists a set of numeric data types, `byte`, `shortint`, `int`,
and `longint`. These can represent two-state real numbers of lengths suggested
by their names. They are mostly of use in non-synthesizable simulation, and
will not be further considered here.

The usage of `bit` is similarly discouraged, its two-state nature is simply not
enough state for us in most cases. However, it does see some use in
synthesizable code.

There are also 4-state numeric types, the 32-bit `integer` and the 64-bit
`time`. If we need such types in synthesizable code, we should be using
vectors. These too will not be further considered.

Finally there are user-defined data types. These include structures,
enumerations, and typedefs which we have manifested into existence. They too may
appear in the data type position of a declaration.

At this point it bears mentioning there is a keyword called `reg`, which is
almost-but-not-quite a data type. Like Twinnings' relation to tea or the
Electoral College's relation to democracy, it leaves something to be
desired. If it were a data type `reg` would be analogous to `logic`, a
four-state scalar or vector type. This will be explored more later.

## Conceptions of Kinds

There are two major groupings of object kinds, **nets** and **variables**.

In truth, "variables" should not be plural. There is only one variable kind,
`var`. Data objects of kind `var` can be written to by one or more procedural
statements, or alternatively can be written by one continuous assignment or
one port.

Outside the context of port declarations, all data objects are variables by
default. This means we can omit the `var` keyword from our scalar declarations,
it is implicit.

{{< collapse label="Examples of Variable Declarations" >}}

The following are examples of variable declarations in SystemVerilog:

```verilog
var logic alpha;
var beta;    // Equivalent to above, logic is implicit
logic gamma; // Equivalent to above, var is implicit

var bit delta;
bit epsilon; // Equivalent to above, var is implicit
```

{{< /collapse >}}

All other object kinds are nets. The most prolific of these is the old,
reliable, `wire`. There is also a cohort of more specialized net kinds, such as
`tri`, `wor`, `wand`, and more. In addition to these, we can have user-defined
net kinds manifested using the `nettype` keyword.

{{< img src="king" resize="205x q75 webp" darkmode="filter" imgstyle="border-radius:50%;" style="shape-outside: circle(); width:30%; float: right; margin: 0.5rem 0 0.5rem 0.5rem;" />}}

An exploration of even just the built-in net kinds is beyond the scope of this
post. However, they all follow the same rules with regards to assignment: a net
can be written by one or more continuous assignments and/or module ports. A net
_cannot_ be procedurally assigned to.

A final caveat, nets only work with four-state data types. For example, you
cannot combine `wire` with `bit`.

{{< collapse label="Examples of Net Declarations" >}}

The following are examples of net declarations in SystemVerilog:

```verilog
wire logic alpha;
wire beta;      // Equivalent to above, logic is implicit

wire bit gamma; // Invalid, bit is only a two-state data type
```

{{< /collapse >}}

Earlier we said that our bits will encode _at least_ four states. Net objects
can encode far more information. In order to resolve the value of a net driven
by more than one continuous assignment, nets carry additional inform about the
**strength** of their value. Strength can be one of seven possible levels, and
this allows for a trivial sort of mixed-signal simulation that is useful in the
digital design space.

Notably, this can be used to model multi-driver buses where non-selected
components are in a high-impedance state, or simulate the presence of
pull-up/pull-down resistors.

From this we can derive a simple rule for the use of nets and variables. If the
circuit being modeled is multi-driver use a `wire`, for everything else use
a `var`.

## And sometimes reg

Consider the following scalar declarations:

```verilog
var reg alpha;  // Four-state variable
reg beta;       // Equivalent to above, var is implicit

wire reg gamma; // Invalid ???
```

We see here why `reg` is only _sorta_ a data type. It cannot be combined with
net kinds. `reg` **must** be a variable.

The reason is staring us in the face. `wire reg` is a phrase that puts a shiver
down one's spine. Even barbarous idolators, worshippers of the silicon throne
such as we, are appalled by the combination.

{{< img src="ruins" resize="684x q75 webp" imgstyle="border-radius:10% / 50%;" darkmode="filter" />}}

`reg` is a keyword brought over from the original Verilog standard, which had
no concept of data types or object kinds. In SystemVerilog, `wire` and its kin
were made into object kinds, while `reg` was nominally classified as a data
type.

The rules of the language would allow us to combine these, but the authors of
the LRM could not bring themselves to sanction this unholy marriage. Such a union could only be made
in error or as the result of an elaborate torture, no person would ever do so
of their own free will. Thus it is forbidden as a mercy to wayword and anguished
souls.

It is recommended to avoid the `reg` keyword. It is a misleading half-type, let
it be relinquished to the sands of legacy compatibility and spoken of no more.

## But what of the ports?

So far we have discussed declarations in isolation, but port declarations have
some special rules associated with them.

Firstly, port declarations have an additional characteristic, **direction**,
which precedes all other characteristics in a declaration. The three basic
directions a port may be are `input`, `output`, and `inout`. Their usage is
self-evident. If omitted and not otherwise able to be derived, the default
direction is `inout`.

Next we must differentiate between the two styles of port declarations, ANSI and
non-ANSI.

In a **non-ANSI** port list, the declarations of port characteristics are
seperated from the port list itself.

{{< collapse label="Example of non-ANSI Port Declaration" >}}

The following is an example of a non-ANSI port list and declaration in
SystemVerilog:

```verilog
module Mod(alpha, beta, gamma);
  input logic alpha;
  input logic beta;

  output logic gamma;
  // ...
endmodule
```

{{< /collapse >}}

If the direction, object kind, and data type are all omitted from the first
element of the port list, the port list is non-ANSI. All other constructions
are ANSI port lists.

Non-ANSI port lists have a number of curious properties of questionable utility.
As with the various specialized net kinds and the particular details of vectors
and arrays, we will not explore them further here. Non-ANSI port lists are not
recommended as they are both verbose and error-prone.

{{< img src="letters2" resize="684x q75 webp" darkmode="filter" />}}

**ANSI** port lists declare port characteristics inside the port list. The rules
for determining implicit defaults for ANSI port lists are involved, what follows
is a best effort attempt to condense them.

* If all characteristics of a port are omitted, then they are inherited from the
previous port declaration.

Otherwise:

* If the direction is omitted, it is inherited from the previous port
declaration. If this is not possible (first port in the list), the direction
is `inout`

* If the data type is omitted, it is `logic`

* If the object kind is omitted:
  * For `input` and `inout` ports, the object kind will be a net defined by the
    `default_nettype` compiler directive
  * For `output` ports:
    * If the data type has also been omitted, the object kind will be a net
      defined by the `default_nettype` compiler directive
    * If the data type was declared, the object kind will be `var`

The `default_nettype` is `wire` initially.

{{< collapse label="Example of ANSI Port Declaration" >}}

The following is an example of an ANSI port declaration in SystemVerilog:

```verilog
module Mod(
  // inout wire logic, inout and wire are implicit
  logic alpha,
  // inout wire logic, all characteristic inherited
  beta,

  // input wire logic, wire and logic are implicit
  input gamma,
  // input wire logic, input is inherited, wire is implicit
  logic delta,

  // input var bit, bits cannot be nets, so var is implicit
  input bit epsilon,

  // output wire logic, wire and logic are implicit
  output zeta,
  // output var logic, output is inherited, var is implicit
  logic eta,
);
  // ...
endmodule
```

{{< /collapse >}}

## Final Recommendations

A quick summary of recommendations:

* Use `logic` for single driver circuits, `wire` for everything else

* Stick to `logic` in synthesizable code. Avoid `reg`

* Allow `var` to be implicit, just `logic` and `wire` are enough for almost all
  declarations

* Use ANSI-style ports

* Always declare port direction for each port

* Allow everything else in a port declaration to be implicit except if you
  need an output variable, then use `output logic`

There exist various reasons to break these rules, but this will get you correct,
compact, readable code in most situations.
