import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { SidebarLayerProvider } from "@/context/SidebarLayerContext";
import type { ProjectFileRecord } from "@/types/projects";
import { ProjectFileViewerDrawer } from "./ProjectFileViewerDrawer";

const imageFile: ProjectFileRecord = {
  id: "file-image-1",
  project_id: "project-1",
  name: "Plano del proyecto.png",
  category: "diseño",
  file_source: "local",
  file_url: "/files/plan.png",
  file_type: "image/png",
  created_at: "2026-10-04T12:00:00Z",
};

function renderViewer(file: ProjectFileRecord) {
  return render(
    <SidebarLayerProvider>
      <ProjectFileViewerDrawer file={file} isOpen onClose={vi.fn()} />
    </SidebarLayerProvider>,
  );
}

describe("ProjectFileViewerDrawer", () => {
  it("exposes named image controls and supports zoom and rotation by keyboard-accessible buttons", async () => {
    const user = userEvent.setup();
    const { container } = renderViewer(imageFile);

    expect(screen.getByRole("dialog", { name: "Visor Universal Embebido" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: imageFile.name })).toHaveClass(
      "text-[hsl(var(--text-primary))]",
    );
    const image = screen.getByRole("img", { name: imageFile.name });
    expect(image).toHaveStyle({ transform: "scale(1) rotate(0deg)" });

    await user.click(screen.getByRole("button", { name: "Acercar" }));
    expect(image).toHaveStyle({ transform: "scale(1.25) rotate(0deg)" });
    await user.click(screen.getByRole("button", { name: "Rotar 90°" }));
    expect(image).toHaveStyle({ transform: "scale(1.25) rotate(90deg)" });
    expect((await axe(container)).violations).toEqual([]);
  });

  it("uses a semantic surface token for the video letterbox background", () => {
    const videoFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-video-1",
      name: "Presentación.mp4",
      file_url: "/files/presentation.mp4",
      file_type: "video/mp4",
    };
    renderViewer(videoFile);

    const video = document.querySelector("video");
    expect(video).not.toBeNull();
    expect(video).toHaveClass("bg-[hsl(var(--surface-2))]");
    expect(video).not.toHaveClass("bg-black");
  });

  it("does not embed an unsafe historical Drive preview URL", () => {
    const driveFile: ProjectFileRecord = {
      ...imageFile,
      id: "file-drive-1",
      name: "Minuta de comité.pdf",
      file_source: "drive",
      file_url: "https://drive.google.com/file/d/abc123/view",
      embed_url: "javascript:alert(document.domain)",
      file_type: "application/pdf",
    };
    renderViewer(driveFile);

    expect(screen.getByTitle(driveFile.name)).toHaveAttribute(
      "src",
      driveFile.file_url,
    );
  });

  it("blocks unsafe historical file URLs instead of rendering active content", () => {
    const unsafeFile: ProjectFileRecord = {
      ...imageFile,
      file_url: "javascript:alert(document.domain)",
    };
    renderViewer(unsafeFile);

    expect(screen.getByRole("alert")).toHaveTextContent(/enlace.*se bloqueó/i);
    expect(document.querySelector("iframe, img, audio, video, a[href]")).toBeNull();
  });
});
