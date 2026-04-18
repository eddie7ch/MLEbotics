# Marketing Analytics Event Matrix

Schema version: `2026-04-elite-2`

## Base payload fields (auto-attached by `window.mleTrack`)

- `schema_version`: Event schema version for downstream compatibility.
- `session_id`: Browser-session scoped identifier.
- `page_path`: URL path (example: `/projects`).
- `page_route`: Route bucket from layout (`home`, `projects`, `contact`, `other`).
- `hero_variant`: Active hero experiment variant (`control`, `velocity`, or `unassigned`).
- `ts_ms`: Event timestamp in epoch milliseconds.

## Event naming standard

- Format: `noun_or_domain_action`
- Lowercase with underscores only.
- Keep event names stable; evolve payload fields for iteration.

## Event catalog

### Navigation and CTA

- `page_view_custom`
  - Trigger: Layout boot.
  - Purpose: Baseline page-view sanity signal independent of auto GA view config.
  - Key params:
    - `source`: `layout_boot`

- `cta_click`
  - Trigger: Any element with `data-cta`.
  - Purpose: Primary click-through measurement across the funnel.
  - Key params:
    - `cta_key`: Stable CTA identifier.
    - `route`: Route bucket where click happened.
    - `variant`: Experiment variant at click time.

### Homepage

- `hero_variant_seen`
  - Trigger: Hero experiment assignment on homepage load.
  - Purpose: Denominator for experiment analysis.
  - Key params:
    - `variant`: `control` or `velocity`

- `control_room_mode_change`
  - Trigger: Homepage control-room mode switch.
  - Purpose: Interaction-depth proxy for feature comprehension.
  - Key params:
    - `mode`: `build`, `operate`, or `scale`

- `waitlist_signup`
  - Trigger: Waitlist form success.
  - Purpose: Mid-funnel conversion.
  - Key params:
    - `source`: `homepage_waitlist`
    - `variant`: Hero variant

- `scroll_depth`
  - Trigger: First cross of 20, 50, 80 percent depth.
  - Purpose: Narrative engagement and drop-off modeling.
  - Key params:
    - `depth_percent`: `20`, `50`, `80`
    - `page`: `home`

### Projects

- `projects_filter_change`
  - Trigger: Projects filter tab click.
  - Purpose: Category demand signal.
  - Key params:
    - `filter`: `all`, `ai`, `mobile`, `tools`, `school`

- `project_story_toggle`
  - Trigger: Before/After toggle click in project card.
  - Purpose: Case-study engagement depth.
  - Key params:
    - `state`: `before` or `after`
    - `project_id`: Project card id

### Contact

- `contact_validation_error`
  - Trigger: Contact submit with invalid input.
  - Purpose: Form friction detection.
  - Key params:
    - `reason`: Validation reason (current: `invalid_email`)

- `contact_brief_prepared`
  - Trigger: Contact brief converted to mailto draft.
  - Purpose: High-intent conversion event.
  - Key params:
    - `subject`: Subject option selected
    - `timeline`: Timeline option selected

- `contact_mailto_opened`
  - Trigger: User clicks draft mailto action.
  - Purpose: Completion step after brief generation.
  - Key params:
    - `source`: `contact_page`

- `contact_brief_copied`
  - Trigger: User copies generated brief.
  - Purpose: Alternate completion path when mail client is not used.
  - Key params:
    - `source`: `contact_page`

## Dashboard starter views

- Conversion funnel:
  - `hero_variant_seen` -> `cta_click` (`hero_primary_projects`) -> `contact_brief_prepared` -> `contact_mailto_opened`

- Experiment readout:
  - Compare `waitlist_signup` and `cta_click` rates by `hero_variant`.

- Engagement quality:
  - Correlate `scroll_depth` (80%) with `projects_filter_change` and `project_story_toggle`.

## QA checklist

- Confirm `schema_version` is present on every custom event.
- Confirm `hero_variant` is never empty on homepage events.
- Confirm no event names contain spaces or camelCase.
- Confirm `cta_key` values are stable across redesign iterations.
