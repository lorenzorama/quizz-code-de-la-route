# Quiz layout — bigger, viewport-fit, photo on top

**Date:** 2026-07-05
**Status:** approved

## Problem

In the quiz UI the situation photo renders too small. The images are wide
(1920×632, ~3:1). In practice mode the quiz sits in a `max-w-2xl` (672px)
column, so the photo is capped at ~210px tall and the page scrolls. In exam
mode the layout already fits the viewport but places the photo *beside* the
options on desktop and still caps it at `max-h-[50vh]`.

The user wants: a **bigger** photo that **adapts to the screen/browser**, with
everything **fitting in the viewport without scrolling**, laid out as **photo on
top, question + choices below**. Applied to **both** practice and exam modes.

## Behaviour decisions (from the user)

- **Small-screen priority:** everything must fit without scroll; the photo
  shrinks as needed so the question and all choices stay visible ("tout tient,
  photo ajustée"). On desktop the photo is large; on mobile it is modest (the
  3:1 ratio limits height on narrow screens).
- **Layout:** photo on top (full width), question + choices below. Applied to
  practice and exam alike.
- **Choices:** responsive grid — 1 column on mobile, 2 columns on desktop
  (mirrors the source-video A|B / C|D format and frees vertical space for the
  photo).

## Design

### Sizing mechanism (the core fix)

The quiz runs inside a full-height flex column (`100dvh`, outer
`overflow-hidden`, no page scroll — exam already does this; practice adopts it
for the answering screen).

Top → bottom inside that column:

```
TopBar (fixed height)
meta row: "Question 3/10"  ·  countdown (exam only)      [shrink-0]
Card (flex-col, min-h-0, flex-1):
  PHOTO region        [flex-1, min-h-0]  ← takes ALL remaining vertical space
  theme badge + question text            [shrink-0]
  choices grid (1 col mobile / 2 col sm+) [shrink-0]
action row: [Quitter]              [Vérifier/Suivant]   [shrink-0]
```

The photo region is `flex-1 min-h-0`; the question and choices take their
natural height first, so the photo automatically fills whatever vertical space
remains and shrinks when space is tight. The image is `object-contain` (whole
photo always visible — must not crop road signs) and centered.

Container widens from `max-w-2xl` to **`max-w-5xl`** (~1024px) so the
width-limited 3:1 photo is much larger on desktop (~1024×340 vs ~210 tall).

### Components

1. **`QuestionMedia`** — add a `fill` prop. When `fill` is true it fills its
   flex parent (`h-full w-full object-contain`, centered) for the viewport-fit
   runners. Default (unchanged) keeps `max-h-[50vh]` natural sizing so the
   scrollable exam-review list is unaffected.
2. **New shared `QuestionStage`** — presentational component rendering the Card
   body: photo region (top) + theme badge + question text + choices grid. Takes
   `question`, `selectedIds`, `onToggle`. Used by both runners so the layout has
   a single source of truth. Uses `QuestionMedia fill` and `OptionCard` (in a
   `grid grid-cols-1 sm:grid-cols-2` wrapper).
3. **Exam runner** (`app/exam/page.tsx`) — replace the side-by-side card body
   with `QuestionStage`. Keep the existing `h-dvh` wrapper, meta row, countdown,
   and action row.
4. **Practice runner + page** (`components/practice/PracticeRunner.tsx`,
   `app/practice/page.tsx`) — the answering screen adopts the full-height
   layout with `QuestionStage`. The theme-selection screen and the **revealed
   correction** screen (which shows a possibly long explanation) stay
   scrollable / normal-flow.

### Out of scope (unchanged)

- Exam review page (`app/exam/[attemptId]/review/page.tsx`) — a scrollable list
  of results; `ReviewQuestionCard` keeps the default (non-fill) `QuestionMedia`.
- Theme-selection screen.
- Backend, media files, question content.

## Testing

- Keep existing tests green: `PracticeRunner.test.tsx`, `exam/page.test.tsx`,
  `OptionCard.test.tsx` — adapt selectors if markup changes, without weakening
  assertions.
- Add/adjust a test asserting choices render in the grid and that
  `QuestionStage` shows media above the options.
- Manual check via the dev server at desktop and mobile widths: photo large and
  everything fits with no page scroll; on a short viewport the photo shrinks but
  question + all choices remain visible.

## Risks / notes

- Keep the plain `<img>` (media is served dynamically from `/media/`); do not
  switch to `next/image` (would need width/height or `remotePatterns`). Matches
  existing code.
- Very tall option text on a tiny screen is the edge case: choices keep their
  natural height (priority), so on an extreme small viewport the photo can get
  quite small — acceptable per the chosen behaviour.
