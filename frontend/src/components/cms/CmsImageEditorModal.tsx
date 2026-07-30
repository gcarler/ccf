"use client";

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
    X,
    RotateCcw,
    RotateCw,
    FlipHorizontal,
    FlipVertical,
    Crop,
    Sun,
    Contrast,
    Check,
    Save,
    RefreshCw
} from 'lucide-react';
import { toast } from 'sonner';
import { apiFetch } from '@/lib/http';

interface MediaItemData {
    id: string;
    url: string;
    filename: string;
    alt_text?: string;
    section?: string;
    tags?: string[];
    mime_type?: string;
    file_size?: number;
}

interface CmsImageEditorModalProps {
    item: MediaItemData;
    token: string | null;
    onClose: () => void;
    onSaveSuccess: (newItem: MediaItemData) => void;
}

interface CropBox {
    x: number; // percentage 0..100
    y: number; // percentage 0..100
    width: number; // percentage 0..100
    height: number; // percentage 0..100
}

export default function CmsImageEditorModal({
    item,
    token,
    onClose,
    onSaveSuccess,
}: CmsImageEditorModalProps) {
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const containerRef = useRef<HTMLDivElement | null>(null);

    const [loadedImage, setLoadedImage] = useState<HTMLImageElement | null>(null);
    const [saving, setSaving] = useState(false);

    // Adjustments state
    const [rotation, setRotation] = useState<number>(0);
    const [flipH, setFlipH] = useState<boolean>(false);
    const [flipV, setFlipV] = useState<boolean>(false);
    const [brightness, setBrightness] = useState<number>(0); // -100 to +100
    const [contrast, setContrast] = useState<number>(0); // -100 to +100

    // Crop overlay state
    const [isCropping, setIsCropping] = useState<boolean>(false);
    const [cropBox, setCropBox] = useState<CropBox>({ x: 10, y: 10, width: 80, height: 80 });
    const [activeHandle, setActiveHandle] = useState<string | null>(null);
    const dragStartRef = useRef<{ mouseX: number; mouseY: number; initialBox: CropBox } | null>(null);

    // Load initial image
    useEffect(() => {
        if (!item?.url) return;
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => {
            setLoadedImage(img);
        };
        img.onerror = () => {
            // Fallback load without crossOrigin if CORS header fails
            const fallbackImg = new Image();
            fallbackImg.onload = () => setLoadedImage(fallbackImg);
            fallbackImg.src = item.url;
        };
        img.src = item.url;
    }, [item.url]);

    // Draw canvas based on transformations & adjustments
    const renderCanvas = useCallback(() => {
        const canvas = canvasRef.current;
        if (!canvas || !loadedImage) return;
        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const isRotated90 = Math.abs(rotation % 180) === 90;
        const targetWidth = isRotated90 ? loadedImage.height : loadedImage.width;
        const targetHeight = isRotated90 ? loadedImage.width : loadedImage.height;

        canvas.width = targetWidth;
        canvas.height = targetHeight;

        ctx.save();
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Apply brightness and contrast filters
        const bPercent = 100 + brightness;
        const cPercent = 100 + contrast;
        ctx.filter = `brightness(${bPercent}%) contrast(${cPercent}%)`;

        // Transform origin
        ctx.translate(canvas.width / 2, canvas.height / 2);
        ctx.rotate((rotation * Math.PI) / 180);
        ctx.scale(flipH ? -1 : 1, flipV ? -1 : 1);

        ctx.drawImage(
            loadedImage,
            -loadedImage.width / 2,
            -loadedImage.height / 2,
            loadedImage.width,
            loadedImage.height
        );

        ctx.restore();
    }, [loadedImage, rotation, flipH, flipV, brightness, contrast]);

    useEffect(() => {
        renderCanvas();
    }, [renderCanvas]);

    // Handle rotation buttons
    const handleRotateLeft = () => setRotation((prev) => (prev - 90) % 360);
    const handleRotateRight = () => setRotation((prev) => (prev + 90) % 360);

    // Handle flip buttons
    const handleToggleFlipH = () => setFlipH((prev) => !prev);
    const handleToggleFlipV = () => setFlipV((prev) => !prev);

    // Apply crop selection onto canvas
    const handleApplyCrop = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const cropPixelX = Math.round((cropBox.x / 100) * canvas.width);
        const cropPixelY = Math.round((cropBox.y / 100) * canvas.height);
        const cropPixelW = Math.round((cropBox.width / 100) * canvas.width);
        const cropPixelH = Math.round((cropBox.height / 100) * canvas.height);

        if (cropPixelW <= 0 || cropPixelH <= 0) {
            toast.error("Área de recorte inválida");
            return;
        }

        const croppedCanvas = document.createElement('canvas');
        croppedCanvas.width = cropPixelW;
        croppedCanvas.height = cropPixelH;
        const croppedCtx = croppedCanvas.getContext('2d');
        if (!croppedCtx) return;

        croppedCtx.drawImage(
            canvas,
            cropPixelX,
            cropPixelY,
            cropPixelW,
            cropPixelH,
            0,
            0,
            cropPixelW,
            cropPixelH
        );

        const newImg = new Image();
        newImg.onload = () => {
            setLoadedImage(newImg);
            setRotation(0);
            setFlipH(false);
            setFlipV(false);
            setBrightness(0);
            setContrast(0);
            setIsCropping(false);
            setCropBox({ x: 10, y: 10, width: 80, height: 80 });
            toast.success("Recorte aplicado");
        };
        newImg.src = croppedCanvas.toDataURL('image/png');
    };

    // Save edited canvas to backend (non-destructive)
    const handleSaveChanges = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        setSaving(true);
        canvas.toBlob(async (blob) => {
            if (!blob) {
                toast.error("Error al exportar la imagen editada");
                setSaving(false);
                return;
            }

            try {
                const formData = new FormData();
                const mimeType = item.mime_type || 'image/png';
                const ext = mimeType.includes('jpeg') || mimeType.includes('jpg') ? '.jpg' : '.png';
                const filename = item.filename || `edited_image${ext}`;
                formData.append('file', blob, filename);

                if (item.alt_text) {
                    formData.append('alt_text', `${item.alt_text} (editado)`);
                }
                if (item.section) {
                    formData.append('section', item.section);
                }

                const newItem = await apiFetch<MediaItemData>(`/cms/media/${item.id}/edit`, {
                    method: 'POST',
                    token,
                    body: formData,
                });

                toast.success("Imagen editada guardada exitosamente");
                onSaveSuccess(newItem);
                onClose();
            } catch (err) {
                toast.error("Error al guardar la imagen editada");
            } finally {
                setSaving(false);
            }
        }, item.mime_type || 'image/png');
    };

    // Crop box mouse drag handlers
    const handleMouseDown = (e: React.MouseEvent, handle: string) => {
        e.stopPropagation();
        setActiveHandle(handle);
        dragStartRef.current = {
            mouseX: e.clientX,
            mouseY: e.clientY,
            initialBox: { ...cropBox },
        };
    };

    const handleMouseMove = useCallback((e: MouseEvent) => {
        if (!activeHandle || !dragStartRef.current || !containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        const deltaXPercent = ((e.clientX - dragStartRef.current.mouseX) / rect.width) * 100;
        const deltaYPercent = ((e.clientY - dragStartRef.current.mouseY) / rect.height) * 100;
        const { initialBox } = dragStartRef.current;

        let newBox = { ...initialBox };

        if (activeHandle === 'move') {
            newBox.x = Math.max(0, Math.min(100 - initialBox.width, initialBox.x + deltaXPercent));
            newBox.y = Math.max(0, Math.min(100 - initialBox.height, initialBox.y + deltaYPercent));
        } else {
            if (activeHandle.includes('left')) {
                const maxLeft = initialBox.x + initialBox.width - 5;
                const newX = Math.max(0, Math.min(maxLeft, initialBox.x + deltaXPercent));
                newBox.width = initialBox.width + (initialBox.x - newX);
                newBox.x = newX;
            }
            if (activeHandle.includes('right')) {
                const maxWidth = 100 - initialBox.x;
                newBox.width = Math.max(5, Math.min(maxWidth, initialBox.width + deltaXPercent));
            }
            if (activeHandle.includes('top')) {
                const maxTop = initialBox.y + initialBox.height - 5;
                const newY = Math.max(0, Math.min(maxTop, initialBox.y + deltaYPercent));
                newBox.height = initialBox.height + (initialBox.y - newY);
                newBox.y = newY;
            }
            if (activeHandle.includes('bottom')) {
                const maxHeight = 100 - initialBox.y;
                newBox.height = Math.max(5, Math.min(maxHeight, initialBox.height + deltaYPercent));
            }
        }

        setCropBox(newBox);
    }, [activeHandle]);

    const handleMouseUp = useCallback(() => {
        setActiveHandle(null);
        dragStartRef.current = null;
    }, []);

    useEffect(() => {
        if (activeHandle) {
            window.addEventListener('mousemove', handleMouseMove);
            window.addEventListener('mouseup', handleMouseUp);
        }
        return () => {
            window.removeEventListener('mousemove', handleMouseMove);
            window.removeEventListener('mouseup', handleMouseUp);
        };
    }, [activeHandle, handleMouseMove, handleMouseUp]);

    const resetAdjustments = () => {
        setBrightness(0);
        setContrast(0);
        setRotation(0);
        setFlipH(false);
        setFlipV(false);
    };

    return (
        <div className="fixed inset-0 z-50 flex flex-col bg-black/95 text-white backdrop-blur-md">
            {/* Modal Header */}
            <header className="flex h-14 items-center justify-between border-b border-white/10 px-6 bg-neutral-900/80">
                <div className="flex items-center gap-3">
                    <Crop className="size-5 text-blue-400" />
                    <h2 className="text-sm font-semibold tracking-wide uppercase">
                        Editor de Imagen: <span className="text-neutral-400">{item.filename}</span>
                    </h2>
                </div>
                <div className="flex items-center gap-3">
                    <button
                        onClick={onClose}
                        className="p-2 text-neutral-400 hover:text-white rounded-lg hover:bg-white/10 transition-colors"
                        title="Cerrar editor"
                    >
                        <X size={20} />
                    </button>
                    <button
                        onClick={handleSaveChanges}
                        disabled={saving || !loadedImage}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold uppercase tracking-wide flex items-center gap-2 shadow-lg disabled:opacity-50 transition-all"
                    >
                        <Save size={16} />
                        {saving ? 'Guardando...' : 'Guardar Cambios'}
                    </button>
                </div>
            </header>

            {/* Main Editor Body */}
            <div className="flex flex-1 overflow-hidden">
                {/* Center Canvas Area */}
                <div className="flex-1 flex flex-col items-center justify-center p-6 relative bg-neutral-950/60 overflow-auto select-none">
                    {!loadedImage ? (
                        <div className="flex flex-col items-center gap-3 text-neutral-400">
                            <RefreshCw className="animate-spin size-8" />
                            <p className="text-xs uppercase tracking-wide">Cargando lienzo de imagen...</p>
                        </div>
                    ) : (
                        <div
                            ref={containerRef}
                            className="relative inline-block border border-white/10 shadow-2xl rounded-sm max-w-full max-h-full"
                        >
                            <canvas
                                ref={canvasRef}
                                className="max-w-[70vw] max-h-[70vh] object-contain block"
                            />

                            {/* Crop Interactive Overlay */}
                            {isCropping && (
                                <div className="absolute inset-0 pointer-events-auto">
                                    {/* Darkened unselected mask */}
                                    <div
                                        className="absolute bg-black/60"
                                        style={{ top: 0, left: 0, right: 0, height: `${cropBox.y}%` }}
                                    />
                                    <div
                                        className="absolute bg-black/60"
                                        style={{
                                            top: `${cropBox.y}%`,
                                            left: 0,
                                            width: `${cropBox.x}%`,
                                            height: `${cropBox.height}%`,
                                        }}
                                    />
                                    <div
                                        className="absolute bg-black/60"
                                        style={{
                                            top: `${cropBox.y}%`,
                                            right: 0,
                                            width: `${100 - cropBox.x - cropBox.width}%`,
                                            height: `${cropBox.height}%`,
                                        }}
                                    />
                                    <div
                                        className="absolute bg-black/60"
                                        style={{
                                            bottom: 0,
                                            left: 0,
                                            right: 0,
                                            height: `${100 - cropBox.y - cropBox.height}%`,
                                        }}
                                    />

                                    {/* Crop Box Window */}
                                    <div
                                        onMouseDown={(e) => handleMouseDown(e, 'move')}
                                        className="absolute border-2 border-blue-400 cursor-move box-border shadow-outline"
                                        style={{
                                            top: `${cropBox.y}%`,
                                            left: `${cropBox.x}%`,
                                            width: `${cropBox.width}%`,
                                            height: `${cropBox.height}%`,
                                        }}
                                    >
                                        {/* Grid lines inside crop box */}
                                        <div className="absolute inset-0 grid grid-cols-3 grid-rows-3 pointer-events-none opacity-30">
                                            <div className="border-r border-b border-blue-200" />
                                            <div className="border-r border-b border-blue-200" />
                                            <div className="border-b border-blue-200" />
                                            <div className="border-r border-b border-blue-200" />
                                            <div className="border-r border-b border-blue-200" />
                                            <div className="border-b border-blue-200" />
                                            <div className="border-r border-blue-200" />
                                            <div className="border-r border-blue-200" />
                                            <div />
                                        </div>

                                        {/* Resize Handles */}
                                        {[
                                            { handle: 'top-left', pos: '-top-1.5 -left-1.5 cursor-nwse-resize' },
                                            { handle: 'top-right', pos: '-top-1.5 -right-1.5 cursor-nesw-resize' },
                                            { handle: 'bottom-left', pos: '-bottom-1.5 -left-1.5 cursor-nesw-resize' },
                                            { handle: 'bottom-right', pos: '-bottom-1.5 -right-1.5 cursor-nwse-resize' },
                                            { handle: 'top', pos: '-top-1.5 left-1/2 -translate-x-1/2 cursor-ns-resize' },
                                            { handle: 'bottom', pos: '-bottom-1.5 left-1/2 -translate-x-1/2 cursor-ns-resize' },
                                            { handle: 'left', pos: 'top-1/2 -left-1.5 -translate-y-1/2 cursor-ew-resize' },
                                            { handle: 'right', pos: 'top-1/2 -right-1.5 -translate-y-1/2 cursor-ew-resize' },
                                        ].map(({ handle, pos }) => (
                                            <div
                                                key={handle}
                                                onMouseDown={(e) => handleMouseDown(e, handle)}
                                                className={`absolute size-3 bg-blue-500 border border-white rounded-full ${pos}`}
                                            />
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Bottom Crop Controls Bar */}
                    {isCropping && (
                        <div className="mt-4 flex items-center gap-3 bg-neutral-900/90 backdrop-blur border border-white/10 px-4 py-2 rounded-full shadow-2xl">
                            <span className="text-xs font-medium text-neutral-300">Modo Recorte Activo</span>
                            <button
                                onClick={handleApplyCrop}
                                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded-full text-xs font-semibold uppercase tracking-wide flex items-center gap-1.5"
                            >
                                <Check size={14} /> Aplicar recorte
                            </button>
                            <button
                                onClick={() => setIsCropping(false)}
                                className="px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded-full text-xs font-semibold uppercase tracking-wide"
                            >
                                Cancelar
                            </button>
                        </div>
                    )}
                </div>

                {/* Right Controls Sidebar */}
                <aside className="w-80 border-l border-white/10 bg-neutral-900/90 p-5 overflow-y-auto space-y-6">
                    {/* Recorte (Crop) Section */}
                    <div className="space-y-3">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-400 flex items-center gap-2">
                            <Crop size={14} className="text-blue-400" /> Recorte (Crop)
                        </h3>
                        <div className="space-y-2">
                            <button
                                onClick={() => setIsCropping((prev) => !prev)}
                                className={`w-full py-2.5 px-3 rounded-lg text-xs font-semibold uppercase tracking-wide border flex items-center justify-center gap-2 transition-all ${
                                    isCropping
                                        ? 'bg-blue-600/20 border-blue-500 text-blue-300'
                                        : 'bg-neutral-800/80 border-white/10 hover:bg-neutral-800 text-neutral-200'
                                }`}
                            >
                                <Crop size={16} />
                                {isCropping ? 'Desactivar Recorte' : 'Activar Recorte'}
                            </button>
                            {isCropping && (
                                <button
                                    onClick={handleApplyCrop}
                                    className="w-full py-2 px-3 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold uppercase tracking-wide flex items-center justify-center gap-2 shadow"
                                >
                                    <Check size={14} /> Aplicar Recorte
                                </button>
                            )}
                        </div>
                    </div>

                    <hr className="border-white/10" />

                    {/* Rotación (Rotation) Section */}
                    <div className="space-y-3">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-400 flex items-center gap-2">
                            <RotateCw size={14} className="text-blue-400" /> Rotación
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            <button
                                onClick={handleRotateLeft}
                                className="py-2.5 px-3 bg-neutral-800/80 hover:bg-neutral-800 border border-white/10 rounded-lg text-xs font-semibold uppercase tracking-wide flex items-center justify-center gap-2"
                            >
                                <RotateCcw size={16} /> -90°
                            </button>
                            <button
                                onClick={handleRotateRight}
                                className="py-2.5 px-3 bg-neutral-800/80 hover:bg-neutral-800 border border-white/10 rounded-lg text-xs font-semibold uppercase tracking-wide flex items-center justify-center gap-2"
                            >
                                <RotateCw size={16} /> +90°
                            </button>
                        </div>
                    </div>

                    <hr className="border-white/10" />

                    {/* Brillo / Contraste (Brightness / Contrast) Section */}
                    <div className="space-y-4">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-400 flex items-center gap-2">
                            <Sun size={14} className="text-blue-400" /> Brillo / Contraste
                        </h3>
                        <div className="space-y-2">
                            <div className="flex justify-between text-xs font-semibold text-neutral-300">
                                <span className="flex items-center gap-1.5">
                                    <Sun size={13} /> Brillo
                                </span>
                                <span>{brightness > 0 ? `+${brightness}` : brightness}</span>
                            </div>
                            <input
                                type="range"
                                min="-100"
                                max="100"
                                value={brightness}
                                onChange={(e) => setBrightness(Number(e.target.value))}
                                className="w-full h-1.5 bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                            />
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between text-xs font-semibold text-neutral-300">
                                <span className="flex items-center gap-1.5">
                                    <Contrast size={13} /> Contraste
                                </span>
                                <span>{contrast > 0 ? `+${contrast}` : contrast}</span>
                            </div>
                            <input
                                type="range"
                                min="-100"
                                max="100"
                                value={contrast}
                                onChange={(e) => setContrast(Number(e.target.value))}
                                className="w-full h-1.5 bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
                            />
                        </div>
                    </div>

                    <hr className="border-white/10" />

                    {/* Voltear (Flip) Section */}
                    <div className="space-y-3">
                        <h3 className="text-xs font-bold uppercase tracking-wider text-neutral-400 flex items-center gap-2">
                            <FlipHorizontal size={14} className="text-blue-400" /> Voltear (Flip)
                        </h3>
                        <div className="grid grid-cols-2 gap-2">
                            <button
                                onClick={handleToggleFlipH}
                                className={`py-2.5 px-3 rounded-lg text-xs font-semibold uppercase tracking-wide border flex items-center justify-center gap-2 transition-all ${
                                    flipH
                                        ? 'bg-blue-600/20 border-blue-500 text-blue-300'
                                        : 'bg-neutral-800/80 border-white/10 hover:bg-neutral-800 text-neutral-200'
                                }`}
                            >
                                <FlipHorizontal size={16} /> Horizontal
                            </button>
                            <button
                                onClick={handleToggleFlipV}
                                className={`py-2.5 px-3 rounded-lg text-xs font-semibold uppercase tracking-wide border flex items-center justify-center gap-2 transition-all ${
                                    flipV
                                        ? 'bg-blue-600/20 border-blue-500 text-blue-300'
                                        : 'bg-neutral-800/80 border-white/10 hover:bg-neutral-800 text-neutral-200'
                                }`}
                            >
                                <FlipVertical size={16} /> Vertical
                            </button>
                        </div>
                    </div>

                    <hr className="border-white/10" />

                    {/* Reset button */}
                    <button
                        onClick={resetAdjustments}
                        className="w-full py-2 px-3 bg-neutral-800 hover:bg-neutral-700 text-neutral-400 hover:text-white rounded-lg text-xs font-semibold uppercase tracking-wide flex items-center justify-center gap-2"
                    >
                        <RefreshCw size={14} /> Restablecer Ajustes
                    </button>
                </aside>
            </div>
        </div>
    );
}
