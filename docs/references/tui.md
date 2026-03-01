# References: TUI + Token Advisor

External resources consulted during the design and implementation of the tokenmeter TUI dashboard
and UsageAdvisor feature.

---

## Textual Framework

- **Title:** Textual — build terminal user interfaces in Python
- **URL:** https://textual.textualize.io/
- **Used for:** Framework selection, widget API (DataTable, TabbedContent, ProgressBar, ListView,
  Markdown, Static), Pilot test API, TCSS theming syntax, App/Widget lifecycle, reactive
  attributes, and key bindings.

- **Title:** Textual — Testing guide (Pilot)
- **URL:** https://textual.textualize.io/guide/testing/
- **Used for:** Understanding `app.run_test()`, `Pilot`, and async test patterns for TUI widgets.

- **Title:** Textual — Styles reference (TCSS)
- **URL:** https://textual.textualize.io/guide/CSS/
- **Used for:** TCSS layout, color variables (`$primary`, `$surface`, etc.), and widget styling.

---

## plotext

- **Title:** plotext — plots in the terminal
- **URL:** https://github.com/piccolomo/plotext
- **Used for:** ASCII line and bar chart rendering inside Textual `Static` widgets. Used
  `plt.show(output=buf)` to capture chart output as a string.

---

## pytest-asyncio

- **Title:** pytest-asyncio — async test support for pytest
- **URL:** https://pytest-asyncio.readthedocs.io/
- **Used for:** Running async Textual Pilot tests with `@pytest.mark.asyncio`.

---

## Anthropic / OpenAI Pricing and Energy

- **Title:** Claude API Pricing — Anthropic
- **URL:** https://platform.claude.com/docs/en/about-claude/pricing
- **Used for:** Verifying model pricing data used in advisor cost-saving estimates.

- **Title:** OpenAI API Pricing
- **URL:** https://openai.com/api/pricing/
- **Used for:** Verifying OpenAI model pricing used in advisor cost-saving estimates.

---

## Sustainability / Water Footprint

- **Title:** Making AI Less Thirsty: Uncovering and Addressing the Secret Water Footprint of AI
  Models (Li et al., 2023)
- **URL:** https://arxiv.org/abs/2304.03271
- **Used for:** Understanding PUE/WUE methodology underlying the water estimation module, informing
  the 500 mL threshold used in the water-usage advisor rule.

---

## Design Patterns

- **Title:** Facade pattern — Refactoring Guru
- **URL:** https://refactoring.guru/design-patterns/facade
- **Used for:** Confirming that `Meter.get_tips()` should delegate to `UsageAdvisor` rather than
  embed advisor logic directly, consistent with the existing facade pattern.

- **Title:** Registry pattern overview
- **URL:** https://martinfowler.com/eaaCatalog/registry.html
- **Used for:** Confirming that `PricingRegistry` and `EnergyRegistry` should be passed into
  `UsageAdvisor` rather than constructed internally, following the existing registry pattern.
