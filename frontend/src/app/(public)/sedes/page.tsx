"use client";

import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import SedeDetailDrawer, { SedeDetailItem } from "@/components/public/SedeDetailDrawer";
import { AnimatePresence, motion } from "framer-motion";
import {
  Calendar,
  Clock,
  Home,
  Navigation,
  Phone,
  Search,
  MapPin,
  ExternalLink,
  Copy,
  Check,
  Building2,
  Globe,
  User,
  Map,
  List,
  ChevronRight,
  Sparkles,
  Info,
} from "lucide-react";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

interface LocationItem extends SedeDetailItem {
  services?: string[];
}

export default function SedesPage() {
  const heroPage = useCmsV2Page("locations");
  const heroContent = heroPage?.blocks?.hero as Record<string, unknown> | undefined;
  const locationsContent = heroPage?.blocks?.feed as Record<string, unknown> | undefined;

  const mapEmbedUrl = typeof heroContent?.map_embed_url === "string" ? heroContent.map_embed_url : "";
  const mainBadge = typeof heroContent?.main_badge === "string" ? heroContent.main_badge : "Sede Principal";
  const emptyLocations =
    typeof heroContent?.empty_locations === "string"
      ? heroContent.empty_locations
      : "No hay sedes registradas en este momento.";
  const emptySearch =
    typeof heroContent?.empty_search === "string"
      ? heroContent.empty_search
      : "No encontramos sedes que coincidan con los filtros aplicados.";
  const eyebrow = typeof heroContent?.eyebrow === "string" ? heroContent.eyebrow : "Nuestra Presencia";
  const titleLead = typeof heroContent?.title_lead === "string" ? heroContent.title_lead : "Nuestras";
  const titleAccent = typeof heroContent?.title_accent === "string" ? heroContent.title_accent : "Sedes";
  const title = typeof heroContent?.title === "string" ? heroContent.title : `${titleLead} ${titleAccent}`;
  const searchPlaceholder =
    typeof heroContent?.search_placeholder === "string"
      ? heroContent.search_placeholder
      : "Buscar por nombre, barrio, pastor...";

  const rawLocations = (locationsContent?.parsed ?? locationsContent) as unknown;
  const parsedLocations: LocationItem[] = Array.isArray(rawLocations)
    ? (rawLocations as LocationItem[])
    : Array.isArray((rawLocations as Record<string, unknown>)?.items)
    ? ((rawLocations as Record<string, unknown>).items as LocationItem[])
    : [];

  const locations: LocationItem[] = useMemo(() => {
    return parsedLocations.map((loc, i) => {
      const schedule =
        loc.schedule ||
        (Array.isArray(loc.services) && loc.services.length > 0 ? loc.services.join(" • ") : "") ||
        "Domingos 8:00 AM y 10:30 AM";
      const midweek = loc.midweek || "Miércoles 7:00 PM (Oración y Faros)";
      const farokids_schedule = loc.farokids_schedule || "En todos los cultos dominicales";
      const image = loc.image || loc.image_url || "";
      const pastor = loc.pastor || loc.pastor_name || "";
      const isMain = Boolean(loc.is_main || loc.isMain || i === 0);
      const mapsUrl = loc.maps_url || loc.mapsUrl || "";
      const mapEmbedUrl = loc.map_embed_url || loc.mapEmbedUrl || "";

      return {
        ...loc,
        id: loc.id ?? `sede-${i + 1}`,
        name: loc.name || "Sede El Faro",
        address: loc.address || "",
        city: loc.city || "Barranquilla",
        schedule,
        midweek,
        farokids_schedule,
        pastor,
        image,
        isMain,
        mapsUrl,
        mapEmbedUrl,
      };
    });
  }, [parsedLocations]);

  // States
  const [selected, setSelected] = useState<LocationItem | null>(null);
  const [search, setSearch] = useState("");
  const [selectedCity, setSelectedCity] = useState<string>("Todas");
  const [mobileView, setMobileView] = useState<"lista" | "mapa">("lista");
  const [drawerSede, setDrawerSede] = useState<LocationItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<string | number | null>(null);

  // Canonical city filters
  const cities = useMemo(() => {
    const list = ["Todas", "Barranquilla", "Cartagena", "Soledad", "Online"];
    locations.forEach((loc) => {
      if (loc.city && !list.includes(loc.city)) {
        list.push(loc.city);
      }
    });
    return list;
  }, [locations]);

  useEffect(() => {
    if (locations.length > 0) {
      setSelected((current) => {
        if (current) {
          const found = locations.find((l) => String(l.id) === String(current.id));
          if (found) return found;
        }
        return locations.find((l) => l.isMain) || locations[0];
      });
    }
  }, [locations]);

  // Filter logic
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return locations.filter((loc) => {
      // City check
      if (selectedCity !== "Todas") {
        if (selectedCity === "Online") {
          const isOnline =
            loc.city?.toLowerCase().includes("online") ||
            loc.name.toLowerCase().includes("online") ||
            loc.address.toLowerCase().includes("online") ||
            loc.address.toLowerCase().includes("youtube");
          if (!isOnline) return false;
        } else {
          if (loc.city?.toLowerCase() !== selectedCity.toLowerCase()) {
            return false;
          }
        }
      }

      // Search query check
      if (!q) return true;
      const name = (loc.name || "").toLowerCase();
      const address = (loc.address || "").toLowerCase();
      const city = (loc.city || "").toLowerCase();
      const pastor = (loc.pastor || "").toLowerCase();
      return name.includes(q) || address.includes(q) || city.includes(q) || pastor.includes(q);
    });
  }, [locations, search, selectedCity]);

  // Compute dynamic reactive Map URL
  const selectedMapUrl = useMemo(() => {
    const active = selected || locations[0];
    if (!active) {
      return (
        mapEmbedUrl ||
        "https://maps.google.com/maps?q=Barranquilla%2C%20Colombia&t=&z=13&ie=UTF8&iwloc=&output=embed"
      );
    }

    // 1. Explicit embed URL if provided
    if (active.mapEmbedUrl && active.mapEmbedUrl.startsWith("http")) {
      return active.mapEmbedUrl;
    }

    // 2. OpenStreetMap if GPS coordinates exist
    if (
      typeof active.lat === "number" &&
      typeof active.lng === "number" &&
      !isNaN(active.lat) &&
      !isNaN(active.lng)
    ) {
      const delta = 0.012;
      const minLng = (active.lng - delta).toFixed(5);
      const minLat = (active.lat - delta).toFixed(5);
      const maxLng = (active.lng + delta).toFixed(5);
      const maxLat = (active.lat + delta).toFixed(5);
      return `https://www.openstreetmap.org/export/embed.html?bbox=${minLng}%2C${minLat}%2C${maxLng}%2C${maxLat}&layer=mapnik&marker=${active.lat}%2C${active.lng}`;
    }

    // 3. Fallback to Google Maps query embed
    const targetQuery = [active.name, active.address, active.city || "Colombia"]
      .filter(Boolean)
      .join(", ");
    return `https://maps.google.com/maps?q=${encodeURIComponent(targetQuery)}&t=&z=16&ie=UTF8&iwloc=&output=embed`;
  }, [selected, locations, mapEmbedUrl]);

  const activeSede = selected || locations[0] || null;

  const handleCopyAddress = (e: React.MouseEvent, sede: LocationItem) => {
    e.stopPropagation();
    if (!sede.address) return;
    navigator.clipboard.writeText(sede.address);
    setCopiedId(sede.id);
    toast.success("Dirección copiada al portapapeles");
    setTimeout(() => setCopiedId(null), 2500);
  };

  const handleOpenDrawer = (e: React.MouseEvent, loc: LocationItem) => {
    e.stopPropagation();
    setDrawerSede(loc);
    setIsDrawerOpen(true);
  };

  return (
    <main
      className="pt-[88px] flex flex-col md:flex-row bg-site-surface min-h-screen text-site-on-surface"
      style={{
        background: "var(--site-surface, #fcfcfd)",
        color: "var(--site-on-surface, #1e1f21)",
      }}
    >
      {/* ── RESPONSIVE MOBILE TOGGLE (LISTA / MAPA) ──────────────────── */}
      <div className="md:hidden sticky top-[88px] z-30 px-4 py-2.5 bg-site-surface-container-lowest/95 backdrop-blur-md border-b border-site-outline-variant/15 flex items-center justify-between gap-2 shadow-xs">
        <div className="flex items-center gap-1.5 bg-site-surface-container-high/60 p-1 rounded-xl w-full">
          <button
            type="button"
            onClick={() => setMobileView("lista")}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-bold transition-all ${
              mobileView === "lista"
                ? "bg-white text-site-primary shadow-xs"
                : "text-site-on-surface-variant hover:text-site-on-surface"
            }`}
            style={{
              color: mobileView === "lista" ? "var(--site-primary, #2563eb)" : undefined,
            }}
          >
            <List size={15} />
            <span>Lista de Sedes ({filtered.length})</span>
          </button>
          <button
            type="button"
            onClick={() => setMobileView("mapa")}
            className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-bold transition-all ${
              mobileView === "mapa"
                ? "bg-white text-site-primary shadow-xs"
                : "text-site-on-surface-variant hover:text-site-on-surface"
            }`}
            style={{
              color: mobileView === "mapa" ? "var(--site-primary, #2563eb)" : undefined,
            }}
          >
            <Map size={15} />
            <span>Ver en Mapa</span>
          </button>
        </div>
      </div>

      {/* ── SIDEBAR LISTADO DE SEDES ──────────────────────────── */}
      <aside
        className={`w-full md:w-[420px] lg:w-[480px] xl:w-[520px] flex flex-col md:h-[calc(100vh-88px)] md:sticky md:top-[88px] border-r border-site-outline-variant/15 bg-site-surface-container-lowest shrink-0 ${
          mobileView === "mapa" ? "hidden md:flex" : "flex"
        }`}
      >
        {/* Header & Search */}
        <div className="p-4 sm:p-5 border-b border-site-outline-variant/15 space-y-3.5 bg-site-surface-container-lowest">
          <div>
            {eyebrow && (
              <span
                className="font-extrabold text-2xs tracking-wider uppercase block mb-1"
                style={{ color: "var(--site-primary, #2563eb)" }}
              >
                {eyebrow}
              </span>
            )}
            {title && (
              <h1 className="text-xl sm:text-2xl font-black tracking-tight text-site-on-surface">
                {title}
              </h1>
            )}
            <p className="text-xs text-site-on-surface-variant mt-1 leading-relaxed">
              Encuentra tu comunidad de fe más cercana. Hay un lugar especial preparado para ti y tu familia.
            </p>
          </div>

          {/* Search Box */}
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-site-outline w-4 h-4 opacity-60" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-site-surface-container rounded-xl py-2.5 pl-10 pr-4 text-xs outline-none focus:ring-2 focus:ring-site-primary/40 transition-all border border-site-outline-variant/20"
              placeholder={searchPlaceholder}
            />
          </div>

          {/* City Chips Filter */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
            {cities.map((city) => {
              const isActive = selectedCity === city;
              return (
                <button
                  key={city}
                  type="button"
                  onClick={() => setSelectedCity(city)}
                  className={`px-3 py-1.5 rounded-full text-xs font-bold tracking-tight whitespace-nowrap transition-all border ${
                    isActive
                      ? "border-site-primary text-white shadow-2xs scale-102"
                      : "border-site-outline-variant/20 bg-site-surface-container text-site-on-surface-variant hover:bg-site-surface-container-high"
                  }`}
                  style={{
                    background: isActive ? "var(--site-primary, #2563eb)" : undefined,
                    color: isActive ? "#ffffff" : undefined,
                  }}
                >
                  {city}
                </button>
              );
            })}
          </div>
        </div>

        {/* List of Sedes */}
        {locations.length === 0 ? (
          <div className="flex-1 flex items-center justify-center p-8 text-center">
            <div>
              <Building2 size={44} className="mx-auto mb-3 opacity-30 text-site-primary" />
              <p className="text-xs text-site-on-surface-variant max-w-xs">{emptyLocations}</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-3 sm:p-4 space-y-3.5 scrollbar-thin">
            {filtered.map((loc) => {
              const isSelected = activeSede?.id === loc.id;
              const isMain = Boolean(loc.isMain || loc.is_main);

              return (
                <div
                  key={String(loc.id)}
                  onClick={() => {
                    setSelected(loc);
                    // On mobile, tapping card opens drawer directly for seamless UX
                    if (window.innerWidth < 768) {
                      setDrawerSede(loc);
                      setIsDrawerOpen(true);
                    }
                  }}
                  className={`group rounded-2xl border transition-all cursor-pointer p-4 relative overflow-hidden ${
                    isSelected
                      ? "border-site-primary shadow-sm"
                      : "border-site-outline-variant/15 hover:border-site-outline-variant/30 hover:shadow-xs"
                  }`}
                  style={{
                    background: isSelected
                      ? "var(--site-primary-container-lowest, rgba(37,99,235,0.04))"
                      : "var(--site-surface-container-lowest, #ffffff)",
                    borderColor: isSelected
                      ? "var(--site-primary, #2563eb)"
                      : undefined,
                  }}
                >
                  {/* Left accent bar for active */}
                  {isSelected && (
                    <div
                      className="absolute left-0 top-0 bottom-0 w-1.5"
                      style={{ background: "var(--site-primary, #2563eb)" }}
                    />
                  )}

                  <div className="flex items-start gap-3.5">
                    {/* Sede Photo or Icon */}
                    <div className="relative w-16 h-16 rounded-xl overflow-hidden bg-site-surface-container-high shrink-0 border border-site-outline-variant/20 flex items-center justify-center">
                      {loc.image ? (
                        <Image
                          src={loc.image}
                          alt={loc.name}
                          fill
                          className="object-cover group-hover:scale-105 transition-transform duration-300"
                          sizes="64px"
                        />
                      ) : (
                        <Home
                          size={24}
                          style={{
                            color: isSelected ? "var(--site-primary, #2563eb)" : "var(--site-outline, #94a3b8)",
                          }}
                        />
                      )}
                    </div>

                    {/* Sede Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1.5 mb-1">
                        <h3 className="font-bold text-sm text-site-on-surface truncate group-hover:text-site-primary transition-colors">
                          {loc.name}
                        </h3>
                        {isMain && (
                          <span
                            className="text-3xs font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0 shadow-2xs"
                            style={{ background: "var(--site-cta-gradient, #2563eb)", color: "#ffffff" }}
                          >
                            {mainBadge}
                          </span>
                        )}
                      </div>

                      <p className="text-site-on-surface-variant text-xs mb-2 line-clamp-1 opacity-90 flex items-center gap-1">
                        <MapPin size={12} className="shrink-0 text-site-primary" />
                        <span className="truncate">{loc.address}</span>
                      </p>

                      <div className="flex items-center gap-2 flex-wrap">
                        {loc.city && (
                          <span className="inline-flex items-center gap-1 text-3xs font-bold px-2 py-0.5 rounded-md bg-site-surface-container-high text-site-on-surface-variant">
                            <Globe size={10} /> {loc.city}
                          </span>
                        )}
                        {loc.pastor && (
                          <span className="inline-flex items-center gap-1 text-3xs font-semibold px-2 py-0.5 rounded-md bg-site-surface-container text-site-on-surface-variant truncate max-w-[160px]">
                            <User size={10} className="shrink-0" /> {loc.pastor}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Resumen de Horarios */}
                  <div className="mt-3 pt-3 border-t border-site-outline-variant/10 flex items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-1.5 text-site-on-surface-variant truncate">
                      <Clock size={12} className="text-site-primary shrink-0" />
                      <span className="truncate text-3xs sm:text-2xs font-medium">
                        {loc.schedule || "Domingos: 8:00 AM y 10:30 AM"}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {/* Copiar dirección */}
                      <button
                        type="button"
                        onClick={(e) => handleCopyAddress(e, loc)}
                        title="Copiar dirección"
                        className="p-1.5 rounded-lg border border-site-outline-variant/20 hover:bg-site-surface-container text-site-on-surface-variant transition-colors"
                      >
                        {copiedId === loc.id ? (
                          <Check size={12} className="text-emerald-600" />
                        ) : (
                          <Copy size={12} />
                        )}
                      </button>

                      {/* Botón Ver Detalles (Abre Drawer) */}
                      <button
                        type="button"
                        onClick={(e) => handleOpenDrawer(e, loc)}
                        className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-3xs font-bold uppercase tracking-wider text-site-primary bg-site-primary-container/20 hover:bg-site-primary-container/35 transition-colors"
                        style={{
                          color: "var(--site-primary, #2563eb)",
                        }}
                      >
                        <Info size={11} />
                        <span>Detalles</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}

            {filtered.length === 0 && (
              <div className="rounded-2xl border border-dashed border-site-outline-variant/20 p-6 text-center text-xs text-site-on-surface-variant bg-site-surface-container/30">
                <p className="font-semibold">{emptySearch}</p>
                <button
                  type="button"
                  onClick={() => {
                    setSearch("");
                    setSelectedCity("Todas");
                  }}
                  className="mt-3 text-xs font-bold text-site-primary hover:underline block mx-auto"
                >
                  Restablecer filtros
                </button>
              </div>
            )}
          </div>
        )}
      </aside>

      {/* ── MAPA INTERACTIVO (Garantizado 100% visible) ──────────────────── */}
      <section
        className={`flex-1 relative min-h-[50vh] md:h-[calc(100vh-88px)] md:sticky md:top-[88px] flex flex-col bg-site-surface-container-low overflow-hidden ${
          mobileView === "lista" ? "hidden md:flex" : "flex"
        }`}
      >
        {/* Floating Active Sede Overlay Card */}
        {activeSede && (
          <div className="absolute top-4 left-4 right-4 z-20 pointer-events-none">
            <div className="pointer-events-auto max-w-xl mx-auto md:mx-0 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-md p-3.5 rounded-2xl border border-site-outline-variant/20 shadow-xl flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                  style={{
                    background: "var(--site-primary-container, rgba(37,99,235,0.12))",
                    color: "var(--site-primary, #2563eb)",
                  }}
                >
                  <MapPin size={20} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <h2 className="font-bold text-sm text-site-on-surface truncate">
                      {activeSede.name}
                    </h2>
                    {activeSede.isMain && (
                      <span className="text-3xs font-extrabold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-700 dark:text-amber-300 shrink-0">
                        Principal
                      </span>
                    )}
                  </div>
                  <p className="text-3xs text-site-on-surface-variant truncate opacity-85">
                    {activeSede.address || "Ubicación en el mapa"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  type="button"
                  onClick={(e) => handleOpenDrawer(e, activeSede)}
                  className="px-3 py-1.5 rounded-xl text-3xs font-bold uppercase tracking-wider border border-site-outline-variant/20 hover:bg-site-surface-container transition-colors"
                >
                  Ver Horarios
                </button>

                <a
                  href={
                    activeSede.mapsUrl ||
                    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                      [activeSede.name, activeSede.address, activeSede.city || "Colombia"].filter(Boolean).join(", ")
                    )}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-3xs font-bold uppercase tracking-wider text-white shadow-2xs hover:opacity-95 transition-opacity"
                  style={{ background: "var(--site-cta-gradient, #2563eb)" }}
                >
                  <Navigation size={12} />
                  <span>GPS</span>
                </a>
              </div>
            </div>
          </div>
        )}

        {/* Live Interactive Map Iframe */}
        <iframe
          key={activeSede ? String(activeSede.id) : "default-map"}
          src={selectedMapUrl}
          className="w-full h-full border-0 block flex-1"
          allowFullScreen
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          title={`Mapa interactivo de ${activeSede?.name || "Sedes El Faro"}`}
          style={{ minHeight: "60vh" }}
        />
      </section>

      {/* ── DRAWER LATERAL DESLIZANTE AUTÓNOMO (0 MODALES) ──────────────────── */}
      <SedeDetailDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        sede={drawerSede}
      />
    </main>
  );
}
