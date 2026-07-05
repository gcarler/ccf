import PublicCmsHead from "@/components/public/cms/PublicCmsHead";

export default function Head() {
  return (
    <PublicCmsHead
      slug="boletin"
      fallbackTitle="Mi Comunidad | Boletín Semanal"
      fallbackDescription="Recibe cada semana una reflexión bíblica y consejos prácticos."
    />
  );
}
