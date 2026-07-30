export function sanitizeText(text: string): string {
    return text.replace(/<[^>]*>/g, "");
}
