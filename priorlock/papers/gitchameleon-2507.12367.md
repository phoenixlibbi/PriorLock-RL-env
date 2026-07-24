# GitChameleon 2.0: Evaluating AI Code Generation Against Python Library Version Incompatibilities

- arXiv: 2507.12367 | PDF: https://arxiv.org/pdf/2507.12367 | Code: github.com/mrcabbage972/GitChameleonBenchmark

## Abstract (fetched 2026-07-25)

The rapid evolution of software libraries poses a considerable hurdle for code generation,
necessitating continuous adaptation to frequent version updates while preserving backward
compatibility. While existing code evolution benchmarks provide valuable insights, they typically
lack execution-based evaluation for generating code compliant with specific library versions. To
address this, we introduce GitChameleon 2.0, a novel, meticulously curated dataset comprising 328
Python code completion problems, each conditioned on specific library versions and accompanied by
executable unit tests. GitChameleon 2.0 rigorously evaluates the capacity of contemporary large
language models (LLMs), LLM-powered agents, code assistants, and RAG systems to perform
version-conditioned code generation that demonstrates functional accuracy through execution. Our
extensive evaluations indicate that state-of-the-art systems encounter significant challenges with
this task; enterprise models achieving baseline success rates in the 48-51% range, underscoring the
intricacy of the problem. By offering an execution-based benchmark emphasizing the dynamic nature of
code libraries, GitChameleon 2.0 enables a clearer understanding of this challenge and helps guide
the development of more adaptable and dependable AI code generation methods.

## What PriorLock cites

- Enterprise models 48-51% baseline success on version-conditioned generation WITH the version
  stated in the prompt -> the gap is prior-override failure, not missing information.
- Evaluates agents/assistants/RAG too; RAG helps but does not close the gap.
- Limitation we exploit as our coverage argument: 328 single-function completion problems - an
  eval quiz, not an agentic environment; no terminal, repo, or reward machinery; built from REAL
  libraries' breaking changes (contamination dissolves it over time).
