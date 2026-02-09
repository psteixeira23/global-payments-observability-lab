import http from "k6/http";
import { check } from "k6";
import { Counter, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8080";
const VUS = Number(__ENV.IDEMPOTENCY_VUS || 120);
const ITERATIONS = Number(__ENV.IDEMPOTENCY_ITERATIONS || 150);

const idempotencyLatency = new Trend("idempotency_collision_latency", true);
const samePaymentIdCounter = new Counter("idempotency_same_payment_id_total");
const mismatchPaymentIdCounter = new Counter("idempotency_mismatch_payment_id_total");

export const options = {
  scenarios: {
    idempotency_collision: {
      executor: "per-vu-iterations",
      vus: VUS,
      iterations: ITERATIONS,
      maxDuration: "10m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.02"],
    idempotency_collision_latency: ["p(95)<1200", "p(99)<2500"],
    idempotency_mismatch_payment_id_total: ["count==0"],
  },
};

function payloadFor(iteration) {
  return JSON.stringify({
    amount: 99.5,
    currency: "BRL",
    method: "PIX",
    destination: `dest-idem-collision-${iteration % 100}`,
  });
}

function postOnce(idempotencyKey, body) {
  const merchantId = `merchant-idem-${__VU % 50}`;
  const headers = {
    "Content-Type": "application/json",
    "Idempotency-Key": idempotencyKey,
    "X-Merchant-Id": merchantId,
    "X-Customer-Id": "customer-basic-001",
    "X-Account-Id": `account-idem-${__VU % 50}`,
  };
  return http.post(`${BASE_URL}/payments`, body, { headers: headers });
}

export default function () {
  const key = `collision-key-${Math.floor(__ITER / 2)}`;
  const body = payloadFor(__ITER);

  const first = postOnce(key, body);
  const second = postOnce(key, body);
  idempotencyLatency.add(first.timings.duration);
  idempotencyLatency.add(second.timings.duration);

  check(first, {
    "first idempotent call accepted": (r) => r.status === 202,
  });
  check(second, {
    "second idempotent call accepted": (r) => r.status === 202,
  });

  let firstBody = null;
  let secondBody = null;
  try {
    firstBody = first.json();
    secondBody = second.json();
  } catch (_) {
    firstBody = null;
    secondBody = null;
  }

  if (firstBody?.payment_id && secondBody?.payment_id && firstBody.payment_id === secondBody.payment_id) {
    samePaymentIdCounter.add(1);
  } else {
    mismatchPaymentIdCounter.add(1);
  }
}
