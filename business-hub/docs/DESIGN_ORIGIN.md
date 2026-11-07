# Design origin and maintenance policy

Launchpad is maintained as a self-contained implementation in `business-hub/`. Its HTML, CSS, JavaScript and SVG artwork are authored for this project. The design revision uses navy, royal blue and coral, with the palette recorded in [the customization guide](CUSTOMIZATION.md).

Work on this project must not consult, import, copy or reference another project's assets, templates, design or source. This includes layouts, styles, colour schemes, logos, icons and illustrations. Keep future design and code edits within `business-hub/`, unless the human user explicitly supplies or authorizes additional material for this project.

A resource-path review on 14 October 2026 found that the app's stylesheets, scripts and artwork resolve to its own `static/` files. Browser data requests use its local API. Python imports use the standard library and this project's `hub/` and `tools/` modules. No sibling-project resource dependencies were found. The launcher's installed or bundled Python executable is a runtime dependency.

This file records the project's working policy and technical dependencies. It does not provide legal clearance.
