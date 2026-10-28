# CodeUpdateArena: Benchmarking Knowledge Editing on API Updates

- Zeyu Leo Liu, Shrey Pandit, Xi Ye, Eunsol Choi, Greg Durrett. arXiv: 2407.06249 | PDF: https://arxiv.org/pdf/2407.06249

## Abstract (fetched 2026-10-28 from the arXiv API)

Large language models (LLMs) are increasingly being used to synthesize and reason about source code.
However, the static nature of these models' knowledge does not reflect the fact that libraries and
API functions they invoke are continuously evolving, with functionality being added or changing.
While numerous benchmarks evaluate how LLMs can generate code, no prior work has studied how an
LLMs' knowledge about code API functions can be updated. To fill this gap, we present
CodeUpdateArena, a benchmark for knowledge editing in the code domain. An instance in our benchmark
consists of a synthetic API function update paired with a program synthesis example that uses the
updated functionality; our goal is to update an LLM to be able to solve this program synthesis
example without providing documentation of the update at inference time. Compared to knowledge
editing for facts encoded in text, success here is more challenging: a code LLM must correctly
reason about the semantics of the modified function rather than just reproduce its syntax. Our
dataset is constructed by first prompting GPT-4 to generate atomic and executable function updates.
Then, for each update, we generate program synthesis examples whose code solutions are prone to use
the update. Our benchmark covers updates of various types to 54 functions from seven diverse Python
packages, with a total of 670 program synthesis examples. Our experiments show that prepending
documentation of the update to open-source code LLMs (i.e., DeepSeek, CodeLlama) does not allow them
to incorporate changes for problem solving, and existing knowledge editing techniques also have
substantial room for improvement. We hope our benchmark will inspire new methods for knowledge
updating in code LLMs.

## Why it is on the list

Closest prior work on synthetic API changes: it measures whether a model can use an API update it is
given. PriorLock's difference is that the update is not given; it sits in the repository and the
agent has to notice and read it, and the result is a reward for an agent loop rather than a
knowledge-editing benchmark.
