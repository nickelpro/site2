---
title: "Addendum: Command Line Flags in C++"
subtitle: "Handling Positional Arguments"
date: 2022-02-13T14:42:00-04:00
image: "social-media"
draft: false
---

In the Reddit comments for the original [Command Line Flags post](/posts/min-guide-to-cli)
there was an interesting discussion about what to do for positional parameters
when the user wants to pass an argument that matches an existing flag.
[/u/AlmaemberTheGreat pointed out](https://www.reddit.com/r/cpp/comments/sr75ch/command_line_flags_in_c_a_minimalists_guide/hwrsq5s/)
the standard way to do this in the Unix world is to handle a pseudo-flag: `--`.

The intent being when `--` is encountered the remaining command line arguments
should be interpreted positionally. Adding this to the original parse function
is both simple and illustrative of the flexibility of the approach.

### Solution

Let's assume we have the same `MySettings` struct as laid out in
***Figure 1***, but this time both `infile` and `outfile` are positional
arguments. To adapt the final parser, let's first write a small helper function
that knows how to handle positional arguments. We'll assume that `infile` is
the first positional argument (if not already provided) and `outfile` is
the second (if not already provided).

{{< collapse label="Figure 6">}}
```cpp
MySettings parse_positional(
    int argc, const char* argv[], MySettings& settings) {

  // Assume the first element of the char* array is the
  // "positional arguments" flag, ie "--", and skip it
  // by starting at i = 1
  for(int i {1}; i < argc; i++)
    if(!settings.infile)
      settings.infile = argv[i];
    else if(!settings.outfile)
      settings.outfile = argv[i];
    else
      break;

  return settings;
}
```
{{< /collapse >}}

All that's left to do is add this to the original ***Figure 5*** parser:

{{< collapse label="Figure 7">}}
```cpp
MySettings parse_settings(int argc, const char* argv[]) {
  MySettings settings;

  // argv[0] is traditionally the program name, so start at 1
  for(int i {1}; i < argc; i++) {
    string opt {argv[i]};

    // Are we finished parsing flags?
    if(opt == "--")
      // Yes, handle remaining positional arguments
      return parse_positional(argc - i, argv + i, settings);

    // No, is this a NoArg?
    else if(auto j {NoArgs.find(opt)}; j != NoArgs.end())
      j->second(settings); // Yes, handle it!

    // Remainder of code is the same as Figure 5
  }

  return settings;
}
```
{{< /collapse >}}
