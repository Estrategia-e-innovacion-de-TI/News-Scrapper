/**
 * Property-based tests for mock backend API endpoints.
 *
 * Feature: newsradar-frontend
 * Uses fast-check for property-based testing with 20 iterations for speed.
 */
const request = require("supertest");
const fc = require("fast-check");
const path = require("path");
const fs = require("fs");
const app = require("../server");

// ── Property 18: Search endpoints return valid structure with ≥5 results ──
// Feature: newsradar-frontend, Property 18: Search endpoints return valid structure
// Validates: Requirements 7.1, 7.2, 7.3

describe("P18: Search endpoints return valid structure with ≥5 results", () => {
  it("ARAS: for any valid search request, response has run_id, total_documents, total_classified, results (≥5), excel_url", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.record({
          company: fc.option(fc.string({ minLength: 1, maxLength: 30 }), { nil: undefined }),
          nit: fc.option(fc.string({ minLength: 1, maxLength: 15 }), { nil: undefined }),
          risk_category: fc.option(
            fc.constantFrom("Lavado de Activos", "Fraude", "Corrupción"),
            { nil: undefined }
          ),
        }).filter((r) => r.company !== undefined || r.nit !== undefined || r.risk_category !== undefined),
        async (body) => {
          const res = await request(app)
            .post("/api/aras/search")
            .send(body);

          expect(res.status).toBe(200);
          expect(res.body).toHaveProperty("run_id");
          expect(res.body).toHaveProperty("total_documents");
          expect(res.body).toHaveProperty("total_classified");
          expect(res.body).toHaveProperty("results");
          expect(res.body).toHaveProperty("excel_url");
          expect(res.body.results.length).toBeGreaterThanOrEqual(5);
          expect(typeof res.body.run_id).toBe("string");
        }
      ),
      { numRuns: 20 }
    );
  }, 30000);

  it("Riesgos: for any valid search request, response has run_id, total_documents, total_classified, results (≥5), excel_url", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.oneof(
          fc.record({
            terms: fc.string({ minLength: 1, maxLength: 30 }),
          }),
          fc.record({
            terms_preset: fc.constantFrom("ciber", "fraude", "operacional", "ambiental_social", "all"),
          })
        ),
        async (body) => {
          const res = await request(app)
            .post("/api/riesgos/search")
            .send(body);

          expect(res.status).toBe(200);
          expect(res.body).toHaveProperty("run_id");
          expect(res.body).toHaveProperty("total_documents");
          expect(res.body).toHaveProperty("total_classified");
          expect(res.body).toHaveProperty("results");
          expect(res.body).toHaveProperty("excel_url");
          expect(res.body.results.length).toBeGreaterThanOrEqual(5);
          expect(typeof res.body.run_id).toBe("string");
        }
      ),
      { numRuns: 20 }
    );
  }, 30000);
});

// ── Property 19: Empty search returns 400 ────────────────────────────
// Feature: newsradar-frontend, Property 19: Empty search returns 400
// Validates: Requirements 7.5

describe("P19: Empty search returns 400", () => {
  it("ARAS: for any request with no valid search fields, response is 400", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom({}, { company: "" }, { company: "", nit: "" }, { nit: null }),
        async (body) => {
          const res = await request(app)
            .post("/api/aras/search")
            .send(body);

          expect(res.status).toBe(400);
          expect(res.body).toHaveProperty("error");
        }
      ),
      { numRuns: 20 }
    );
  });

  it("Riesgos: for any request with no valid search fields, response is 400", async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.constantFrom({}, { terms: "" }, { terms: "", terms_preset: "" }, { terms_preset: null }),
        async (body) => {
          const res = await request(app)
            .post("/api/riesgos/search")
            .send(body);

          expect(res.status).toBe(400);
          expect(res.body).toHaveProperty("error");
        }
      ),
      { numRuns: 20 }
    );
  });
});

// ── Property 20: Invalid subscription returns 400 ────────────────────
// Feature: newsradar-frontend, Property 20: Invalid subscription returns 400
// Validates: Requirements 8.4, 8.5

describe("P20: Invalid subscription returns 400", () => {
  it("for any request with invalid email or empty query_groups, response is 400", async () => {
    const invalidPayloads = fc.oneof(
      // Invalid email format
      fc.record({
        email: fc.stringOf(fc.constantFrom("a", "b", "c", "1", "2"), { minLength: 1, maxLength: 10 }).filter((s) => !s.includes("@")),
        name: fc.string({ minLength: 1, maxLength: 20 }),
        query_groups: fc.array(fc.constantFrom("ia_ml", "blockchain"), { minLength: 1, maxLength: 3 }),
      }),
      // Empty query_groups
      fc.record({
        email: fc.constant("valid@example.com"),
        name: fc.string({ minLength: 1, maxLength: 20 }),
        query_groups: fc.constant([]),
      }),
      // Missing query_groups
      fc.record({
        email: fc.constant("valid@example.com"),
        name: fc.string({ minLength: 1, maxLength: 20 }),
      }),
      // Missing email
      fc.record({
        name: fc.string({ minLength: 1, maxLength: 20 }),
        query_groups: fc.array(fc.constantFrom("ia_ml"), { minLength: 1, maxLength: 2 }),
      })
    );

    await fc.assert(
      fc.asyncProperty(invalidPayloads, async (body) => {
        const res = await request(app)
          .post("/api/vigilancia/subscribe")
          .send(body);

        expect(res.status).toBe(400);
        expect(res.body).toHaveProperty("error");
      }),
      { numRuns: 20 }
    );
  });
});

// ── Property 21: Trendmap round-trip ─────────────────────────────────
// Feature: newsradar-frontend, Property 21: Trendmap round-trip
// Validates: Requirements 9.1, 9.2, 9.4

describe("P21: Trendmap round-trip", () => {
  it("data served by /api/trendmap/clusters matches trendmap.json file content", async () => {
    const trendmapPath = path.join(__dirname, "../../trendmap/data/trendmap.json");
    const fileContent = JSON.parse(fs.readFileSync(trendmapPath, "utf-8"));

    const res = await request(app).get("/api/trendmap/clusters");

    expect(res.status).toBe(200);
    expect(res.body).toEqual(fileContent);
  });

  it("data served by /api/trendmap/trends matches fresh_llm_analysis.json file content", async () => {
    const freshLlmPath = path.join(__dirname, "../../trendmap/data/fresh_llm_analysis.json");
    const fileContent = JSON.parse(fs.readFileSync(freshLlmPath, "utf-8"));

    const res = await request(app).get("/api/trendmap/trends");

    expect(res.status).toBe(200);
    expect(res.body).toEqual(fileContent);
  });
});

// ── Property 22: Subscription round-trip ─────────────────────────────
// Feature: newsradar-frontend, Property 22: Subscription round-trip
// Validates: Requirements 8.2, 8.3

describe("P22: Subscription round-trip", () => {
  it("for any valid subscription, the data persists in memory", async () => {
    const validSubscription = fc.record({
      email: fc.tuple(
        fc.stringOf(fc.constantFrom("a", "b", "c", "d", "e"), { minLength: 3, maxLength: 8 }),
        fc.constantFrom("@test.com", "@example.org", "@mail.co")
      ).map(([local, domain]) => local + domain),
      name: fc.string({ minLength: 1, maxLength: 30 }).filter((s) => s.trim().length > 0),
      query_groups: fc.array(
        fc.constantFrom("ia_ml", "blockchain", "ciberseguridad", "fintech", "regtech", "cloud", "datos", "banca_digital"),
        { minLength: 1, maxLength: 4 }
      ),
    });

    // Access the in-memory subscribers store
    const vigilanciaRouter = require("../routes/vigilancia");

    await fc.assert(
      fc.asyncProperty(validSubscription, async (sub) => {
        const beforeCount = vigilanciaRouter._subscribers.length;

        const res = await request(app)
          .post("/api/vigilancia/subscribe")
          .send(sub);

        expect(res.status).toBe(200);
        expect(res.body.status).toBe("ok");
        expect(res.body.email).toBe(sub.email);
        expect(res.body.subscribed_groups).toEqual(sub.query_groups);

        // Verify data persisted in memory
        const afterCount = vigilanciaRouter._subscribers.length;
        expect(afterCount).toBe(beforeCount + 1);

        const stored = vigilanciaRouter._subscribers[vigilanciaRouter._subscribers.length - 1];
        expect(stored.email).toBe(sub.email);
        expect(stored.name).toBe(sub.name.trim());
        expect(stored.query_groups).toEqual(sub.query_groups);
        expect(stored).toHaveProperty("subscribed_at");
      }),
      { numRuns: 20 }
    );
  });
});
