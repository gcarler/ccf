import { describe, it, expect } from "vitest";
import type { CourseItem, BookItem } from "./cursos";

describe("data/cursos — interfaces", () => {
  it("CourseItem: campos básicos", () => {
    const c: CourseItem = {
      id: "c1",
      tag: "Liderazgo",
      modality: "online",
      title: "Curso de Liderazgo",
      desc: "Aprende a liderar con propósito.",
      excerpt: "Curso intensivo",
      cta: "Inscribirme",
      lessons: 12,
      imageUrl: "/img.png",
      syllabus: ["Mod 1", "Mod 2"],
      instructor: "Pastor X",
    };
    expect(c.id).toBe("c1");
    expect(c.title).toBe("Curso de Liderazgo");
    expect(c.lessons).toBe(12);
    expect(c.syllabus?.length).toBe(2);
  });
  it("CourseItem: campos opcionales ausentes", () => {
    const c: CourseItem = { id: "c", title: "T", desc: "D" };
    expect(c.tag).toBeUndefined();
    expect(c.lessons).toBeUndefined();
  });
  it("BookItem: campos completos", () => {
    const b: BookItem = {
      id: "b1",
      title: "Título",
      author: "Autor",
      price: "$10",
      img: "/img.png",
      desc: "Un libro",
    };
    expect(b.id).toBe("b1");
    expect(b.price).toBe("$10");
  });
});
