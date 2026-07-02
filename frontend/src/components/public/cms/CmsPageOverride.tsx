"use client";

import React from "react";

type CmsPageOverrideProps = {
    slug: string;
    children: React.ReactNode;
};

export default function CmsPageOverride({ children, slug: _slug }: CmsPageOverrideProps) {
    return <>{children}</>;
}
