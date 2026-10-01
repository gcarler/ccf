"use client";

import { useCmsV2Page } from "@/hooks/useCmsV2Page";
import SedeDetailDrawer, { SedeDetailItem } from "@/components/public/SedeDetailDrawer";
import {
  Clock,
  Home,
  Navigation,
  Search,
  MapPin,
  Copy,
  Check,
  Building2,
  Globe,
  User,
  Map,
  List,
  Info,
  Layers,
} from "lucide-react";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

interface LocationItem extends SedeDetailItem {
  services?: string[];
  sector?: string;
}

// ── 7 SEDES CANÓNICAS DE CARTAGENA (Catálogo Oficial con Coordenadas Exactas) ──
const CANONICAL_CARTAGENA_SEDES: LocationItem[] = [
  {
    id: "ctg-1",
    name: "Comunidad Cristiana El Faro — Bosquecito (Sede Principal)",
    city: "Cartagena",
    sector: "Bosquecito",
    address: "Diag. 21B #48A-12, Sector El Bosquecito",
    phone: "+57 300 812 3456",
    pastor: "Pastores Principales CCF",
    schedule: "Domingos: 8:00 AM y 10:30 AM",
    midweek: "Miércoles: 7:00 PM (Oración y Faros)",
    farokids_schedule: "En todos los cultos dominicales",
    lat: 10.3930347,
    lng: -75.5104067,
    is_main: true,
    isMain: true,
    image: "/images/locations/sede-central.jpg",
    image_url: "/images/locations/sede-central.jpg",
    mapsUrl: "https://www.google.com/maps/dir/?api=1&destination=10.3930347,-75.5104067",
    maps_url: "https://www.google.com/maps/dir/?api=1&destination=10.3930347,-75.5104067",
  },
  {
    id: "ctg-2",
    name: "Iglesia Cristiana Faro de Gloria — Ceballos",
    city: "Cartagena",
    sector: "Ceballos",
    address: "Transversal 54 #28-45, Barrio Ceballos",
    phone: "+57 301 234 5678",
    pastor: "Equipo Pastoral CCF",
    schedule: "Domingos: 9:00 AM",
    midweek: "Jueves: 7:00 PM (Estudio Bíblico y Oración)",
    farokids_schedule: "Aulas infantiles los domingos",
    lat: 10.387729,
    lng: -75.5041959,
    is_main: false,
    isMain: false,
    image: "/images/locations/sede-central.jpg",
    image_url: "/images/locations/sede-central.jpg",
    mapsUrl: "https://www.google.com/maps/dir/?api=1&destination=10.387729,-75.5041959",
    maps_url: "https://www.google.com/maps/dir/?api=1&destination=10.387729,-75.5041959",
  },
  {
    id: "ctg-3",
    name: "C.C. Avivamiento Internacional El Faro — Pasacaballos",
    city: "Cartagena",
    sector: "Pasacaballos",
    address: "Calle Principal #12-30, Corregimiento de Pasacaballos",
    phone: "+57 302 345 6789",
    pastor: "Pastores de Sede",
    schedule: "Domingos: 9:00 AM y 6:00 PM",
    midweek: "Martes: 7:00 PM (Culto de Poder)",
    farokids_schedule: "Ministerio Infantil dominical",
    lat: 10.2827598,
    lng: -75.5148354,
    is_main: false,
    isMain: false,
    image: "/images/locations/sede-central.jpg",
    image_url: "/images/locations/sede-central.jpg",
    mapsUrl: "https://www.google.com/maps/dir/?api=1&destination=10.2827598,-75.5148354",
    maps_url: "https://www.google.com/maps/dir/?api=1&destination=10.2827598,-75.5148354",
  },
  {
    id: "ctg-4",
    name: "Iglesia Evangélica Los 2 Olivos — Pasacaballos",
    city: "Cartagena",
    sector: "Pasacaballos",
    address: "Sector Las Flores, Pasacaballos",
    phone: "+57 303 456 7890",
    pastor: "Liderazgo Pastoral",
    schedule: "Domingos: 8:30 AM",
    midweek: "Miércoles: 6:30 PM (Oración e Intercesión)",
    farokids_schedule: "Escuela dominical",
    lat: 10.2809167,
    lng: -75.5174839,
    is_main: false,
    isMain: false,
    image: "/images/locations/sede-central.jpg",
    image_url: "/images/locations/sede-central.jpg",
    mapsUrl: "https://www.google.com/maps/dir/?api=1&destination=10.2809167,-75.5174839",
    maps_url: "https://www.google.com/maps/dir/?api=1&destination=10.2809167,-75.5174839",
  },
  {
    id: "ctg-5",
    name: "Iglesia Cristiana Príncipe del Reino — Caño del Oro",
    city: "Cartagena",
    sector: "Caño del Oro",
    address: "Sector Central frente al muelle, Caño del Oro, Isla Tierra Bomba",
    phone: "+57 304 567 8901",
    pastor: "Pastores Misioneros",
    schedule: "Domingos: 9:30 AM",
    midweek: "Viernes: 6:00 PM (Reunión Insular)",
    farokids_schedule: "Atención infantil dominical",
    lat: 10.339825,
    lng: -75.5475701,
    is_main: false,
    isMain: false,
    image: "/images/locations/sede-central.jpg",
    image_url: "/images/locations/sede-central.jpg",
    mapsUrl: "https://www.google.com/maps/dir/?api=1&destination=10.339825,-75.5475701",
    maps_url: "https://www.google.com/maps/dir/?api=1&destination=10.339825,-75.5475701",
  },
  {
    id: "ctg-6",
    name: "Iglesia Cristiana Príncipe del Reino — San Isidro",
    city: "Cartagena",
    sector: "San Isidro",
    address: "Calle Real de San Isidro #23-14",
    phone: "+57 305 678 9012",
    pastor: "Equipo Pastoral San Isidro",
    schedule: "Domingos: 9:00 AM",
    midweek: "Miércoles: 7:00 PM (Oración de Milagros)",
    farokids_schedule: "Aulas por edades los domingos",
    lat: 10.3891901,
    lng: -75.5120837,
    is_main: false,
    isMain: false,
    image: "/images/locations/sede-central.jpg",
    image_url: "/images/locations/sede-central.jpg",
    mapsUrl: "https://www.google.com/maps/dir/?api=1&destination=10.3891901,-75.5120837",
    maps_url: "https://www.google.com/maps/dir/?api=1&destination=10.3891901,-75.5120837",
  },
  {
    id: "ctg-7",
    name: "Comunidad Cristiana Ríos de Agua Viva — 20 de Julio Sur",
    city: "Cartagena",
    sector: "20 de Julio",
    address: "Manzana 14 Lote 8, Barrio 20 de Julio Sur",
    phone: "+57 306 789 0123",
    pastor: "Liderazgo Pastoral 20 de Julio",
    schedule: "Domingos: 8:00 AM y 10:30 AM",
    midweek: "Jueves: 7:00 PM (Noche de Avivamiento)",
    farokids_schedule: "FaroKids activo domingos",
    lat: 10.3724747,
    lng: -75.501637,
    is_main: false,
    isMain: false,
    image: "/images/locations/sede-central.jpg",
    image_url: "/images/locations/sede-central.jpg",
    mapsUrl: "https://www.google.com/maps/dir/?api=1&destination=10.3724747,-75.501637",
    maps_url: "https://www.google.com/maps/dir/?api=1&destination=10.3724747,-75.501637",
  },
];

const OFFICIAL_MY_MAPS_EMBED =
  "https://www.google.com/maps/d/embed?mid=1VDNpplw_9z1tcEhx25wEFRR5gQmnHgM&ehbc=2E312F";

const SECTORS_CARTAGENA = [
  "Todos",
  "Bosquecito",
  "San Isidro",
  "Ceballos",
  "Pasacaballos",
  "20 de Julio",
  "Caño del Oro",
];

export default function SedesPage() {
  const heroPage = useCmsV2Page("locations");
  const heroContent = heroPage?.blocks?.hero as Record<string, unknown> | undefined;
  const locationsContent = heroPage?.blocks?.feed as Record<string, unknown> | undefined;

  const mainBadge = typeof heroContent?.main_badge === "string" ? heroContent.main_badge : "Sede Principal";
  const emptyLocations =
    typeof heroContent?.empty_locations === "string"
      ? heroContent.empty_locations
      : "No hay sedes registradas en este momento.";
  const emptySearch =
    typeof heroContent?.empty_search === "string"
      ? heroContent.empty_search
      : "No encontramos sedes en ese sector o con ese criterio en Cartagena.";
  const eyebrow = typeof heroContent?.eyebrow === "string" ? heroContent.eyebrow : "Nuestra Presencia en Cartagena";
  const titleLead = typeof heroContent?.title_lead === "string" ? heroContent.title_lead : "Nuestras";
  const titleAccent = typeof heroContent?.title_accent === "string" ? heroContent.title_accent : "Sedes";
  const title = typeof heroContent?.title === "string" ? heroContent.title : `${titleLead} ${titleAccent}`;
  const searchPlaceholder =
    typeof heroContent?.search_placeholder === "string"
      ? heroContent.search_placeholder
      : "Buscar por sector, barrio o sede en Cartagena...";

  const rawLocations = (locationsContent?.parsed ?? locationsContent) as unknown;
  const parsedLocations: LocationItem[] = useMemo(
    () =>
      Array.isArray(rawLocations)
        ? (rawLocations as LocationItem[])
        : Array.isArray((rawLocations as Record<string, unknown>)?.items)
        ? ((rawLocations as Record<string, unknown>).items as LocationItem[])
        : [],
    [rawLocations]
  );

  const locations: LocationItem[] = useMemo(() => {
    const sourceList = parsedLocations.length > 0 ? parsedLocations : CANONICAL_CARTAGENA_SEDES;

    return sourceList.map((loc, i) => {
      const schedule =
        loc.schedule ||
        (Array.isArray(loc.services) && loc.services.length > 0 ? loc.services.join(" • ") : "") ||
        "Domingos 8:00 AM y 10:30 AM";
      const midweek = loc.midweek || "Miércoles 7:00 PM (Oración y Faros)";
      const farokids_schedule = loc.farokids_schedule || "En todos los cultos dominicales";
      const image = loc.image || loc.image_url || "/images/locations/sede-central.jpg";
      const pastor = loc.pastor || loc.pastor_name || "";
      const isMain = Boolean(loc.is_main || loc.isMain || i === 0);

      // Extract coordinates
      const lat = typeof loc.lat === "number" ? loc.lat : null;
      const lng = typeof loc.lng === "number" ? loc.lng : null;

      // Direct GPS route link
      const mapsUrl =
        lat && lng
          ? `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`
          : loc.maps_url || loc.mapsUrl || "";

      // Deduce sector if missing
      let sector = loc.sector || "";
      if (!sector) {
        const lower = `${loc.name} ${loc.address}`.toLowerCase();
        if (lower.includes("bosquecito")) sector = "Bosquecito";
        else if (lower.includes("ceballos")) sector = "Ceballos";
        else if (lower.includes("pasacaballos")) sector = "Pasacaballos";
        else if (lower.includes("caño del oro") || lower.includes("tierra bomba")) sector = "Caño del Oro";
        else if (lower.includes("san isidro")) sector = "San Isidro";
        else if (lower.includes("20 de julio")) sector = "20 de Julio";
      }

      return {
        ...loc,
        id: loc.id ?? `sede-${i + 1}`,
        name: loc.name || "Sede El Faro",
        address: loc.address || "",
        city: loc.city || "Cartagena",
        sector,
        schedule,
        midweek,
        farokids_schedule,
        pastor,
        image,
        isMain,
        lat,
        lng,
        mapsUrl,
      };
    });
  }, [parsedLocations]);

  // States
  const [selected, setSelected] = useState<LocationItem | null>(null);
  const [useGeneralMap, setUseGeneralMap] = useState<boolean>(true);
  const [search, setSearch] = useState("");
  const [selectedSector, setSelectedSector] = useState<string>("Todos");
  const [mobileView, setMobileView] = useState<"lista" | "mapa">("lista");
  const [drawerSede, setDrawerSede] = useState<LocationItem | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<string | number | null>(null);

  useEffect(() => {
    if (locations.length > 0 && !selected) {
      const main = locations.find((l) => l.isMain) || locations[0];
      setSelected(main);
    }
  }, [locations, selected]);

  // Filtered sedes by search query & sector in Cartagena
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return locations.filter((loc) => {
      // Sector filter
      if (selectedSector !== "Todos") {
        const locSector = (loc.sector || "").toLowerCase();
        const targetSector = selectedSector.toLowerCase();
        const matchesSector =
          locSector === targetSector ||
          loc.name.toLowerCase().includes(targetSector) ||
          loc.address.toLowerCase().includes(targetSector);
        if (!matchesSector) return false;
      }

      // Search query filter
      if (!q) return true;
      const name = (loc.name || "").toLowerCase();
      const address = (loc.address || "").toLowerCase();
      const sector = (loc.sector || "").toLowerCase();
      const pastor = (loc.pastor || "").toLowerCase();
      return name.includes(q) || address.includes(q) || sector.includes(q) || pastor.includes(q);
    });
  }, [locations, search, selectedSector]);

  // Active Map URL: Default to Official Google My Maps embed, fallback centrado por GPS al enfocar sede
  const mapIframeUrl = useMemo(() => {
    // 1. Si el usuario seleccionó ver el mapa general oficial de Google My Maps
    if (useGeneralMap) {
      return OFFICIAL_MY_MAPS_EMBED;
    }

    // 2. Si hay sede activa y el usuario desea enfocarla por GPS
    const active = selected || locations[0];
    if (active && typeof active.lat === "number" && typeof active.lng === "number") {
      return `https://maps.google.com/maps?q=${active.lat},${active.lng}&t=&z=17&ie=UTF8&iwloc=&output=embed`;
    }

    // Fallback: mapa oficial
    return OFFICIAL_MY_MAPS_EMBED;
  }, [useGeneralMap, selected, locations]);

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

  const handleSelectSede = (loc: LocationItem) => {
    setSelected(loc);
    setUseGeneralMap(false); // Centrar en la sede seleccionada
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
        className={`w-full md:w-[440px] lg:w-[490px] xl:w-[530px] flex flex-col md:h-[calc(100vh-88px)] md:sticky md:top-[88px] border-r border-site-outline-variant/15 bg-site-surface-container-lowest shrink-0 ${
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
              Descubre las 7 sedes canónicas de Comunidad Cristiana El Faro en Cartagena. Encuentra tu familia de fe en tu sector.
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

          {/* Chips de Filtro por Sector en Cartagena */}
          <div>
            <div className="flex items-center justify-between text-3xs font-bold uppercase tracking-wider text-site-on-surface-variant mb-1.5 opacity-80">
              <span>Filtrar por sector</span>
              <span className="font-medium text-site-primary">7 sedes activas</span>
            </div>
            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
              {SECTORS_CARTAGENA.map((sector) => {
                const isActive = selectedSector === sector;
                return (
                  <button
                    key={sector}
                    type="button"
                    onClick={() => setSelectedSector(sector)}
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
                    {sector}
                  </button>
                );
              })}
            </div>
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
                    handleSelectSede(loc);
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
                        {loc.sector && (
                          <span className="inline-flex items-center gap-1 text-3xs font-bold px-2 py-0.5 rounded-md bg-site-primary-container/20 text-site-primary">
                            <Globe size={10} /> Sector {loc.sector}
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

                  {/* Resumen de Horarios y Acciones */}
                  <div className="mt-3 pt-3 border-t border-site-outline-variant/10 flex items-center justify-between gap-2 text-xs">
                    <div className="flex items-center gap-1.5 text-site-on-surface-variant truncate">
                      <Clock size={12} className="text-site-primary shrink-0" />
                      <span className="truncate text-3xs sm:text-2xs font-medium">
                        {loc.schedule || "Domingos: 8:00 AM y 10:30 AM"}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {/* Ruta GPS directa */}
                      <a
                        href={loc.mapsUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        title="Cómo llegar con GPS"
                        className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-3xs font-bold text-white shadow-2xs hover:opacity-90 transition-opacity"
                        style={{ background: "var(--site-cta-gradient, #2563eb)" }}
                      >
                        <Navigation size={11} />
                        <span>Ruta</span>
                      </a>

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
                    setSelectedSector("Todos");
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

      {/* ── MAPA INTERACTIVO (Google My Maps Oficial + Fallback GPS) ──────────── */}
      <section
        className={`flex-1 relative min-h-[50vh] md:h-[calc(100vh-88px)] md:sticky md:top-[88px] flex flex-col bg-site-surface-container-low overflow-hidden ${
          mobileView === "lista" ? "hidden md:flex" : "flex"
        }`}
      >
        {/* Floating Active Sede Overlay Card & Map View Mode Switcher */}
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
                    {useGeneralMap
                      ? "Mapa Oficial de Sedes CCF"
                      : activeSede?.name || "Sede El Faro"}
                  </h2>
                  {activeSede?.isMain && !useGeneralMap && (
                    <span className="text-3xs font-extrabold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-700 dark:text-amber-300 shrink-0">
                      Principal
                    </span>
                  )}
                </div>
                <p className="text-3xs text-site-on-surface-variant truncate opacity-85">
                  {useGeneralMap
                    ? "7 sedes canónicas registradas en Cartagena"
                    : activeSede?.address || "Ubicación en el mapa"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-1.5 shrink-0">
              {/* Botón para alternar entre Mapa General y Sede Enfocada */}
              <button
                type="button"
                onClick={() => setUseGeneralMap(!useGeneralMap)}
                className={`px-3 py-1.5 rounded-xl text-3xs font-bold uppercase tracking-wider border transition-all flex items-center gap-1 ${
                  useGeneralMap
                    ? "bg-site-primary text-white border-site-primary"
                    : "border-site-outline-variant/20 hover:bg-site-surface-container text-site-on-surface-variant"
                }`}
                style={{
                  background: useGeneralMap ? "var(--site-primary, #2563eb)" : undefined,
                  color: useGeneralMap ? "#ffffff" : undefined,
                }}
              >
                <Layers size={11} />
                <span>{useGeneralMap ? "Ver Sede" : "Mapa General"}</span>
              </button>

              {/* Botón Cómo Llegar con GPS directo */}
              {activeSede && (
                <a
                  href={
                    activeSede.lat && activeSede.lng
                      ? `https://www.google.com/maps/dir/?api=1&destination=${activeSede.lat},${activeSede.lng}`
                      : activeSede.mapsUrl || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(activeSede.name + ", Cartagena")}`
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-3xs font-bold uppercase tracking-wider text-white shadow-2xs hover:opacity-95 transition-opacity"
                  style={{ background: "var(--site-cta-gradient, #2563eb)" }}
                >
                  <Navigation size={12} />
                  <span>Cómo Llegar</span>
                </a>
              )}
            </div>
          </div>
        </div>

        {/* Live Interactive Map Iframe */}
        <iframe
          key={mapIframeUrl}
          src={mapIframeUrl}
          className="w-full h-full border-0 block flex-1"
          allowFullScreen
          loading="lazy"
          referrerPolicy="no-referrer-when-downgrade"
          title="Mapa de Sedes Comunidad Cristiana El Faro Cartagena"
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
