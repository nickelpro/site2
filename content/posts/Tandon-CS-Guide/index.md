---
title: "Vito's Guide to Tandon CS \"Placement\""
subtitle: "\"Guide to Skipping Class\" might give people the wrong idea"
description: "Fuck you Reddit"
image: "social-media"
date: 2021-06-13T10:47:32-04:00
draft: false
---

Tandon's CS program, unlike CAS and the majority of other schools with CS programs, does not have any sort of CS placement. Officially, the only course an incoming CS/CE/ECE major can skip is the very first Intro course with an AP CS exam score of 4 or 5. Unofficially, you can skip all of the requirements of any of the majors so long as you get enough credits in the required course work by graduation. This guide is intended to be helpful to underclassmen attempting to take an unorthodox approach to these majors.

## Intended Audience

You are an incoming freshman or rising sophmore with a large amount of personal programming experience. You program for fun, are engaged in open source work, and/or have some professional experience under your belt already. You do not need anyone to teach you language syntax, control flow, boolean algebra, or how to setup a dev environment. Perhaps you've been programming for as long as you can remember, or maybe you're a non-traditional student. If you connect with any of this, this guide might be for you.

{{< collapse label="And who are you exactly?" >}}

Hi I'm Vito, I'm a rising sophmore ECE student at Tandon. Over the course of my freshman year I went through (and continue to tangle with) a lot of frustration getting placed into CS courses that met my level of experience. One of the biggest frustrations was that no one seemed to know who I was supposed to talk to, what I needed to demonstrate, or what the general process was for placing out of course requirements. I'm writing this guide to put out some of my lessons learned in hopes that others might have a slightly easier path than I did.

{{< /collapse >}}


## General Approach

Placing out of any given class has a single requirement surrounded by a lot of question marks: You need the professor's recommendation that you possess the prerequisite knowledge the course is trying to teach. The steps to do this are more straight forward than you might think:

1. Find which professor teaches the course via Albert
2. Email that professor, explain your situation, and ask if they have time to talk about a recommendation
3. Interview with the professor
4. Ensure the recommendation reaches the CSE Manager of Academics (and make sure to save copies of the recommendation email), who will place you into the next course in the major
5. Return to Step 1

Crucially, ***you DO NOT have to wait for classes to start to do this***. You do not have to attend a lecture with the professor, approach them in person, get to know them, etc. If you wait to personally meet with each professor, you're going to find yourself right up against the drop deadline in September trying to schedule meetings and hoping the CSE Manager is paying attention to her email.

Step 3 is the tricky one. Since there is no formal process for this there is no _specific_ knowledge you must possess for these interviews. While it's a good idea to read the syllabus for the course and be generally prepared for any subject listed on it, I will try to provide some guidance about what I was interviewed about.


**GPA Warning:** This process does not grant you credit for courses you interview out of. If you are a talented programmer you can generally get through lower level courses with straight-As, by interviewing out you are asking to take more advanced and difficult coursework for the same credits. This might be something to consider.

## Freshman Advisement

I'll be frank, the freshman advisors are crap and don't know what they're doing. Their job is to make sure students "manage the transition" to college, which means on the actual _academics_ they fall woefully short. They also don't have the ability to help you in any meaningful way, since they don't have permission to make decisions about academic requirements for the departments. My advice is to keep your advisor in the loop about your intent to place out of courses, but largely bypass them and communicate directly with the CSE Advisement Department and the CSE Manager.


## Specific Course Recommendations

Disclaimer, courses have professors who rotate through, so my advice may be dated already

**CS-UY 1114 Introduction to Programming and Problem Solving**

You can place out of this course with an AP CS score of 4 or 5. For me I simply asked to place out of it and sent the professor a link to my Github, and they immediately sent a recommendation that I place out. This course covers very trivial introductory programming topics, any interview that might happen will be similarly trivial. I'll take this moment to mention most Tandon courses are taught in C/C++ and Python, so those are the languages you best have under your belt.

**CS-UY 1134 Data Structures and Algorithms**

One of the harder courses to interview out of, effectively easy-medium level leetcode questions. Know your data structures, lists, stacks, queues, maps, and how they're implemented. Know your sorting algorithms, their complexities, and how they're implemented. And by "know them" I mean: be able to implement merge sort on the spot, not merely describe it. Finally, be able to look at some arbitrary chunks of code and calculate the big-O complexity.

**CS-UY 2124 Object Oriented Programming**

This is a C++ course about C++. You need to know C++. Constructors, destructors, inheritance/polymorphism, virtual inheritance, various types of initialization, memory management, operator overloads, etc. This interview is much easier if you have a smallish (<1.5k LoC) project you can use as an example while talking about these things. Again, I just sent a Github link for this one and then talked about the project and the various C++ things it did with the professor.

**CS-UY 2204 Digital Logic and State Machine Design**

Typically this course is only for the CE/ECEs, so pure CS don't need to consider this one. This is a course about boolean algebra, state machines, Verilog, and device building blocks (adders, flip-flops, muxes, etc). You must be able to work through K-Maps to get equations into SOP/POS form, write out state-transition tables and draw the associated state diagram, know the construction of basic devices from logic gates, and work out larger devices from those primitive devices (think universal shift register from muxes and flip-flops). Finally you need to know basic Verilog syntax to implement all those things, and again a Github link is handy here.

This interview is either very easy if you have a background in digital electronics, or very very hard if you don't. Feel free to DM me for advice about this one if you're attempting it.


**CS-UY 2214 Computer Architecture and Organization**

_Full disclosure: I ran out of time for interviews and actually ended up taking this course instead of skipping it. That said I think I can extrapolate what would be in an interview._

There's some overlap here with 2204. This course also requires boolean algebra and Verilog, but instead of discreet digital electronics you're going to want to know how to describe an ALU in gates and in Verilog. After that it's all about cache, addressing modes, and x86 assembly. Be able to describe cache placement policies, LRU cache replacement, and multi-level caches as well as write-through vs write-back write policies. Be able to describe virtual memory and page-table layouts. And finally, know some basic x86 assembly, be able to read simple functions, loops, etc. Nothing more complex than writing an `atoi` in asm. Oh and it's all Intel syntax.

## Conclusion

And that's what I've got. I'm not a CS major so I've got no advice for the courses that typically only CS majors take like CS-UY 2413, Design and Analysis of Algorithms. If anyone has interviewed out of it or can guess at the requirements I would love to add it.

Also, for any course you skip ever, save the recommendation. I mentioned this once already but it bears repeating. I'm in a month long back and forth with the CSE department right now about whether I had permission to skip all those courses (they forgot, I guess) and if I hadn't saved all the emails I would have been screwed.
