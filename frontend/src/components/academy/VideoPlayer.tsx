"use client";

import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, RotateCcw, Volume2, Maximize, Settings } from 'lucide-react';

interface VideoPlayerProps {
    src: string;
    onProgress: (percent: number, currentTime: number) => void;
    onComplete: () => void;
    initialTime?: number;
}

export default function VideoPlayer({ src, onProgress, onComplete, initialTime = 0 }: VideoPlayerProps) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [isPlaying, setIsPlaying] = useState(false);
    const [progress, setProgress] = useState(0);
    const [duration, setDuration] = useState(0);
    useEffect(() => {
        if (videoRef.current && initialTime > 0) {
            videoRef.current.currentTime = initialTime;
        }
    }, [initialTime]);

    const togglePlay = () => {
        if (videoRef.current) {
            if (isPlaying) videoRef.current.pause();
            else videoRef.current.play();
            setIsPlaying(!isPlaying);
        }
    };

    const handleTimeUpdate = () => {
        if (videoRef.current) {
            const current = videoRef.current.currentTime;
            const total = videoRef.current.duration;
            const percent = (current / total) * 100;
            setProgress(percent);
            onProgress(percent, current);

            if (percent >= 95) {
                onComplete();
            }
        }
    };

    const handleLoadedMetadata = () => {
        if (videoRef.current) {
            setDuration(videoRef.current.duration);
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="relative group bg-black rounded-lg overflow-hidden shadow-2xl aspect-video">
            <video
                ref={videoRef}
                src={src}
                className="w-full h-full cursor-pointer"
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onClick={togglePlay}
            />

            {/* Overlay Controls */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-4 space-y-3">
                {/* Progress Bar */}
                <div className="relative h-1.5 w-full bg-white/20 rounded-full cursor-pointer overflow-hidden">
                    <div
                        className="absolute top-0 left-0 h-full bg-[hsl(var(--primary))] transition-all duration-100"
                        style={{ width: `${progress}%` }}
                    />
                </div>

                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <button onClick={togglePlay} className="text-white hover:scale-110 transition-transform">
                            {isPlaying ? <Pause size={24} fill="currentColor" /> : <Play size={24} fill="currentColor" />}
                        </button>
                        <button className="text-white hover:rotate-12 transition-transform">
                            <RotateCcw size={20} />
                        </button>
                        <div className="text-white text-[12px] font-bold font-mono">
                            {formatTime(videoRef.current?.currentTime || 0)} / {formatTime(duration)}
                        </div>
                    </div>

                    <div className="flex items-center gap-4">
                        <button className="text-white"><Volume2 size={20} /></button>
                        <button className="text-white"><Settings size={20} /></button>
                        <button className="text-white"><Maximize size={20} /></button>
                    </div>
                </div>
            </div>

            {/* Big Play Button when paused */}
            {!isPlaying && (
                <div
                    onClick={togglePlay}
                    className="absolute inset-0 flex items-center justify-center bg-black/20 backdrop-blur-[2px] cursor-pointer"
                >
                    <div className="size-10 rounded-full bg-[hsl(var(--primary))] text-white flex items-center justify-center shadow-2xl shadow-[hsl(var(--info)/40%)] animate-pulse">
                        <Play size={32} fill="currentColor" className="ml-1" />
                    </div>
                </div>
            )}
        </div>
    );
}
