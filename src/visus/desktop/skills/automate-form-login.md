---
name: automate-form-login
description: Fill in a username / password form and submit. Works for desktop apps and browser pages reachable through visus-desktop's OCR + native automation. Use when the user asks to "sign in", "log in", or describes credential entry into a UI form.
when_to_use: Activate when the user wants to drive a sign-in form (username + password + submit) and has provided (or will provide) the credentials in the conversation.
---

# Automate a form login

## Prerequisites

* The login window is **already visible** on screen. If it isn't, ask the user to open it first or chain a `launch(command=…)` step.
* The user has shared the credentials in this conversation. If not, ask for them now and do not proceed.

## Steps

1. `focus_window(title_substring=<window title>)` — bring the app forward. Use a short, unique title fragment (e.g. `"Login"`, `"SAP"`).
2. `take_screenshot()` — confirm the form is on screen and capture the rough field positions.
3. Locate the **username field**:
   * Prefer `hybrid_find(name="Username")` (the native UI tree often labels the field).
   * Fall back to `find_text(text="Username")` if hybrid misses.
4. `click_at(x=…, y=…)` using the returned center of the box, or call `click_text(text="Username")` directly to bypass the inspection.
5. `type_text(text=<username>)`.
6. `keyboard_command(command="Tab")` — most forms move to the password field. If the layout puts password elsewhere, repeat steps 3–4 with `name="Password"`.
7. `type_text(text=<password>)`. **Never echo the password back in your reply.**
8. Locate and click the submit button:
   * `hybrid_find(name="Sign in")` or `click_text(text="Login")` / `click_text(text="Sign in")`.
   * If the button is an image with no text, use `click_image(image_path=<…>.png)` when the user provides the asset.
9. `wait_for_stable_screen(stable_for=0.8, timeout=20)` — give the post-login page time to render before any follow-up action.
10. Verify success: `find_text(text=<something visible only after login>)`. If `None`, the login failed — capture `take_screenshot()` and report back.

## Compact task-list version

When you have all the targets known up front, ship a single `execute_tasks` call so backtrack + screenshot-on-failure kick in automatically:

```json
[
  {"text": "Username", "region": [200, 100, 600, 400]},
  {"type": "type_text", "text": "<username>"},
  {"type": "keyboard_command", "command": "Tab"},
  {"type": "type_text", "text": "<password>"},
  {"text": "Sign in", "region": [200, 100, 600, 500]},
  {"type": "keyboard_command", "command": "Enter"}
]
```

Call:

```text
execute_tasks(tasks=<list above>)
```

## What to do when it fails

* `failure_screenshot` on the result → look at the PNG path; describe what you see (wrong field, captcha, locale change).
* `find_text` for the field returns `None` → the label is probably localized. Ask the user for the localized term, then retry.
* Login form has a captcha → switch to `solve-image-captcha` skill before retrying.

## Safety reminders

* Do not log or quote the password in the response.
* Confirm before re-submitting after a failure (some apps lock accounts after N attempts).
