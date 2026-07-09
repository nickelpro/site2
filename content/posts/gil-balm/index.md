---
title: "Balm in GILead"
subtitle: "Fast string construction for CPython extensions"
description: "An unorthodox approach to optimizing Python C extensions that operate on Python strings"
epigraph: "Speed is found in the minds of people"
epigraphAuthor: "Andrei Alexandrescu"
image: "social-media"
date: 2023-12-14T22:00:00-04:00
draft: false
---

Python isn't slow. [The core eval loop](https://github.com/python/cpython/blob/97857ac0580057c3a4f75d34209841c81ee11a96/Python/ceval.c#L679),
while slower than a JIT, is no slouch when it comes to dispatching bytecode.
There is no reason that business logic written in Python which orchestrates the
operation of highly optimized extension libraries should be a bottle neck.


{{< collapse label="Time is precious, get to the point" >}}

[Code and benchmarks are here](https://github.com/nickelpro/gilbench), fair
winds and following seas.

Also, hey, if you're real busy because you have a job and you're hiring,
I also would like a job. [Resume is here.](https://vito.nyc/vito_gamberini_cv.pdf)

{{< /collapse >}}

Well, there are two reasons. The first is the infamous ***Global Interpreter
Lock***, the GIL, which forces serialization onto operations that might
otherwise have been able to be executed in parallel by extensions. This is
widely recognized and improving, [the future appears GIL-less](https://peps.python.org/pep-0703/),
or at least GIL-optional.

Yet the second I rarely see discussed except among hardcore extension devs:
building `PyObject`s for blessed types like strings and dictionaries is damn
expensive. Every call to `PyUnicode_New()` makes me quiver with fear, no matter
how optimized CPython's small object allocator is. Worse yet, as long as the GIL
still walks among us, one ***must*** hold the GIL to create objects of the
blessed types.

{{< img src="doctor.webp" resize="684x q100" darksrc="doctor_dark.webp" imgstyle="border-radius: 10% / 30%; margin-left:auto; margin-right:auto;" />}}

The common solution is to abandon the world of blessed types. No `PyList`s,
no `PyUnicode`s, not even a measely `PyLong`. Building your own types makes you
strong, like ox, or Mark Shannon. Once a type exists outside the blessed Python
type system you are free to create your own allocators and deallocators for it,
and you may optimize its operations as you see fit.

Of course, you now must do a great deal of work to ensure that `TimmysDict`
interops with all the other Python types, and god forbid it ever encounters a
`PetersDict`. You're also banned by international treaty (and several local
state laws) from ever interacting with Python standards like WSGI, which dictate
only pure-bred Python types may be used.

## GIL Balm'ing

The uncommon solution to this problem is something my ~~dumb~~ ~~challenged~~
creative friends and I call **GIL Balm'ing** (the name, of course, is derived
from a sacred text of the Italian American native faith: _raised Catholic_). In
a sentence, GIL Balm'ing is the act of intrusively adapting a native CPython
type to be used outside the context of the GIL.

In the simplest case, this means replacing `tp_new`, `tp_free`, and `tp_dealloc`
of the type you are Balm'ing with something more suitable (often `NULL`). Every
Python type is a little different and no two applications the same, so the exact
steps to get this working depends on the use case.

The Python `str` type serves as a useful example because we have two major use
cases that lots of applications benefit from:

* Converting string views into `str`s without performing a copy

* Pooling compact `str` objects for use without grabbing the GIL or allocating

{{< collapse label="Caveats & Complications" >}}

A natural question might be, if this is so good for string views and compact
strings, why not also use it for really big strings where an allocation is
going to be necessary? At least we'll get to avoid the GIL, right?

Ya, sure, but the entire point of doing something like this is to avoid the
allocation at all. If you're going to take the hit on the allocation anyway,
doing one more operation while holding the GIL (to allocate an actual string)
is not going to matter that much.

And as we'll get to later, GIL Balm'ing is not completely transparent and
involves deciding what parts of the CPython contract you're going to honor. If
the performance gain is negligible, you should use the blessed CPython type,
not a Balm'd type.

{{< /collapse >}}

Python `str` is also useful because its structure is amenable to various
Balm'ing strategies.

## The Measure of a String

In order to Balm the `str`, we must first understand the `str`. The CPython
source code [is extensively commented](https://github.com/python/cpython/blob/97857ac0580057c3a4f75d34209841c81ee11a96/Include/cpython/unicodeobject.h#L48)
and from it we learn there are three string structures:

* **Compact ASCII (**`PyASCIIObject`**):** Promises to store only ASCII bytes,
  and stores the data immediately following the object in memory
* **Compact (**`PyCompactUnicodeObject`**):** Similar to the above, but for
  Unicode encodings
* **Legacy String (**`PyUnicodeObject`**):** Stores data in a separate buffer
  pointed to by the object, may or may not be ASCII

This brings us to the second point about GIL Balm'ing, this is a general
technique, not a specific library or code recommendation. Python strings are
flexible structures that can be adapted to many applications, which you choose
to do is up to you. Will you support Unicode or only ASCII? Do you want to take
advantage of the compact string representations or just plug pointers into
legacy strings?

Now that we know the string, we can adapt it. For this demonstration we'll be
targeting the string view and pooling uses described above (with a fallback for
strings that don't fit inside our compact representation), but only for ASCII
strings. **Figure 1** demonstrates a structure we'll be exploring.

{{< collapse label="Figure 1" >}}
Assume there are headers for anything that requires one
```c
typedef union {
  PyASCIIObject ascii;
  struct {
    // Force alignment on data[] to be correct
    struct {
      PyObject_HEAD;
      Py_ssize_t length;
      Py_hash_t hash;
      struct {
        unsigned int interned : 2;
        unsigned int kind : 3;
        unsigned int compact : 1;
        unsigned int ascii : 1;
        unsigned int statically_allocated : 1;
        unsigned int : 6;
        // Balm state data, lives in unused padding bytes
        unsigned int balm : 2;
        unsigned int balm_offset : 16;
      } state;
    };
    char data[];
  };
  struct {
    PyUnicodeObject uc;
    RefCountedData* rd;
  };
} BalmString;
```
{{< /collapse >}}

{{< img src="capture.webp" darksrc="capture_dark.webp" resize="x273 q90" imgstyle="border-radius:50%;" style="width:273px; float: right; margin: 2rem 0 1rem 0; shape-outside: inset(2rem 0 1rem 0 round 50%);" />}}

The first thing to note is that this is not a necessary part of GIL Balm'ing,
often we can re-use the structures from CPython directly. Here we do so in order
to have one unified string type for both of our use cases, string views and
compact strings.

The second is that we're replicating the structure of the PyASCIIObject inside
an anonymous structure. Sometimes this sort of replication is necessary, either
because CPython doesn't expose the necessary structures (looking at you,
`dict`), or because we want to do a little smuggling.

{{< collapse label="Stop Right There, Criminal Scum!" >}}

> Union type punning? Storing things in unused padding? **Replicating private
> internal CPython data structures?** This is a recipe for disaster!

I mean, ya. None of this stuff is safe. There's a reason you won't find this
in the official Python documentation. We're leaps and bounds outside the
official API and associated safety guarantees.

[_𝅘𝅥𝅮 Do what you want cause a pirate is free 𝅘𝅥𝅮_](https://www.youtube.com/watch?v=i8ju_10NkGY)

{{< /collapse >}}

For `BalmString`, we want to store some state data inside the structure and
`PyASCIIObject` very conveniently has a bunch of unused padding bits. It's a
simple thing to use some of those for our state data.

## The Author Hasn't Read Knuth

There is probably a very efficient way to collect and dispatch a group of
pre-allocated objects. If you know of one, please implement it and use it and
stuff, that sounds great.

We're going to use this list-stack thing in **Figure 2**.

{{< collapse label="Figure 2" >}}
```c
typedef struct BalmStringNode {
  struct BalmStringNode* next;
  BalmString str;
} BalmStringNode;

#define GET_STRUCT_FROM_FIELD(pointer, s_type, field) \
  ((s_type*) (((char*) pointer) - offsetof(s_type, field)))

#define GET_NODE_PYOBJ(pointer) \
  GET_STRUCT_FROM_FIELD(pointer, BalmStringNode, str)

typedef struct {
  mtx_t lock;
  BalmStringNode* head;
} StrPool;

static struct {
  StrPool bigviews;
  StrPool compacts;
} pools;

static void balmstr_push(StrPool* pool, PyObject* str) {
  BalmStringNode* node = GET_NODE_PYOBJ(str);
  mtx_lock(&pool->lock);
  node->next = pool->head;
  pool->head = node;
  mtx_unlock(&pool->lock);
}

static BalmString* balmstr_pop(
    StrPool* pool,
    BalmStringNode* (*alloc)(size_t),
    size_t alloc_len
) {
  mtx_lock(&pool->lock);
  if(!pool->head)
    pool->head = alloc(alloc_len);
  BalmStringNode* node = pool->head;
  pool->head = node->next;
  mtx_unlock(&pool->lock);
  return &node->str;
}
```

I actually have no formal education on data structures or algorithms at all. It
never slows me down except when I need to know what to call these things.

This feels like a singly-linked list, but we provide no capacity for random
access / extracting / etc. You can only push and pop from it, and that seems like a
stack. But there's no stack pointer or storage array, so a queue? But it's not
FIFO.

A stack-implemented-using-a-singly-linked-list-thingy.
{{< /collapse >}}

I don't think this code needs too much commentary for those who can read C. For
those who can't, thanks for tagging along, we're happy to have you.

{{<
  img src="book.webp" darksrc="book_dark.webp" resize="x406 q90" imgstyle="border-radius:5rem;"
  style="width:40%; float: left; margin: 0.5rem 0.3rem 0 0; shape-outside: inset(0 0 0 0 round 5rem);"
/>}}

We're going to be creating a list or a queue or something, whatever, a _pool_
of pre-allocated `BalmString`s. We can `push` to and `pop` from the pool instead
of having to allocate and deallocate objects from the memory manager. If the
pool is empty, we can allocate more `BalmString`s using whatever allocation
strategy the user wants.

The only thing of note is the layout of the `BalmStringNode`, the `next`
pointer comes **before** the `BalmString` itself. This makes things a little
more complicated than they need to be, because we have to do some pointer
arithmetic to recover a `BalmStringNode` from a given `BalmString` instead of
pointer casting between them directly.

However, recall the layout of a compact Python string, the data _immediately
follows_ the object in memory. If we placed the `next` pointer after the
`str`, it would be considered a part of the string. That's nonsense, so we
make do with some macros to recover the `BalmStringNode`.

More interesting are the block allocators in **Figure 3**.

{{< collapse label="Figure 3" >}}
```c
enum BalmStringType {
  BALM_STRING_VIEW,
  BALM_STRING_COMPACT,
  BALM_STRING_BIG,
};


BalmStringNode* balmstr_block_alloc(size_t len) {
  BalmStringNode* base = malloc(sizeof(*base) * len);
  BalmStringNode* prev = NULL;
  for(BalmStringNode* v = base; v < base + len; ++v) {
    v->next = prev;
    prev = v;
    v->str = (BalmString) {
      .state = {.kind = PyUnicode_1BYTE_KIND, .ascii = 1}
    };
  }
  return prev;
}

// Powers of two are cool
#define BALM_COMPACT_ALLOCATION 128
#define BALM_COMPACT_MAX_STR \
  (BALM_COMPACT_ALLOCATION - sizeof(PyASCIIObject))

BalmStringNode* compactbalmstr_block_alloc(size_t len) {
  size_t sz = BALM_COMPACT_ALLOCATION * len;
  BalmStringNode* base = malloc(sz);
  char* cur = (char*) base;
  char* end = cur + sz;
  BalmStringNode* prev = NULL;

  for(
    BalmStringNode* v = base;
    cur < end;
    v = (BalmStringNode*) (cur += BALM_COMPACT_ALLOCATION)
  ) {
    v->next = prev;
    prev = v;
    v->str = (BalmString) {
        .ob_base.ob_type = &BalmStringCompact_Type,
        .state = {
            .kind = PyUnicode_1BYTE_KIND,
            .compact = 1,
            .ascii = 1,
            .balm = BALM_STRING_COMPACT,
        },
    };
  }
  return prev;
}
```
{{< /collapse >}}

Both `balmstr_block_alloc` and `compactbalmstr_block_alloc` allocate `len`
number of their respective object types and then iterate over the allocation
linking up the objects.

What's interesting is the initialization we can do here. For the regular
`balmstr_block_alloc` we can only set up the parts of the `PyASCIIStringObject`
state that we know will always be true; it will only contain ASCII strings, and
the underlying data will definitely occupy one byte per character.

For the `compactbalmstr_block_alloc` we have more information and we can
initialize the `ob_type` along with our `balm` state data that we smuggled into
the padding bits. The latter is how we can tell, given a random `BalmString`,
the nature of the underlying data.

The former is the `PyTypeObject` for our compact strings, so let's get into
that.

## Your Type is My Type

The entire purpose GIL Balm'ing is to avoid the kosher practice of hand-crafting
new Python types. That means we need to steal a pre-existing type and replace
its allocators with our own. **Figure 4** demonstrates exactly that.

{{< collapse label="Figure 4" >}}
```c
static PyTypeObject BalmString_Type;
static PyTypeObject BalmStringCompact_Type;


static void balmstr_dealloc(PyObject* str) {
  BalmString* balm = (BalmString*) str;
  RefCountedData* rd = balm->rd;
  if(!(--rd->ref_count))
    free(rd);
  balmstr_push(&pools.bigviews, str);
}

static void balmstrcompact_dealloc(PyObject* str) {
  balmstr_push(&pools.compacts, str);
}

void balm_init() {
  BalmString_Type = PyUnicode_Type;
  BalmString_Type.tp_new = NULL;
  BalmString_Type.tp_free = NULL;
  BalmString_Type.tp_dealloc = balmstr_dealloc;

  BalmStringCompact_Type = BalmString_Type;
  BalmStringCompact_Type.tp_dealloc = balmstrcompact_dealloc;

  init_strpool(&pools.bigviews, balmstr_block_alloc);
  init_strpool(&pools.compacts, compactbalmstr_block_alloc);
}
```
{{< /collapse >}}

In `balm_init` (which will be called from the module initialization method
of whatever this gets embedded in) we copy the `PyUnicode_Type` and replace
the `tp_new` with `NULL`. It won't be valid to create this objects of this type
within Python.

Similarly, we replace `tp_dealloc` with the appropriate deallocation function.
We also replace `tp_free` and I'm not entirely certain if this is necessary,
but we're already playing with fire here so best not tempt the gods.

{{< collapse label="Confessions of a Type Thief" >}}
These types are forgeries, but pretty good ones. Given we have a function called
`make_balm()` which hands us a `BalmString`:
```python
>>> type(make_balm())
# <class 'str'>

>>> isinstance(make_balm(), str)
True
```

Pretty good right? Enough to get through customs at least. Beware however, they
won't stand up under closer inspection from investigators who know what they're
looking for:

```python
>>> type(make_balm()) == type(str())
False

>>> id(type(make_balm()))
140086316104800

>>> id(str)
140086333381056
```

Additionally, we violated several oaths of a `PyUnicode` object. We make no
guarantees, for example, that our `BalmString`s will be null-terminated. This
could be problematic if consumed by another C extension.

{{< /collapse >}}

To complete the ruse, we need to ensure an in-use `BalmString` carries the
correct type and metadata with it. For that we have the functions in
**Figure 5**.

{{< collapse label="Figure 5" >}}
```c
typedef struct {
  size_t ref_count;
  char data[];
} RefCountedData;

static void string_view(
  BalmString* str,
  RefCountedData* rd,
  char* data,
  size_t len
) {
  str->rd = rd;
  str->uc.data.any = data;
  str->uc._base.utf8 = data;
  str->uc._base.utf8_length = len;
  str->length = len;
}

Py_LOCAL_SYMBOL BalmString* New_BalmString(size_t len) {

  if(len <= BALM_COMPACT_MAX_STR) {
    BalmString* str = balmstr_pop(
      &pools.compacts,
      compactbalmstr_block_alloc,
      BALM_STRING_ALLOCATION_BLOCK_SIZE
    );
    str->length = len;
    return str;
  }

  RefCountedData* rd = malloc(sizeof(*rd) + len);
  rd->ref_count = 1;
  BalmString* str = balmstr_pop(
    &pools.bigviews,
    balmstr_block_alloc,
    BALM_STRING_ALLOCATION_BLOCK_SIZE
  );
  string_view(str, rd, rd->data, len);
  str->ob_base.ob_type = &BalmString_Type;
  str->state.balm = BALM_STRING_BIG;
  return str;
}

Py_LOCAL_SYMBOL BalmString* New_BalmStringView(
  RefCountedData* rd,
  char* data,
  size_t len
) {
  BalmString* str = balmstr_pop(
    &pools.bigviews,
    balmstr_block_alloc,
    BALM_STRING_ALLOCATION_BLOCK_SIZE
  );
  string_view(str, rd, data, len);
  str->ob_base.ob_type = &BalmString_Type;
  str->state.balm = BALM_STRING_VIEW;
  return str;
}
```
{{< /collapse >}}

Again, nothing revolutionary here for people who can read C. We've created two
functions, `New_BalmString` and `New_BalmStringView`, that pop a `BalmString`
object from the appropriate pool depending on what type of string the user
wants and how big it is.

For compact strings, the only work we need to do is setup the length field,
everything else was taken care of in the block allocator. For string view and
big strings, we now need to fill in the  `ob_type`, `balm` state data, and link
up the `data`, `length`, and `utf8` fields appropriately.

Additionally, for this particular Balm'ing, we're using a reference count to
keep track of when to `free` the underlying string data for the non-compact
string types. This might not be appropriate for your application, especially
for the string views. That's another reason why Balm'ing is a technique, not a
library.

{{< img src="whale.webp" resize="684x q90" darksrc="whale_dark.webp" imgstyle="border-radius: 10% / 30%; margin-left:auto; margin-right:auto;" />}}


## Call Me Ishmael

What is an optimization? A miserable little pile of code. Unless it is proven,
undeniably; trial by benchmark. Let the gods, Turing, Moore, Hennessy, and
Patterson, decide which is the best approach.

For this trial I have divided Herman Melville's _Moby Dick_ somewhat arbitrarily
into 7515 lines. I have attached a binary header to the file which describes
the offset and length of each line. The goal is to construct a string for each
line and deliver it as a 7515-length tuple to the Python interpreter.

Then repeat that exact process another 9999 times and we're done. In other
words, construct roughly 7.5 million Python strings as fast as you can.

{{< collapse_img label="Benchmark #1" src="uni_vs_balm.webp" resize="646x q100" darksrc="uni_vs_balm_dark.webp" imgstyle="margin-left:auto; margin-right:auto;" />}}

And we did it, case closed, **2x** speed up with this one weird trick. Except,
`BalmString`s don't use a great layout for constructing _millions_ of strings.
If we allocated them in blocks we could go even faster...

{{< collapse_img label="Benchmark #2" src="uni_vs_balm2.webp" resize="646x q100" darksrc="uni_vs_balm2_dark.webp" imgstyle="margin-left:auto; margin-right:auto;" />}}

And we did it, case closed, **5x** speed up with this one weird trick. This
benchmark is memory bound, it won't benefit from threading. We would just be
measuring the overhead of locking and unlocking the GIL.

But hey, it might be fun, let's split the 10k runs across 16 threads, 650 runs
each.

{{< collapse_img label="Benchmark #3" src="uni_vs_balm3.webp" resize="646x q100" darksrc="uni_vs_balm3_dark.webp" imgstyle="margin-left:auto; margin-right:auto;" >}}
Note that the scale has gained an order of magnitude
{{< /collapse_img >}}

Disaster for our `BalmString` implementation. The "naïve" `UnicodeString`
baseline is fully serial, it never releases the GIL to begin with, thus what
we're measuring is pure locking and contention overhead.

`BalmString` becomes _effectively_ serialized by the act of popping string views
from the pool, and the overhead of the highly granular locking strategy is
a crushing blow.

`BalmBlock`, which allocates all its strings as a block up front and thus needs
almost no locks at all, barely notices the GIL overhead. It is entirely memory
bound, with ~100ms of variance from the OS scheduler.

For highly parallel code, you could argue this is a **20x** speed up.

## Final Thoughts and Applications

GIL Balm'ing isn't for everyone. It maybe shouldn't exist at all, and perhaps
I am the fool for even suggesting it. Certainly, it is a fragile, precarious
strategy for squeezing speed out of CPython, but with the benefit of
maintaining a very high level of "natural" compatibility with Python code that
interacts with extensions leveraging it.

{{< collapse label="Not Just Strings" >}}
While the focus here is on strings, in the benchmark repo you will also find a
Balm'd tuple. This strategy is easily applied to any immutable Python type,
and _less_ easily applied to mutable ones.

The problem with mutable types is they love-love-love to allocate memory. For
example, when Balm'ing a List, one must decide what to do with the `append`,
`extend`, and `insert` methods. Each of these might _resize_ the list,
invoking the Python allocator, which means they must be replaced in a
Balm'd type.
{{< /collapse >}}


The codebases where I personally apply strategies like this are low-latency
libraries and services. Application servers like
[gunicorn](https://gunicorn.org/) can add a full millisecond of latency to
requests, when in principle they should be completely transparent. Some C
extensions, notably [FastWSGI](https://github.com/jamesroberts/fastwsgi),
demonstrate that the act of packaging and forwarding HTTP requests to CPython
should take only microseconds.

FastWSGI never releases the GIL, because it needs to construct Python objects.
It cannot run the application in parallel with processing HTTP headers for the
next request due to this restriction. GIL Balm'ing then becomes an act of
desperation, of last resort when one is unwilling to sacrifice speed or
convenience.
