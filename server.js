'use strict';

/**
 * 1BOX Dashboard — Backend API Server
 * Serves static index.html + live data from GA4, Google Ads, and ClickUp
 */

require('dotenv').config();
const express = require('express');
const path = require('path');
const { execSync } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;

// CORS — allow all origins for deployed proxy
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
  next();
});

// ─── Constants ────────────────────────────────────────────────────────────────

const GA4_PROPERTY_ID = process.env.GA4_PROPERTY_ID || '308309603';
const GA4_CLIENT_ID = process.env.GA4_CLIENT_ID || '';
const GA4_CLIENT_SECRET = process.env.GA4_CLIENT_SECRET || '';
const GA4_REFRESH_TOKEN = process.env.GA4_REFRESH_TOKEN || '';

const GADS_ACCOUNT_ID = '5400964678';
const CLICKUP_LIST_ID = '901415219099';
const CLICKUP_WORKSPACE_ID = '9014577435';
const CLICKUP_SPACE_ID = '90150527892';

// Location slugs for the funnel
const LOCATION_SLUGS = [
  'alkmaar', 'almere', 'amsterdam-schepenbergweg', 'amsterdam-zuidoost',
  'bergen-op-zoom', 'boxtel', 'breda',
  'den-bosch', 'den-haag', 'eindhoven-best', 'goes', 'groningen',
  'heerlen', 'helmond', 'hellevoetsluis', 'lelystad', 'nijmegen-wijchen',
  'rijswijk', 'roermond', 'rotterdam-centrum', 'rotterdam-zuid', 'schiedam',
  'sittard', 'tilburg', 'utrecht', 'venlo',
  'alphen-aan-den-rijn', 'barendrecht', 'heerlen-heerlerbaan', 'helmond-kanaaldijk'
];

// Friendly location names (slug → display name)
const LOCATION_NAMES = {
  'alkmaar': 'Alkmaar',
  'almere': 'Almere',
  'amsterdam-schepenbergweg': 'Amsterdam Schepenbergweg',
  'amsterdam-zuidoost': 'Amsterdam-Zuidoost',
  'bergen-op-zoom': 'Bergen op Zoom',
  'boxtel': 'Boxtel',
  'breda': 'Breda',
  'den-bosch': 'Den Bosch',
  'den-haag': 'Den Haag',
  'eindhoven-best': 'Eindhoven Best',
  'goes': 'Goes',
  'groningen': 'Groningen',
  'heerlen': 'Heerlen',
  'helmond': 'Helmond',
  'hellevoetsluis': 'Hellevoetsluis',
  'lelystad': 'Lelystad',
  'nijmegen-wijchen': 'Nijmegen Wijchen',
  'rijswijk': 'Rijswijk',
  'roermond': 'Roermond',
  'rotterdam-centrum': 'Rotterdam Centrum',
  'rotterdam-zuid': 'Rotterdam Zuid',
  'schiedam': 'Schiedam',
  'sittard': 'Sittard',
  'tilburg': 'Tilburg',
  'utrecht': 'Utrecht',
  'venlo': 'Venlo',
  'alphen-aan-den-rijn': 'Alphen aan den Rijn',
  'barendrecht': 'Barendrecht',
  'heerlen-heerlerbaan': 'Heerlen Heerlerbaan',
  'helmond-kanaaldijk': 'Helmond Kanaaldijk',
};

// GA4 customEvent:locatie value → slug mapping
// GA4 fires events with locatie param like "Breda", "Den Haag", "Amsterdam-Zuidoost" etc.
// This maps those exact GA4 values to our slug keys.
const LOCATIE_TO_SLUG = {};
Object.entries(LOCATION_NAMES).forEach(([slug, name]) => {
  LOCATIE_TO_SLUG[name] = slug;
  // Also map without dashes for variants (e.g. "Nijmegen Wijchen" → "nijmegen-wijchen")
  LOCATIE_TO_SLUG[name.replace(/-/g, ' ')] = slug;
});
// Explicit overrides for GA4 locatie values that differ from display names
// GA4 returns values like "Amsterdam-Schepenbergweg" (with dash) while display names may not have dashes
LOCATIE_TO_SLUG['Amsterdam Schepenbergweg'] = 'amsterdam-schepenbergweg';
LOCATIE_TO_SLUG['Amsterdam-Schepenbergweg'] = 'amsterdam-schepenbergweg';
LOCATIE_TO_SLUG['Heerlen Heerlerbaan'] = 'heerlen-heerlerbaan';
LOCATIE_TO_SLUG['Heerlen-Heerlerbaan'] = 'heerlen-heerlerbaan';
LOCATIE_TO_SLUG['Nijmegen Wijchen'] = 'nijmegen-wijchen';
LOCATIE_TO_SLUG['Nijmegen-Wijchen'] = 'nijmegen-wijchen';
LOCATIE_TO_SLUG['Amsterdam-Zuidoost'] = 'amsterdam-zuidoost';
LOCATIE_TO_SLUG['Amsterdam Zuidoost'] = 'amsterdam-zuidoost';
LOCATIE_TO_SLUG['Helmond Kanaaldijk'] = 'helmond-kanaaldijk';
LOCATIE_TO_SLUG['Bergen op Zoom'] = 'bergen-op-zoom';

// Display name → GA4 locatie value mapping (for cases where they differ)
// Most are identical, but some GA4 values use dashes while display names don't
const NAME_TO_GA4_LOCATIE = {
  'Amsterdam Schepenbergweg': 'Amsterdam-Schepenbergweg',
  'Heerlen Heerlerbaan': 'Heerlen-Heerlerbaan',
  'Nijmegen Wijchen': 'Nijmegen-Wijchen',
};

const FUNNEL_EVENTS = [
  'clickto_sizepage_transparent',
  'clickto_detailspage_transparent',
  'select_unit_size_transparent',
  'transparent_booking',
  'transparent_booking_start',
  'transparent_booking_step_2',
  'transparent_booking_step_3',
  'transparent_booking_payment',
  'transparent_booking_complete',
  'bm_transparent_booking_complete',
];

// Budget targets (static)
const BUDGET_TARGETS = {
  leads: {
    'Amsterdam Schepenbergweg': 40, 'Utrecht': 35, 'Den Haag': 35, 'Rotterdam Centrum': 30,
    'Rotterdam Zuid': 28, 'Breda': 28, 'Tilburg': 25, 'Almere': 25, 'Heerlen': 22,
    'Heerlen Heerlerbaan': 22, 'Barendrecht': 20, 'Rijswijk': 20, 'Eindhoven Best': 20,
    'Alphen aan den Rijn': 18, 'Schiedam': 18, 'Groningen': 18, 'Den Bosch': 15,
    'Helmond Kanaaldijk': 15, 'Nijmegen Wijchen': 15, 'Goes': 12, 'Lelystad': 12,
    'Hellevoetsluis': 10, 'Roermond': 10, 'Sittard': 10, 'Venlo': 10,
  },
  moveins: {
    'Amsterdam Schepenbergweg': 20, 'Utrecht': 18, 'Den Haag': 18, 'Rotterdam Centrum': 15,
    'Rotterdam Zuid': 14, 'Breda': 14, 'Tilburg': 12, 'Almere': 12, 'Heerlen': 11,
    'Heerlen Heerlerbaan': 11, 'Barendrecht': 10, 'Rijswijk': 10, 'Eindhoven Best': 10,
    'Alphen aan den Rijn': 9, 'Schiedam': 9, 'Groningen': 9, 'Den Bosch': 8,
    'Helmond Kanaaldijk': 8, 'Nijmegen Wijchen': 8, 'Goes': 6, 'Lelystad': 6,
    'Hellevoetsluis': 5, 'Roermond': 5, 'Sittard': 5, 'Venlo': 5,
  },
};

// ─── In-memory cache ──────────────────────────────────────────────────────────

const cache = new Map(); // key → { data, expiry }
const CACHE_TTL = 5 * 60 * 1000; // 5 minutes

function cacheGet(key) {
  const entry = cache.get(key);
  if (entry && Date.now() < entry.expiry) return entry.data;
  cache.delete(key);
  return null;
}

function cacheSet(key, data) {
  cache.set(key, { data, expiry: Date.now() + CACHE_TTL });
}

// ─── GA4 token management ─────────────────────────────────────────────────────

let ga4Token = null;
let ga4TokenExpiry = 0;

async function getGA4Token() {
  if (ga4Token && Date.now() < ga4TokenExpiry) return ga4Token;

  const params = new URLSearchParams({
    client_id: GA4_CLIENT_ID,
    client_secret: GA4_CLIENT_SECRET,
    refresh_token: GA4_REFRESH_TOKEN,
    grant_type: 'refresh_token',
  });

  const resp = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params,
  });

  const data = await resp.json();
  if (!data.access_token) throw new Error(`GA4 token error: ${JSON.stringify(data)}`);
  ga4Token = data.access_token;
  ga4TokenExpiry = Date.now() + 55 * 60 * 1000;
  return ga4Token;
}

// ─── GA4 API helper ───────────────────────────────────────────────────────────

// Semaphore to limit concurrent GA4 requests (max 5 at a time)
let ga4ActiveRequests = 0;
const ga4Queue = [];
const GA4_MAX_CONCURRENT = 5;

function ga4Throttle(fn) {
  return new Promise((resolve, reject) => {
    const run = async () => {
      ga4ActiveRequests++;
      try { resolve(await fn()); }
      catch (e) { reject(e); }
      finally {
        ga4ActiveRequests--;
        if (ga4Queue.length > 0) ga4Queue.shift()();
      }
    };
    if (ga4ActiveRequests < GA4_MAX_CONCURRENT) run();
    else ga4Queue.push(run);
  });
}

async function ga4RunReport(body, retries = 3) {
  return ga4Throttle(async () => {
    for (let attempt = 0; attempt < retries; attempt++) {
      const token = await getGA4Token();
      const resp = await fetch(
        `https://analyticsdata.googleapis.com/v1beta/properties/${GA4_PROPERTY_ID}:runReport`,
        {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
        }
      );
      const json = await resp.json();
      if (json.error) {
        if (json.error.code === 429 && attempt < retries - 1) {
          const delay = (attempt + 1) * 2000; // 2s, 4s, 6s
          console.warn(`GA4 rate limited, retrying in ${delay}ms (attempt ${attempt + 1}/${retries})`);
          await new Promise(r => setTimeout(r, delay));
          continue;
        }
        throw new Error(`GA4 API error: ${JSON.stringify(json.error)}`);
      }
      return json;
    }
  });
}

// Parse GA4 rows into flat objects
function parseGA4Rows(report) {
  if (!report || !report.rows) return [];
  const dimHeaders = (report.dimensionHeaders || []).map((h) => h.name);
  const metHeaders = (report.metricHeaders || []).map((h) => h.name);
  return report.rows.map((row) => {
    const obj = {};
    (row.dimensionValues || []).forEach((dv, i) => { obj[dimHeaders[i]] = dv.value; });
    (row.metricValues || []).forEach((mv, i) => { obj[metHeaders[i]] = mv.value; });
    return obj;
  });
}

// Build GA4 date range
function buildDateRange(start, end) {
  return [{
    startDate: start || '30daysAgo',
    endDate: end || 'yesterday',
  }];
}

// Build previous date range (same length, immediately prior)
function buildPrevDateRange(start, end) {
  if (!start || !end) {
    // Default 30 days ago
    const endDate = new Date();
    endDate.setDate(endDate.getDate() - 1);
    const startDate = new Date(endDate);
    startDate.setDate(startDate.getDate() - 30);
    const prevEnd = new Date(startDate);
    prevEnd.setDate(prevEnd.getDate() - 1);
    const prevStart = new Date(prevEnd);
    prevStart.setDate(prevStart.getDate() - 30);
    return {
      start: prevStart.toISOString().split('T')[0],
      end: prevEnd.toISOString().split('T')[0],
    };
  }
  const s = new Date(start);
  const e = new Date(end);
  const diff = Math.round((e - s) / (1000 * 60 * 60 * 24));
  const prevEnd = new Date(s);
  prevEnd.setDate(prevEnd.getDate() - 1);
  const prevStart = new Date(prevEnd);
  prevStart.setDate(prevStart.getDate() - diff);
  return {
    start: prevStart.toISOString().split('T')[0],
    end: prevEnd.toISOString().split('T')[0],
  };
}

// ─── External tool CLI helper ─────────────────────────────────────────────────

function callTool(sourceId, toolName, args) {
  const payload = JSON.stringify({ source_id: sourceId, tool_name: toolName, arguments: args });
  // Escape single quotes in payload for shell safety
  const escaped = payload.replace(/'/g, "'\\''");
  try {
    const result = execSync(`external-tool call '${escaped}'`, {
      timeout: 90000,
      maxBuffer: 20 * 1024 * 1024, // 20MB
    }).toString();
    return JSON.parse(result);
  } catch (err) {
    const stderr = err.stderr ? err.stderr.toString() : '';
    throw new Error(`external-tool error: ${stderr || err.message}`);
  }
}

// ─── Google Ads date range mapping ────────────────────────────────────────────

function gadsDateRange(range) {
  const mapping = {
    '7d': { dateRange: 'LAST_7_DAYS' },
    '14d': { dateRange: 'LAST_14_DAYS' },
    '30d': { dateRange: 'LAST_30_DAYS' },
    '3m': { dateRange: 'CUSTOM', startDate: daysAgoStr(90), endDate: daysAgoStr(1) },
    '6m': { dateRange: 'CUSTOM', startDate: daysAgoStr(180), endDate: daysAgoStr(1) },
  };
  return mapping[range] || { dateRange: 'LAST_30_DAYS' };
}

function daysAgoStr(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().split('T')[0];
}

function ga4DateFromRange(range) {
  const mapping = {
    '7d': { startDate: '7daysAgo', endDate: 'yesterday' },
    '14d': { startDate: '14daysAgo', endDate: 'yesterday' },
    '30d': { startDate: '30daysAgo', endDate: 'yesterday' },
    '3m': { startDate: '90daysAgo', endDate: 'yesterday' },
    '6m': { startDate: '180daysAgo', endDate: 'yesterday' },
  };
  return mapping[range] || { startDate: '30daysAgo', endDate: 'yesterday' };
}

// ─── Channel bucketing ────────────────────────────────────────────────────────

function bucketChannel(channel) {
  const ch = (channel || '').toLowerCase();
  if (['organic search', 'organic social'].some((c) => ch.includes(c.replace(' ', '').toLowerCase()) || ch === c.toLowerCase())) {
    return 'organic';
  }
  if (['paid search', 'paid social', 'paid other', 'display', 'cross-network'].some((c) =>
    ch === c.toLowerCase() || ch.includes(c.replace(' ', '').toLowerCase()))) {
    return 'paid';
  }
  return 'direct';
}

// ─── Static file serving ──────────────────────────────────────────────────────

app.use(express.static(path.join(__dirname)));

// ─── API: /api/ga4/overview ───────────────────────────────────────────────────

app.get('/api/ga4/overview', async (req, res) => {
  const start = req.query.start || req.query.start_date;
  const end = req.query.end || req.query.end_date;
  const cacheKey = `ga4-overview-${start}-${end}`;
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    const dateRanges = buildDateRange(start, end);

    // Run all GA4 queries in parallel
    const [
      rentReport,
      reservationsReport,
      deviceReport,
      convDeviceReport,
      channelReport,
      genderReport,
      ageReport,
      engagementReport,
      rentByMonthReport,
      resByMonthReport,
      citiesReport,
      dowReport,
      bookSrcTransparentReport,
      bookSrcCompleteReport,
    ] = await Promise.all([
      // a) Rent count
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'bm_transparent_booking_complete' } },
        },
      }),
      // b) Reservations
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'transparent_booking' } },
        },
      }),
      // c) Visits by device
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'activeUsers' }],
        dimensions: [{ name: 'deviceCategory' }],
      }),
      // d) Conversions by device
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensions: [{ name: 'deviceCategory' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'bm_transparent_booking_complete' } },
        },
      }),
      // e) Users by source/channel
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'activeUsers' }],
        dimensions: [{ name: 'sessionDefaultChannelGrouping' }],
      }),
      // f) Demographics gender
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'activeUsers' }],
        dimensions: [{ name: 'userGender' }],
      }),
      // g) Demographics age
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'activeUsers' }],
        dimensions: [{ name: 'userAgeBracket' }],
      }),
      // h) Engagement by month (users, sessions, duration)
      ga4RunReport({
        dateRanges,
        metrics: [
          { name: 'activeUsers' },
          { name: 'engagedSessions' },
          { name: 'userEngagementDuration' },
        ],
        dimensions: [{ name: 'year' }, { name: 'month' }],
        orderBys: [{ dimension: { dimensionName: 'year' } }, { dimension: { dimensionName: 'month' } }],
      }),
      // i) Rentals by month
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensions: [{ name: 'year' }, { name: 'month' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'bm_transparent_booking_complete' } },
        },
        orderBys: [{ dimension: { dimensionName: 'year' } }, { dimension: { dimensionName: 'month' } }],
      }),
      // j) Reservations by month
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensions: [{ name: 'year' }, { name: 'month' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'transparent_booking' } },
        },
        orderBys: [{ dimension: { dimensionName: 'year' } }, { dimension: { dimensionName: 'month' } }],
      }),
      // k) Top cities
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'activeUsers' }, { name: 'sessions' }],
        dimensions: [{ name: 'city' }],
        orderBys: [{ metric: { metricName: 'activeUsers' }, desc: true }],
        limit: 10,
      }),
      // l) Sessions by day of week
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'activeUsers' }, { name: 'sessions' }],
        dimensions: [{ name: 'dayOfWeekName' }],
      }),
      // m) Bookings by source — transparent_booking
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensions: [{ name: 'sessionDefaultChannelGrouping' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'transparent_booking' } },
        },
      }),
      // n) Bookings by source — bm_transparent_booking_complete
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensions: [{ name: 'sessionDefaultChannelGrouping' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'bm_transparent_booking_complete' } },
        },
      }),
    ]);

    // Parse scorecards
    const rentRows = parseGA4Rows(rentReport);
    const resRows = parseGA4Rows(reservationsReport);
    const rent = rentRows.length ? parseInt(rentRows[0].eventCount, 10) : 0;
    const reservations = resRows.length ? parseInt(resRows[0].eventCount, 10) : 0;

    // Visits by device
    const deviceRows = parseGA4Rows(deviceReport);
    const visits_by_device = { mobile: 0, desktop: 0, tablet: 0 };
    deviceRows.forEach((r) => {
      const cat = (r.deviceCategory || '').toLowerCase();
      if (visits_by_device.hasOwnProperty(cat)) visits_by_device[cat] = parseInt(r.activeUsers, 10);
    });

    // Conversions by device
    const convDeviceRows = parseGA4Rows(convDeviceReport);
    const conversions_by_device = { mobile: 0, desktop: 0, tablet: 0 };
    convDeviceRows.forEach((r) => {
      const cat = (r.deviceCategory || '').toLowerCase();
      if (conversions_by_device.hasOwnProperty(cat)) conversions_by_device[cat] = parseInt(r.eventCount, 10);
    });

    // Conversions by source (activeUsers per channel)
    const channelRows = parseGA4Rows(channelReport);
    const conversions_by_source = channelRows
      .map((r) => ({ source: r.sessionDefaultChannelGrouping, users: parseInt(r.activeUsers, 10) }))
      .sort((a, b) => b.users - a.users);

    // Demographics gender
    const genderRows = parseGA4Rows(genderReport);
    const demographics_gender = { unknown: 0, male: 0, female: 0 };
    genderRows.forEach((r) => {
      const g = (r.userGender || '').toLowerCase();
      if (demographics_gender.hasOwnProperty(g)) demographics_gender[g] = parseInt(r.activeUsers, 10);
      else demographics_gender[g] = parseInt(r.activeUsers, 10);
    });

    // Demographics age
    const ageRows = parseGA4Rows(ageReport);
    const demographics_age = {};
    ageRows.forEach((r) => {
      demographics_age[r.userAgeBracket || 'unknown'] = parseInt(r.activeUsers, 10);
    });

    // Engagement table — merge monthly engagement + rentals + reservations
    const engRows = parseGA4Rows(engagementReport);
    const rentByMonthRows = parseGA4Rows(rentByMonthReport);
    const resByMonthRows = parseGA4Rows(resByMonthReport);

    // Build lookup maps
    const rentByMonth = {};
    rentByMonthRows.forEach((r) => { rentByMonth[`${r.year}-${r.month}`] = parseInt(r.eventCount, 10); });
    const resByMonth = {};
    resByMonthRows.forEach((r) => { resByMonth[`${r.year}-${r.month}`] = parseInt(r.eventCount, 10); });

    const engagement_table = engRows.map((r) => {
      const key = `${r.year}-${r.month}`;
      const durationSec = parseFloat(r.userEngagementDuration || 0);
      const users = parseInt(r.activeUsers || 0, 10);
      return {
        year: r.year,
        month: r.month,
        users,
        engaged_sessions: parseInt(r.engagedSessions || 0, 10),
        avg_engagement_time: users > 0 ? Math.round((durationSec / users) * 100) / 100 : 0,
        rentals: rentByMonth[key] || 0,
        reservations: resByMonth[key] || 0,
      };
    });

    const trend = engagement_table.map((r) => ({
      year: r.year,
      month: r.month,
      rentals: r.rentals,
      reservations: r.reservations,
    }));

    // Top cities
    const cityRows = parseGA4Rows(citiesReport);
    const top_cities = cityRows.map((r) => ({
      city: r.city,
      users: parseInt(r.activeUsers, 10),
      sessions: parseInt(r.sessions, 10),
    }));

    // Sessions by DOW
    const dowRows = parseGA4Rows(dowReport);
    const DAY_ORDER = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    const sessions_by_dow = {};
    DAY_ORDER.forEach((day) => { sessions_by_dow[day] = { users: 0, sessions: 0 }; });
    dowRows.forEach((r) => {
      const day = r.dayOfWeekName;
      if (day) {
        sessions_by_dow[day] = {
          users: parseInt(r.activeUsers, 10),
          sessions: parseInt(r.sessions, 10),
        };
      }
    });

    // Bookings by source
    const bookTransRows = parseGA4Rows(bookSrcTransparentReport);
    const bookCompRows = parseGA4Rows(bookSrcCompleteReport);

    function buildBookingBySource(rows) {
      return rows.map((r) => ({
        source: r.sessionDefaultChannelGrouping || 'Unknown',
        count: parseInt(r.eventCount, 10),
      })).sort((a, b) => b.count - a.count);
    }

    const source_by_event = {
      transparent_booking: buildBookingBySource(bookTransRows),
      booking_complete: buildBookingBySource(bookCompRows),
    };

    const result = {
      scorecards: { rent, reservations, total_cost: null },
      visits_by_device,
      conversions_by_device,
      conversions_by_source,
      demographics_gender,
      demographics_age,
      engagement_table,
      trend,
      top_cities,
      sessions_by_dow,
      source_by_event,
    };

    cacheSet(cacheKey, result);
    res.json(result);
  } catch (err) {
    console.error('[/api/ga4/overview]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─── API: /api/ga4/funnel ─────────────────────────────────────────────────────

app.get('/api/ga4/funnel', async (req, res) => {
  const start = req.query.start || req.query.start_date;
  const end = req.query.end || req.query.end_date;
  const location = req.query.location;
  const cacheKey = `ga4-funnel-${start}-${end}-${location || ''}`;
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    const dateRanges = buildDateRange(start, end);
    const prevRange = buildPrevDateRange(start, end);

    // Resolve actual date strings for response
    const actualStart = start || daysAgoStr(30);
    const actualEnd = end || daysAgoStr(1);

    // Build dimension filter for location if provided
    // Use customEvent:locatie — the GA4 event parameter that contains location name
    // for ALL funnel events (including booking events that fire on generic pages)
    let locationFilter = null;
    if (location) {
      // Map display name to GA4 locatie value
      // Frontend sends display name (e.g. "Amsterdam Schepenbergweg")
      // GA4 may store it differently (e.g. "Amsterdam-Schepenbergweg")
      const displayName = LOCATION_NAMES[location] || location;
      const locatieName = NAME_TO_GA4_LOCATIE[displayName] || displayName;
      locationFilter = {
        filter: {
          fieldName: 'customEvent:locatie',
          stringFilter: {
            matchType: 'EXACT',
            value: locatieName,
            caseSensitive: false,
          },
        },
      };
    }

    // Query all funnel events in one request with eventName + channel dimensions
    const body = {
      dateRanges,
      metrics: [{ name: 'eventCount' }],
      dimensions: [{ name: 'eventName' }, { name: 'sessionDefaultChannelGrouping' }],
      dimensionFilter: {
        andGroup: {
          expressions: [
            {
              filter: {
                fieldName: 'eventName',
                inListFilter: { values: FUNNEL_EVENTS },
              },
            },
            ...(locationFilter ? [locationFilter] : []),
          ],
        },
      },
    };

    const report = await ga4RunReport(body);
    const rows = parseGA4Rows(report);

    // Aggregate: event → channel → count
    const eventData = {};
    FUNNEL_EVENTS.forEach((e) => { eventData[e] = { organic: 0, paid: 0, direct: 0 }; });

    rows.forEach((r) => {
      const event = r.eventName;
      const channel = r.sessionDefaultChannelGrouping || '';
      const count = parseInt(r.eventCount, 10);
      if (!eventData[event]) return;
      const bucket = bucketChannelGA4(channel);
      eventData[event][bucket] += count;
    });

    const funnel = FUNNEL_EVENTS.map((event, i) => {
      const d = eventData[event];
      return {
        step: i + 1,
        event,
        organic: d.organic,
        paid: d.paid,
        direct: d.direct,
        total: d.organic + d.paid + d.direct,
      };
    });

    const result = {
      funnel,
      locations: Object.values(LOCATION_NAMES),
      date_range: { start: actualStart, end: actualEnd },
      prev_date_range: prevRange,
    };

    cacheSet(cacheKey, result);
    res.json(result);
  } catch (err) {
    console.error('[/api/ga4/funnel]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// Channel bucketing for GA4 sessionDefaultChannelGrouping
function bucketChannelGA4(channel) {
  const c = (channel || '').toLowerCase();
  if (c === 'organic search' || c === 'organic social') return 'organic';
  if (['paid search', 'paid social', 'paid other', 'display', 'cross-network'].includes(c)) return 'paid';
  return 'direct';
}

// ─── API: /api/ga4/funnel/locations ──────────────────────────────────────────

app.get('/api/ga4/funnel/locations', async (req, res) => {
  const start = req.query.start || req.query.start_date;
  const end = req.query.end || req.query.end_date;
  const cacheKey = `ga4-funnel-locations-${start}-${end}`;
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    const dateRanges = buildDateRange(start, end);
    const actualStart = start || daysAgoStr(30);
    const actualEnd = end || daysAgoStr(1);

    // Query all three events with customEvent:locatie dimension
    // This correctly attributes booking events to locations even when they fire
    // on generic pages like /bestellen/reservation-confirmed/
    const [startedReport, bookingReport, completedReport] = await Promise.all([
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensions: [{ name: 'customEvent:locatie' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'clickto_sizepage_transparent' } },
        },
        limit: 5000,
      }),
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensions: [{ name: 'customEvent:locatie' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'transparent_booking' } },
        },
        limit: 5000,
      }),
      ga4RunReport({
        dateRanges,
        metrics: [{ name: 'eventCount' }],
        dimensions: [{ name: 'customEvent:locatie' }],
        dimensionFilter: {
          filter: { fieldName: 'eventName', stringFilter: { value: 'bm_transparent_booking_complete' } },
        },
        limit: 5000,
      }),
    ]);

    // Aggregate by locatie name → slug using LOCATIE_TO_SLUG mapping
    function aggregateByLocatie(rows) {
      const result = {};
      rows.forEach((r) => {
        const locatie = r['customEvent:locatie'] || '';
        if (!locatie || locatie === '(not set)') return;
        const slug = LOCATIE_TO_SLUG[locatie];
        if (slug) {
          result[slug] = (result[slug] || 0) + parseInt(r.eventCount, 10);
        }
      });
      return result;
    }

    const startedBySlug = aggregateByLocatie(parseGA4Rows(startedReport));
    const bookingBySlug = aggregateByLocatie(parseGA4Rows(bookingReport));
    const completedBySlug = aggregateByLocatie(parseGA4Rows(completedReport));

    const locations = Object.keys(LOCATION_NAMES).map((slug) => {
      const started = startedBySlug[slug] || 0;
      const booking = bookingBySlug[slug] || 0;
      const completed = completedBySlug[slug] || 0;
      const completionRate = started > 0 ? Math.round((completed / started) * 1000) / 10 : 0;
      const avgBounce = started > 0
        ? Math.round(((started - booking) / started) * 1000) / 10
        : 0;
      return {
        name: LOCATION_NAMES[slug],
        started,
        booking,
        completed,
        avgBounce,
        completionRate,
      };
    }).sort((a, b) => b.started - a.started);

    const result = {
      locations,
      date_range: { start: actualStart, end: actualEnd },
    };

    cacheSet(cacheKey, result);
    res.json(result);
  } catch (err) {
    console.error('[/api/ga4/funnel/locations]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─── API: /api/ga4/monthly-report ────────────────────────────────────────────

app.get('/api/ga4/monthly-report', async (req, res) => {
  // Accept optional start_date & end_date query params to react to date dropdown
  const qStart = req.query.start_date;
  const qEnd = req.query.end_date;
  const cacheKey = qStart && qEnd ? `ga4-monthly-report-${qStart}-${qEnd}` : 'ga4-monthly-report';
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    let monthStart, today, monthName, year, month;

    const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'];

    if (qStart && qEnd) {
      // Use dropdown-selected range
      monthStart = qStart;
      today = qEnd;
      const startD = new Date(qStart + 'T00:00:00');
      year = startD.getFullYear();
      month = startD.getMonth() + 1;
      const endD = new Date(qEnd + 'T00:00:00');
      // Build a descriptive label from the date range
      const diffDays = Math.round((endD - startD) / (1000 * 60 * 60 * 24));
      if (diffDays <= 40) {
        // Within roughly one month — use start month name
        monthName = MONTH_NAMES[month - 1];
      } else {
        // Multi-month range — show range
        monthName = MONTH_NAMES[startD.getMonth()] + ' – ' + MONTH_NAMES[endD.getMonth()];
        year = endD.getFullYear();
      }
    } else {
      // Default: current month
      const now = new Date();
      year = now.getFullYear();
      month = now.getMonth() + 1;
      const monthStr = String(month).padStart(2, '0');
      monthStart = `${year}-${monthStr}-01`;
      today = now.toISOString().split('T')[0];
      monthName = MONTH_NAMES[month - 1];
    }

    // Compute previous period (same duration, immediately before)
    const startD = new Date(monthStart + 'T00:00:00');
    const endD = new Date(today + 'T00:00:00');
    const rangeDays = Math.round((endD - startD) / (1000 * 60 * 60 * 24));
    const prevEndDate = new Date(startD);
    prevEndDate.setDate(prevEndDate.getDate() - 1);
    const prevStartDate = new Date(prevEndDate);
    prevStartDate.setDate(prevStartDate.getDate() - rangeDays + 1);
    const prevStart = prevStartDate.toISOString().split('T')[0];
    const prevEnd = prevEndDate.toISOString().split('T')[0];

    const buildMonthData = async (s, e) => {
      const dateRanges = [{ startDate: s, endDate: e }];
      const [usersReport, leadsReport, customersReport, webReport] = await Promise.all([
        ga4RunReport({ dateRanges, metrics: [{ name: 'activeUsers' }] }),
        ga4RunReport({
          dateRanges,
          metrics: [{ name: 'eventCount' }],
          dimensionFilter: {
            filter: { fieldName: 'eventName', stringFilter: { value: 'transparent_booking' } },
          },
        }),
        ga4RunReport({
          dateRanges,
          metrics: [{ name: 'eventCount' }],
          dimensionFilter: {
            filter: {
              fieldName: 'eventName',
              stringFilter: { value: 'bm_transparent_booking_complete' },
            },
          },
        }),
        ga4RunReport({
          dateRanges,
          metrics: [
            { name: 'activeUsers' },
            { name: 'bounceRate' },
            { name: 'averageSessionDuration' },
            { name: 'screenPageViewsPerSession' },
            { name: 'engagementRate' },
          ],
        }),
      ]);

      const usersVal = parseGA4Rows(usersReport)[0]?.activeUsers || '0';
      const leadsVal = parseGA4Rows(leadsReport)[0]?.eventCount || '0';
      const customersVal = parseGA4Rows(customersReport)[0]?.eventCount || '0';
      const webRow = parseGA4Rows(webReport)[0] || {};

      const totalUsers = parseInt(usersVal, 10);
      const totalLeads = parseInt(leadsVal, 10);
      const totalCustomers = parseInt(customersVal, 10);

      return {
        conversion: {
          total_users: totalUsers,
          total_leads: totalLeads,
          total_customers: totalCustomers,
          user_to_lead_rate: totalUsers > 0
            ? Math.round((totalLeads / totalUsers) * 1000) / 10
            : 0,
          lead_to_customer_rate: totalLeads > 0
            ? Math.round((totalCustomers / totalLeads) * 1000) / 10
            : 0,
        },
        website_data: {
          unique_visitors: parseInt(webRow.activeUsers || '0', 10),
          bounce_rate: Math.round(parseFloat(webRow.bounceRate || '0') * 1000) / 10,
          avg_session_duration: Math.round(parseFloat(webRow.averageSessionDuration || '0') * 100) / 100,
          pages_per_session: Math.round(parseFloat(webRow.screenPageViewsPerSession || '0') * 10) / 10,
          engagement_rate: Math.round(parseFloat(webRow.engagementRate || '0') * 1000) / 10,
        },
      };
    };

    const [curr, prev] = await Promise.all([
      buildMonthData(monthStart, today),
      buildMonthData(prevStart, prevEnd),
    ]);

    // Merge prev values into conversion/website_data with prev_ prefix
    const conversionMerged = { ...curr.conversion };
    for (const [k, v] of Object.entries(prev.conversion)) {
      conversionMerged[`prev_${k}`] = v;
    }
    const websiteMerged = { ...curr.website_data };
    for (const [k, v] of Object.entries(prev.website_data)) {
      websiteMerged[`prev_${k}`] = v;
    }

    const result = {
      month_name: monthName,
      month_number: month,
      year,
      date_range: { start: monthStart, end: today },
      conversion: conversionMerged,
      leads_by_facility: [],
      website_data: websiteMerged,
      prev_conversion: prev.conversion,
      prev_website_data: prev.website_data,
    };

    cacheSet(cacheKey, result);
    res.json(result);
  } catch (err) {
    console.error('[/api/ga4/monthly-report]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─── API: /api/ga4/conversion-trend ──────────────────────────────────────────

app.get('/api/ga4/conversion-trend', async (req, res) => {
  const cacheKey = 'ga4-conversion-trend';
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    // Last 6 full months (not including current month)
    const now = new Date();
    const months = [];
    for (let i = 6; i >= 1; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const lastDay = new Date(d.getFullYear(), d.getMonth() + 1, 0);
      months.push({
        year: y,
        month: m,
        start: `${y}-${m}-01`,
        end: lastDay.toISOString().split('T')[0],
        label: d.toLocaleString('en-US', { month: 'short' }),
      });
    }

    // Fetch data for all months in parallel
    const monthData = await Promise.all(
      months.map(async (mo) => {
        const dateRanges = [{ startDate: mo.start, endDate: mo.end }];
        const [usersR, leadsR, customersR] = await Promise.all([
          ga4RunReport({ dateRanges, metrics: [{ name: 'activeUsers' }] }),
          ga4RunReport({
            dateRanges,
            metrics: [{ name: 'eventCount' }],
            dimensionFilter: {
              filter: { fieldName: 'eventName', stringFilter: { value: 'transparent_booking' } },
            },
          }),
          ga4RunReport({
            dateRanges,
            metrics: [{ name: 'eventCount' }],
            dimensionFilter: {
              filter: {
                fieldName: 'eventName',
                stringFilter: { value: 'bm_transparent_booking_complete' },
              },
            },
          }),
        ]);
        const users = parseInt(parseGA4Rows(usersR)[0]?.activeUsers || '0', 10);
        const leads = parseInt(parseGA4Rows(leadsR)[0]?.eventCount || '0', 10);
        const customers = parseInt(parseGA4Rows(customersR)[0]?.eventCount || '0', 10);
        return {
          month: mo.label,
          year: mo.year,
          user_to_lead: users > 0 ? Math.round((leads / users) * 1000) / 10 : 0,
          lead_to_customer: leads > 0 ? Math.round((customers / leads) * 1000) / 10 : 0,
        };
      })
    );

    const result = { trend: monthData };
    cacheSet(cacheKey, result);
    res.json(result);
  } catch (err) {
    console.error('[/api/ga4/conversion-trend]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─── API: /api/budget/pace ────────────────────────────────────────────────────

app.get('/api/budget/pace', async (req, res) => {
  const cacheKey = 'budget-pace';
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth(); // 0-indexed
    const monthStart = `${year}-${String(month + 1).padStart(2, '0')}-01`;
    const today = now.toISOString().split('T')[0];
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const currentDay = now.getDate();

    // Fetch leads per location from GA4 (transparent_booking events by pagePath)
    const leadsReport = await ga4RunReport({
      dateRanges: [{ startDate: monthStart, endDate: today }],
      dimensions: [{ name: 'pagePath' }],
      metrics: [{ name: 'eventCount' }],
      dimensionFilter: {
        filter: {
          fieldName: 'eventName',
          stringFilter: { matchType: 'EXACT', value: 'transparent_booking' },
        },
      },
    });

    // Map page paths to location names and count leads
    const leadsPerLocation = {};
    const slugToName = {};
    for (const [slug, name] of Object.entries(LOCATION_NAMES)) {
      slugToName[slug] = name;
    }

    parseGA4Rows(leadsReport).forEach(row => {
      const path = (row.pagePath || '').toLowerCase();
      for (const [slug, name] of Object.entries(slugToName)) {
        if (path.includes(slug)) {
          leadsPerLocation[name] = (leadsPerLocation[name] || 0) + parseInt(row.eventCount) || 0;
          break;
        }
      }
    });

    // Build facilities array with budget vs actual
    const facilities = Object.entries(BUDGET_TARGETS.leads).map(([name, budget]) => ({
      name,
      leads_budget: budget,
      leads_actual: leadsPerLocation[name] || 0,
      moveins_budget: BUDGET_TARGETS.moveins[name] || 0,
    }));

    const result = {
      month: `${year}-${String(month + 1).padStart(2, '0')}`,
      days_in_month: daysInMonth,
      current_day: currentDay,
      targets: BUDGET_TARGETS,
      facilities,
    };

    cacheSet(cacheKey, result);
    res.json(result);
  } catch (err) {
    console.error('[/api/budget/pace]', err.message);
    // Fallback with empty facilities
    const now = new Date();
    res.json({
      month: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`,
      days_in_month: new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate(),
      current_day: now.getDate(),
      targets: BUDGET_TARGETS,
      facilities: Object.entries(BUDGET_TARGETS.leads).map(([name, budget]) => ({
        name, leads_budget: budget, leads_actual: 0, moveins_budget: BUDGET_TARGETS.moveins[name] || 0,
      })),
    });
  }
});

// ─── API: /api/gads/overview ──────────────────────────────────────────────────

app.get('/api/gads/overview', async (req, res) => {
  const range = req.query.range || '30d';
  const cacheKey = `gads-overview-${range}`;
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    const { dateRange, startDate, endDate } = gadsDateRange(range);
    const ga4DateR = ga4DateFromRange(range);

    const gadsArgs = {
      accountId: GADS_ACCOUNT_ID,
      dateRange,
      metrics: [
        'metrics.cost_micros',
        'metrics.clicks',
        'metrics.conversions',
        'metrics.all_conversions',
        'metrics.average_cpc',
      ],
    };
    if (dateRange === 'CUSTOM') {
      gadsArgs.startDate = startDate;
      gadsArgs.endDate = endDate;
    }

    // Fetch Google Ads totals + GA4 paid search bookings in parallel
    const [gadsResult, ga4TransReport, ga4CompleteReport] = await Promise.all([
      Promise.resolve(callTool('google_ads__pipedream', 'google_ads-create-customer-report', gadsArgs)),
      ga4RunReport({
        dateRanges: [{ startDate: ga4DateR.startDate, endDate: ga4DateR.endDate }],
        metrics: [{ name: 'eventCount' }],
        dimensionFilter: {
          andGroup: {
            expressions: [
              { filter: { fieldName: 'eventName', stringFilter: { value: 'transparent_booking' } } },
              {
                filter: {
                  fieldName: 'sessionDefaultChannelGrouping',
                  stringFilter: { value: 'Paid Search' },
                },
              },
            ],
          },
        },
      }),
      ga4RunReport({
        dateRanges: [{ startDate: ga4DateR.startDate, endDate: ga4DateR.endDate }],
        metrics: [{ name: 'eventCount' }],
        dimensionFilter: {
          andGroup: {
            expressions: [
              {
                filter: {
                  fieldName: 'eventName',
                  stringFilter: { value: 'bm_transparent_booking_complete' },
                },
              },
              {
                filter: {
                  fieldName: 'sessionDefaultChannelGrouping',
                  stringFilter: { value: 'Paid Search' },
                },
              },
            ],
          },
        },
      }),
    ]);

    // Aggregate Google Ads customer report (returns per-day rows, sum them)
    const gadsRows = gadsResult.results || [];
    let totalCostMicros = 0;
    let totalClicks = 0;
    let totalConversions = 0;
    let totalAllConversions = 0;
    let totalCpcSum = 0;
    let cpcCount = 0;

    gadsRows.forEach((row) => {
      const m = row.metrics || {};
      totalCostMicros += parseInt(m.costMicros || m.cost_micros || '0', 10);
      totalClicks += parseInt(m.clicks || '0', 10);
      totalConversions += parseFloat(m.conversions || '0');
      totalAllConversions += parseFloat(m.allConversions || m.all_conversions || '0');
      if (m.averageCpc || m.average_cpc) {
        totalCpcSum += parseFloat(m.averageCpc || m.average_cpc || '0');
        cpcCount++;
      }
    });

    const cost = Math.round(totalCostMicros / 1000) / 1000; // micros → euros (÷1,000,000 but we div by 1000 twice)
    const avgCpc = cpcCount > 0 ? Math.round(totalCpcSum / cpcCount / 1000) / 1000 : 0;
    const costPerConversion = totalConversions > 0
      ? Math.round((cost / totalConversions) * 100) / 100
      : 0;

    const transparentBookings = parseInt(parseGA4Rows(ga4TransReport)[0]?.eventCount || '0', 10);
    const bookingComplete = parseInt(parseGA4Rows(ga4CompleteReport)[0]?.eventCount || '0', 10);

    const result = {
      cost: Math.round(cost * 100) / 100,
      clicks: totalClicks,
      conversions: Math.round(totalConversions * 100) / 100,
      allConversions: Math.round(totalAllConversions * 100) / 100,
      avgCpc: Math.round(avgCpc * 100) / 100,
      costPerConversion,
      transparentBookings,
      bookingComplete,
    };

    cacheSet(cacheKey, result);
    res.json(result);
  } catch (err) {
    console.error('[/api/gads/overview]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─── API: /api/gads/campaigns ─────────────────────────────────────────────────

app.get('/api/gads/campaigns', async (req, res) => {
  const range = req.query.range || '30d';
  const cacheKey = `gads-campaigns-${range}`;
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    const { dateRange, startDate, endDate } = gadsDateRange(range);

    const gadsArgs = {
      accountId: GADS_ACCOUNT_ID,
      dateRange,
      fields: ['campaign.name', 'campaign.id'],
      metrics: [
        'metrics.cost_micros',
        'metrics.clicks',
        'metrics.conversions',
        'metrics.all_conversions',
        'metrics.average_cpc',
        'metrics.conversions_from_interactions_rate',
      ],
      orderBy: 'metrics.cost_micros',
      direction: 'DESC',
    };
    if (dateRange === 'CUSTOM') {
      gadsArgs.startDate = startDate;
      gadsArgs.endDate = endDate;
    }

    const gadsResult = callTool('google_ads__pipedream', 'google_ads-create-campaign-report', gadsArgs);
    const rows = gadsResult.results || [];

    // Aggregate daily rows per campaign
    const campaigns = {};
    rows.forEach((row) => {
      const name = row.campaign?.name || 'Unknown';
      const m = row.metrics || {};

      if (!campaigns[name]) {
        campaigns[name] = {
          name,
          cost: 0, clicks: 0, conversions: 0, allConversions: 0, avgCpcSum: 0, avgCpcCount: 0, convRateSum: 0, convRateCount: 0,
        };
      }
      const c = campaigns[name];
      c.cost += parseInt(m.costMicros || m.cost_micros || '0', 10);
      c.clicks += parseInt(m.clicks || '0', 10);
      c.conversions += parseFloat(m.conversions || '0');
      c.allConversions += parseFloat(m.allConversions || m.all_conversions || '0');
      if (m.averageCpc || m.average_cpc) {
        c.avgCpcSum += parseFloat(m.averageCpc || m.average_cpc || '0');
        c.avgCpcCount++;
      }
      if (m.conversionsFromInteractionsRate || m.conversions_from_interactions_rate) {
        c.convRateSum += parseFloat(m.conversionsFromInteractionsRate || m.conversions_from_interactions_rate || '0');
        c.convRateCount++;
      }
    });

    const result = Object.values(campaigns).map((c) => {
      const costEur = Math.round(c.cost / 10000) / 100; // micros → euros
      const convs = Math.round(c.conversions * 100) / 100;
      const avgCpc = c.avgCpcCount > 0
        ? Math.round(c.avgCpcSum / c.avgCpcCount / 10000) / 100
        : 0;
      const costPerConv = convs > 0 ? Math.round((costEur / convs) * 100) / 100 : 0;
      const convRate = c.convRateCount > 0
        ? Math.round((c.convRateSum / c.convRateCount) * 10000) / 100
        : 0;
      return {
        name: c.name,
        cost: costEur,
        clicks: c.clicks,
        conversions: convs,
        allConversions: Math.round(c.allConversions * 100) / 100,
        avgCpc,
        costPerConversion: costPerConv,
        convRate,
      };
    }).sort((a, b) => b.cost - a.cost);

    cacheSet(cacheKey, result);
    res.json(result);
  } catch (err) {
    console.error('[/api/gads/campaigns]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─── API: /api/gads/chart ─────────────────────────────────────────────────────

app.get('/api/gads/chart', async (req, res) => {
  const cacheKey = 'gads-chart';
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    // Last 3 calendar months + current month (partial)
    const now = new Date();
    const months = [];
    for (let i = 3; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const y = d.getFullYear();
      const m = String(d.getMonth() + 1).padStart(2, '0');
      const lastDay = i === 0 ? now : new Date(d.getFullYear(), d.getMonth() + 1, 0);
      months.push({
        label: d.toLocaleString('en-US', { month: 'short' }) + ' ' + String(y).slice(2),
        start: `${y}-${m}-01`,
        end: lastDay.toISOString().split('T')[0],
      });
    }

    // Fetch per month using date segments from Google Ads
    const gadsArgs = {
      accountId: GADS_ACCOUNT_ID,
      dateRange: 'CUSTOM',
      startDate: months[0].start,
      endDate: months[months.length - 1].end,
      segments: ['segments.date'],
      metrics: ['metrics.cost_micros', 'metrics.conversions'],
    };

    const gadsResult = callTool('google_ads__pipedream', 'google_ads-create-customer-report', gadsArgs);
    const rows = gadsResult.results || [];

    // Aggregate by month
    const monthAgg = {};
    months.forEach((mo) => { monthAgg[mo.label] = { cost: 0, conversions: 0 }; });

    rows.forEach((row) => {
      const date = row.segments?.date || '';
      if (!date) return;
      const d = new Date(date);
      const label = d.toLocaleString('en-US', { month: 'short' }) + ' ' + String(d.getFullYear()).slice(2);
      if (!monthAgg[label]) return;
      monthAgg[label].cost += parseInt(row.metrics?.costMicros || row.metrics?.cost_micros || '0', 10);
      monthAgg[label].conversions += parseFloat(row.metrics?.conversions || '0');
    });

    const labels = months.map((m) => m.label);
    const conversions = labels.map((l) => Math.round(monthAgg[l]?.conversions || 0));
    const cost = labels.map((l) => Math.round((monthAgg[l]?.cost || 0) / 1000000)); // micros → euros

    const result = { labels, conversions, cost };
    cacheSet(cacheKey, result);
    res.json(result);
  } catch (err) {
    console.error('[/api/gads/chart]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─── API: /api/clickup/tasks ──────────────────────────────────────────────────

app.get('/api/clickup/tasks', async (req, res) => {
  const cacheKey = 'clickup-tasks';
  const cached = cacheGet(cacheKey);
  if (cached) return res.json(cached);

  try {
    const result = callTool('clickup__pipedream', 'clickup-get-tasks', {
      workspaceId: CLICKUP_WORKSPACE_ID,
      spaceId: CLICKUP_SPACE_ID,
      listId: CLICKUP_LIST_ID,
      subtasks: true,
      includeClosed: true,
    });

    // result is a JSON string or array
    let tasks;
    if (typeof result === 'string') {
      tasks = JSON.parse(result);
    } else if (Array.isArray(result)) {
      tasks = result;
    } else if (result && Array.isArray(result.tasks)) {
      tasks = result.tasks;
    } else {
      tasks = result;
    }

    cacheSet(cacheKey, tasks);
    res.json(tasks);
  } catch (err) {
    console.error('[/api/clickup/tasks]', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ─── Health check ─────────────────────────────────────────────────────────────

app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// ─── Catch-all: serve index.html for non-API routes ──────────────────────────

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'index.html'));
});

// ─── Start server ─────────────────────────────────────────────────────────────

app.listen(PORT, () => {
  console.log(`1BOX Dashboard server running at http://localhost:${PORT}`);
});

module.exports = app;
