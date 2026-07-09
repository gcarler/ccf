export interface CourseItem {
    id: string;
    tag?: string;
    modality?: string;
    title: string;
    desc: string;
    excerpt?: string;
    cta?: string;
    lessons?: number;
    imageUrl?: string;
    syllabus?: string[];
    instructor?: string;
}

export interface BookItem {
    id: string;
    title: string;
    author: string;
    price: string;
    img: string;
    desc: string;
}
