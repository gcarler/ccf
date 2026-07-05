import PublicCmsHead from "@/components/public/cms/PublicCmsHead";

export default function Head() {
  return (
    <PublicCmsHead
      slug="welcome"
      fallbackTitle="Mi Comunidad | Bienvenida"
      fallbackDescription="Un punto de partida para conocer la comunidad y dar tu siguiente paso."
    />
  );
}
