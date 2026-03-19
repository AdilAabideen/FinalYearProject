# @agents.md

Repository guide for human/AI contributors working in:
`/Users/adil/Documents/University/MultiAgentResearch/UseCase1ESIFrontEnd`

## 1. Project Purpose
- Frontend for IntelliTriage agent workspace.
- Primary flow today: browse agents, inspect tools, run agents, review traces/runs, run test harness.

## 2. Stack + Commands
- Stack: React 19, TypeScript, Vite, Tailwind v4.
- Dev: `npm run dev`
- Lint: `npm run lint`
- Build: `npm run build`

## 3. Architecture Rules (Must Follow)
- Keep **service architecture** in `src/services/*` as API boundary.
- Keep API DTO/domain mapping inside services, not in components.
- Put async orchestration into hooks/utils before adding more component-local logic.
- Reuse `src/shared/ui/*` and `src/features/agents/components/*` primitives before creating new ones.
- If logic is used in 2+ places, extract to `features/.../hooks` or `features/.../utils`.

## 4. Folder Map
- `src/app/*`: shell, global layout, navigation.
- `src/features/home/*`: home feature.
- `src/features/agents/*`: agents feature (pages/components/hooks/utils).
- `src/shared/ui/*`: app-wide reusable visual primitives.
- `src/shared/lib/*`: app-wide non-feature utilities.
- `src/services/*`: backend API calls + response normalization.
- `src/types/*`: DTO + domain data shapes.

## 5. Reusable Component Registry

### App/Layout
- `src/app/layout/AppShell.tsx`: top-level shell with sidebar + topbar + page content.
- `src/app/layout/PageContainer.tsx`: standard page width wrapper.
- `src/app/layout/SectionHeader.tsx`: simple section title + description block.

### Shared UI (Use First)
- `src/shared/ui/Badge.tsx`
- `src/shared/ui/CodeBlock.tsx`
- `src/shared/ui/IconButton.tsx`
- `src/shared/ui/JsonInspector.tsx`
- `src/shared/ui/SegmentedTabs.tsx`
- `src/shared/ui/SlidingModal.tsx`
- `src/shared/ui/StatChip.tsx`
- `src/shared/ui/TextInput.tsx`

### Agents Feature Components
- `AgentCard.tsx`: agent list card.
- `AgentDetailSplitView.tsx`: diagram + tabbed detail split layout.
- `AgentDiagram.tsx`: interactive tool graph + schema popover.
- `AgentTab.tsx`: run/previous/tests tab switch.
- `RunAgentTab.tsx`: run form + live traces/results.
- `PreviousRuns.tsx`: previous runs list + inspect.
- `AgentRunReview.tsx`: historical run review (traces/results/inputs).
- `AgentTestCases.tsx`: selectable test case table + run launcher.
- `AgentTestRunDrawer.tsx`: streaming test harness drawer.
- `AgentTracesComponent.tsx`: SSE traces stream renderer.
- `RunStatusBadge.tsx`: standardized run-status badge.
- `ToolStatusBadge.tsx`: standardized tool-status badge.
- `TraceOutputHoverBadge.tsx`: hover output preview badge.

## 6. Hooks Registry
- `src/features/agents/hooks/useModels.ts`
  - Responsibility: model list loading state + selected model id.
  - Reuse in any feature needing model selector behavior.

## 7. Utilities Registry

### Shared
- `src/shared/lib/cn.ts`: className join helper.
- `src/shared/lib/formatJson.ts`: safe JSON pretty printer.

### Agents
- `src/features/agents/utils/status.ts`
  - `runStatusBadgeClass`, `formatStatusLabel`, `classifyToolStatus`, `toolStatusBadgeClass`.
- `src/features/agents/utils/trace.ts`
  - `isLogThoughtTool`, `truncateText`, `prettifyToolName`, `tryParseJson`.
- `src/features/agents/utils/jsonSchema.ts`
  - schema resolving/ref support + schema metadata helpers (`getObjectSchema`, `getPrimaryType`, etc.).
- `src/features/agents/utils/runInput.ts`
  - `getDefaultInputs`, `coerceInputForRun`.

## 8. Do-Not-Duplicate Rules
- Do not reimplement model loading logic; use `useModels`.
- Do not create ad-hoc status color mapping; use `utils/status` + status badge components.
- Do not duplicate trace parsing/formatting helpers; use `utils/trace`.
- Do not duplicate schema parsing/ref resolution; use `utils/jsonSchema`.
- Do not duplicate run-input coercion/defaults; use `utils/runInput`.
- Do not create new JSON display widgets unless `JsonInspector` is insufficient.

## 9. Where New Code Should Go
- New API endpoint integration:
  - Add/extend service in `src/services/*`
  - Add/update type in `src/types/*`
  - Consume via feature hook/component
- Reusable UI primitive across features:
  - Add to `src/shared/ui/*`
- Agents-only reusable logic:
  - Add to `src/features/agents/hooks/*` or `src/features/agents/utils/*`
- One-off feature UI:
  - Add to `src/features/<feature>/components/*`

## 10. PR/Change Checklist
- Confirm existing component/hook/util can’t satisfy the task before adding new ones.
- If adding a reusable hook/component/util, register it in this file in the same PR.
- Run `npm run lint` and `npm run build` before finalizing.
- Preserve service contracts unless backend contract change is intentional and coordinated.
