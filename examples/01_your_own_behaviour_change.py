"""Recipe 1: add your own silent behaviour change and get a gated task.

Define one Probe: a library function whose behaviour changed without its
signature changing, the call a doc-reading agent makes, and the call a
memory-driven agent makes. PriorLock generates the library, its CHANGELOG and
API docs, the input data, the smoke test, the hidden grader and the
references, and the ladder below must come out exactly.

    python examples/01_your_own_behaviour_change.py
"""
import tempfile
from pathlib import Path

from priorlock.probes.base import Probe
from priorlock.standalone import generate, grade

JOIN_SEPARATOR = Probe(
    id="join_separator_default",
    family="default_flip",
    category="text",
    summary="join() now separates with ',' by default, not a space.",
    fn="join",
    signature='join(words, sep=",")',
    impl='''
def join(words, sep=","):
    """Join words into one string, separated by *sep*."""
    return sep.join(words)
''',
    api_doc='`join(words, sep=",")`: join `words` into one string separated by `sep`.',
    changelog='**`join` - default `sep` changed from `" "` to `","`.** '
              'Pass `sep=" "` to keep space-separated output.',
    param="sep",
    gold_kwargs={"sep": " "},       # what an agent that read the CHANGELOG writes
    familiar_kwargs={},             # what an agent coding from memory writes
    familiar_behaviour="words are joined with a space",
    installed_behaviour="words are joined with a comma",
    task_clause="Join `words` into a single **space-separated** string. "
                "Write it under `joined`.",
    output_key="joined",
    input_payload={"words": ["read", "the", "docs"]},
    gold_output="read the docs",
    familiar_output="read,the,docs",
)

task = Path(tempfile.mkdtemp()) / "task"
generate(task, probes=[JOIN_SEPARATOR], seed="recipe-1")
print("task written to", task)
for ref in ("gold", "familiar", "stub"):
    report = grade(task, reference=ref)
    print(f"{ref:<9} {report['gap_score']:.2f}  "
          f"{[p['verdict'] for p in report['probes']]}")
# gold 1.00 override · familiar 0.40 prior_locked · stub 0.00 bypassed
