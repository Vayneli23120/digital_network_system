# UI Reference Extraction: IT AMS HTML Prototype

## 1. Executive summary

This document extracts the reusable design language from `it_ams.html`, a static high-fidelity prototype for an enterprise IT asset / spare-parts management system. The prototype uses a Goodyear-inspired visual language: deep blue navigation, yellow brand accents, white card surfaces, compact data density, semantic status colors, and operational dashboard patterns.

This is documentation-only. It does not modify the current EAM application, does not generate Vue code, does not connect to APIs, and does not migrate business workflows. The prototype should be treated as a visual and interaction reference, not as production source code.

Key reusable themes:

- Brand-driven enterprise shell with fixed topbar and grouped left navigation.
- Compact operational workspace with KPI cards, panels, tables, tags, forms, and modal workflows.
- Strong data-display system for inventory counts, risk states, trends, category distribution, logs, and analytics.
- Advanced but optional workflow primitives: dual-panel modals, batch intake, serial entry, tree editors, and audit-log diff details.

## 2. Visual identity

### Overall visual tone

The prototype feels like a compact enterprise operations console rather than a generic admin template. It combines a low-noise white/blue surface system with high-recognition yellow brand accents. The UI is dense but controlled: small typography, tight table rows, concise labels, rounded cards, and subtle shadows.

### Brand and color model

- **Primary brand yellow** is used for active top navigation, logo treatment, accents, section markers, and important callouts.
- **Deep blue** anchors the topbar, primary buttons, active text, progress bars, and informational accents.
- **White surfaces** are used for cards, panels, sidebar, and modals.
- **Pale blue/gray backgrounds** separate workspace areas, form fields, hover states, and side panels.
- **Semantic colors** are reserved for success, warning, danger, and info states.

### Typography

- Primary font: `DM Sans`, falling back to `-apple-system` and generic sans-serif.
- Monospace font: `DM Mono`, used for IDs, timestamps, counts, keyboard hints, SKU/SN values, and KPI numeric values.
- Body baseline: `13px` with `line-height: 1.5`.
- The design relies on light-to-medium font weights (`300`, `400`, `500`) rather than heavy headings.

### Radius, border, shadow, and density

- Common radius: `8px–14px`; modal radius is `16px`.
- Borders are light and consistent, usually `1px solid var(--border)`.
- Shadows are subtle for resting elements and stronger only for topbar, dropdowns, and modals.
- Density is compact: table cells are around `10–11px` vertical padding, form controls around `9px 13px`, buttons around `8px 16px`.

## 3. Layout and navigation

### App shell

- **Topbar:** fixed at top, `60px` height, full width, z-indexed above content, deep-blue gradient background, and a `3px` yellow underline.
- **Sidebar:** `220px` wide, sticky below topbar, full viewport height minus topbar, white surface, right border, grouped navigation.
- **Main content:** flexible workspace with `28px` page padding and `min-width: 0` to support grids/tables.

### Layout hierarchy

1. Top navigation expresses primary business domains.
2. Sidebar navigation expresses secondary navigation and grouped tasks.
3. Main content becomes the operational workspace for dashboards, lists, details, forms, and workflows.

This differs from a traditional single-sidebar admin UI because the topbar owns high-level product areas while the sidebar provides local context. It makes the app feel more like a business operations suite than a simple CRUD dashboard.

### Grid and panel system

- KPI overview uses `.kpi-grid` with four equal columns and `14px` gaps.
- Main dashboard panels use `.grid2` with `1fr 340px` and `.grid2b` with two equal columns.
- Analytics uses `.an-grid-3`, `.an-grid-2`, and `.an-grid-2-3` for metric and chart layouts.
- Modal workflows use single-column, large, small, extra-large, and dual-column modal layouts.

### Responsive limitations

The prototype includes `viewport` metadata but does not define a complete responsive breakpoint system. Several fixed widths are visible: `220px` sidebar, `240px` search, `340px` secondary dashboard column, `320px` modal side panel, and fixed table column widths. A future implementation should add mobile/tablet behavior explicitly.

### Navigation structure extracted

**Top-level nav:** Dashboard, 备件库存, 申领管理, 审批中心, 备件台账, 系统设置.

**Sidebar groups:**

- 总览: Dashboard
- 库存管理: 备件库存, 库存盘点, 库存预警
- 流程管理: 申领管理, 审批中心, 归还记录
- 数据与报表: 备件台账, 使用分析, 系统设置

Active states are synchronized between top navigation and sidebar for mapped screens. Sidebar-only routes such as analytics can still activate sidebar state while optionally syncing top-level state if mapped.

## 4. Design tokens

### Color and layout tokens

| Prototype token | Value | Observed usage | Suggested migration token |
| --- | --- | --- | --- |
| --gy | #FFCC00 | Goodyear yellow accent, active top nav, logo oval, primary brand highlight | --color-gy |
| --gy-dim | #E6B800 | Darker yellow for dividers, active sidebar border, section title marker | --color-gy-dim |
| --gy-pale | #FFF9D6 | Pale yellow active sidebar and category surfaces | --color-gy-pale |
| --gy-ghost | #FFFDF0 | Subtle yellow callout/assignment surface | --color-gy-ghost |
| --gb | #003087 | Primary deep blue for buttons, active text, bars, nav counts | --color-gb |
| --gb-mid | #00419E | Primary button hover blue | --color-gb-mid |
| --gb-deep | #001F5C | Darkest brand blue for logo text and yellow-button text | --color-gb-deep |
| --gb-light | #EAF0FA | Light blue surface/accent | --color-gb-light |
| --gb-ghost | #F4F7FD | Very light blue hover and panel background | --color-gb-ghost |
| --ink | #0D1B2A | Primary text | --color-ink |
| --ink2 | #3A4A5C | Secondary heading/body text | --color-ink2 |
| --ink3 | #6B7A8D | Muted metadata text | --color-ink3 |
| --ink4 | #9BAABB | Placeholder/disabled text | --color-ink4 |
| --border | #E2E8F2 | Default border line | --color-border |
| --border2 | #C8D4E4 | Stronger hover border | --color-border2 |
| --surface | #FFFFFF | Cards, panels, sidebar, modals | --color-surface |
| --bg | #F0F4FA | Page background and form fields | --color-bg |
| --success | #1A7F4B | Positive semantic text | --color-success |
| --success-bg | #E6F4EC | Positive semantic background | --color-success-bg |
| --warn | #8A5F00 | Warning semantic text | --color-warn |
| --warn-bg | #FFF4CC | Warning semantic background | --color-warn-bg |
| --danger | #B91C1C | Danger/error semantic text | --color-danger |
| --danger-bg | #FEE8E8 | Danger/error background | --color-danger-bg |
| --info-bg | #EAF0FA | Informational background | --color-info-bg |
| --sidebar-w | 220px | Sidebar width layout token | --layout-sidebar-w |
| --topbar-h | 60px | Topbar height layout token | --layout-topbar-h |

### Spacing and radius tokens

| Token / pattern | Value | Usage |
| --- | --- | --- |
| Page padding | `28px` | Main workspace padding |
| Topbar horizontal padding | `0 28px` | Header alignment |
| Sidebar group padding | `0 12px` | Grouped nav spacing |
| KPI card padding | `18px 20px` | Dashboard metric cards |
| Panel header padding | `14px 20px` | Panel title/action row |
| Panel body padding | `18px 20px` | Panel content area |
| Modal header padding | `18px 24px` | Dialog title row |
| Modal body padding | `20px 24px` | Dialog content |
| Modal footer padding | `14px 24px` | Dialog actions |
| Button radius | `7px–9px` | Default and small buttons |
| Card/panel radius | `12px–14px` | Cards, panels, inventory cards |
| Modal radius | `16px` | Dialog shell |
| Pill radius | `20px` | Tags, chips, badges |

### Typography tokens

| Role | Size | Weight | Line height | Usage |
| --- | --- | --- | --- | --- |
| Body | `13px` | `400` | `1.5` | App baseline |
| Page title | `20px` | `500` | `1.2` | Screen headings |
| Page subtitle | `12px` | `400` | Inherits | Muted screen description |
| Top nav item | `12.5px` | `400/500 active` | Inherits | Primary navigation |
| Sidebar label | `10px` | `500` | Inherits | Uppercase group label, mono |
| Sidebar item | `13px` | `400/500 active` | Inherits | Secondary navigation |
| KPI value | `28px` | `300` | `1` | Large numeric metrics, mono |
| Table header | `11px` | `500` | Inherits | Uppercase column labels |
| Table cell | `12.5px` | `400` | Inherits | Dense data rows |
| Form label | `11px` | `500` | Inherits | Compact form labels |
| Form control | `12.5px` | `400` | Inherits | Inputs/selects/textareas |
| Tag/chip | `11–12px` | `500` | Inherits | Status and filters |
| Modal title | `15px` | `500` | Inherits | Dialog heading |
| Metadata/IDs | `10–12px` | `400/500` | Inherits | `DM Mono` IDs, counts, timestamps |

### Layout tokens

| Token | Value | Usage |
| --- | --- | --- |
| Topbar height | `60px` | Fixed global header |
| Sidebar width | `220px` | Left navigation |
| Search width | `240px` | Header search input |
| Modal default width | `max-width: 720px` | Standard workflows |
| Modal small width | `max-width: 520px` | Confirmation/compact dialogs |
| Modal large width | `max-width: 900px` | Richer workflows |
| Modal XL width | `max-width: 1180px` | Dual-panel/workflow-heavy dialogs |
| Dual modal side panel | `320px` | Workflow summary/recent activity rail |
| Dashboard side column | `340px` | Secondary dashboard panel |

## 5. Component inventory

| Component name | CSS/classes in prototype | Purpose | Visual behavior | Interaction behavior | Reusability | Notes for future migration |
| --- | --- | --- | --- | --- | --- | --- |
| Topbar | .topbar, .top-nav | Primary business-domain navigation | Fixed deep-blue gradient bar with yellow underline | Top nav tabs switch screens; active tab becomes yellow | High | Build as app shell header; keep business domains horizontal |
| Top nav item | .tn, .tn.active, .tn-count | Top-level module selector | Compact pill tabs; active is yellow with blue text | Hover brightens; active syncs with screen/sidebar | High | Counts can map to pending records |
| Global search | .search-wrap, .search-kbd | Global lookup placeholder | Dark translucent field in topbar with keyboard hint | Focus adds yellow border and glow | Medium | Implement placeholder first; wire search later |
| Notification button | .icon-btn, .notif-dot | Operational alerts entry | Square translucent icon with red dot | Hover border/brightness | Medium | Good visual pattern for alerts |
| Avatar/user menu | .avatar-wrap, .user-menu, .um-* | User profile and account actions | Yellow avatar on dark header; white dropdown card | Open/close dropdown; logout confirmation path | High | Reusable account-menu shell |
| Sidebar group | .sg, .sg-label | Secondary navigation grouping | Uppercase monospace group labels | Static grouping; supports grouped IA | High | Better than flat admin menus |
| Sidebar item | .si, .si.active, .si-badge | Sub-navigation route item | Rounded row; pale-yellow active with left border | Hover blue ghost; active sync with top nav | High | Map to current EAM secondary pages |
| Page header | .ph, .pt, .ps | Screen title and actions | Title/subtitle left; button row right | Static container for toolbar actions | High | Use consistently across pages |
| Button row | .btn-row | Action grouping | Tight 8px gap, inline actions | Buttons trigger modals/navigation | High | Use in headers and panel toolbars |
| Panel | .panel, .panel-hd, .panel-body | Content grouping card | White surface, 14px radius, thin border | Panel actions can link/open detail | High | Core reusable card primitive |
| Section title | .section-title | Subsection label inside modals/details | Uppercase text with yellow vertical rule | Static section divider | High | Useful for dense enterprise forms |
| Grid containers | .kpi-grid, .grid2, .grid2b, .an-grid-* | Dashboard and form layout | 4-column KPI, 2-column content, analytics variants | Responsive behavior is not fully defined | High | Add responsive breakpoints in implementation |
| KPI card | .kpi, .kpi-blue/yellow/red/green | Clickable metric summary | White card with colored top rule and mono value | Hover lifts and reveals expand hint | High | Excellent dashboard primitive |
| KPI trend chip | .kpi-trend, .trend-up/dn/warn | Trend/status annotation | Small colored semantic pill | Static or click-through if metric is interactive | High | Map to counts, deltas, alerts |
| Progress bar | .pbar-row, .pbar, .pbar-fill-* | Inventory or utilization progress | Thin 5px bar with mono value | Read-only display | High | Reusable for asset lifecycle/compliance |
| Category bar | .cat-item, .cat-bar, .cat-fill | Category distribution row | Label, bar, count, tag | Filter can hide/show categories | High | Good for dashboard/category summaries |
| Stat card | .stat-card | Small standalone metric in modal/detail | Muted background with mono value | Read-only | Medium | Use in modal side panels |
| Donut chart | .donut-wrap, .donut-svg, .donut-legend | Composition analytics | SVG ring plus legend | Read-only visual summary | Medium | Replace static SVG with chart component later |
| Bar chart | .chart-wrap, .chart-bar, .chart-col* | Monthly/count comparison | CSS bars with mono labels | Hover opacity on dual bars | Medium | Prototype pattern; production should use chart library |
| Line chart | .line-chart, .line-svg, .line-x-labels | Trend over time | SVG line with x labels | Read-only | Medium | Use for reports/analytics |
| Heatmap | .heatmap, .heat-cell | Department/category usage intensity | Grid cells with scale legend | Hover scale and shadow | Medium | Useful for usage analytics |
| Ranking list | .rank-list, .rank-item, .rank-num | Top items/users/categories | Number badge, title, meta, bar, value | Hover border highlight | High | Reusable for reports and dashboards |
| Lifecycle metric card | .lc-grid, .lc-card | Lifecycle summary metrics | Two-column muted metric cards | Read-only | Medium | Useful for age, disposal, warranty |
| Compact table | table.tbl, .tbl-wrap | Dense records display | Fixed layout, uppercase headers, ellipsis cells | Row hover blue ghost; action links | High | Core EAM list pattern |
| Mono ID cell | .td-mono | IDs, timestamps, SKU/SN values | DM Mono, blue/muted sizing | Read-only or clickable when paired with action | High | Use for IDs, tags, timestamps |
| Action link | .td-action, .panel-action | Inline secondary actions | Blue text with underline on hover | Opens details/modals | High | Use sparingly in dense tables |
| Status tags | .tag, .tag-green/red/yellow/blue/gray | Record state labels | Small rounded semantic pills | Read-only state indication | High | Centralize semantic mappings |
| Form controls | .finput, .fselect, .ftextarea | Dense input fields | Muted background, 9px radius, compact text | Focus blue border and white background | High | Core form token pattern |
| Form grid | .fgrid, .frow, .flb.req | Two-column dense forms | Small labels, required star | Validation not implemented | High | Add validation states during migration |
| Filter chips | .chips, .chip, .chip.ca, .chip.cw | Quick filter selection | Rounded pills; active blue or warning red | Single active selection in prototype | High | Useful for tabs and filters |
| Filter dropdown | .filter-wrap, .filter-trigger, .filter-pop, .filter-opt | Multi-select filter | Popover with checkbox rows and count badge | Open/close, check/uncheck, reset | Medium | Implement as reusable controlled component |
| Buttons | .btn, .btn-primary/yellow/ghost/danger/success, .btn-sm, .btn-tiny | Action system | Blue/yellow/ghost/semantic variants; compact sizes | Hover state per variant | High | Build tokenized button component |
| Modal shell | .modal-overlay, .modal, .modal-hd/body/ft | Dialog container | Blurred overlay, white rounded modal, sticky-ish footer | Open/close; modal stack supported | High | Core workflow wrapper |
| Modal sizes | .modal-sm, .modal-lg, .modal-xl | Dialog sizing scale | 520/720/900/1180 max widths | Chosen per workflow complexity | High | Define modal size enum |
| Dual modal layout | .modal-dual, .modal-dual-main, .modal-dual-side | Main workflow plus summary/activity side panel | Two-column modal with gray side rail | Used for add-part intake/log side panel | Medium | Advanced workflow wrapper |
| Assignment block | .assign-block, .assign-block-hd | Attention block inside approval workflow | Dashed yellow callout | Static guidance/assignment section | Medium | Useful for warnings and required follow-up |
| Alert list item | .al-item, .al-icon, .al-body | Dashboard risk/warning feed | Icon block, title, summary, time | Can link to detail modal | High | Reusable alert feed |
| Timeline item | .tl-item, .tl-dot | Activity history | Vertical connector with semantic dots | Read-only history display | High | Useful for audit trails |
| Approval card | .acard, .acard-btns | Pending approval record | Card row with meta and approve/reject buttons | Buttons open assignment/reject modals | Medium | Only migrate if workflow exists |
| Inventory card | .inv-grid, .inv-card | Visual spare part card | Icon, name/SKU, meta, footer | Hover border/shadow; click to detail | Medium | Alternative to table view |
| Log row/detail | .log-row, .log-detail-section, .log-diff-row | Audit log list and detail diff | Mono timestamp; diff old/new values | Rows open detail modal | High | Good for audit/history |
| Serial block | .serial-block, .serial-list, .serial-item | Serial-number intake | Dashed blue block with mono inputs | Add/delete rows; count sync | Medium | Useful for serialized assets |
| Batch table row | .batch-row, .batch-del | Bulk item intake | Grid row fields in compact table layout | Add/delete rows; optional serial mode | Medium | Advanced bulk workflow |
| Today scan/log list | .today-log-list, .today-log-item | Recent intake side panel | Small cards with quantity and SN line | New entries prepend with animation | Medium | Useful for scan/import workflows |
| Tree editor | .tree-wrap, .tree-parent, .tree-child | Reference/category/location editor | Nested rows, child background, action buttons | Expand/collapse, rename, drag/drop, add/delete | Medium | Defer until reference management is needed |
| Drag handle | .tree-drag-handle, .dragging, .drag-over | Reordering affordance | Low-opacity during drag; yellow drop target | HTML drag/drop in prototype | Low | Implement accessibly if migrated |
| Reassign banner | .reassign-banner | Reference-management warning | Caution banner for reassignment impact | Static warning before delete/reassign | Medium | Useful for destructive reference changes |

## 6. Interaction patterns

| Pattern | Prototype behavior | Essential for future migration? | Notes |
| --- | --- | --- | --- |
| Hover states | Buttons, nav items, table rows, KPI cards, inventory cards, ranking rows, tree rows, and dropdown options all have subtle hover feedback. | Yes | Gives the dense UI enough affordance without visual noise. |
| Active states | Top nav `.tn.active`, sidebar `.si.active`, chips `.chip.ca`, period chips, mode tabs, screens `.screen.active`, modals `.modal-overlay.active`. | Yes | Centralize active state in route/component state rather than DOM classes. |
| Focus states | Search and form controls use border changes, white background, or yellow glow. | Yes | Add keyboard-visible focus states in implementation. |
| Clickable KPI cards | KPI cards lift on hover and reveal `.kpi-expand`. Some open detail modals. | Yes | Use for dashboard drill-downs. |
| Chips/filter selection | Single-selection chips and multi-select dropdown filters. | Yes | Implement as reusable filter components. |
| Dropdown open/close | User menu and filter popover use `.open`; caret rotates for filters. | Yes | Needs outside-click and Escape behavior in production. |
| Sidebar active sync | `nav`, `sideNav`, and `syncSidebar` keep top and side navigation aligned. | Yes | Replace inline JavaScript with router-aware state. |
| Modal open/close | Modal overlay uses `.active`, body scroll lock, and a modal stack for nested flows. | Yes | Modal stack is valuable for approval-to-assignment flows. |
| User menu dropdown | Opens from avatar; contains profile header, settings actions, and logout. | Medium | Keep visual style; wire to actual auth actions later. |
| Tree expand/collapse | Parent rows toggle `.open`; caret rotates; children appear in blue ghost area. | Medium | Important only for reference editors. |
| Drag/drop visual states | `.dragging` lowers opacity; `.drag-over` uses yellow ghost highlight. | Low/Medium | Implement later with accessible drag support. |
| Batch input behavior | Batch rows can be added/deleted; serial mode changes row fields. | Medium | Valuable for bulk intake, but only if workflow exists. |
| Scan/log side panel | Dual modal side panel shows today’s additions and counters. | Medium | Good pattern for scan/import workflows. |
| Toggle/switch behavior | Toggles use blue active state and gray inactive state; switch rows can highlight when on. | Yes | Useful for settings, serial tracking, and options. |
| Inline table actions | Blue text links open detail modals. | Yes | Use for dense administrative data. |
| Audit detail diff | Log detail modal uses old/new diff rows. | Medium | Useful for auditability and compliance. |

## 7. Screen inventory

| Screen name | Prototype subtitle | Business purpose | Main components used | Data displayed | Actions shown | Potential future EAM mapping |
| --- | --- | --- | --- | --- | --- | --- |
| Dashboard 总览 | 2024 年第四季度 · 最后同步于 10 分钟前 | Executive inventory/operations overview | KPI grid, alert list, category bars, tables/logs | SKU count, requests, warnings, recent movement | Open metric details, view alerts, open logs | EAM home/dashboard |
| 备件库存 | 共 1,248 个 SKU · 7 大类别 · 4 个仓库 | Spare parts inventory browse/search | Filters, cards/tables, inventory grid, tags, progress | Stock counts, category, location, status, SKU/SN | Add part, filter, open detail | Asset/spares list or inventory module |
| 光模块 SFP+ 10G | SKU: NET-SFP-10G-001 · 网络设备类 · 库存预警 | Item detail view | Breadcrumb, info panel, timeline/logs, tables | SKU metadata, stock, lifecycle, movement history | Back to inventory, related actions | Asset/spare detail page |
| 申领管理 | 本月共 87 条申领记录 | Request management | Request tables/cards, status tags, filters | Request IDs, requester, part, qty, status | Open request detail, navigate approval | Request/work-order module if in scope |
| 审批中心 | 7 条申请待处理 | Approval center | Approval cards, approve/reject actions | Pending approval metadata and urgency | Approve with assignment, reject | Approval workflow if planned |
| 备件台账 | 完整出入库历史记录 | Full transaction ledger | Filter row, compact table | Operation time/type, item, quantity, actor, related ID, location | Export ledger, search/filter | Audit/history/export history |
| 系统设置 | IT 备件管理平台配置中心 | System/reference settings | Setting rows, toggles, editor buttons, logs | Rules, reference trees, role/config hints | Open category/location editors/logs | Settings/reference management/RBAC |
| 使用分析 | 备件领用、流转、寿命周期数据洞察 · 2024 Q4 | Usage analytics dashboard | KPI cards, donut, bar, line, heatmap, ranking, lifecycle cards | Usage counts, category share, return rate, stock age | Period chips, export report | Reports/analytics dashboard |

### Modal workflow inventory

| Modal title | Prototype ID | Observed purpose/subtitle |
| --- | --- | --- |
| 备件总 SKU 详情 | modal-sku | 1,248 个 SKU · 按分类分布 |
| 本月申领详情 | modal-request-stats | 2024 年 12 月 · 共 87 次申领 |
| 库存预警详情 | modal-warning | 5 个备件低于安全库存线，需尽快补货 |
| 新增备件入库 | modal-add-part | 支持单件录入、批量入库 · 可记录序列号 |
| 待处理审批 | modal-approval-list | 7 条申请等待处理 · 可直接批复 |
| 申领单详情 | modal-request-detail | REQ-0328 |
| 审批通过 · 分配产品信息 | modal-approve-assign | REQ-0328 · 申请人：张工 |
| 驳回申请 | modal-reject | REQ-0328 · 请填写驳回理由 |
| 编辑备件分类 | modal-category-editor | 支持父类 / 子类两级 · 可新增、删除、重命名、拖拽重新分配 |
| 编辑仓库位置 | modal-location-editor | 仓库 / 子位置（货架、库房）两级 · 可拖拽重新分配子位置 |
| 操作日志详情 | modal-log-detail | L-001 · 2024-12-05 09:32 |
| 系统操作日志 | modal-logs-list | 最近 30 天 · 共 248 条 · 点击行查看详情 |

## 8. Data display patterns

### Counts and KPIs

Large numbers are displayed in mono typography inside KPI cards or stat cards. Color-coded top rules distinguish metric categories. Trend chips explain the metric direction or state without overusing chart color.

Reusable for:

- Asset dashboard totals.
- Inventory counts and stock warnings.
- Maintenance open/overdue counts.
- Disposal candidates and lifecycle summaries.
- ServiceNow export success/failure totals.
- RBAC/user-management counts.

### Trends and lifecycle metrics

The analytics screen combines KPI deltas, line charts, bar charts, period chips, ranking lists, lifecycle cards, and a heatmap. This creates a report-like pattern that can be reused for operational analytics without changing business logic.

### Risk and warning items

Warnings are shown through semantic tags, alert list items, sidebar badges, and yellow/red trend chips. The pattern is compact and avoids full-page warning banners except for destructive/reference-management cases.

### Tables and records

Tables use fixed layout, uppercase headers, ellipsis cells, mono IDs/timestamps, and hover rows. This is suitable for enterprise records where scanability matters more than large visual cards.

### Logs and audit trails

Logs are shown in two ways:

- Compact log rows with timestamp, action, and actor.
- Detail modal with sections and old/new diff rows.

This should be considered for inventory history, asset lifecycle changes, settings changes, ServiceNow export history, and RBAC audit trails.

### Charts and analytical visuals

The prototype includes handcrafted SVG/CSS chart visuals: donut chart, bar chart, dual bar chart, line chart, heatmap, ranking list, stacked purpose bars, and lifecycle cards. These are valuable visual references, but production should use maintainable chart components or a charting library where appropriate.

## 9. Form/dialog patterns

### Form density

Forms are compact and enterprise-oriented:

- Small labels at `11px`.
- Compact controls at `12.5px`.
- Two-column grids for standard fields.
- Required fields indicated by a red asterisk via `.flb.req`.
- Muted input backgrounds that turn white on focus.

### Dialog structure

Dialog composition is consistent:

1. Header with icon, title, subtitle, and close button.
2. Scrollable body.
3. Footer with right-aligned actions.
4. Optional side panel for summary/recent activity.

### Workflow patterns supported

- Item creation through single-entry and batch-entry modes.
- Batch intake via grid rows and add/delete actions.
- Serial-number entry via dedicated serial block and mono inputs.
- Approval flow with request detail, approve assignment, and reject modal.
- Inventory update through add-part and warning-to-add flows.
- Settings/reference editing through tree editors.
- Audit review through log list and log detail modals.

### Recommended reusable dialog primitives

- `BaseModal` with sizes: small, default, large, xl.
- `DualPanelModal` with main form area and right summary/activity rail.
- `FormSection` with section title marker.
- `DenseFormGrid` for two-column fields.
- `SerialEntryList` for serialized assets.
- `BatchEntryTable` for bulk workflows.
- `AuditDiffList` for old/new values.

## 10. Migration recommendations

### Phase A: Theme/token extraction

| Area | Recommendation | Risk level | Expected benefit | Implementation complexity | Backend changes needed? |
| --- | --- | --- | --- | --- | --- |
| Colors | Convert prototype CSS variables into EAM theme tokens. | Low | Immediate visual consistency. | Low | No |
| Typography | Adopt font scale and mono usage rules; decide whether remote Google Fonts are allowed. | Low/Medium | Better hierarchy and data readability. | Low | No |
| Surfaces | Standardize card/panel/table radius, border, and shadows. | Low | Polished enterprise look. | Low | No |
| Status styles | Create shared tag/badge semantic variants. | Low | Consistent statuses across modules. | Low | No |
| Buttons | Implement primary, yellow, ghost, danger, success, small, and tiny variants. | Low | Faster UI modernization. | Low/Medium | No |

### Phase B: Navigation modernization

| Area | Recommendation | Risk level | Expected benefit | Implementation complexity | Backend changes needed? |
| --- | --- | --- | --- | --- | --- |
| Topbar | Introduce fixed branded topbar with product/domain tabs. | Medium | Stronger product identity and clearer domain navigation. | Medium | No |
| Sidebar | Group sidebar items by business function. | Medium | Better information architecture. | Medium | No |
| Active sync | Drive topbar/sidebar state from router metadata. | Medium | Fewer state bugs than DOM class toggles. | Medium | No |
| User menu | Add account dropdown shell. | Low/Medium | More complete enterprise shell. | Low | Usually no |
| Global search placeholder | Add visual search first; defer full search behavior. | Low | Improves perceived capability. | Low | Not initially |

### Phase C: Dashboard modernization

| Area | Recommendation | Risk level | Expected benefit | Implementation complexity | Backend changes needed? |
| --- | --- | --- | --- | --- | --- |
| KPI cards | Replace existing summary blocks with tokenized KPI cards. | Low | High visual impact. | Low/Medium | No if using existing data |
| Panels | Use consistent panel header/body structure. | Low | Cleaner dashboard composition. | Low | No |
| Alerts | Add alert list pattern for warnings, overdue items, and stock risks. | Medium | Better operational awareness. | Medium | Possibly, only if new alert data is needed |
| Charts | Recreate chart visuals with maintainable components. | Medium | Better reporting experience. | Medium/High | Depends on available metrics |

### Phase D: Core page components

| Area | Recommendation | Risk level | Expected benefit | Implementation complexity | Backend changes needed? |
| --- | --- | --- | --- | --- | --- |
| Compact tables | Adopt `.tbl` density, mono ID cells, hover rows, and action links. | Low | Better list scanability. | Medium | No |
| Modal wrappers | Standardize modal header/body/footer and sizes. | Low | Consistent workflows. | Medium | No |
| Toolbar/header | Standardize page header and button row. | Low | Consistent page rhythm. | Low | No |
| Status tags | Centralize tag variants and labels. | Low | Reduces duplicated styling. | Low | No |
| Forms | Adopt dense form grid and focus states. | Low | Cleaner edit/create pages. | Medium | No |

### Phase E: Advanced components

| Area | Recommendation | Risk level | Expected benefit | Implementation complexity | Backend changes needed? |
| --- | --- | --- | --- | --- | --- |
| Tree editor | Explore for categories, locations, departments, or references. | Medium/High | Better reference-data management. | High | Possibly |
| Dual modal | Use for complex workflows with side summary/activity rail. | Medium | Strong workflow guidance. | Medium/High | No for shell; maybe for activity data |
| Scan side panel | Use for intake/import/scan workflows. | Medium | Improves operator feedback. | Medium | Possibly |
| Filter dropdown | Add reusable multi-select filter. | Medium | Better dense list filtering. | Medium | No if client-side; maybe if server-side filters |
| Timeline/log detail | Add audit timeline and diff components. | Medium | Better traceability. | Medium | Depends on audit data availability |

## 11. Risks and cautions

### What not to copy directly

- Do not directly paste the static HTML into the Vue application.
- Do not copy inline JavaScript as production logic.
- Do not depend on remote Google Fonts unless approved by security/performance requirements.
- Do not import business concepts that do not belong to the current EAM, such as spare-parts approval workflows, unless those workflows are explicitly planned.
- Do not expand scope into new modules simply because the prototype contains them.
- Use the prototype as a visual/design reference, not as direct production source code.

### Additional migration cautions

- The prototype has limited responsive behavior; production needs breakpoints.
- Some controls are visual-only and need accessibility work: keyboard focus, ARIA roles, Escape/outside-click behavior, and screen-reader labels.
- Static chart visuals should not be copied as hardcoded production charts.
- Drag/drop tree behavior requires careful accessibility and data-integrity handling.
- Modal stacking should be implemented deliberately to avoid trapping users in nested workflows.
- Existing EAM data models should drive which workflows are migrated; visual components should not force new business logic.

## 12. Suggested next UI tasks

| Task | Scope | Output |
| --- | --- | --- |
| FE-UI-1: Implement EAM theme tokens | Colors, typography, radius, borders, shadows, semantic states | Shared token file / theme layer |
| FE-UI-2: Navigation redesign using extracted layout | Fixed topbar, grouped sidebar, active route mapping, user menu shell | Modernized app shell |
| FE-UI-3: Dashboard visual upgrade | KPI cards, panels, alerts, basic charts | Updated dashboard UI using existing data |
| FE-UI-4: Core component polish | Buttons, tags, compact tables, page headers, forms, modal wrapper | Shared component improvements |
| FE-UI-5: Reference tree editor exploration | Category/location tree patterns, reassignment warnings, drag/drop feasibility | Prototype or technical design only |

## Validation

- Documentation-only deliverable.
- No backend changes.
- No frontend application changes.
- No API changes.
- No migration performed.
- No feature additions.
- No business workflow changes.
- No direct HTML import into Vue.
- docs-only; tests not run.
