# Embers of Autoregression: Understanding LLMs Through the Problem They are Trained to Solve

- McCoy, Yao, Friedman, Hardy, Griffiths. arXiv: 2309.13638 | PDF: https://arxiv.org/pdf/2309.13638
- Journal version: PNAS ("Embers of autoregression show how large language models are shaped by the
  problem they are trained to solve"), https://www.pnas.org/doi/10.1073/pnas.2322420121

## Abstract (fetched 2026-07-25)

The widespread adoption of large language models (LLMs) makes it important to recognize their
strengths and limitations. We argue that in order to develop a holistic understanding of these
systems we need to consider the problem that they were trained to solve: next-word prediction over
Internet text. By recognizing the pressures that this task exerts we can make predictions about the
strategies that LLMs will adopt, allowing us to reason about when they will succeed or fail. This
approach - which we call the teleological approach - leads us to identify three factors that we
hypothesize will influence LLM accuracy: the probability of the task to be performed, the
probability of the target output, and the probability of the provided input. We predict that LLMs
will achieve higher accuracy when these probabilities are high than when they are low - even in
deterministic settings where probability should not matter. To test our predictions, we evaluate two
LLMs on eleven tasks, and we find robust evidence that LLMs are influenced by probability in the
ways that we have hypothesized. In many cases, the experiments reveal surprising failure modes. For
instance, GPT-4's accuracy at decoding a simple cipher is 51% when the output is a high-probability
word sequence but only 13% when it is low-probability.

## What PriorLock cites

- The MECHANISM behind our gap: next-token pressure makes the high-probability (familiar) behavior
  the default, even when the context demands the low-probability (deviant) one.
- 51% -> 13% cipher example = the probability cliff our silent deviations stand on.
- Our traps are, precisely, low-probability variants of high-probability API surfaces.
