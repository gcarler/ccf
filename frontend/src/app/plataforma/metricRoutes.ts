export function getPlatformMetricHref(title: string): string | null {
    const normalized = title.toLowerCase();
    if (normalized.includes('persona')) {
        return '/plataforma/crm/personas';
    }
    if (normalized.includes('proyecto') || normalized.includes('project')) {
        return '/plataforma/projects/list';
    }
    if (normalized.includes('pendient') || normalized.includes('pending')) {
        return '/plataforma/tasks';
    }
    if (normalized.includes('testimonio') || normalized.includes('testimonial')) {
        return '/plataforma/admin/testimonials';
    }
    return null;
}
