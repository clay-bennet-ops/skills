#!/usr/bin/env node
/**
 * PointsYeah Flight Search API Client
 * Reverse-engineered from pointsyeah.com frontend
 * 
 * Flow: 
 *   1. Refresh Cognito tokens
 *   2. Encrypt search params with AES-CBC
 *   3. POST to api2.pointsyeah.com/flight/search/create_task
 *   4. Poll api2.pointsyeah.com/flight/search/fetch_result
 */

const https = require('https');
const crypto = require('crypto');

// ---- CONFIG ----
const COGNITO_CLIENT_ID = '3im8jrentts1pguuouv5s57gfu';
const REFRESH_TOKEN = process.env.PY_REFRESH_TOKEN || 'eyJjdHkiOiJKV1QiLCJlbmMiOiJBMjU2R0NNIiwiYWxnIjoiUlNBLU9BRVAifQ.HWxA7WfwbSsGNunv4lby6BxLDa78mZ1wqu4P21fLPI0xiHLElaCfutolIgs3jyjZMz5fPrsZiLR-CeqP0_cXVjDk1QiMPM-HjjEU7Tk1W5vNeC0VkXhSUftM25YzSDnbl8JiHzAePk0OnD1422qqFx1-t6Z35cgYFmOrqQ7f6q0ym1hZdalepIi6r_BjRiFlasqS7pVMtY67Ff9iS_h9K8Ws2uVKByLLD9p9olgHl32mHoihvOLjGxHJTSDDeufMTazbvkYWIJFdRMWHrwjEirL0Yd6HFkPYxo9iJmKnLShjU3mRiENSj0tq2E75E-Wfts1JONiMatircTbxmyy-3A.PN03wLSuHC_KErTR.ntFBBreJp1ev05o281UzyHEPZHzLLfkMOyeigAsIlbxUMrTfl7VXwSF7-3TwFj1AHZMHo4V41lLjd61CmXugD5tFRv4AfZex-wQNjhHXeljuFYcVnKu0eoiOhByU40JgFZcA_ipkq_1rCsa7cHY_CZ0JtQtx786i0hPHne3Af6xJYalSyAWF932ywPYH_5hDce5h0Hrzj43YGfckXopdA8biKtb-tZB-K93scHQ4tlms54LThCjgisWFwvFOFCrEoiE1xPaZ41hz1WbAUF-2EG4NGC4kayzjftEw_dB8fa8IvHuRsR-h0cYVm_ZTChfa7AHycGkqtjpiUf1BrwWOVU7nMveOSq0hlcPSwlFHfm0-JsiQzfnyOXwICVXjixGUKo0jRKDtfmQjjK_aOAR5cVHjlZqqKgUCCu7qCce756NP_zPi4nD6Xotzt1T3ZRBNeIefXkPW8gFl3nx5Cv_4kG_Ri5BV2zJHUsuSrluTFIeWLLoXlt6JU_VNpaXQOFEyJ0pVkofoCWVcXWhdz8MSEV7qiwui-1kCamt5R0RGHUJF5nCvPKa_oX4AuMV2KboKiOTWHYwtqkm3Qj4814dVoZDQFp06NxFkHlDMUlTKoBYJvyPbE7f0F62q04IEvjH5N_OWJYTtOQPYGLA9Z7HgaG2jye-GFeTjEC9aG324CUv0CCA2kJr3b6w4Y_oq8jLqgCPQUFtInOLK306QZX9xSIhXra6isSRvlavBKMTWlRHjRZMUYX8IlHohKTRPe9iLCXV3u3nVRCGpodAYGmGwpng-dtLPXNnNihL82BTJ2aPYhhF3pWDgQ9fYKagqc2HMNkAyvck0puPaWJlAeRTrvnOZEuxPIjvZnSgRo1DZ1tdaiGpe8lp50AxZ3iuFpxoHcovbz6d2EePHvKA0emXzBDnuLLdmQWesrmXRccCHrJCL_zlg-ZTXPisDGbbbeSLB0c4ZLcjcQRsAjezK9U_eYh7BvxTGWVFfNLi_el5rfKQOnJ5z1dl4uH34_wYWhVbIW4YbBVjRR3FoJ6AK5auvqsLs8GxMC9pVjpuINj6xDILxcXyr1qrtChaWNKt1twgZVtUuPDOPaD_cV83EuA_x2eGrfeGB6AHYthUPzOcnlFLeS0R6RDFe57vR0COFWim356h6HReNVY1qDgAfazox87DGO78vosVqC08NOXu6uAblIkCGY60T9Wwvre1HFXUaK8TOw10YNNiUtLbwhxnkFkFFCVMAYRJCueQ6R1dxX1toVO_E7X2agjndxEEcT-NhjIjJBEppkl9wmyycdJi0WHaVvFVDkHHhHpueObbCSXk5NUg4BghrAs4mNg.kcPHDGIKeH5SqmrahFUePA';

// ---- HELPERS ----

function httpPost(url, headers, body) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const data = JSON.stringify(body);
    const opts = {
      hostname: u.hostname,
      path: u.pathname,
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

async function refreshTokens() {
  const body = {
    AuthFlow: 'REFRESH_TOKEN_AUTH',
    ClientId: COGNITO_CLIENT_ID,
    AuthParameters: { REFRESH_TOKEN: REFRESH_TOKEN }
  };
  // Can't use httpPost because it overwrites Content-Type
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
  // Key: Base64 decode of "LefjQ2pEXmiy/nNZvhJ43i8" + parseKeySection + "YHYbn1hOuAgA="
  const keyB64 = 'LefjQ2pEXmiy/nNZvhJ43i8' + parseKeySection + 'YHYbn1hOuAgA=';
  const key = Buffer.from(keyB64, 'base64');
  const iv = Buffer.from('1020304050607080', 'utf8');
  
  const cipher = crypto.createCipheriv('aes-256-cbc', key, iv);
  let encrypted = cipher.update(json, 'utf8', 'base64');
  encrypted += cipher.final('base64');
  return encrypted;
}

// ---- MAIN SEARCH ----

async function searchFlights(opts) {
  const {
    departure = 'JFK',
    arrival = 'CDG', 
    departDate = '2026-08-15',
    departDateTo = null,
    cabins = ['Business'],
    adults = 1,
    children = 0,
    banks = ['Chase', 'Bilt'],
    airlines = ['KL', 'AF', 'AS', 'AA', 'DL', 'UA']
  } = opts;

  const endDate = departDateTo || departDate;
  const dateLabel = departDateTo ? `${departDate} to ${departDateTo}` : departDate;
  console.log(`🔎 Searching: ${departure} → ${arrival} on ${dateLabel} (${cabins.join(', ')})`);

  // Step 1: Get fresh tokens
  console.log('🔑 Refreshing auth tokens...');
  const tokens = await refreshTokens();
  const idToken = tokens.IdToken;
  const payload = parseJwt(idToken);
  
  // parseKeySection = first 8 chars of jti
  const parseKeySection = payload.jti && payload.jti.length > 0 ? payload.jti.slice(0, 8) : 'hJuaknzb';
  
  const headers = {
    authorization: idToken,
    origin: 'https://www.pointsyeah.com',
    referer: 'https://www.pointsyeah.com/'
  };

  // Step 2: Build search params (exact format from browser)
  const searchParams = {
    search_type: 'one_way',
    cabins,
    segments: [{
      arrival,
      departure,
      departure_date: { from: departDate, to: endDate }
    }],
    passengers_v2: { adults, children },
    source: 'pc'
  };

  // Step 3: Encrypt and create task
  const data = encryptParams(searchParams);
  const encrypted = encryptParams(searchParams, parseKeySection);
  
  console.log('📤 Creating search task...');
  const taskResult = await httpPost('https://api2.pointsyeah.com/flight/search/create_task', headers, {
    data,
    encrypted
  });
  
  console.log('Task response:', JSON.stringify(taskResult).substring(0, 500));
  
  if (!taskResult || taskResult.error) {
    throw new Error('create_task failed: ' + JSON.stringify(taskResult));
  }

  // Step 4: Poll for results using task_id
  const taskId = taskResult.data.task_id;
  console.log(`⏳ Polling for results (task: ${taskId}, ${taskResult.data.total_sub_tasks} sub-tasks)...`);
  let attempts = 0;
  const maxAttempts = 60;
  let allResults = [];
  
  while (attempts < maxAttempts) {
    attempts++;
    await new Promise(r => setTimeout(r, 3000));
    
    const result = await httpPost('https://api2.pointsyeah.com/flight/search/fetch_result', headers, { task_id: taskId });
    
    if (result.success && result.data) {
      const { result: flights, status } = result.data;
      if (flights && flights.length > 0) {
        allResults = allResults.concat(flights);
        console.log(`  Poll ${attempts}: +${flights.length} flights (total: ${allResults.length}), status=${status}`);
      } else {
        console.log(`  Poll ${attempts}: status=${status}`);
      }
      
      if (status === 'done' || status === 'completed') {
        console.log(`✅ Search completed after ${attempts} polls, ${allResults.length} total results`);
        return allResults;
      }
    } else {
      console.log(`  Poll ${attempts}: ${JSON.stringify(result).substring(0, 200)}`);
    }
  }
  
  if (allResults.length > 0) {
    console.log(`⚠️ Timed out but got ${allResults.length} partial results`);
    return allResults;
  }
  throw new Error('Search timed out after ' + maxAttempts + ' attempts');
}

// ---- CLI ----
async function main() {
  const args = process.argv.slice(2);
  const opts = {};
  
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i].replace('--', '');
    const val = args[i + 1];
    if (key === 'departDateTo') {
      opts.departDateTo = val;
    } else if (key === 'cabins' || key === 'banks' || key === 'airlines') {
      opts[key] = val.split(',');
    } else if (key === 'adults' || key === 'children') {
      opts[key] = parseInt(val);
    } else {
      opts[key] = val;
    }
  }
  
  try {
    const results = await searchFlights(opts);
    console.log('\n📊 Results:');
    console.log(JSON.stringify(results, null, 2));
  } catch (err) {
    console.error('❌ Error:', err.message);
    process.exit(1);
  }
}

main();
