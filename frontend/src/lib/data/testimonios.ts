export interface Testimonial {
    id: number;
    content: string;
    emotion?: string;
    media_type?: "text" | "image" | "video" | "podcast" | string;
    media_url?: string | null;
    image_url?: string | null;
    video_url?: string | null;
    podcast_url?: string | null;
    author?: { id: number; username: string; role?: string; avatarUrl?: string } | null;
    is_approved?: boolean;
    show_on_home?: boolean;
}