"use client";

import { useCmsV2Page } from "@/hooks/useCmsV2Page";
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
} from "lucide-react";
import Image from "next/image";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

interface LocationItem {
  id: number | string;
  name: string;
  address: string;
  city?: string;
  mapsUrl?: string;
  maps_url?: string;
  mapEmbedUrl?: string;
  map_embed_url?: string;
  lat?: number | null;
  lng?: number | null;
  phone?: string;
  pastor?: string;
  pastor_name?: string;
  schedule?: string;
  schedules?: string;
  midweek?: string;
  image?: string;
  image_url?: string;
  isMain?: boolean;
  is_main?: boolean;
  services?: string[];
}

export default function SedesPage() {
  const heroPage = useCmsV2Page("locations");
  const heroContent = heroPage?.blocks?.hero as Record<string, unknown> | undefined;
  const locationsContent = heroPage?.blocks?.feed as Record<string, unknown> | undefined;

  const mapEmbedUrl = typeof heroContent?.map_embed_url === "string" ? heroContent.map_embed_url : "";
  const mainBadge = typeof heroContent?.main_badge === "string" ? heroContent.main_badge : "Sede Principal";
  const directionsCta = typeof heroContent?.directions_cta === "string" ? heroContent.directions_cta : "Cómo llegar";
  const emptyLocations =
    typeof heroContent?.empty_locations === "string"
      ? heroContent.empty_locations
      : "No hay sedes registradas en este momento.";
  const emptySearch =
    typeof heroContent?.empty_search === "string"
      ? heroContent.empty_search
      : "No encontramos sedes que coincidan con tu búsqueda.";
  const eyebrow = typeof heroContent?.eyebrow === "string" ? heroContent.eyebrow : "Nuestra Presencia";
  const titleLead = typeof heroContent?.title_lead === "string" ? heroContent.title_lead : "Nuestras";
  const titleAccent = typeof heroContent?.title_accent === "string" ? heroContent.title_accent : "Sedes";
  const title = typeof heroContent?.title === "string" ? heroContent.title : `${titleLead} ${titleAccent}`;
  const searchPlaceholder =
    typeof heroContent?.search_placeholder === "string"
      ? heroContent.search_placeholder
      : "Buscar ciudad, barrio o sede...";

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
        loc.schedules ||
        (Array.isArray(loc.services) && loc.services.length > 0 ? loc.services.join(" • ") : "") ||
        "";
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
        city: loc.city || "",
        schedule,
        pastor,
        image,
        isMain,
        mapsUrl,
        mapEmbedUrl,
      };
    });
  }, [parsedLocations]);

  const [selected, setSelected] = useState<LocationItem | null>(null);
  const [search, setSearch] = useState("");
  const [copied, setCopied] = useState(false);

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

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return locations;
    return locations.filter((l) => {
      const name = (l.name || "").toLowerCase();
      const address = (l.address || "").toLowerCase();
      const city = (l.city || "").toLowerCase();
      const pastor = (l.pastor || "").toLowerCase();
      return name.includes(q) || address.includes(q) || city.includes(q) || pastor.includes(q);
    });
  }, [locations, search]);

  // Compute live dynamic Map URL (always guaranteed to load, no missing key)
  const selectedMapUrl = useMemo(() => {
    const active = selected || locations[0];
    if (!active) {
      return mapEmbedUrl || "https://maps.google.com/maps?q=Cartagena%2C%20Colombia&t=&z=13&ie=UTF8&iwloc=&output=embed";
    }

    // 1. Custom embed URL if explicitly provided
    if (active.mapEmbedUrl && active.mapEmbedUrl.startsWith("http")) {
      return active.mapEmbedUrl;
    }

    // 2. OpenStreetMap if exact GPS coordinates are set
    if (typeof active.lat === "number" && typeof active.lng === "number" && !isNaN(active.lat) && !isNaN(active.lng)) {
      const delta = 0.012;
      const minLng = (active.lng - delta).toFixed(5);
      const minLat = (active.lat - delta).toFixed(5);
      const maxLng = (active.lng + delta).toFixed(5);
      const maxLat = (active.lat + delta).toFixed(5);
      return `https://www.openstreetmap.org/export/embed.html?bbox=${minLng}%2C${minLat}%2C${maxLng}%2C${maxLat}&layer=mapnik&marker=${active.lat}%2C${active.lng}`;
    }

    // 3. Google Maps query embed (free, reliable, pinpointed to church name/address/city)
    const targetQuery = [active.name, active.address, active.city || "Colombia"]
      .filter(Boolean)
      .join(", ");
    return `https://maps.google.com/maps?q=${encodeURIComponent(targetQuery)}&t=&z=16&ie=UTF8&iwloc=&output=embed`;
  }, [selected, locations, mapEmbedUrl]);

  const activeSede = selected || locations[0] || null;

  const handleCopyAddress = (address: string) => {
    if (!address) return;
    navigator.clipboard.writeText(address);
    setCopied(true);
    toast.success("Dirección copiada al portapapeles");
    setTimeout(() => setCopied(false), 2500);
  };

  return (
    <main className="pt-[88px] flex flex-col md:flex-row bg-site-surface" style={{ minHeight: "100vh" }}>
      {/* ── SIDEBAR LISTADO DE SEDES ──────────────────────────── */}
      <aside className="w-full md:w-[380px] lg:w-[440px] xl:w-[480px] flex flex-col max-h-[55vh] md:max-h-none md:h-[calc(100vh-88px)] md:sticky md:top-[88px] bg-site-surface-container-lowest border-r border-site-outline-variant/10 overflow-hidden shrink-0">
        <div className="p-4 border-b border-site-outline-variant/10 bg-site-surface-container-lowest">
          {eyebrow && (
            <span className="font-semibold text-2xs tracking-wider uppercase block mb-1 text-site-primary">
              {eyebrow}
            </span>
          )}
          {title && (
            <h1 className="text-xl font-black tracking-tight text-site-on-surface mb-3">
              {title}
            </h1>
          )}
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-site-outline w-4 h-4 opacity-60" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-site-surface-container rounded-xl py-2 pl-10 pr-4 text-xs outline-none focus:ring-2 focus:ring-site-primary/40 transition-all border border-site-outline-variant/20"
              placeholder={searchPlaceholder}
            />
          </div>
        </div>

        {locations.length === 0 ? (
          <div className="flex-1 flex items-center justify-center p-6 text-center">
            <div>
              <Building2 size={40} className="mx-auto mb-3 opacity-30 text-site-primary" />
              <p className="text-xs text-site-on-surface-variant max-w-xs">{emptyLocations}</p>
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto p-3 space-y-3 scrollbar-thin">
            {filtered.map((loc) => {
              const isSelected = activeSede?.id === loc.id;
              return (
                <motion.div
                  key={String(loc.id)}
                  onClick={() => setSelected(loc)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? "border-site-primary bg-site-primary-container/20 shadow-sm"
                      : "border-site-outline-variant/10 bg-site-surface-container hover:bg-site-surface-container-high"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    {/* Sede Icon / Photo */}
                    <div className="relative w-12 h-12 rounded-lg overflow-hidden bg-site-surface-container-high shrink-0 border border-site-outline-variant/20 flex items-center justify-center">
                      {loc.image ? (
                        <Image
                          src={loc.image}
                          alt={loc.name}
                          fill
                          className="object-cover"
                          sizes="48px"
                        />
                      ) : (
                        <Home size={20} className={isSelected ? "text-site-primary" : "text-site-outline"} />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <h3 className="font-bold text-sm text-site-on-surface truncate leading-snug">
                          {loc.name}
                        </h3>
                        {loc.isMain && (
                          <span
                            className="text-3xs font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0"
                            style={{ background: "var(--site-cta-gradient)", color: "white" }}
                          >
                            {mainBadge}
                          </span>
                        )}
                      </div>

                      <p className="text-site-on-surface-variant text-xs mb-1.5 line-clamp-1 opacity-80 flex items-center gap-1">
                        <MapPin size={11} className="shrink-0 text-site-primary" />
                        <span className="truncate">{loc.address}</span>
                      </p>

                      {loc.city && (
                        <span className="inline-flex items-center gap-1 text-3xs font-semibold px-2 py-0.5 rounded-md bg-site-surface-container-highest text-site-on-surface-variant mb-1">
                          <Globe size={9} /> {loc.city}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Expanded details for selected sede */}
                  <AnimatePresence>
                    {isSelected && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="space-y-2.5 pt-3 mt-3 border-t border-site-outline-variant/10 overflow-hidden"
                      >
                        {loc.pastor && (
                          <div className="flex items-center gap-2 text-site-on-surface text-xs font-medium">
                            <User size={13} className="text-site-primary shrink-0" />
                            <span className="truncate">{loc.pastor}</span>
                          </div>
                        )}

                        {loc.schedule && (
                          <div className="flex items-center gap-2 text-site-on-surface-variant text-xs">
                            <Clock size={13} className="text-site-primary shrink-0" />
                            <span>{loc.schedule}</span>
                          </div>
                        )}

                        {loc.midweek && (
                          <div className="flex items-center gap-2 text-site-on-surface-variant text-xs">
                            <Calendar size={13} className="text-site-primary shrink-0" />
                            <span>{loc.midweek}</span>
                          </div>
                        )}

                        {loc.phone && (
                          <div className="flex items-center gap-2 text-site-on-surface-variant text-xs">
                            <Phone size={13} className="text-site-primary shrink-0" />
                            <a
                              href={`tel:${loc.phone}`}
                              onClick={(e) => e.stopPropagation()}
                              className="hover:underline hover:text-site-primary"
                            >
                              {loc.phone}
                            </a>
                          </div>
                        )}

                        <div className="flex items-center gap-2 pt-1">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              window.open(
                                loc.mapsUrl ||
                                  `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
                                    [loc.name, loc.address, loc.city || "Colombia"].filter(Boolean).join(", ")
                                  )}`,
                                "_blank",
                                "noopener,noreferrer"
                              );
                            }}
                            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-bold transition-opacity hover:opacity-95 shadow-2xs"
                            style={{ background: "var(--site-cta-gradient)", color: "white" }}
                          >
                            <Navigation size={13} />
                            {directionsCta}
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}

            {filtered.length === 0 && (
              <div className="rounded-xl border border-dashed border-site-outline-variant/20 p-4 text-center text-xs text-site-on-surface-variant">
                {emptySearch}
              </div>
            )}
          </div>
        )}
      </aside>

      {/* ── MAPA INTERACTIVO (Garantizado 100% visible) ──────────────────── */}
      <section className="flex-1 relative min-h-[50vh] md:h-[calc(100vh-88px)] md:sticky md:top-[88px] flex flex-col bg-site-surface-container-low overflow-hidden">
        {/* Floating Active Sede Overlay Header */}
        {activeSede && (
          <div className="absolute top-4 left-4 right-4 z-10 pointer-events-none">
            <div className="pointer-events-auto max-w-xl bg-site-surface-container-lowest/90 dark:bg-zinc-900/90 backdrop-blur-md p-3.5 rounded-2xl border border-site-outline-variant/20 shadow-lg flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-9 h-9 rounded-xl bg-site-primary/10 text-site-primary flex items-center justify-center shrink-0">
                  <MapPin size={18} />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <h2 className="font-bold text-xs text-site-on-surface truncate">
                      {activeSede.name}
                    </h2>
                    {activeSede.isMain && (
                      <span className="text-3xs font-semibold px-1.5 py-0.2 rounded bg-amber-500/20 text-amber-600 dark:text-amber-400">
                        Principal
                      </span>
                    )}
                  </div>
                  <p className="text-3xs text-site-on-surface-variant truncate opacity-80">
                    {activeSede.address || "Ubicación en el mapa"}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  type="button"
                  onClick={() => handleCopyAddress(activeSede.address)}
                  title="Copiar dirección"
                  className="p-2 rounded-xl bg-site-surface-container hover:bg-site-surface-container-high text-site-on-surface-variant text-xs transition-colors"
                >
                  {copied ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
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
                  className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-3xs font-bold uppercase tracking-wider text-white shadow-2xs hover:opacity-90 transition-opacity"
                  style={{ background: "var(--site-cta-gradient)" }}
                >
                  <Navigation size={11} />
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
          title={`Mapa de ${activeSede?.name || "Sedes El Faro"}`}
          style={{ minHeight: "50vh" }}
        />
      </section>
    </main>
  );
}
