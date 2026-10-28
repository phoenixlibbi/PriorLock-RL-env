# Adaptive Chameleon or Stubborn Sloth: Revealing the Behavior of Large Language Models in Knowledge Conflicts

- Jian Xie, Kai Zhang, Jiangjie Chen, Renze Lou, Yu Su. arXiv: 2305.13300 | PDF: https://arxiv.org/pdf/2305.13300

## Abstract (fetched 2026-10-28 from the arXiv API)

By providing external information to large language models (LLMs), tool augmentation (including
retrieval augmentation) has emerged as a promising solution for addressing the limitations of LLMs'
static parametric memory. However, how receptive are LLMs to such external evidence, especially when
the evidence conflicts with their parametric memory? We present the first comprehensive and
controlled investigation into the behavior of LLMs when encountering knowledge conflicts. We propose
a systematic framework to elicit high-quality parametric memory from LLMs and construct the
corresponding counter-memory, which enables us to conduct a series of controlled experiments. Our
investigation reveals seemingly contradicting behaviors of LLMs. On the one hand, different from
prior wisdom, we find that LLMs can be highly receptive to external evidence even when that
conflicts with their parametric memory, given that the external evidence is coherent and convincing.
On the other hand, LLMs also demonstrate a strong confirmation bias when the external evidence
contains some information that is consistent with their parametric memory, despite being presented
with conflicting evidence at the same time. These results pose important implications that are worth
careful consideration for the further development and deployment of tool- and retrieval-augmented
LLMs. Resources are available at https://github.com/OSU-NLP-Group/LLM-Knowledge-Conflict.

## Why it is on the list

The general question behind PriorLock: when does a model follow in-context evidence that contradicts
its parametric memory? PriorLock is a coding-agent instance of that question, graded on the library
calls the code actually made.
