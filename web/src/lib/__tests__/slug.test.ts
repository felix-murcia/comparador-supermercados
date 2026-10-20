import { describe, expect, it } from "vitest";

import { aSlug } from "@/lib/slug";

describe("aSlug", () => {
  it("lowercase, quita tildes y une con guiones", () => {
    expect(aSlug("Leche Entera Pascual 1L")).toBe("leche-entera-pascual-1l");
    expect(aSlug("Jamón de York")).toBe("jamon-de-york");
  });

  it("recorta los guiones sobrantes", () => {
    expect(aSlug("  Leche  ")).toBe("leche");
  });
});
