/**
 * Unit tests — FeedSection (tipo "feed").
 *
 * Cubre las 7 variantes (home, sermons, courses, testimonials, pastors,
 * events, locations) + fallback genérico, y protege la regresión de la
 * detección de variantes: los seeders guardan los feeds envueltos como
 * ``{content: "<json-string>"}``, así que la variante NO puede detectarse por
 * la presencia de la clave ``content`` (está en casi todos los feeds).
 */
import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { FeedSection } from "./media";
import { apiFetch } from "@/lib/http";
import { createMockCmsSection } from "@/test-utils/factories";
import type { CmsSection } from "@/types/cms-v2";
import type { FeedProps } from "@/types/cms-section-props";

// ── Mocks ────────────────────────────────────────────────────────────────────
vi.mock("@/lib/http", () => ({ apiFetch: vi.fn() }));
const mockedApiFetch = vi.mocked(apiFetch);

vi.mock("next/link", async () => {
  const ReactMock = await vi.importActual<typeof import("react")>("react");
  return {
    __esModule: true,
    default: ({
      href,
      children,
      ...rest
    }: {
      href: string;
      children: React.ReactNode;
    }) => ReactMock.createElement("a", { href, ...rest }, children),
  };
});

vi.mock("@/components/ui/OptimizedImage", async () => {
  const ReactMock = await vi.importActual<typeof import("react")>("react");
  return {
    __esModule: true,
    default: (props: { src?: string; alt?: string }) =>
      ReactMock.createElement("img", { src: props.src ?? "", alt: props.alt ?? "" }),
  };
});

// ── Helpers ──────────────────────────────────────────────────────────────────

function makeFeed(props: FeedProps | unknown[]): CmsSection<"feed"> {
  return {
    ...createMockCmsSection("feed"),
    section_key: "feed",
    props_json: props as unknown as CmsSection<"feed">["props_json"],
  };
}


// La caja de la variante sermons tiene texto completo distinto; se matchea por
// substring con regex para que las aserciones negativas no pasen trivialmente.
const YOUTUBE_BOX = /Biblioteca de videos desde YouTube/;

describe("FeedSection", () => {
  describe("Home feed (featured_card + cards)", () => {
    it("renders featured card, cards grid and newsletter", () => {
      const section = makeFeed({
        eyebrow: "Nuestra esencia",
        section_title: "Bienvenidos a Casa",
        section_description: "Rutas públicas para conocer la comunidad.",
        featured_card: {
          title: "Conocer a Jesús",
          desc: "Descubre la base de nuestra fe.",
          href: "/conocer-a-jesus",
          cta: "Empezar el camino",
          img: "/img/featured.jpg",
          alt: "Equipo pastoral",
        },
        cards: [
          { title: "Librería", desc: "Recursos para estudiar.", href: "/cursos", img: "/img/c1.jpg" },
          { title: "Horarios", desc: "Reuniones cada semana.", href: "/eventos" },
          { title: "Sedes", desc: "Encuéntranos en tu ciudad.", href: "/sedes" },
        ],
        newsletter_eyebrow: "Boletín semanal",
        newsletter_title: "¿Quieres recibir nuestras novedades?",
        newsletter_submit: "Suscribirme",
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Bienvenidos a Casa")).toBeDefined();
      expect(screen.getByText("Conocer a Jesús")).toBeDefined();
      expect(screen.getByText(/Empezar el camino/)).toBeDefined();
      expect(screen.getByText("Librería")).toBeDefined();
      expect(screen.getByText("Horarios")).toBeDefined();
      expect(screen.getByText("Sedes")).toBeDefined();
      expect(screen.getByText("¿Quieres recibir nuestras novedades?")).toBeDefined();
      // La variante home no debe renderizar la caja de YouTube de sermons.
      expect(screen.queryByText(YOUTUBE_BOX)).toBeNull();
    });
  });

  describe("Sermons feed (content envuelto en JSON)", () => {
    it("desenvuelve content y renderiza el hero + caja de YouTube", () => {
      const section = makeFeed({
        content: JSON.stringify({
          hero_eyebrow: "Ministerios CCF Oficial",
          hero_title_lead: "Prédicas &",
          hero_title_accent: "Mensajes",
          hero_description: "Alimento para el alma.",
          cta_label: "Ver todos en YouTube",
        }),
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Ministerios CCF Oficial")).toBeDefined();
      expect(screen.getByText("Prédicas &")).toBeDefined();
      expect(screen.getByText("Mensajes")).toBeDefined();
      expect(screen.getByText("Alimento para el alma.")).toBeDefined();
      expect(screen.getByText(YOUTUBE_BOX)).toBeDefined();
      expect(screen.getByText("Ver todos en YouTube")).toBeDefined();
    });

    it("soporta content como objeto (no solo string JSON)", () => {
      const section = makeFeed({
        content: {
          hero_eyebrow: "Ministerios CCF Oficial",
          hero_title_lead: "Prédicas &",
          hero_title_accent: "Mensajes",
        } as unknown as string,
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Ministerios CCF Oficial")).toBeDefined();
      expect(screen.getByText("Prédicas &")).toBeDefined();
    });
  });

  describe("Events feed (no debe caer en la variante sermons)", () => {
    it("renderiza la variante events con contenido envuelto en JSON", () => {
      const section = makeFeed({
        content: JSON.stringify({
          empty_title: "Esperando agenda desde el CMS",
          empty_description: "Cuando haya eventos reales publicados, aparecerán aquí.",
          no_events_title: "Sin eventos publicados",
          calendar_title: "Explora nuestro Calendario",
          calendar_description: "Organiza tu tiempo.",
        }),
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Esperando agenda desde el CMS")).toBeDefined();
      expect(screen.getByText("Explora nuestro Calendario")).toBeDefined();
      // Regresión BUG-1: la caja de YouTube pertenece a la variante sermons.
      expect(screen.queryByText(YOUTUBE_BOX)).toBeNull();
    });

    it("soporta props planos sin envolver (variante events)", () => {
      const section = makeFeed({
        empty_title: "Sin eventos publicados",
        no_events_title: "Sin eventos publicados",
        no_events_description: "Cuando el CMS publique eventos, aparecerán aquí.",
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Sin eventos publicados")).toBeDefined();
      expect(screen.queryByText(YOUTUBE_BOX)).toBeNull();
    });
  });

  describe("Testimonials feed (no debe caer en la variante sermons)", () => {
    it("renderiza la variante testimonials", () => {
      const section = makeFeed({
        content: JSON.stringify({
          hero_badge: "Impacto Real",
          hero_title_lead: "Historias de",
          hero_title_accent: "Transformación",
          hero_description: "Vidas reales, cambios reales.",
          cta_label: "Compartir mi historia",
        }),
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Impacto Real")).toBeDefined();
      expect(screen.getByText("Historias de")).toBeDefined();
      expect(screen.getByText("Transformación")).toBeDefined();
      expect(screen.queryByText(YOUTUBE_BOX)).toBeNull();
    });
  });

  describe("Pastors feed (no debe caer en la variante sermons)", () => {
    it("renderiza la variante pastors con campos repartidos al nivel superior", () => {
      // Mismo shape que ensure_public_cms_pastors: {content, **feed}.
      const feed = {
        hero_badge: "Conoce a nuestro equipo pastoral",
        hero_title: "Liderazgo Pastoral",
        hero_description: "Hombres y mujeres llamados por Dios.",
        loading_label: "Cargando...",
        empty_title: "No hay líderes pastorales registrados aún.",
        card_cta: "Conocer más",
        principal_label: "Pastor Principal",
      };
      const section = makeFeed({
        content: JSON.stringify(feed),
        ...feed,
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Conoce a nuestro equipo pastoral")).toBeDefined();
      expect(screen.getByText("Liderazgo Pastoral")).toBeDefined();
      expect(screen.queryByText(YOUTUBE_BOX)).toBeNull();
    });
  });

  describe("Courses feed", () => {
    it("renderiza hero de imagen + grid de cta_images", () => {
      const section = makeFeed({
        courses_title: "Cursos & Academia",
        courses_description: "Formación teológica y práctica.",
        hero_image_url: "/img/hero-cursos.jpg",
        cta_images: [
          { src: "/img/academia1.jpg", alt: "Estudio" },
          { src: "/img/academia2.jpg", alt: "Librería" },
        ],
      });

      const { container } = render(<FeedSection section={section} />);

      expect(screen.getByText("Cursos & Academia")).toBeDefined();
      expect(screen.getByText("Formación teológica y práctica.")).toBeDefined();
      const images = container.querySelectorAll("img");
      expect(images.length).toBeGreaterThanOrEqual(3); // hero + 2 cta_images
      expect(screen.queryByText(YOUTUBE_BOX)).toBeNull();
    });
  });

  describe("Merge de unwrapFeedProps (top-level gana sobre content interno)", () => {
    it("da prioridad a los campos del nivel superior", () => {
      const section = makeFeed({
        content: JSON.stringify({
          hero_badge: "Badge interno",
          hero_title: "Título interno",
          hero_description: "Descripción interna.",
        }),
        hero_badge: "Badge del nivel superior",
        hero_title: "Título del nivel superior",
        card_cta: "Conocer más",
      });

      render(<FeedSection section={section} />);

      // El merge debe resolver el campo al nivel superior (shape de
      // ensure_public_cms_pastors: {content, **feed}).
      expect(screen.getByText("Título del nivel superior")).toBeDefined();
      expect(screen.getByText("Badge del nivel superior")).toBeDefined();
      expect(screen.queryByText("Título interno")).toBeNull();
      expect(screen.queryByText("Badge interno")).toBeNull();
    });
  });

  describe("Pastors grid feed (section_key='pastors' con lista real)", () => {
    it("renderiza el grid del equipo pastoral desde la clave pastors", () => {
      const section = makeFeed({
        content: JSON.stringify({
          pastors: [
            { slug: "luis-ricardo-meza", name: "Luis Ricardo Meza", role: "Pastor Principal" },
            { slug: "martina-herrera", name: "Martina Herrera", role: "Pastora Fundadora" },
          ],
        }),
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Luis Ricardo Meza")).toBeDefined();
      expect(screen.getByText("Pastor Principal")).toBeDefined();
      expect(screen.getByText("Martina Herrera")).toBeDefined();
      // No debe caer en la caja de YouTube de sermons.
      expect(screen.queryByText(YOUTUBE_BOX)).toBeNull();
    });
  });

  describe("Locations feed (BUG-2: antes renderizaba vacío)", () => {
    it("renderiza la lista de sedes cuando props_json es un array plano", () => {
      const section = makeFeed([
        { name: "Sede Central", address: "Barranquilla, Colombia", phone: "+57 300 000 0000", schedule: "Domingos 9 AM" },
        { name: "Campus Norte", address: "Norte de Barranquilla", schedule: "Domingos 10 AM" },
      ]);

      render(<FeedSection section={section} />);

      expect(screen.getByText("Sede Central")).toBeDefined();
      expect(screen.getByText("Campus Norte")).toBeDefined();
      expect(screen.getByText("Barranquilla, Colombia")).toBeDefined();
      expect(screen.queryByText(YOUTUBE_BOX)).toBeNull();
    });

    it("renderiza la lista de sedes cuando vienen en items", () => {
      const section = makeFeed({
        items: [
          { name: "Sede Central", address: "Barranquilla, Colombia", schedule: "Domingos 9 AM" },
          { name: "Campus Sur", address: "Sur de Barranquilla" },
        ],
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Sede Central")).toBeDefined();
      expect(screen.getByText("Campus Sur")).toBeDefined();
    });
  });

  describe("Newsletter form (envío real + éxito/error)", () => {
    beforeEach(() => {
      mockedApiFetch.mockReset();
    });

    it("renderiza el formulario en un feed solo-newsletter y envía con site_key ccf", async () => {
      mockedApiFetch.mockResolvedValue({ success: true });
      // Sin featured_card/cards: newsletter_title activa la variante home y el
      // bloque del boletín debe renderizarse igualmente.
      const section = makeFeed({
        newsletter_title: "Boletín semanal",
        newsletter_submit: "Suscribirme",
        newsletter_placeholder: "Tu correo",
      });

      render(<FeedSection section={section} />);

      fireEvent.change(screen.getByRole("textbox", { name: /correo electrónico/i }), {
        target: { value: "usuario@example.com" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Suscribirme" }));

      await waitFor(() => {
        expect(mockedApiFetch).toHaveBeenCalledWith("/cms/v2/public/subscribe", {
          method: "POST",
          body: { site_key: "ccf", email: "usuario@example.com" },
          silent: true,
        });
      });
    });

    it("muestra el estado de éxito con los textos configurados y oculta el formulario", async () => {
      mockedApiFetch.mockResolvedValue({ success: true });
      const section = makeFeed({
        newsletter_title: "Boletín semanal",
        newsletter_submit: "Suscribirme",
        newsletter_success_title: "¡Listo! Revisa tu bandeja.",
        newsletter_success_desc: "Te enviamos un correo de confirmación.",
      });

      render(<FeedSection section={section} />);

      fireEvent.change(screen.getByRole("textbox", { name: /correo electrónico/i }), {
        target: { value: "usuario@example.com" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Suscribirme" }));

      expect(await screen.findByText("¡Listo! Revisa tu bandeja.")).toBeDefined();
      expect(screen.getByText("Te enviamos un correo de confirmación.")).toBeDefined();
      expect(screen.queryByRole("button", { name: "Suscribirme" })).toBeNull();
    });

    it("muestra error inline y conserva el formulario para reintentar", async () => {
      mockedApiFetch.mockRejectedValue(new Error("red caída"));
      const section = makeFeed({
        newsletter_title: "Boletín semanal",
        newsletter_submit: "Suscribirme",
      });

      render(<FeedSection section={section} />);

      fireEvent.change(screen.getByRole("textbox", { name: /correo electrónico/i }), {
        target: { value: "usuario@example.com" },
      });
      fireEvent.click(screen.getByRole("button", { name: "Suscribirme" }));

      expect(await screen.findByText(/No se pudo suscribir/)).toBeDefined();
      expect(screen.getByRole("button", { name: "Suscribirme" })).toBeDefined();
    });
  });

  describe("Fallback genérico", () => {
    it("renderiza title/body + tarjetas de items sin exponer JSON crudo", () => {
      const section = makeFeed({
        title: "Título genérico",
        body: "Descripción genérica.",
        items: [{ title: "Item 1", body: "Detalle 1" }],
      });

      render(<FeedSection section={section} />);

      expect(screen.getByText("Título genérico")).toBeDefined();
      expect(screen.getByText("Descripción genérica.")).toBeDefined();
      expect(screen.getByText("Item 1")).toBeDefined();
      expect(screen.getByText("Detalle 1")).toBeDefined();
      // No debe aparecer JSON crudo en el DOM público.
      expect(screen.queryByText(/{"title"/)).toBeNull();
    });

    it("muestra estado vacío cuando no hay contenido", () => {
      const section = makeFeed({});

      render(<FeedSection section={section} />);

      expect(screen.getByText("Sección sin contenido configurado.")).toBeDefined();
    });
  });
});
