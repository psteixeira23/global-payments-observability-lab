import http from "k6/http";
import { check } from "k6";
import { Counter, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8080";
const TARGET_RPS = Number(__ENV.TARGET_RPS || 200);
const TEST_DURATION = __ENV.TEST_DURATION || "2m";
const PREALLOCATED_VUS = Number(__ENV.PREALLOCATED_VUS || Math.max(300, TARGET_RPS));
const MAX_VUS = Number(__ENV.MAX_VUS || Math.max(PREALLOCATED_VUS * 2, TARGET_RPS * 3));
const STATUS_QUERY_RATIO = Number(__ENV.STATUS_QUERY_RATIO || 0.1);
const DESTINATION_BLOCK_RATIO = Number(__ENV.DESTINATION_BLOCK_RATIO || 0.01);

const paymentCreateLatency = new Trend("payment_create_latency", true);
const paymentStatusLatency = new Trend("payment_status_query_latency", true);

const allowCounter = new Counter("payment_allow_total");
const blockedCounter = new Counter("payment_blocked_total");
const reviewCounter = new Counter("payment_review_total");
const rateLimitedCounter = new Counter("payment_rate_limited_total");
const validationErrorCounter = new Counter("payment_validation_error_total");
const serverErrorCounter = new Counter("payment_server_error_total");

export const options = {
  scenarios: {
    mixed_rails: {
      executor: "constant-arrival-rate",
      rate: TARGET_RPS,
      timeUnit: "1s",
      duration: TEST_DURATION,
      preAllocatedVUs: PREALLOCATED_VUS,
      maxVUs: MAX_VUS,
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.03"],
    http_req_duration: ["p(95)<1500", "p(99)<3000"],
    payment_create_latency: ["p(95)<1200", "p(99)<2500"],
    payment_status_query_latency: ["p(95)<800", "p(99)<1500"],
  },
};

const railConfig = [
  { method: "PIX", weight: 65, min: 5, max: 4800 },
  { method: "BOLETO", weight: 20, min: 10, max: 9000 },
  { method: "TED", weight: 10, min: 80, max: 19000 },
  { method: "CARD", weight: 5, min: 2, max: 7000 },
];

function chooseRail() {
  const ticket = Math.random() * 100;
  let cumulativeWeight = 0;
  for (const option of railConfig) {
    cumulativeWeight += option.weight;
    if (ticket <= cumulativeWeight) {
      return option;
    }
  }
  return railConfig[0];
}

function randomAmount(min, max) {
  return Math.round((min + Math.random() * (max - min)) * 100) / 100;
}

function destinationFor(iteration) {
  if (Math.random() < DESTINATION_BLOCK_RATIO) {
    return "dest-blocked-001";
  }
  return `dest-${__VU}-${iteration % 1000}`;
}

function customerFor(method, iteration) {
  if (method === "TED") {
    return iteration % 10 === 0 ? "customer-basic-001" : "customer-full-001";
  }
  return iteration % 20 === 0 ? "customer-none-001" : "customer-basic-001";
}

function classifyResponse(status, body) {
  if (status === 202 && body?.status === "BLOCKED") {
    blockedCounter.add(1);
    return;
  }
  if (status === 202 && body?.status === "IN_REVIEW") {
    reviewCounter.add(1);
    return;
  }
  if (status === 202) {
    allowCounter.add(1);
    return;
  }
  if (status === 429) {
    rateLimitedCounter.add(1);
    return;
  }
  if (status === 422 || status === 400 || status === 403) {
    validationErrorCounter.add(1);
    return;
  }
  if (status >= 500) {
    serverErrorCounter.add(1);
  }
}

function buildHeaders(method, iteration) {
  const merchantId = `merchant-${(iteration % 200) + 1}`;
  const customerId = customerFor(method, iteration);
  return {
    "Content-Type": "application/json",
    "Idempotency-Key": `k6-${method}-${__VU}-${iteration}`,
    "X-Merchant-Id": merchantId,
    "X-Customer-Id": customerId,
    "X-Account-Id": `account-${(iteration % 500) + 1}`,
  };
}

export default function () {
  const rail = chooseRail();
  const amount = randomAmount(rail.min, rail.max);
  const body = JSON.stringify({
    amount: amount,
    currency: "BRL",
    method: rail.method,
    destination: destinationFor(__ITER),
  });
  const headers = buildHeaders(rail.method, __ITER);

  const response = http.post(`${BASE_URL}/payments`, body, { headers: headers });
  paymentCreateLatency.add(response.timings.duration);

  let parsed = null;
  try {
    parsed = response.json();
  } catch (_) {
    parsed = null;
  }

  classifyResponse(response.status, parsed);
  check(response, {
    "payment request accepted or controlled reject": (r) =>
      r.status === 202 || r.status === 403 || r.status === 422 || r.status === 429,
  });

  if (parsed?.payment_id && Math.random() < STATUS_QUERY_RATIO) {
    const statusResponse = http.get(`${BASE_URL}/payments/${parsed.payment_id}`);
    paymentStatusLatency.add(statusResponse.timings.duration);
    check(statusResponse, {
      "status endpoint returns 200": (r) => r.status === 200,
    });
  }
}
