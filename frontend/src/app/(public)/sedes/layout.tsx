import type { Metadata } from "next";
import { publicCmsMetadata } from "@/lib/cms/publicMetadata";

export async function generateMetadata(): Promise<Metadata> {
    return publicCmsMetadata("locations");
}

export default function Layout({ children }: { children: React.ReactNode }) {
    return <>{children}</>;
}
