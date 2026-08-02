import { Canvas, FabricImage } from "fabric";

export function handleImageDrop(e: DragEvent, canvas: Canvas, saveNow: (c: Canvas) => void) {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        if (file.type.startsWith("image/")) {
            insertImageFile(file, canvas, e.clientX, e.clientY, saveNow);
        }
    }
}

export function handleImagePaste(e: ClipboardEvent, canvas: Canvas, saveNow: (c: Canvas) => void) {
    if (e.clipboardData && e.clipboardData.items) {
        for (let i = 0; i < e.clipboardData.items.length; i++) {
            const item = e.clipboardData.items[i];
            if (item.type.startsWith("image/")) {
                e.preventDefault();
                const file = item.getAsFile();
                if (file) {
                    insertImageFile(file, canvas, window.innerWidth / 2, window.innerHeight / 2, saveNow);
                }
                break;
            }
        }
    }
}

export function insertImageFile(file: File, canvas: Canvas, clientX: number, clientY: number, saveNow: (c: Canvas) => void) {
    const reader = new FileReader();
    reader.onload = (f) => {
        const data = f.target?.result as string;
        FabricImage.fromURL(data).then((img: FabricImage) => {
            // Transform client coordinates to canvas coordinates
            const vpt = canvas.viewportTransform || [1, 0, 0, 1, 0, 0];
            const x = (clientX - vpt[4]) / vpt[0];
            const y = (clientY - vpt[5]) / vpt[3];
            
            // Resize if too large
            if (img.width! > 800) {
                img.scaleToWidth(800);
            }
            
            img.set({
                left: x,
                top: y,
                originX: "center",
                originY: "center",
                cornerStyle: "circle",
                transparentCorners: false,
                data: { shapeId: crypto.randomUUID(), type: "image" }
            });
            
            canvas.add(img);
            canvas.setActiveObject(img);
            canvas.renderAll();
            saveNow(canvas);
        });
    };
    reader.readAsDataURL(file);
}
