# Running Modes

This project is designed to run in **three modes** from a **single public codebase**,
so anyone who clones it can demonstrate the mechanistic-interpretability (mech-interp)
pipeline in whatever environment they have — from a modest laptop to a cloud GPU.

The interpretability analysis and the interp→escalation logic are written **once**
against a common `InterpBackend` interface. Only the *backend* that supplies
activations/attention/SAE-features differs between modes, so results are comparable and
there is no rework moving between environments.

| Mode | Name | Hardware | Model | Needs torch? | Purpose |
|------|------|----------|-------|--------------|---------|
| 1 | **Offline proof** | Any laptop (no GPU) | none — precomputed artifacts | **No** | Prove the mech-interp pipeline + escalation logic *work*, reproducibly, with no model or GPU. Runs in CI. |
| 2 | **Local real** | Enough RAM / a local GPU | GPT-2-small → optionally Gemma-2-2b | Yes | Run *actual* mech-interp locally. |
| 3 | **Cloud** | Cloud GPU (Colab/Kaggle/rented) | Gemma-2-2b + Gemma Scope SAEs | Yes | Full-fidelity study on the real target model; **generates the artifacts Mode 1 replays**. |

## Mode selection

A capability detector chooses the backend automatically, with graceful fallback to
Mode 1 if torch / a model / enough memory is not available. You can force a mode with an
environment variable:

```bash
export INTERP_MODE=artifact   # Mode 1 (default fallback)
export INTERP_MODE=local      # Mode 2
export INTERP_MODE=cloud      # Mode 3
```

If `INTERP_MODE` is unset, the detector tries `local`/`cloud` when torch + a usable
model are present, otherwise falls back to `artifact` (Mode 1).

---

## Mode 1 — Offline proof (runs on any laptop)

**What it is.** The mech-interp analysis and escalation logic run against small
**precomputed interpretability artifacts** (captured activations, attention maps, SAE
feature activations for the example answers) shipped in `data/interp_artifacts/`. No
model weights, no torch, no GPU.

**Why it matters.** Anyone cloning the public repo can immediately see interpretability
"work" — the spurious-feature detector flags the right answers, and flagged grades route
to human review — without any hardware. This is the reproducible **proof**.

**Honesty note.** Until a Mode 3 run has generated real artifacts, the shipped artifacts
are clearly labelled **synthetic placeholders**. Once you run the cloud notebook, they
are replaced by *real* Gemma-derived captures, so Mode 1 becomes a faithful replay of
genuine results — not a fabrication.

**Requirements.** Only the core deps:
```bash
pip install -r requirements.txt        # numpy, einops, jaxtyping, pytest
```

**Run (indicative — commands finalised when the code lands):**
```bash
export INTERP_MODE=artifact
python -m evals.run_all              # includes interp-based escalation
```

---

## Mode 2 — Local real (machine with enough RAM / a GPU)

**What it is.** The same code, but a `LocalTorchBackend` loads a real model via
TransformerLens and captures real activations/attention, and SAEs via `sae_lens`.

**Start with GPT-2-small.** It is ~500 MB, needs no license, downloads automatically on
first use, and fits comfortably on a modest machine (CPU is fine). It is the canonical
TransformerLens model and is ideal for validating the *pipeline*. GPT-2 is too weak to
*grade* Social Science well, but perfect for developing/verifying the interp machinery.

**Then optionally Gemma-2-2b** if your machine has the RAM/GPU (see hardware note below).

**Requirements.**
```bash
pip install -r requirements.txt
pip install -r requirements-interp.txt      # torch, transformer_lens, sae_lens, ...
```

**Downloads happen in this order:**
1. `pip install -r requirements-interp.txt` → libraries (once per environment).
2. First run → **GPT-2-small weights (~500 MB)** auto-download, cached to
   `~/.cache/huggingface`.
3. (If you choose Gemma) first Gemma run → **Gemma-2-2b (~5 GB)** + **Gemma Scope SAEs**,
   after accepting the license (see Mode 3).

**Run (indicative):**
```bash
export INTERP_MODE=local
export INTERP_MODEL=gpt2            # or gemma-2-2b when hardware allows
python -m evals.run_all
```

---

## Mode 3 — Cloud (Colab / Kaggle / rented GPU)

**What it is.** The full study on the real target model: **Gemma-2-2b + Gemma Scope
SAEs** on a cloud GPU. This mode also **exports the interpretability artifacts** that
Mode 1 ships and replays — closing the loop between the real run and the laptop proof.

**Gated model — one-time setup.** Gemma is a gated Hugging Face model:
1. Create a Hugging Face account.
2. Visit the Gemma-2-2b model page and **accept Google's license**.
3. Create an HF access token and provide it to the environment (e.g. `huggingface-cli
   login`, or set `HF_TOKEN`). **Never commit the token.**

**Requirements.** Inside the Colab/Kaggle notebook:
```bash
pip install -r requirements.txt
pip install -r requirements-interp.txt
```

**Run.** Open the notebook at `interpretability/cloud_gemma_scope.ipynb` in Colab or
Kaggle. It:
1. installs deps and authenticates to Hugging Face,
2. loads Gemma-2-2b + Gemma Scope SAEs,
3. runs logit lens / activation patching / attention analysis / SAE feature maps on the
   example answers,
4. **exports artifacts** to `data/interp_artifacts/` for Mode 1.

---

## Hardware notes & the RAM/quantization tension

These are guidelines about what the **models** require — compare them against whatever
machine you intend to use.

- **Model memory.** Gemma-2-2b needs roughly **~5–6 GB just for the weights** (bf16),
  before activations and framework overhead. As a rule of thumb, if the weights do not
  fit comfortably in your available RAM/VRAM with headroom to spare, expect heavy
  swapping or out-of-memory errors. In that case, use **GPT-2-small locally** (Mode 2)
  and run **Gemma on a GPU** (Mode 3). GPT-2-small (~500 MB) fits on essentially any
  modern machine and runs on CPU.
- **Quantization vs. mech-interp.** Aggressive 4-/8-bit quantization can shrink a model
  to fit limited memory, but it interferes with the clean, full-precision **activations**
  that logit lens, activation patching, and Gemma Scope SAEs rely on. Gemma Scope SAEs
  are trained on non-quantized activation spaces. So quantization is **not** the right
  way to force faithful interpretability onto a memory-constrained machine — prefer
  GPT-2-small locally and Gemma on a GPU.
- **GPU.** Not required for Modes 1–2 with GPT-2 (CPU works). A GPU is strongly
  recommended for Gemma-2-2b (Mode 3, or a capable Mode 2).
- **Disk.** Libraries plus cached weights total roughly ~10–15 GB. Not usually a
  constraint.

## Summary of what each mode downloads

| | Mode 1 | Mode 2 (GPT-2) | Mode 2/3 (Gemma) |
|---|---|---|---|
| Python libs | `requirements.txt` only | + `requirements-interp.txt` | + `requirements-interp.txt` |
| Model weights | none | GPT-2-small (~500 MB, auto) | Gemma-2-2b (~5 GB, gated) |
| SAEs | none (uses artifacts) | optional | Gemma Scope SAEs |
| GPU | no | no (CPU ok) | recommended |
