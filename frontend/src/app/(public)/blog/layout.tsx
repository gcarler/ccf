import type { Metadata } from "next";
import { publicCmsMetadata } from "@/lib/cms/publicMetadata";

export async function generateMetadata(): Promise<Metadata> {
  return publicCmsMetadata("blog");
}

export default function BlogLayout({ children }: { children: React.ReactNode }) {
  return children;
}
