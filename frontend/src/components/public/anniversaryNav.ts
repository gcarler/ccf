export type AnniversaryNavItem = {
  href: string;
  label: string;
};

/** Navegación propia de la landing pública del aniversario. */
export const ANNIVERSARY_NAV_ITEMS: AnniversaryNavItem[] = [
  { href: "/aniversario40", label: "Inicio" },
  { href: "/aniversario40#agenda", label: "Agenda" },
  { href: "/aniversario40#timeline", label: "Nuestra historia" },
  { href: "/aniversario40#galeria", label: "Galería" },
  { href: "/aniversario40#muro-gratitud", label: "Comparte tu historia" },
];
