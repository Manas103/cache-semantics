"""Build the two step-plot figures (OpenAI, DeepSeek) from already-collected,
already-vetted sweep data. No new API calls. Run from the pilot/ directory.

OpenAI: chunk_sweep_results.json (45 points) with the 4 outlier positions
(1, 23, 36, 45; see paper Sec. 4.2) overridden by recheck_sweep_outliers.json.

DeepSeek: deepseek_full_sweep_results.json (45 points) with the 7 landmark
positions marked source="rep0_reuse" (self-hit-contaminated, see paper Sec. 3
methods note) overridden by deepseek_recheck_outliers.json's independently
rechecked values. The other 38 points (source="fresh") are used as-is.
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT_DIR = "../paper/figures"

# ---- OpenAI ----
openai_sweep = json.load(open("chunk_sweep_results.json"))
openai_corrected = {d["tool_index"]: d["cached"] for d in openai_sweep}
openai_outliers = json.load(open("recheck_sweep_outliers.json"))
for d in openai_outliers:
    openai_corrected[d["tool_index"]] = d["cached"]

xs = sorted(openai_corrected.keys())
ys = [openai_corrected[x] for x in xs]

fig, ax = plt.subplots(figsize=(6, 3.2))
ax.step(xs, ys, where="post", color="#1f5fa8", linewidth=1.6)
ax.set_xlabel("Edit position (tool index)")
ax.set_ylabel("Credited tokens")
ax.set_title("OpenAI: 45-position sweep, tool-schema prefix")
ax.set_xlim(1, 45)
ax.set_ylim(0, max(ys) * 1.08)
ax.grid(True, linewidth=0.4, alpha=0.5)
fig.tight_layout()
fig.savefig(f"{OUT_DIR}/openai_sweep.pdf")
plt.close(fig)

# ---- DeepSeek ----
ds_sweep = json.load(open("deepseek_full_sweep_results.json"))
ds_outliers = json.load(open("deepseek_recheck_outliers.json"))
ds_corrected = {}
for k, v in ds_sweep.items():
    idx = int(k)
    if v["source"] == "rep0_reuse":
        ds_corrected[idx] = ds_outliers[k]["cached"]
    else:
        ds_corrected[idx] = v["cached"]

xs2 = sorted(ds_corrected.keys())
ys2 = [ds_corrected[x] for x in xs2]

fig2, ax2 = plt.subplots(figsize=(6, 3.2))
ax2.step(xs2, ys2, where="post", color="#a83232", linewidth=1.6)
ax2.set_xlabel("Edit position (tool index)")
ax2.set_ylabel("Credited tokens")
ax2.set_title("DeepSeek: 45-position sweep, tool-schema prefix")
ax2.set_xlim(1, 45)
ax2.set_ylim(0, max(ys2) * 1.08)
ax2.grid(True, linewidth=0.4, alpha=0.5)
fig2.tight_layout()
fig2.savefig(f"{OUT_DIR}/deepseek_sweep.pdf")
plt.close(fig2)

print("wrote", f"{OUT_DIR}/openai_sweep.pdf", f"{OUT_DIR}/deepseek_sweep.pdf")
