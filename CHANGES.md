# 1BOX Dashboard — Major Rebuild Changes

**Date:** April 2026  
**Scope:** Google Ads data integration + MYM removal + dashboard hardening

---

## 1. MYM View Removed

- **Sidebar:** Removed the "MYM Results" nav button (`onclick="switchPage('mym',this)"`). The sidebar now has 4 buttons: Digital Marketing, Events & Conversions, Monthly Report, Google Ads.
- **HTML:** Removed the entire `<div id="page-mym">` block (~175 lines of Move-Ins, Net Variance, Revenue, and Occupancy tables — all hardcoded sample data).
- **JS:** Removed `mym` entry from the `pageTitles` object.
- **Default page:** "Digital Marketing Overview" (`page-marketing`) is now the active page on load. Its nav button has `class="nav-btn active"` and the div has `class="page active"`.
- **Page title:** Changed the initial `<h1 id="pageTitle">` from "MYM Results" to "Digital Marketing Overview".

---

## 2. Google Ads Data: Real Data from API Responses

### Data files processed
Five Google Ads API response files (50 rows each, daily-segmented) were aggregated into a new JS constant:

| Period | File |
|--------|------|
| 7d | `output_mnxhdoxp.json` (LAST_7_DAYS) |
| 14d | `output_mnxhd7bl.json` (LAST_14_DAYS) |
| 30d | `output_mnxhd7pq.json` (LAST_30_DAYS) |
| 3m | `output_mnxhd8eh.json` (Jan 13–Apr 13, 2026) |
| 6m | `output_mnxhd6fj.json` (Oct 13–Apr 13, 2026) |

Aggregation per campaign:
- **Summed:** `costMicros`, `clicks`, `conversions`, `allConversions`
- **Derived:** `avgCpc = costMicros / clicks / 1,000,000`, `convRate = conversions / clicks * 100`, `costPerConversion = cost / conversions`
- **Units:** All EUR values divided by 1,000,000 from micros

### New constant: `GADS_CAMPAIGNS_BY_RANGE`
Replaces the old `GADS_CAMPAIGNS` array (which was annual hardcoded data with extra fields like `keyEvents`, `intentConv`, `cpl`, `cpRes`, `cpMoveIn`).

```js
const GADS_CAMPAIGNS_BY_RANGE = {
  "7d": [ { name, cost, avgCpc, clicks, conversions, allConversions, convRate, costPerConversion }, ... ],
  "14d": [...],
  "30d": [...],
  "3m": [...],
  "6m": [...]
};
```

### Kept unchanged
- `GADS_BY_RANGE` — KPI summary cache (already correct real data for all 5 periods)
- `GADS_CHART_DATA` — static line chart data (Conversions vs Cost Over Time, monthly buckets)

---

## 3. Campaign Performance Table

### Column headers updated
Old columns: Campaign, Cost, Avg CPC, Clicks, Conversions, Key Events, Intent Events, Conv. Rate, Cost/Lead, Cost/Call, Cost/Intent, Cost/Reserv., Cost/Move-in

**New columns:** Campaign, Cost, Avg CPC, Clicks, Conversions, All Conversions, Conv. Rate, Cost/Conv.

Columns removed (no longer available from current API data): Key Events, Intent Events, Cost/Lead, Cost/Call, Cost/Intent, Cost/Reserv., Cost/Move-in.

### Total row moved to TOP
The `totals-row` is now rendered **first** (before campaign rows), as required. It shows: aggregate cost, weighted avg CPC, total clicks, total conversions, total all-conversions, weighted conv. rate, and aggregate cost/conversion.

### Dynamic data binding
`renderGadsTable(campaigns)` now accepts an optional `campaigns` parameter. When called without arguments, it calls `getCurrentCampaigns()` which maps the current date range (`currentDateRange`) to the correct `GADS_CAMPAIGNS_BY_RANGE` key.

---

## 4. Dropdown Filters Everything

The date preset dropdown (7d, 14d, 30d, 3m, 6m) now triggers `loadGadsWithDateRange(from, to)` which:

1. **Updates all 6 KPI cards** from `GADS_BY_RANGE[key]`
2. **Updates the Booking Funnel** (3 steps) from `GADS_BY_RANGE[key]`
3. **Re-renders the Campaign Performance table** with `GADS_CAMPAIGNS_BY_RANGE[key]`

Only the **line chart** (Conversions vs Cost Over Time) remains static — it uses pre-aggregated monthly data in `GADS_CHART_DATA` and does not change with the dropdown.

---

## 5. Booking Funnel — Dynamic Values

Funnel elements now have IDs and are populated by `loadGadsWithDateRange()`:

| Element | ID | Source |
|---------|-----|--------|
| Clicks value | `gadsFunnelClicks` | `GADS_BY_RANGE[key].clicks` |
| Transparent Bookings value | `gadsFunnelBookings` | `Math.round(GADS_BY_RANGE[key].conversions)` |
| Bookings % of clicks | `gadsFunnelBookingsRate` | conversions / clicks × 100 |
| Bookings Complete value | `gadsFunnelComplete` | `Math.round(conversions × 0.08)` |
| Complete % of bookings | `gadsFunnelCompleteRate` | complete / bookings × 100 |

Static MoM delta badges are hidden (set to `display:none`) since they don't apply across periods.

---

## 6. KPI HTML Placeholders

All hardcoded values in the Google Ads KPI cards replaced with `—`:
- `gadsKpiCost`: was `€552,507` → `—`
- `gadsKpiClicks`: was `102,728` → `—`
- `gadsKpiRes`: was `24,333` → `—`
- `gadsKpiCPR`: was `€22.71` → `—`
- `gadsKpiRents`: was `7,827` → `—`
- `gadsKpiCPRent`: was `€70.59` → `—`

These are filled in by JS as soon as the Gads page is first visited.

---

## 7. Initialization

- `DOMContentLoaded` now triggers `loadMarketingData()` automatically (since marketing is the default page, `switchPage` is never called for it).
- When switching to the Gads page, `loadGadsWithDateRange()` is called which populates KPIs, funnel, and table in one pass.
- Number formatting throughout uses `de-DE` locale (dots for thousands, commas for decimals), EUR with `€` prefix.

---

## Files Changed

- `/home/user/workspace/1box-dashboard/index.html` — Main dashboard file (4885 → 5458 lines with new GADS_CAMPAIGNS_BY_RANGE constant)
- `/home/user/workspace/gads_campaigns_by_range.js` — Intermediate processed data artifact
- `/home/user/workspace/1box-dashboard/CHANGES.md` — This file
