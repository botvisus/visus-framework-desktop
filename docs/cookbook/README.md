# Visus Desktop — Cookbook

End-to-end recipes for common desktop automation patterns. Each recipe
is self-contained: it shows the goal, the smallest working code, and the
specific Visus Desktop APIs involved.

> Recipes use the public API only (`from visus.desktop import VisusBot`)
> and assume the [installation guide](../installation.md) is complete.

## Index

| Recipe | Status | Summary |
|---|---|---|
| [Download wait](download-wait.md) | ✅ Worked | Trigger a download, then block until the file finished writing to disk. |
| [Oracle Forms](oracle-forms.md) | 🚧 Stub | Notes and patterns for legacy Oracle Forms — the eternal RPA target. |
| [Captcha (OCR)](captcha.md) | 🚧 Stub | Solve image captchas by capturing a region and running OCR. |
| [Excel input](excel-input.md) | 🚧 Stub | Drive an Excel-style spreadsheet from a CSV without OLE. |
| [File dialogs](file-dialogs.md) | 🚧 Stub | Auto-fill the Windows "Open File" dialog. |

## Reading these recipes

* Code blocks are runnable as-is once the listed dependencies are
  installed.
* Every helper used is part of the public API; nothing reaches into
  internal modules.
* When a recipe says **production tip**, that note comes from real
  shipped RPA bots — not theory.

## Adding a recipe

1. Drop a new `.md` file in this directory.
2. Add a row to the index table.
3. Open a PR; the only requirement is that the code copy-pastes into a
   fresh Python session and runs.
