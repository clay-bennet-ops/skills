#!/usr/bin/env node
/**
 * PointsYeah Hotel Search API Client
 * Reverse-engineered from pointsyeah.com frontend
 * 
 * Flow:
 *   1. Refresh Cognito tokens
 *   2. Encrypt search params with AES-CBC (same as flights - module 57577)
 *   3. POST to api.pointsyeah.com/v2/live/hotel/search (get hotel list)
 *   4. POST to api.pointsyeah.com/v2/live/hotel/offers (get pricing per program)
 * 
 * Usage:
 *   node pointsyeah-hotel-api.js --location "Miami" --checkin 2026-08-15 --checkout 2026-08-18
 *   node pointsyeah-hotel-api.js --location "Paris" --checkin 2026-08-16 --checkout 2026-08-20 --adults 2 --rooms 1
 */

const https = require('https');
const crypto = require('crypto');

// ---- CONFIG ----
const COGNITO_CLIENT_ID = '3im8jrentts1pguuouv5s57gfu';
const REFRESH_TOKEN = process.env.PY_REFRESH_TOKEN || 'eyJjdHkiOiJKV1QiLCJlbmMiOiJBMjU2R0NNIiwiYWxnIjoiUlNBLU9BRVAifQ.HWxA7WfwbSsGNunv4lby6BxLDa78mZ1wqu4P21fLPI0xiHLElaCfutolIgs3jyjZMz5fPrsZiLR-CeqP0_cXVjDk1QiMPM-HjjEU7Tk1W5vNeC0VkXhSUftM25YzSDnbl8JiHzAePk0OnD1422qqFx1-t6Z35cgYFmOrqQ7f6q0ym1hZdalepIi6r_BjRiFlasqS7pVMtY67Ff9iS_h9K8Ws2uVKByLLD9p9olgHl32mHoihvOLjGxHJTSDDeufMTazbvkYWIJFdRMWHrwjEirL0Yd6HFkPYxo9iJmKnLShjU3mRiENSj0tq2E75E-Wfts1JONiMatircTbxmyy-3A.PN03wLSuHC_KErTR.ntFBBreJp1ev05o281UzyHEPZHzLLfkMOyeigAsIlbxUMrTfl7VXwSF7-3TwFj1AHZMHo4V41lLjd61CmXugD5tFRv4AfZex-wQNjhHXeljuFYcVnKu0eoiOhByU40JgFZcA_ipkq_1rCsa7cHY_CZ0JtQtx786i0hPHne3Af6xJYalSyAWF932ywPYH_5hDce5h0Hrzj43YGfckXopdA8biKtb-tZB-K93scHQ4tlms54LThCjgisWFwvFOFCrEoiE1xPaZ41hz1WbAUF-2EG4NGC4kayzjftEw_dB8fa8IvHuRsR-h0cYVm_ZTChfa7AHycGkqtjpiUf1BrwWOVU7nMveOSq0hlcPSwlFHfm0-JsiQzfnyOXwICVXjixGUKo0jRKDtfmQjjK_aOAR5cVHjlZqqKgUCCu7qCce756NP_zPi4nD6Xotzt1T3ZRBNeIefXkPW8gFl3nx5Cv_4kG_Ri5BV2zJHUsuSrluTFIeWLLoXlt6JU_VNpaXQOFEyJ0pVkofoCWVcXWhdz8MSEV7qiwui-1kCamt5R0RGHUJF5nCvPKa_oX4AuMV2KboKiOTWHYwtqkm3Qj4814dVoZDQFp06NxFkHlDMUlTKoBYJvyPbE7f0F62q04IEvjH5N_OWJYTtOQPYGLA9Z7HgaG2jye-GFeTjEC9aG324CUv0CCA2kJr3b6w4Y_oq8jLqgCPQUFtInOLK306QZX9xSIhXra6isSRvlavBKMTWlRHjRZMUYX8IlHohKTRPe9iLCXV3u3nVRCGpodAYGmGwpng-dtLPXNnNihL82BTJ2aPYhhF3pWDgQ9fYKagqc2HMNkAyvck0puPaWJlAeRTrvnOZEuxPIjvZnSgRo1DZ1tdaiGpe8lp50AxZ3iuFpxoHcovbz6d2EePHvKA0emXzBDnuLLdmQWesrmXRccCHrJCL_zlg-ZTXPisDGbbbeSLB0c4ZLcjcQRsAjezK9U_eYh7BvxTGWVFfNLi_el5rfKQOnJ5z1dl4uH34_wYWhVbIW4YbBVjRR3FoJ6AK5auvqsLs8GxMC9pVjpuINj6xDILxcXyr1qrtChaWNKt1twgZVtUuPDOPaD_cV83EuA_x2eGrfeGB6AHYthUPzOcnlFLeS0R6RDFe57vR0COFWim356h6HReNVY1qDgAfazox87DGO78vosVqC08NOXu6uAblIkCGY60T9Wwvre1HFXUaK8TOw10YNNiUtLbwhxnkFkFFCVMAYRJCueQ6R1dxX1toVO_E7X2agjndxEEcT-NhjIjJBEppkl9wmyycdJi0WHaVvFVDkHHhHpueObbCSXk5NUg4BghrAs4mNg.kcPHDGIKeH5SqmrahFUePA';

const API_BASE = 'https://api.pointsyeah.com/v2/live';

// ---- HELPERS ----

function httpPost(url, headers, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const data = JSON.stringify(body);
    const opts = {
      hostname: u.hostname,
      path: u.pathname + u.search,
      method: 'POST',
      headers: { ...headers, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(data) }
    };
    const req = https.request(opts, res => {
      let b = '';
      res.on('data', d => b += d);
      res.on('end', () => {
        try { resolve(JSON.parse(b)); } catch { resolve(b); }
      });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

function httpGet(url, headers) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const opts = {
      hostname: u.hostname,
      path: u.pathname + u.search,
      method: 'GET',
      headers: { ...headers }
    };
    const req = https.request(opts, res => {
      let b = '';
      res.on('data', d => b += d);
      res.on('end', () => {
        try { resolve(JSON.parse(b)); } catch { resolve(b); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

async function refreshTokens() {
  const body = {
    AuthFlow: 'REFRESH_TOKEN_AUTH',
    ClientId: COGNITO_CLIENT_ID,
    AuthParameters: { REFRESH_TOKEN: REFRESH_TOKEN }
  };
  const result = await new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const opts = {
      hostname: 'cognito-idp.us-east-1.amazonaws.com',
      path: '/',
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-amz-json-1.1',
        'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
        'Content-Length': Buffer.byteLength(data)
      }
    };
    const req = https.request(opts, res => {
      let b = '';
      res.on('data', d => b += d);
      res.on('end', () => { try { resolve(JSON.parse(b)); } catch { resolve(b); } });
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
  if (!result.AuthenticationResult) throw new Error('Token refresh failed: ' + JSON.stringify(result));
  return result.AuthenticationResult;
}

function parseJwt(token) {
  const payload = token.split('.')[1];
  return JSON.parse(Buffer.from(payload, 'base64url').toString());
}

function encryptParams(params, parseKeySection = 'hJuaknzb') {
  const json = JSON.stringify(params);
  const keyB64 = 'LefjQ2pEXmiy/nNZvhJ43i8' + parseKeySection + 'YHYbn1hOuAgA=';
  const key = Buffer.from(keyB64, 'base64');
  const iv = Buffer.from('1020304050607080', 'utf8');
  const cipher = crypto.createCipheriv('aes-256-cbc', key, iv);
  let encrypted = cipher.update(json, 'utf8', 'base64');
  encrypted += cipher.final('base64');
  return encrypted;
}

async function getAuthContext() {
  const tokens = await refreshTokens();
  const idToken = tokens.IdToken;
  const claims = parseJwt(idToken);
  const pks = claims.jti && claims.jti.length > 0 ? claims.jti.slice(0, 8) : 'hJuaknzb';
  const uniqueKey = claims.email + '-' + Date.now();
  return { idToken, pks, uniqueKey, email: claims.email };
}

function buildEncryptedBody(params, pks) {
  return {
    data: encryptParams(params),
    encrypted: encryptParams(params, pks)
  };
}

// ---- AUTOCOMPLETE ----

async function autocomplete(query, auth) {
  const headers = { authorization: auth.idToken, 'Content-Type': 'application/json' };
  const result = await httpPost(API_BASE + '/hotel/autocomplete', headers, { query, limit: 5 });
  return result;
}

// ---- HOTEL SEARCH ----

async function searchHotels(opts) {
  const {
    location = 'Miami',
    latitude = null,
    longitude = null,
    destType = 'city',
    countryCode = 'us',
    checkin = '2026-08-15',
    checkout = '2026-08-18',
    adults = 2,
    children = 0,
    rooms = 1,
    distance = 30000,
  } = opts;

  process.stderr.write('Refreshing tokens...\n');
  const auth = await getAuthContext();
  
  // Step 1: Autocomplete to get location details (if lat/lng not provided)
  let loc = { value: location, label: location, latitude, longitude, dest_type: destType, country_code: countryCode, city: location, distance };
  
  if (!latitude || !longitude) {
    process.stderr.write(`Autocompleting "${location}"...\n`);
    const acResult = await autocomplete(location, auth);
    if (acResult && acResult.data && acResult.data.length > 0) {
      const first = acResult.data[0];
      loc = {
        value: first.value || first.label || location,
        label: first.label || location,
        latitude: first.latitude,
        longitude: first.longitude,
        dest_type: first.dest_type || destType,
        country_code: first.country_code || countryCode,
        city: first.city || location,
        distance
      };
      process.stderr.write(`Location: ${loc.label} (${loc.latitude}, ${loc.longitude})\n`);
    } else {
      process.stderr.write('Autocomplete returned no results, using raw location\n');
    }
  }

  // Step 2: Search for hotels
  const searchParams = {
    query: { ...loc, location: loc.value },
    checkin,
    checkout,
    guests: { adults, children },
    filter: {},
    room: rooms
  };

  process.stderr.write('Searching hotels...\n');
  const encBody = buildEncryptedBody(searchParams, auth.pks);
  const headers = { 'Content-Type': 'application/json', authorization: auth.idToken };
  const searchResult = await httpPost(API_BASE + '/hotel/search', headers, encBody);
  
  if (!searchResult.success || searchResult.code !== 0) {
    process.stderr.write('Search failed: ' + JSON.stringify(searchResult) + '\n');
    return null;
  }

  const hotels = searchResult.data?.hotels || searchResult.data || [];
  process.stderr.write(`Found ${hotels.length} hotels\n`);

  if (hotels.length === 0) return { searchParams: { location: loc.label, checkin, checkout, adults, rooms }, hotels: [] };

  // Step 3: Get offers (pricing) - batch by program
  const programGroups = {};
  for (const hotel of hotels) {
    const prog = hotel.program;
    if (!programGroups[prog]) programGroups[prog] = [];
    programGroups[prog].push(hotel);
  }

  process.stderr.write(`Fetching offers for ${Object.keys(programGroups).length} programs...\n`);
  
  const allOffers = [];
  const offerPromises = Object.entries(programGroups).map(async ([program, programHotels]) => {
    const offersParams = {
      hotels: programHotels.map(h => ({
        hotel_id: h.hotel_id,
        code: h.code,
        program: h.program,
        latitude: h.location?.latitude || h.latitude,
        longitude: h.location?.longitude || h.longitude,
        ota: (h.ota || []).map(o => ({ code: o.code, program: o.program })),
        corporate_code: ''
      })),
      checkin,
      checkout,
      guests: { adults, children: [] },
      rooms
    };

    const encOffer = buildEncryptedBody(offersParams, auth.pks);
    try {
      const result = await httpPost(API_BASE + '/hotel/offers', headers, encOffer);
      if (result.success && result.code === 0 && result.data?.hotels) {
        return result.data.hotels;
      }
      process.stderr.write(`  ${program}: ${result.success ? 'no results' : 'failed'}\n`);
      return [];
    } catch (e) {
      process.stderr.write(`  ${program}: error - ${e.message}\n`);
      return [];
    }
  });

  const offerResults = await Promise.all(offerPromises);
  for (const offerBatch of offerResults) {
    allOffers.push(...offerBatch);
  }

  process.stderr.write(`Got pricing for ${allOffers.length} hotels\n`);

  // Merge search results with offers
  const offerMap = new Map();
  for (const offer of allOffers) {
    offerMap.set(offer.hotel_id, offer);
  }

  const merged = hotels.map(h => {
    const offer = offerMap.get(h.hotel_id);
    const points = offer?.point_price?.points || null;
    const cash = offer?.cash_price?.price || null;
    const pointUrl = offer?.point_price?.url || null;
    const cashUrl = offer?.cash_price?.url || null;
    const soldout = offer?.point_price?.soldout || false;
    const roomType = offer?.point_price?.room_type_name || null;
    const otherPointPrices = (offer?.other_point_prices || []).map(p => ({
      points: p.points, type: p.room_type_name, soldout: p.soldout
    }));
    const otaPrices = (offer?.ota_prices || []).filter(o => o.price > 0).map(o => ({
      program: o.program, price: o.price, currency: o.currency, url: o.url, miles: o.earn_miles
    }));

    return {
      hotel_id: h.hotel_id,
      name: h.name,
      program: h.program,
      brand: h.brand,
      category: h.category || null,
      location: h.location,
      distance_km: h.distance || null,
      image: h.image,
      points,
      cash,
      cpp: points && cash ? (cash / points * 100).toFixed(2) : null,
      soldout,
      roomType,
      otherPointPrices,
      otaPrices,
      pointUrl,
      cashUrl,
      available: offer && !soldout && points ? true : false,
    };
  });

  // Sort by CPP descending (best value first)
  merged.sort((a, b) => {
    if (!a.cpp && !b.cpp) return 0;
    if (!a.cpp) return 1;
    if (!b.cpp) return -1;
    return parseFloat(b.cpp) - parseFloat(a.cpp);
  });

  return { searchParams: { location: loc.label, checkin, checkout, adults, rooms }, hotels: merged };
}

// ---- CLI ----

async function main() {
  const args = process.argv.slice(2);
  const opts = {};
  
  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--location': opts.location = args[++i]; break;
      case '--checkin': opts.checkin = args[++i]; break;
      case '--checkout': opts.checkout = args[++i]; break;
      case '--adults': opts.adults = parseInt(args[++i]); break;
      case '--children': opts.children = parseInt(args[++i]); break;
      case '--rooms': opts.rooms = parseInt(args[++i]); break;
      case '--lat': opts.latitude = parseFloat(args[++i]); break;
      case '--lng': opts.longitude = parseFloat(args[++i]); break;
      case '--json': opts.jsonOutput = true; break;
      case '--help':
        console.log(`Usage: node pointsyeah-hotel-api.js [options]
  --location <city>     City/hotel/landmark name (required)
  --checkin <date>      Check-in date YYYY-MM-DD (required)
  --checkout <date>     Check-out date YYYY-MM-DD (required)
  --adults <n>          Number of adults (default: 2)
  --children <n>        Number of children (default: 0)
  --rooms <n>           Number of rooms (default: 1)
  --lat <lat>           Latitude (skip autocomplete)
  --lng <lng>           Longitude (skip autocomplete)
  --json                Output raw JSON`);
        process.exit(0);
    }
  }

  if (!opts.location) {
    console.error('Error: --location is required');
    process.exit(1);
  }
  if (!opts.checkin || !opts.checkout) {
    console.error('Error: --checkin and --checkout are required');
    process.exit(1);
  }

  try {
    const result = await searchHotels(opts);
    if (!result) {
      console.error('Search failed');
      process.exit(1);
    }

    if (opts.jsonOutput) {
      console.log(JSON.stringify(result, null, 2));
    } else {
      // Human-readable output
      const { searchParams: sp, hotels } = result;
      console.log(`\n🏨 Hotel Search: ${sp.location}`);
      console.log(`📅 ${sp.checkin} → ${sp.checkout} | ${sp.adults} adults | ${sp.rooms} room(s)`);
      console.log(`Found ${hotels.length} hotels\n`);

      const available = hotels.filter(h => h.available);
      const unavailable = hotels.filter(h => !h.available);

      if (available.length > 0) {
        console.log(`--- Available with points pricing (${available.length}) ---\n`);
        for (const h of available.slice(0, 30)) {
          const cat = h.category ? ` (Cat ${h.category})` : '';
          const dist = h.distance_km ? `${h.distance_km.toFixed(1)}km` : '';
          console.log(`${h.name}${cat} [${h.program}] ${dist}`);
          console.log(`  Points: ${h.points?.toLocaleString()}/night (${h.roomType || 'standard'}) | Cash: $${h.cash} | CPP: ${h.cpp}¢`);
          if (h.otherPointPrices?.length > 0) {
            const others = h.otherPointPrices.filter(p => !p.soldout).map(p => `${p.type}: ${p.points?.toLocaleString()}`).join(', ');
            if (others) console.log(`  Also: ${others}`);
          }
          if (h.otaPrices?.length > 0) {
            const otas = h.otaPrices.map(o => `${o.program}: $${o.price}`).join(', ');
            console.log(`  OTA: ${otas}`);
          }
          console.log('');
        }
      }

      if (unavailable.length > 0) {
        console.log(`\n--- Unavailable/no pricing (${unavailable.length}) ---`);
        for (const h of unavailable.slice(0, 10)) {
          console.log(`  ${h.name} [${h.program}] ${h.soldout ? '(sold out)' : ''}`);
        }
        if (unavailable.length > 10) console.log(`  ... and ${unavailable.length - 10} more`);
      }
    }
  } catch (e) {
    console.error('Error:', e.message);
    if (process.env.DEBUG) console.error(e.stack);
    process.exit(1);
  }
}

main();
