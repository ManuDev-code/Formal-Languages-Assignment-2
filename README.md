# Subset Construction — SI2002 Formal Languages, Assignment 2

## Student information

- **Full name:** *MANUELA MUÑOZ LUJÁN*
- **Class number:** *4855*


## Environment / tools used

- **Operating system:** *Windows 11*
- **Programming language:** Python 3
- **Interpreter version used for testing:** Python 3.12 (any Python ≥ 3.7 works, since the program only uses the standard library)
- **Libraries:** none beyond the Python standard library (`sys`, `os`, `re`,
  `argparse`, `collections.deque`)

## How to run the program

Detailed step-by-step instructions. A short English
summary:

```bash
# Option 1: interactive console (menu appears automatically)
python3 subset_construction.py

# Option 2: pipe a file into standard input
python3 subset_construction.py < ejemplos/entrada_ejemplo.txt

# Option 3: also show a human-readable, labeled explanation of the
# official output (initial state, final states, transition table with
# labels) — printed on screen right after the official result. This does
# NOT replace or alter the official output in any way.
python3 subset_construction.py -i ejemplos/entrada_ejemplo.txt --legible

# Option 4: pass the input file explicitly with -i (this is the
# "upload a file" mode)
python3 subset_construction.py -i ejemplos/entrada_ejemplo.txt

# Optional bonus feature: also produce Graphviz .dot diagrams of every
# resulting DFA
python3 subset_construction.py -i ejemplos/entrada_ejemplo.txt --dot diagramas.dot

```

No installation step is required: the program is a single self-contained
Python file (`subset_construction.py`) that only uses the Python standard
library.

## Input / output format

The program follows exactly the input format described in the assignment
PDF (`c` cases; per case: `n`, initial states `S`, alphabet `Σ`, final
states `F`, and `n` transition-table rows using `0` for ∅ and `{a b c}`
for a set of destination states).

For the **output**, the assignment leaves the exact table layout free
("you may rename the states of M for readability... indicate the initial
state and the final states"). This implementation mirrors the input
format for consistency and easy manual verification:

```
n_dfa                 <- number of DFA states
initial_state          <- a single state id (the DFA is deterministic)
a b ...                <- same alphabet, same order as the input
f1 f2 ... (or "0")     <- final states of the DFA ("0" if there are none)
n_dfa lines            <- "state_id  target_a  target_b  ..."
                          (no braces here: each target is a single state,
                          never a set, because the automaton is deterministic)
```

DFA states are numbered `1..n_dfa` in the order they are *discovered*
during the subset-construction search (breadth-first from the initial
set), exactly as the assignment allows.

No extra lines (banners, prompts, logs, etc.) are printed when the input
comes from a file or from a redirected/piped standard input. An interactive menu
is only shown when the program is run directly in a terminal with nothing
redirected, purely as a convenience for manual use.

## Algorithm explanation — Subset Construction

Given an NFA `M = (Q, Σ, Δ, S, F)` (as in Kozen's Lecture 6, allowing
**multiple** initial states and no epsilon-transitions), the equivalent
DFA `M' = (Q', Σ, δ', q0', F')` is built as follows:

1. **Initial state:** `q0' = S`, i.e. the *set* of all NFA initial states
   becomes, as a whole, the single initial state of the DFA. No
   epsilon-closure is needed because this NFA variant has no
   epsilon-transitions in its transition table.

2. **Transition function:** for a DFA state `A ⊆ Q` and a symbol
   `a ∈ Σ`:

   ```
   δ'(A, a) = ⋃_{q ∈ A} Δ(q, a)
   ```

   i.e. the set of all NFA states reachable from *any* state currently in
   `A` by reading `a`.

3. **State discovery (worklist / BFS):** starting from `q0' = S`, every
   time `δ'(A, a)` produces a subset that has not been seen before, it is
   added to a queue to be processed later. This guarantees that **only
   reachable subsets** are ever created — never the full power set
   `2^Q`, which would be exponential and mostly useless (unreachable)
   states.

4. **The empty set as a "trap" / "dead" state:** if `δ'(A, a) = ∅` for
   some `A` and `a`, the empty set itself becomes a DFA state (say, with
   id `k`). Its own transitions are then `δ'(∅, a) = ∅` for every symbol
   (a self-loop on every symbol), because there is nothing in the empty
   set of NFA states to take any further transition from. This state is
   what makes the resulting automaton a **complete/total** DFA (a
   transition is defined for every state and every symbol), which is a
   standard part of the subset-construction algorithm and is required for
   the result to be a proper DFA rather than a partial automaton.

5. **Final states:** a DFA state `A` is final if and only if
   `A ∩ F ≠ ∅`, i.e. the subset contains at least one original NFA final
   state.

6. **Renaming:** the DFA states, which are internally represented as sets
   of NFA states, are renamed to plain integers `1, 2, 3, ...` in the
   order they were discovered by the BFS, so the output is simple and
   readable (as explicitly allowed by the assignment).

### Complexity

Let `n = |Q|` and `|Σ| = k`. In the worst case the number of reachable
DFA states is `O(2^n)`, but in practice, because only *reachable* subsets
are generated (not the full power set), the algorithm runs in time
proportional to `(number of DFA states discovered) × k × n`, which for
the great majority of practical automata is far smaller than `2^n`.

## Design decisions worth mentioning to a grader

- **Multiple initial states are supported directly**, without converting
  them into a single state via an artificial epsilon-transition: the DFA
  initial state is simply the frozenset `S` itself, which is exactly what
  the subset-construction algorithm calls for.
- **Sets in the input (`{1 5}`) are parsed with a regular expression**
  that treats `{...}` as one atomic token, instead of naively splitting
  the line on whitespace (which would incorrectly split `{1 5}` into
  `{1` and `5}`).
- **The trap/dead state (∅) is always materialized explicitly** whenever
  it is reachable, so the produced DFA is complete.
- **Only reachable states are generated** (breadth-first search from the
  initial state), never the full power set of `Q`.
- **No extra output lines** are produced in non-interactive mode (file or
  piped input), in line with "Do not print extra lines" from the
  assignment.

## Project structure

```
.
├── subset_construction.py       # Main program (heavily commented in Spanish)
├── README.md                    # This file
├── .gitignore
└── entrada_ejemplo.txt      # The exact example from the assignment PDF
```

## Optional feature implemented

As allowed by the assignment ("Optional: you might include additional
features... for instance, to print automata as diagrams"), this
implementation can optionally emit a **Graphviz `.dot`** representation of
every resulting DFA via the `--dot` flag. This is purely additive and
does not change the required input/output behavior in any way.
