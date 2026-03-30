/**
 * Unit tests for the mock backend Express API.
 *
 * Validates: Req 8.1 (GET /api/vigilancia/topics returns 8 groups),
 *            Req 9.3 (GET /api/trendmap/meta returns metadata),
 *            Req 11.4 (CORS headers present in responses)
 */
const request = require("supertest");
const app = require("../server");

describe("Mock Backend API", () => {
  describe("GET /api/vigilancia/topics", () => {
    it("returns 8 topic groups", async () => {
      const res = await request(app).get("/api/vigilancia/topics");

      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty("topics");
      expect(res.body.topics).toHaveLength(8);

      // Verify all expected group_ids are present
      const groupIds = res.body.topics.map((t) => t.group_id);
      expect(groupIds).toEqual(
        expect.arrayContaining([
          "ia_ml",
          "blockchain",
          "ciberseguridad",
          "fintech",
          "regtech",
          "cloud",
          "datos",
          "banca_digital",
        ])
      );

      // Each topic should have display_name and term_count
      res.body.topics.forEach((topic) => {
        expect(topic).toHaveProperty("group_id");
        expect(topic).toHaveProperty("display_name");
        expect(topic).toHaveProperty("term_count");
        expect(typeof topic.display_name).toBe("string");
        expect(typeof topic.term_count).toBe("number");
      });
    });
  });

  describe("GET /api/trendmap/meta", () => {
    it("returns metadata with expected fields", async () => {
      const res = await request(app).get("/api/trendmap/meta");

      expect(res.status).toBe(200);
      expect(res.body).toHaveProperty("generated_at_utc");
      expect(res.body).toHaveProperty("source_counts");
      expect(res.body).toHaveProperty("date_range");
      expect(res.body).toHaveProperty("methodology");

      // source_counts structure
      expect(res.body.source_counts).toHaveProperty("news");
      expect(res.body.source_counts).toHaveProperty("papers");
      expect(res.body.source_counts).toHaveProperty("total");

      // date_range structure
      expect(res.body.date_range).toHaveProperty("min");
      expect(res.body.date_range).toHaveProperty("max");
    });
  });

  describe("CORS headers", () => {
    it("includes CORS headers in responses", async () => {
      const res = await request(app)
        .get("/api/vigilancia/topics")
        .set("Origin", "http://localhost:3000");

      expect(res.headers["access-control-allow-origin"]).toBe(
        "http://localhost:3000"
      );
    });

    it("responds to OPTIONS preflight with CORS headers", async () => {
      const res = await request(app)
        .options("/api/vigilancia/topics")
        .set("Origin", "http://localhost:3000")
        .set("Access-Control-Request-Method", "GET");

      expect(res.headers["access-control-allow-origin"]).toBe(
        "http://localhost:3000"
      );
    });
  });
});
