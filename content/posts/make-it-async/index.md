---
title: "Make it Async"
subtitle: "or, the Things that <b>sehe</b> Told Me About<br>Building Shared Async Resources with ASIO"
mediaTitle: "Make it Async: Building Shared Async Resources with ASIO"
description: "A discussion about creating custom asynchronous operations with ASIO"
epigraph: "The expert invariably means the person with the most patience."
epigraphAuthor: "sehe"
image: "social-media"
date: 2024-06-05T07:00:00-04:00
draft: false
---

I think it's clear that ASIO is both one of the most important libraries in C++
yet to achieve standardization, and one of the worst documented C++ libraries to
ever hold such a prestigious position. Trying to learn the ins-and-outs of
ASIO's model without spending arduous amounts of time reading the source code is
borderline impossible. Learning the best practices for use cases beyond the
trivial examples is Sisyphean.

The state of things is such that the premier advice for learning ASIO in the C++
community is, ["just ask **sehe**"](https://www.reddit.com/r/cpp/comments/15f1zu8/any_good_sources_for_learning_boost_asio_for/juawmyr/).
Relying on a single StackOverflow account as a tutorial mechanism would be
catastrophic for most projects, but [**sehe**](https://stackoverflow.com/users/85371/sehe)
is so active, insightful, and patient that ASIO almost gets away with it.

{{< collapse label="Not here for a lecture?" >}}

[Code examples are here](https://github.com/nickelpro/make-it-async-examples),
the complete working example is **Figure 4**, using a Python interpreter as the
shared resource in question.

Best of luck.

{{< /collapse >}}

Anyway, this is some stuff I learned about using shared resources
*asynchronously* by listening to **sehe**. I'll be demonstrating by bolting
functionality onto a little echo server and discussing a few other ASIO-isms
along the way.

{{<
  img2 src="dante.webp" darksrc="dante_dark.webp" resize="684x q100"
  style="border-radius: 7% / 20%; margin: 1rem auto;"
>}}

## A server! A server! My kingdom for a server!

Brevity is the heart of wit, and all the world has written an echo server. I
will not patronize the reader with another such implementation here. That said,
complete, compilable, runnable implementations of each figure are available
[in this repository](https://github.com/nickelpro/make-it-async-examples).

However, in the following examples we will be integrating an additional
asynchronous resource into such a server, and to do that we will need the bones
of an ASIO client handler. I present my preferred arrangement of bones in
**Figure 1**. This uses the C++20 coroutine-style of asynchronicity, which
has rapidly become my preferred mechanism.

{{< collapse label="Figure 1" >}}
Assume any `using` statement is replicated across all figures, they won't
be repeated.

The `nbeswap` function is a utility that that swaps between big endian
and native byte orders for any `std::integral` type.
```cpp
using asio::async_read;
using asio::awaitable;
using asio::buffer;
using asio::deferred;
using asio::ip::tcp;

awaitable<void> client_handler(tcp::socket s) {
  try {
    std::vector<char> data;
    for(;;) {
      uint16_t hdr;
      co_await async_read(s, buffer(&hdr, 2), deferred);

      data.resize(nbeswap(hdr));
      co_await async_read(s, buffer(data), deferred);

      std::array seq {buffer(&hdr, 2), buffer(data)};
      co_await async_write(s, seq, deferred);
    }
  } catch(...) {}
}
```
This code implements a simple protocol. It reads a two-byte big-endian size
prefix, then the rest of the message based on that prefix, and then proceeds
to echo both the prefix and the message back to the sender.

The process is repeated indefinitely until any error occurs, at which point the
connection is dropped.
{{< /collapse >}}

We're using one notable ASIO "trick" here, `asio::deferred`. In the spirit of
ASIO, nowhere is the interaction between the `deferred` completion token[^1]
and the C++20 `co_await` operator documented (this gave me a brief existential
crisis [a few months ago](https://www.reddit.com/r/cpp/comments/18njuow/coroutinesinpractice_cannot_be_understood_by/)).
Normally you would have to ask **sehe** what's going on here, but I'll give
you this one for free.

[^1]: Unfortunately I must assume some familiarity on the part of the reader
      with basic ASIO concepts like completion tokens. The
      [ASIO documentation](https://think-async.com/Asio/asio-1.30.2/doc/asio/overview/model/completion_tokens.html)
      covers these decently, but if you're unfamiliar with them it might be
      worthwhile to work through the ASIO tutorial code before tackling this
      post.

      I don't think the constructs presented here make much sense without an
      intuitive understanding of the problem they're trying to solve.

{{<
  img2 src="skel.webp" darksrc="skel_dark.webp" resize="x482 q100"
  shape-outside="true" style="width:40%; float: right; shape-margin: 0.5%;"
>}}

Async functions invoked with `deferred` create functors which represent
*deferred* async operations, operations which are only started when said
functors are invoked with another completion token. Invoking a deferred
operation with a `deferred` completion token is a no-op, it remains a
deferred operation.

So what the hell will `co_await` do with that functor?

It will start the async operation *with the coroutine itself as the completion
token!* Or, you know, something conceptually akin to that. C++20 coroutines are
very hard. The point is the awaiting coroutine will resume following
completion of the async operation, with any results of said operation returned
via the `co_await` operator.

The same effect can be achieved with the `asio::use_awaitable` completion
token, but the advantage of `deferred` is *no coroutine frame is
allocated*. The async operation itself is not a coroutine, so there's no need to
shoulder the burden of the coroutine frame allocation.

Is that intuitive? Is that obvious from the general semantics of
`deferred`? If you say yes, you're a more powerful wizard than I and
likely don't need the rest of this post.

## To block or not to block, that is the question

That was a fun diversion, but back to the task at hand. What if, instead of
building the behavior of the server directly into the C++, we want to delegate
that task to a higher level langauge like Python? We're serious C++ programmers,
our job is to move bytes around as fast as possible, lesser mortals can concern
themselves with the contents of those bytes.

First let's consider the direct approach, we'll call into CPython. CPython
requires us to hold the **Global Interpreter Lock** (GIL) before we muck with
anything.[^2] We do this with the `PyGILState_Ensure` and
`PyGILState_Release` functions.

[^2]: This is not strictly true under all conditions, and the GIL is undergoing
      a lot of changes these days. Someday in the future it may disappear
      entirely. But for right now with the version of Python 3.12 running on
      most machines, we need to grab the GIL.

**Figure 2** illustrates an outline of how we could go about this, minus error
checking and some other Python minutia.


{{< collapse label="Figure 2" >}}
See [the example repository](https://github.com/nickelpro/make-it-async-examples)
for a more complete, error-checked example of this integration.
```cpp
awaitable<void> client_handler(tcp::socket s) {
  try {
    std::vector<char> data;
    PyObject* appReturn {nullptr};
    for(;;) {
      uint16_t hdr;
      co_await async_read(s, buffer(&hdr, 2), deferred);

      data.resize(nbeswap(hdr));
      co_await async_read(s, buffer(data), deferred);

      // Grab the Global Interpreter Lock
      auto state {PyGILState_Ensure()};

      // Do a bunch of Python-specific nonsense
      Py_XDECREF(appReturn);
      auto pyBytes {
        PyBytes_FromStringAndSize(data.data(), data.size())
      };

      appReturn = PyObject_CallOneArg(app, pyBytes);
      Py_DECREF(pyBytes);

      // `out` and `len` will contain the response from
      // the Python app
      char* out;
      Py_ssize_t len;
      PyBytes_AsStringAndSize(appReturn, &out, &len);

      // Release the GIL, we're donc
      PyGILState_Release(state);

      // Make sure the size-prefix header we're sending
      // is correct
      hdr = nbeswap(static_cast<std::uint16_t>(len));
      std::array seq {buffer(&hdr, 2), buffer(out, len)};
      co_await async_write(s, seq, deferred);
    }
  } catch(...) {}
}
```
The purpose of the Python-specific code is to make this a "practical" example,
these are operations performed by "real-world" application servers. That said,
everything between `PyGILState_Acquire` and `PyGILState_Release` can be safely
ignored, the point is we have to acquire a lock in the middle of this handler
function.
{{< /collapse >}}

Clearly our `client_handler` is getting a bit long, the Python code begs to be
abstracted into its own function, but the real issue is that locking call. When
we grab the GIL our executor, the execution resource which is running our
coroutine, becomes completely unavailable. We're no longer stringing together
`co_await`s, we've done a synchronous blocking operation that prevents this
executor from being used elsewhere.

What we need is the ability to suspend our handler until the job is complete,
as is done with `async_read` and `async_write`.

## That which we call blocking,<br>by any other name still blocks

{{<
  img2 src="romeo.webp" darksrc="romeo_dark.webp" resize="x387 q100"
  style="margin: 5.2rem 0.5rem 0 0; border-radius: 20% / 7%; shape-outside: inset(5.2rem 0 0 0 round 20% / 7%); width:25%; float: left;"
>}}

The fundamental unit of asynchronicity in ASIO is the `async_result` trait,[^3]
which is [covered in the ASIO documentation reasonably well](https://think-async.com/Asio/asio-1.30.2/doc/asio/overview/model/completion_tokens.html).
As mentioned in that documentation, we will never touch this trait, always using
its helper function `async_initiate` to handle the twin C++ footguns of
type decay and forwarding.[^4]

[^3]: I have no idea if this is true. It's the way I see the iceberg from the
      tip I'm standing on. Sometimes I tie my shoes wrong. Caveat emptor.

[^4]: There's also `async_compose` for building operations that chain multiple
      other asynchronous operations. It does not spark joy. I use coroutines for
      this.

I won't repeat the ASIO documentation here, but suffice to say
`async_initiate` is the "make it async" secret sauce of ASIO. You have some
function you want to use with ASIO's model, all you need do is pass it through
`async_initiate` and you're there.

Well ok, there's a little bit of work to do. `async_initiate` wants you to invoke
a **completion handler** at the conclusion of whatever operation you're
performing. This is a proxy for the callback, the coroutine, the intermediate
completion object, whatever, that is waiting on the completion of your async
operation.

**Figure 3A** presents an implementation that uses this machinery to run our
Python operations.


{{< collapse label="Figure 3A" >}}
We're going to need to bundle together some data into a structure here so it
can be returned from our `co_await` operator, thus `PyResult`. This result
will get passed as the only argument to the **completion handler** handed
to us by `async_initiate`.
```cpp
using asio::async_initiate;

struct PyResult {
  PyObject* obj;
  char* out;
  Py_ssize_t len;
};

struct PythonApp {
  PythonApp(PyObject* app) : app_ {app} {};

  template <typename CT>
  auto run(
    const std::vector<char>& data, PyObject* prev, CT&& token
  ) {
    auto init = [this, &data, prev](auto handler) {
      std::move(handler)(run_impl(data, prev));
    };

    return async_initiate<CT, void(PyResult)>(init, token);
  }

private:
  PyResult run_impl(
    const std::vector<char>& data, PyObject* prev
  ) {
    PyResult ret {};
    auto state {PyGILState_Ensure()};

    /* Python stuff to fill in PyResult */

    PyGILState_Release(state);
    return ret;
  }

  PyObject* app_;
};
```
You can pass the arguments directly to `async_initiate` and it will invoke
your function with those arguments, but in this usage I find it simpler to
capture arguments into the `init` lambda. As always be careful about lifetimes,
nothing in the `PythonApp.run` stack frame will be alive when the `init`
lambda is invoked.
{{< /collapse >}}

Not so bad, however there's a minor ASIO-ism in the invoking of the completion
`handler`. Note that it is `std::move`'d before we invoke it with the result
of our Python operation. Completion handlers are single-use disposable functors,
and to prove to ASIO we understand this we must `move` them prior to
invocation.

Now that we've got our own async operation, we can refactor our client handler
into **Figure 3B**. Not only is all the nasty Python code factored out, but
we can suspend via `co_await` until the operation has completed.


{{< collapse label="Figure 3B" >}}
Note that `PythonApp.run` takes a completion token. It could be used with any
ASIO mechanism, not just the C++20 coroutine model we're using here.
```cpp
asio::awaitable<void> client_handler(
  tcp::socket s, PythonApp& app
) {
  try {
    std::vector<char> data;
    PyResult pr {};
    for(;;) {
      std::uint16_t hdr;
      co_await asio::async_read(s, buffer(&hdr, 2), deferred);

      data.resize(nbeswap(hdr));
      co_await asio::async_read(s, buffer(data), deferred);

      pr = co_await app.run(data, pr.obj, deferred);

      hdr = nbeswap(static_cast<std::uint16_t>(pr.len));
      std::array seq {buffer(&hdr, 2), buffer(pr.out, pr.len)};
      co_await asio::async_write(s, seq, deferred);
    }
  } catch(...) {}
}
```
For the pendants, as written here, this example leaks a Python object reference
when it drops the connection. The more complete version in the
[provided example repository](https://github.com/nickelpro/make-it-async-examples)
fixes that bug, but it requires a little more supporting machinery than nicely
fits in this slideware.
{{< /collapse >}}

But what have we really done here? `co_await` will suspend our coroutine and
initiate the blocking Python operation. That operation will run, by default and
because we didn't intervene, on the current executor... which will block trying
to acquire the GIL.

**We didn't change anything.**

Well, we made the code a little cleaner and more consistent, but functionally
nothing has changed here, our executor still ends up blocked waiting for the
GIL. If we had 12 threads serving as executors, they would all end up sitting
around waiting for the GIL.

This is somewhat natural. The GIL is a bottleneck for this program. However,
imagine a case where the Python interpreter was fast enough to serve two or
three IO threads handling the `accept`, `read`, and `write` calls, with a
dedicated Python thread handling the data processing. Instead of servicing those
IO operations, the executors spend all their time waiting on the GIL only
servicing IO calls in their brief moments not blocking on it.

We can imagine many resources that might fall into a similar category: memory
pools, hardware devices, stateful thread-unsafe libraries, which all serve as
concurrency bottlenecks but can achieve higher throughput if properly managed.

{{<
  img2 src="lear.webp" darksrc="lear_dark.webp" resize="684x q100"
  style="border-radius: 10% / 20%; margin: 1rem auto;"
>}}

## I am an executor,<br>More dispatch'd to than dispatching

What we want is a queue of operations, a strand of execution, dedicated to just
Python. We want executors to submit work to this strand, but not block on it,
remaining available for any other work that comes along. When the Python
operation is completed, we want the results handed back to the original executor
which submitted the work.

The good news is ASIO provides direct support for such strands of execution,
with the conveniently named `asio::strand`. A `strand` is an executor which
guarantees  **non-concurrent** execution of work submitted to it. This removes
the need to manage any locks, GIL or otherwise, the `strand` will guarantee
only a single operation is inside the Python interpreter at a time.[^5]

[^5]: There exist complications with this approach, and strategies for managing
      those complications, which I'm eliding. They're Python-specific, so don't
      belong in a general discussion of designing asynchronous shared resources.

      The short version is we'll be preventing Python-native threads from ever
      running. We will *never* release the GIL, and manage access to the Python
      interpreter with our `strand`. This is a reasonably common restriction for
      application server implementations.

To build an asynchronous resource which submits all of its work to a provided
strand, we'll use what I call the **double-dispatch trick**.[^6] The principles
of this trick are demonstrated in **Appendix A**; here performed outside the
context of an echo server to focus only on the properties of `asio::dispatch`.

[^6]: Journeymen ASIO programmers will point out this is not a trick at all,
      but a natural exercise of ASIO's intended capabilities. Unix programmers
      say much the same about the double-fork trick, and yet here we are.

{{<
  collapse label="Appendix A"
  preamble="If you want to explore this concept for yourself, click the godbolt link."
  godbolt="https://godbolt.org/z/48h3svfbd"
>}}
```cpp
static std::atomic_int tid_gen;
thread_local int const tid = tid_gen++;

inline void out(auto const& msg) {
  std::println("T{:x} {}", tid, msg);
}

asio::awaitable<void> f(auto strand) {
  out("IO Context Executor");
  co_await dispatch(bind_executor(strand, asio::deferred));
  out("Strand Executor");
  co_await dispatch(asio::deferred);
  out("Back on IO Context Executor");
}

int main() {
  asio::io_context io;
  asio::thread_pool tp(1);

  co_spawn(io, f(make_strand(tp)), asio::detached);

  io.run();
}
```
We're deriving the `strand` from a `thread_pool` instead of the `io_context` so
that it will have a distinguishable thread ID.
{{< /collapse >}}

`dispatch` is an asynchronous operation in the same way that
`async_read` and `PythonApp.run` are, which means we can hand it a completion
token, or make it a deferred operation and `co_await` it as with the others.[^7]

[^7]: `dispatch` has a very similar cousin, `asio::post`, and executors have
      a related underlying method `.execute`, which won't be discussed.
      Reader exploration is encouraged, but it's more than I have space for
      here.


`dispatch` doesn't read a socket or file, it doesn't wait on a timer or signal,
it doesn't perform any work at all really. It immediately invokes the completion
handler if it can, or schedules the completion handler to be run at the next
oppertunity otherwise.

So what's so special about it? It can invoke the completion handler on a
*different* executor. The priority order for which executor `dispatch` uses (as
I understand it) is as follows:

  1. The **associated executor** for the completion token.[^8]

  2. An executor optionally passed as the first argument to `dispatch`.

  3. A default system executor, which will run the completion handler
     *somewhere*.

[^8]: In an `asio::awaitable` / `co_await` context this always defaults to the
      coroutine's current executor if none other exists, thus never advancing
      past this step.

In the above example we `co_await` deferred `dispatch`s which dutifully invoke
their completion handlers, resuming the coroutine on the associated executor.
Since we bound the `strand` to the completion token for the first `dispatch`,
the coroutine is resumed on the `strand`. The second `dispatch` returns
execution to the coroutine's home executor.

**Figure 4** modifies the `PythonApp` to use the double-dispatch trick. No
significant modification of the `client_handler` is necessary.


{{< collapse label="Figure 4" >}}
```cpp
using asio::dispatch;
using asio::append;

template <executor Ex> struct PythonApp {
  PythonApp(Ex ex, PyObject* app)
     : ex_ {std::move(ex)}, app_ {app} {}

  template <typename CT>
  auto run(
    const std::vector<char>& data, PyObject* prev, CT&& token
  ) {
    auto init = [this, &data, prev](auto handler) {
      dispatch(ex_,
        [this, &data, prev, h = std::move(handler)]() mutable {
          dispatch(append(std::move(h), run_impl(data, prev)));
        }
      );
    };

    return async_initiate<CT, void(PyResult)>(init, token);
  }

private:
  PyResult run_impl(
    const std::vector<char>& data, PyObject* prev
  ) {
    // Unchanged
  }

  Ex ex_;
  PyObject* app_;
};
```
{{< /collapse >}}

The first `dispatch` delegates to the designated `PythonApp` executor via the
first-argument mechanism. This works because lambda we're passing to the first
`dispatch` as a completion token has no associated executor.

Inside that lambda is where the `run_impl` call is made, running the Python
code now that execution has been shifted onto `ex_` (presumably a `strand`). The
results are then "appended" to the completion handler.

`asio::append` is somewhat analogous to `std::bind_back`, but for completion
tokens. It produces a completion token which passes additional arguments to an
underlying completion token. In this instance, the underlying completion token
is the completion `handler` for the entire `PythonApp.run` asynchronous
operation, and the argument we want it to be invoked with is the result of
the Python operation.

The completion handler has an associated executor, the executor it originated
from. The second `dispatch` schedules the completion handler to be run on
that executor, and execution inside the original coroutine is resumed by that
completion handler.

Damn that was a lot. Everybody take five.

## I am but mad North-North-West.<br>When the executors are blocked,<br>I know a hawk from a handsaw

Anyway that's what I learned, I hope it's useful. Writing it all out it's not
that much information, but it took weeks of nights and weekends experimenting
and running into dead ends to work out this little demo.

When I was a kid I learned networking from reading
[**Beej's Guide to Network Programming**](https://www.beej.us/guide/bgnet/),
which got me started down the path of asynchronous programming generally. I
struggled to build complete programs though, succeeding merely in little scripts
which blasted hardcoded byte sequences into the aether.

Only after I saw a complete, working, practical implementation of the
fundamentals **Beej** had taught me did it click. My first ever asynchronous
network program was [a Minecraft bot called SpockBot](https://github.com/SpockBotMC/SpockBot),
which started as a wholesale copy of [Barney Gale's barneymc framework](https://github.com/barneygale/barneymc).

I think ASIO desperately needs the same. Complete, practical demonstrations that
can be directly copied and expanded upon by application developers. It needs its
own version of the [Sascha Williams Vulkan-Samples](https://github.com/KhronosGroup/Vulkan-Samples),
or the [LLVM Kaleidoscope tutorial](https://llvm.org/docs/tutorial/). Not toys,
real bedrock developers can build on, supported by complete documentation beyond
the spartan API references.

*Also the double dispatch trick is stupid. ASIO should absolutely have a utility
function for "run this thing on a different executor and dispatch the completion
handler to its associated executor". Just saying.*
