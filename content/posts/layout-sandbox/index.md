---
title: "The Shape of a Future Essay"
subtitle: "A draft sandbox for upcoming layout work"
subsubtitle: "Dummy content, borrowed images, real typography"
description: "A dummy draft post used to exercise the current blog layout before further changes."
postnote: "Draft only. This post exists to exercise the layout and should not be published as-is."
epigraph: "A page should be furnished enough that you can tell when the furniture moves."
epigraphAuthor: "the test harness"
date: 2026-07-09T12:00:00-04:00
draft: true
---

This is not a real essay. It is a deliberately over-equipped draft whose only
job is to hold together while we move the walls around it. If the spacing,
type, images, notes, and collapses all survive here, the real posts have a much
better chance of surviving later changes as well.{{< sn intro-note >}}

{{< banner
  src="river.png"
  alt="River test banner"
  darkmode="img-fill"
  width="80%"
/>}}

The content is intentionally mixed. Some paragraphs are short, some a little
denser, and some exist only so there is enough text for a floating or centered
figure to push against.{{< sidenote side=left >}}This one uses the direct inline
`sidenote` form, so the sandbox now exercises both shortcode authoring styles
in the same post.{{< /sidenote >}} The images are borrowed from older posts
because the stylistic behavior matters here more than the informational
content.

{{< marginalia side="right" >}}
<svg viewBox="0 0 180 236" xmlns="http://www.w3.org/2000/svg" fill="none">
  <path d="M38 30c25-16 54-14 78 6 18 16 26 37 24 62-3 29-19 48-47 58-20 7-37 18-51 33" stroke="#303030" stroke-width="4" stroke-linecap="round"/>
  <path d="M61 82c16-9 34-8 48 4 11 10 16 23 15 39-2 18-13 31-33 37" stroke="#303030" stroke-width="4" stroke-linecap="round"/>
  <circle cx="124" cy="54" r="8" stroke="#303030" stroke-width="4"/>
  <circle cx="74" cy="156" r="10" stroke="#303030" stroke-width="4"/>
  <path d="M90 176l11 14 18-8-7 18 13 12-19 1-8 17-5-18-19-2 15-11-5-18 16 10z" stroke="#303030" stroke-width="3" stroke-linejoin="round"/>
</svg>

A decorative marginal machine, included only to test desktop-only marginalia.
{{< /marginalia >}}

{{< img
  src="doctor.webp"
  darksrc="doctor_dark.webp"
  resize="684x q100"
  imgstyle="border-radius: 10% / 30%; margin-left:auto; margin-right:auto;"
>}}
Borrowed art, used here only to exercise figure sizing, captions, centering,
and dark-mode image swapping.
{{< /img >}}

## Section With Ordinary Prose

There should be enough ordinary prose to make the page feel like an actual post.
That means headings, emphasized phrases, a few rubricated lead-ins like
{{< rb >}}nota{{< /rb >}} and {{< rb blue >}}responsio{{< /rb >}}, a few inline
code fragments like `std::execution`, and at least one list whose spacing can
go wrong in obvious ways.

* The first item exists to check list indentation and vertical rhythm.
* The second exists to make sure emphasized text, links, and punctuation still
  feel balanced.
* The third is here because a layout sandbox that never uses lists is barely a
  sandbox at all.

> A draft post is not literature. It is scaffolding with nicer sentence
> boundaries.

There should also be a code block, because code almost always reveals whether a
layout is merely attractive or actually usable.{{< sn endnote-demo >}}

```cpp
struct LayoutProbe {
  std::string title;
  std::vector<std::string> sections;

  void render() const {
    for (const auto& section : sections) {
      std::println("{}: {}", title, section);
    }
  }
};
```

{{< collapse label="A small folded note" >}}

If we are going to keep collapsible regions around, they deserve to be exercised
in the draft sandbox too. This one exists to verify button spacing, the opened
panel treatment, and the close affordance at the bottom.

{{< /collapse >}}

## Section With A Hidden Figure

Sometimes the page needs a figure that does not dominate the reading flow. A
collapsed figure is a good way to keep that behavior under test without letting
it consume the whole draft.

{{< collapse_img
  label="A concealed figure"
  src="capture.webp"
  darksrc="capture_dark.webp"
  resize="x273 q90"
  imgstyle="border-radius:50%; margin-left:auto; margin-right:auto;"
>}}
The figure itself is ornamental. What matters is that the image, copy, button,
and close interaction all keep their shape when the surrounding layout changes.
{{< /collapse_img >}}

One more paragraph after the collapse keeps the bottom of the article from being
all ornament and no text. That gives us a better sense of final spacing,
especially around the last heading and any notes that follow.{{< sn left-note >}}

{{< sidenote ident="intro-note" >}}
This draft uses the shortcode-driven note system, so it can exercise desktop
margin notes without requiring any changes to the older posts that still rely
on Goldmark footnotes.
{{< /sidenote >}}

{{< sidenote ident="endnote-demo" marginable=false >}}
This note is deliberately not marginable, so the page still exercises the
endnote section on wide screens as well as mobile ones.
{{< /sidenote >}}

{{< sidenote ident="left-note" side="left" >}}
This one explicitly requests the left margin so the layout can exercise both
sides of the page on sufficiently wide screens.
{{< /sidenote >}}
