# References: Energy Tracking Feature

External resources consulted during design and implementation of the energy tracking feature.

---

## Energy Benchmarks for AI Models

**Title:** "Power Hungry Processing: Watts Driving the Cost of AI Deployment?"
**Authors:** Lottick et al. / Emma Strubell et al. (related prior work on NLP energy costs)
**URL:** https://arxiv.org/abs/2311.16863
**Used for:** Understanding the methodology for measuring AI inference energy in Wh per token. Informed the decision to use Wh/MTok as the primary unit.

---

**Title:** Anthropic — Claude model pricing and technical documentation
**URL:** https://platform.claude.com/docs/en/about-claude/pricing
**Used for:** Cross-referencing model families (Opus, Sonnet, Haiku) to assign relative energy tiers. Larger/more capable models consume more energy per token.

---

**Title:** OpenAI — Model overview and pricing documentation
**URL:** https://platform.openai.com/docs/models
**Used for:** Cross-referencing OpenAI model families (GPT-5, GPT-4o, o-series) to assign relative energy tiers.

---

**Title:** "The Carbon Impact of Artificial Intelligence" — Nature Machine Intelligence
**URL:** https://www.nature.com/articles/s42256-020-0219-9
**Used for:** Context on GPU energy consumption ranges and the relationship between model size and energy use. Helped calibrate order-of-magnitude values for Wh/MTok.

---

**Title:** Google Data Center Efficiency — PUE and WUE definitions
**URL:** https://www.google.com/about/datacenters/efficiency/
**Used for:** Understanding PUE and WUE factors already used in the water module, to clarify that energy tracking intentionally omits these environmental conversion factors.

---

## Prior Art in tokenmeter

**File:** `src/tokenmeter/water/_data.py`
**Note:** The Wh/MTok values in `energy/_data.py` are an independent copy of the water module's energy data. The energy module does not import from or depend on the water module.

**File:** `src/tokenmeter/water/__init__.py`, `src/tokenmeter/water/calculator.py`
**Note:** The registry/calculator pattern was reused directly for the energy module.
