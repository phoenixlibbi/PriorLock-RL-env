# VersiCode: Towards Version-controllable Code Generation

- arXiv: 2406.07411 | PDF: https://arxiv.org/pdf/2406.07411 | Code: github.com/wutong8023/VersiCode

## Abstract (fetched 2026-07-25)

Large Language Models (LLMs) have made tremendous strides in code generation, but existing research
fails to account for the dynamic nature of software development, marked by frequent library updates.
This gap significantly limits LLMs' deployment in realistic settings. In this paper, we propose two
novel tasks aimed at bridging this gap: version-specific code completion (VSCC) and version-aware
code migration (VACM). In conjunction, we introduce VersiCode, a comprehensive Python dataset
specifically designed to evaluate LLMs on these two tasks, together with a novel evaluation metric,
Critical Diff Check (CDC@1), which assesses code generation against evolving API requirements. We
conduct an extensive evaluation on VersiCode, which reveals that version-controllable code
generation is indeed a significant challenge, even for GPT-4o and other strong frontier models.

## What PriorLock cites

- Independent dataset/metric confirming the same weakness (>50-point drops vs standard benchmarks
  reported for GPT-4o-class models on version-specific completion).
- Same coverage limitation as GitChameleon: string/diff-level quiz on real libraries; not agentic,
  not a training environment, contaminating over time.
