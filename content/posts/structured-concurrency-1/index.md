---
title: "For Strong Structured Concurrency"
subtitle: "or, How to Avoid Lifetime Footguns in std::execution"
mediaTitle: "Strong Structured Concurrency: How to Avoid Lifetime Footguns in std::execution"
description: "A description of a common failure mode for C++ programs built on C++26 std::execution"
epigraph: "It is possible that the law, which is clear-sighted in one sense, and
blind in another, might in some cases be too severe. But as we have already
observed, the national judges are no more than the mouth that pronounces the
words of the law, mere passive beings incapable of moderating either its force
or rigor."
epigraphAuthor: "Montesquieu"
image: "social-media"
date: 2025-12-18T10:00:00-04:00
draft: false
---

Let us consider for a moment the construction of an operation in C++26's
`std::execution` (hereafter `exec`).[^1] In such a construction we need several
things: we need a `sender`, the source of an operation; and a `receiver`, the
sink of an operation. We combine them with `exec::connect(sender, receiver)` to
form an operation state (`op_state`).

The resulting object captures the idea of work, but does not induce work by
construction. Work begins only when we enter an operation state with
`exec::start(op_state)`. For simple programs[^2] the tree-shaped[^3] collection
of operation states is fixed by composition.[^4] The density of footnotes in the
previous sentence is sufficient evidence that we ought not linger here, for fear
of foundering amongst them.

[^1]: `exec` is also used by several extensions from the `stdexec` reference
      implementation used in this post. No attempt is made to distinguish
      these.

[^2]: "Simple" here does not mean small, trivial, or comprehensible to the
      average bear. It means only that we can speak about the bounds of the
      operation from the manner of its assembly, without needing to analyze the
      internal behavior of the work it performs (its loops, its blocking, its
      I/O peculiarities, and so on).

[^3]: Strictly speaking, not always a tree. Some adapters introduce shared state
      (multiple downstream operations sharing a single upstream completion),
      which makes the dependency shape a DAG. Nothing in this post depends on
      the distinction; “tree-shaped” is the intuition we will keep.

[^4]: That is: the space of possible operation-state types is determined by the
      composed sender expression. Which particular operation-state objects are
      instantiated, and which are ever started, is a runtime affair[^5] and
      varies with control flow; we will treat that as beneath the waterline.

[^5]: ...and thus fit only for footnotes.


{{< collapse label="A Note On Schedulers" >}}

We need a third thing for any `std::execution` program, a scheduler. We will
not deal at length with schedulers in this post, but they're at the core of
what makes `std::execution` different from concurrency models in other
languages. The ability to make schedulers explicit, write your own, *and
compose them* is one of the super powers of the C++ concurrency model and
hugely undersold.

In formal PL settings, schedulers are naturally modeled via *effect handlers*.
There's [a good paper on effect handlers in C++](https://dl.acm.org/doi/10.1145/3563445)
from OOPSLA'22, but [reddit did not like it very much](https://www.reddit.com/r/cpp/comments/yju88z/cppeffects_effect_handlers_in_c/).

Someday I will write up all the amazing things you can do with schedulers, and
what C++ teaches us about effect handlers. However, if I waited to do that I
would not have a single post in 2025, so I wrote this instead.

{{< /collapse >}}

This static tree-shape of operation states is insufficient for more complex
programs where we need a runtime-determined number of operations in flight
concurrently. We materialize this via dynamic operation state nesting,
introducing new child operation states within the active lifetime of parent
operation states.

{{<
  img2 src="mining2.png"
  style="margin: 1rem auto;"
  darkmode="img-fill"
>}}

We describe this style of composing static and dynamic operation states as
*structured concurrency*. Atop this paradigm, we often layer the requirement
that all children must finish their active lifetimes, must exit their receiver’s
continuation, prior to their parent doing the same. Let's call this the
**strong structured concurrency invariant**.[^6]

[^6]: In its strong form, structured concurrency is a reification of the fully
      strict fork-join discipline from programming language theory. The more
      general form of structured concurrency is much younger than the PLT
      notion. It was first described by
      [Sústrik](https://sustrik.github.io/250bpm/blog:71/), and subsequently
      expanded on by [Smith](https://vorpus.org/blog/notes-on-structured-concurrency-or-go-statement-considered-harmful/),
      and [Niebler](https://ericniebler.com/2020/11/08/structured-concurrency/).

But this is C++ we're talking about. The invariant is sound; the language is
not. Let’s proceed.

## The Problem

We need some arbitrary, though plausible, shape for an operation state tree.
**Figure 1** provides this shape. It is contrived, but anyone who has written
a client-server networking service will hopefully recognize a familiar pattern
here.[^7]

[^7]: I’m going to use coroutines to play both the `sender` and `receiver`
      roles in the examples. `exec::task` is a coroutine type that is also
      usable as a sender. When you `co_await` a `sender` inside a `task`, the
      coroutine’s promise provides the glue such that the `sender` can deliver a
      completion back into the coroutine.

      The details are not important here; the examples are meant to illustrate
      lifetime and structuring issues, not the coroutine plumbing.

{{<collapse
  label="Figure 1"
  godbolt="https://godbolt.org/z/e7KhdrEj6"
>}}
```cpp
exec::task<void> work_doer(data& in, data& out) {
  std::println("Running doer on thread: {}", tid);
  std::this_thread::sleep_for(std::chrono::seconds(2));
  out = in;
  co_return;
}

exec::task<void> work_launcher(std::vector<data>& result) {
  std::vector<data> inputs(result.size());
  std::ranges::iota(inputs, 0);

  for(auto [in, out]: std::views::zip(inputs, result))
      co_await work_doer(in, out);
}

exec::task<void> work_server(int len) {
  std::vector<data> result(len);

  auto start = std::chrono::steady_clock::now();
  co_await work_launcher(result);
  auto finish = std::chrono::steady_clock::now();

  std::chrono::duration<double> elapsed = finish - start;

  std::println(
    "Got {} work results in {:.1f}s",
    result.size(), elapsed.count()
  );
  std::println("Results: {}", result);
}

int main() {
    std::println("Running main on thread: {}", tid);
    stdexec::sync_wait(work_server(4));
}
```
{{< /collapse >}}

There is, of course, nothing concurrent about this. Easily verified by looking
at the output:

<div style="display: flex; justify-content: space-around;">
{{<
  img2 src="miners.png"
  style="width:27%; align-self: center;"
  darkmode="img-fill"
>}}

```
Running main on thread: 0
Running doer on thread: 0
Running doer on thread: 0
Running doer on thread: 0
Running doer on thread: 0
Got 4 work results in 8.0s
Results: [0, 1, 2, 3]
```
</div>

Four tasks run sequentially on the same thread, each taking two seconds. No
surprises there. We could write nearly the exact same code using regular
functions and be better off for it. In order for meaningful concurrency to
happen we need to either provide a mechanism for `work_doer` to suspend while
waiting for its "work" (`sleep_for`) to end, or we can use parallelism.

The former is more interesting, but the latter is faster to implement;
consider **Figure 2**.

{{<collapse
  label="Figure 2"
  godbolt="https://godbolt.org/z/zescEn1vc"
>}}

`work_launcher` now accepts a `sched` argument, and schedules `work_doer` onto
that scheduler via `stdexec::on`.

```cpp
exec::task<void> work_launcher(
  auto sched, std::vector<data>& result
) {
  // ...
  for(auto [in, out]: std::views::zip(inputs, result))
      co_await stdexec::on(sched, work_doer(in, out));
}
```

The scheduler is provided by a `exec::static_thread_pool` constructed inside
the `work_server`.

```cpp
exec::task<void> work_server(int len) {
  // ...
  exec::static_thread_pool threads(len);
  co_await work_launcher(threads.get_scheduler(), result);
  // ...
}
```
Nominally the entire task tree could run on the thread pool, including
`work_server` and `work_launcher`, but this introduces pathological behavior
in `stdexec`'s implementation (see [stdexec#1305](https://github.com/NVIDIA/stdexec/issues/1305)).

{{< /collapse >}}

{{<
  img2 src="miners2.png"
  style="width:48%; float: right; margin-right:4%; margin-top:3%"
  darkmode="img-fill"
>}}

Alas, we have made it worse:

```
Running main on thread: 0
Running doer on thread: 1
Running doer on thread: 2
Running doer on thread: 3
Running doer on thread: 4
Got 4 work results in 8.2s
Results: [0, 1, 2, 3]
```

We have achieved neither parallelism nor concurrency: the `work_launcher` loop
`co_await`s each `work_doer` to completion before starting the next. All we have
purchased is scheduling overhead.

We need a mechanism to start work without also waiting on that work to complete.
This operation is usually called `spawn`, and in `stdexec` it is implemented by
`exec::async_scope`.[^8] We will avail ourselves of this mechanism in
**Figure 3**, and finally conquer the tyranny of serial execution.

[^8]: In structured concurrency parlance this is a *nursery*, because it spawns
      a forest of task trees (aren't we clever?). A standardized variant exists in
      `std::execution` as `counting_scope`.

{{<collapse
  label="Figure 3"
  godbolt="https://godbolt.org/z/53Yr1qhGq"
>}}

The difference here is minimal, we use `spawn` instead of `co_await` to begin,
but not await, `work_doer`.

```cpp
exec::task<void> work_launcher(
  auto sched, exec::async_scope& scope,
  std::vector<data>& result
) {
  // ...
  for(auto [in, out]: std::views::zip(inputs, result))
    scope.spawn(stdexec::on(sched, work_doer(in, out)));
}
```

We use `co_await scope.on_empty()` to ensure all spawned work has completed.

```cpp
exec::task<void> work_server(int len) {
  // ...
  co_await work_launcher(
    threads.get_scheduler(), scope, result
  );
  co_await scope.on_empty();
  // ...
}
```

{{< /collapse >}}

The results speak for themselves:

```
Got 4 work results in 2.0s
```

We have achieved concurrent `work_doer` execution (via parallelism), producing a
4x speedup in simulated workloads. I will accept my Turing award at the earliest
convenien--

```
Results: [144536, 0, -1919962110, -1156215799]
```

Ah. Monkey balls.

## The Wrong Solution

Many will have spotted the bug immediately (bravo!). For the remainder fear not:
sanitizers find this like fingertips find papercuts.

The bug exists in the relationship between `work_launcher` and its children, the
`work_doer`s. The input `data&` to `work_doer` is a borrowed reference from
`work_launcher`'s frame. Having spawned the `work_doer`s, `work_launcher`
promptly exits said frame and the reference is left to dangle.

{{<
  img2 src="mining.png"
  style="border-radius: 7% / 20%; margin: 1rem auto;"
  darkmode="img-fill"
>}}

In an unstructured concurrency world, the usual fix is to ensure that spawned
work has some stake in the ownership of its inputs. This leads to one of two
familiar patterns, transfer ownership (`std::move`) or share ownership
(`std::shared_ptr`).

`std::shared_ptr` is unfashionable but still serviceable when an object has no
natural owner. Our program does not have this problem, ownership of each datum
can move cleanly from parent to child. We can fix the bug by switching to
pass-by-value and moving input data into `work_doer`, which we illustrate in
**Figure 4**.

{{<collapse
  label="Figure 4"
  godbolt="https://godbolt.org/z/bfbooY574"
>}}

The only change to `work_doer` is the signature, where we now take `in` by
value.

```cpp
exec::task<void> work_doer(data in, data& out) {
  // ...
}
```
And the only change to `work_launcher` is the `work_doer` callsite now features
a `std::move()`.
```cpp
exec::task<void> work_launcher(
  auto sched, exec::async_scope& scope,
  std::vector<data>& result
) {
  // ...
  for(auto [in, out]: std::views::zip(inputs, result))
    scope.spawn(stdexec::on(
      sched,
      work_doer(std::move(in), out))
    );
}
```

{{< /collapse >}}

Job done right? Well, even on its best day, `std::move()` is not free. At best
it is a smaller `memcpy()`[^9] plus whatever bookkeeping is required to leave the
source in a valid state. There is no such thing as a free `memcpy()`;[^10] some
bytes still have to move, even if it's just a couple pointers. Once you "fix"
lifetimes by ownership transfer, you pay this tax at every spawn boundary.

[^9]: Pedant’s corner: by `memcpy()` I mean "some bounded amount of state must
      be transferred." For many handle types this is a few machine words copied
      via some mechanism; for others (due to allocator quirks, syscalls, etc.)
      it is more involved in ways that are even more performance intensive than
      the best case. Either way, it is never “free” in the sense a borrowed
      reference is.

[^10]: ...except for all the cases where it is free.

Worrying about that might be premature optimization. The real costs are those
of flexibility and reasoning. To transfer ownership, ownership must be
transferable. The data we can "fix" with this mechanism must be move
constructible and at least relatively cheap to move (no
`std::array<char, 4096>`). Moreover, trying to explicitly reason about object
ownership and lifetimes is a layer of complexity we should not engage with
unless absolutely necessary.

## The Right Solution

{{<
  img2 src="machine.png"
  style="width:30%; float: right; border-radius: 20% / 10%; shape-outside: inset(1% 1% 4% 0 round 20% / 7%); margin: 1% 1% 4% 0;"
  darkmode="img-fill"
>}}

The truth is this is not a lifetime bug, it's a scoping bug. This code violates
the **strong structured concurrency invariant**, and all other problems flow
from this violation. The `work_launcher` is the operation which introduces the
dynamic fanout, therefore it must also be the operation which contains it.

If we move `async_scope` inside `work_launcher` and do not let `work_launcher`
return until the scope is empty, the bug disappears. `inputs` may remain a
simple local vector, and the children may borrow from it without any
further contortions. **Figure 5** illustrates this.

{{<collapse
  label="Figure 5"
  godbolt="https://godbolt.org/z/n1b9EjMvG"
>}}

We move the `async_scope` into `work_launcher` and `co_await` it inside that
scope.

```cpp
exec::task<void> work_launcher(auto sched, std::vector<data>& result) {
    std::vector<data> inputs(result.size());
    std::ranges::iota(inputs, 0);
    exec::async_scope scope;

    for(auto [in, out]: std::views::zip(inputs, result))
        scope.spawn(stdexec::on(sched, work_doer(in, out)));
    co_await scope.on_empty();
}
```

{{< /collapse >}}

```
Got 4 work results in 2.0s
Results: [0, 1, 2, 3]
```

Triumph.

## Coda

The alternative title for this post was **Nursery Sharing Considered Harmful**,
but I couldn't bring myself to the cliche. Allowing nurseries (eg,
`async_scope`) to cross task boundaries is a contentious but ubiquitous
capability of structured concurrency implementations. It is a required, or at
least entirely natural, mechanism to tackle some problems.[^11]

The tension comes in the guarantees we want from structured concurency. For
the original formulation of a structured approach to error propagation and
cancellation handling, nursery sharing is not a major obstacle to program
correctness. However, this approach is most popular in languages with reference
counted or borrow-checked object lifetimes. C++ is not that.

**Strong structured concurrency** provides a mechanism to further lighten the
cognitive load associated with authoring concurrent programs. In C++, a shared
nursery is not a convenience; it is an architectural boundary. We should treat
it like one.

[^11]: See Sústrik, ["Two Approaches to Structured Concurrency"](https://www.lesswrong.com/posts/pGySnaGL8WYiDT8vq/two-approaches-to-structured-concurrency).
