import { describe, expect, it } from "vitest";

import { formatCurrency, formatDate, formatPerMillion } from "./format";

describe("format", () => {
  describe("formatCurrency", () => {
    it("renders USD with 2 decimals by default", () => {
      expect(formatCurrency(12.5)).toMatch(/\$12\.50/);
    });
    it("handles zero", () => {
      expect(formatCurrency(0)).toMatch(/\$0\.00/);
    });
  });

  describe("formatPerMillion", () => {
    it("formats sub-cent prices with sufficient precision", () => {
      expect(formatPerMillion(0.15)).toMatch(/\$0\.15/);
    });
  });

  describe("formatDate", () => {
    it("returns a non-empty string for a valid ISO date", () => {
      expect(formatDate("2026-04-26T10:00:00Z")).not.toBe("");
    });
    it("returns em-dash for invalid input", () => {
      expect(formatDate("not-a-date")).toBe("—");
    });
  });
});
