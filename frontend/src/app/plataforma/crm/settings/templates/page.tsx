"use client";

import React, { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/http";
import { useToast } from "@/context/ToastContext";
import SidePanel from "@/components/ui/SidePanel";

interface Plantilla {
  id: string;
  titulo: string;
  canal: string;
  asunto: string | null;
  contenido_texto: string;
  variables_requeridas: string[];
  activo: boolean;
  categoria_id: string;
}

interface Categoria {
  id: string;
  nombre: string;
}

export default function TemplatesPage() {
  const { addToast } = useToast();
  const [plantillas, setPlantillas] = useState<Plantilla[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [loading, setLoading] = useState(true);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState<Partial<Plantilla>>({});
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [catsRes, plantsRes] = await Promise.all([
        apiFetch<Categoria[]>("/crm/resources/categorias"),
        apiFetch<Plantilla[]>("/crm/resources/plantillas")
      ]);
      setCategorias(catsRes);
      setPlantillas(plantsRes);
    } catch (err) {
      console.error(err);
      addToast("No se pudieron cargar las plantillas y categorías", "error");
    } finally {
      setLoading(false);
    }
  }, [addToast]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let createdPlantilla;
      if (formData.id) {
        createdPlantilla = await apiFetch<Plantilla>(`/crm/resources/plantillas/${formData.id}`, {
          method: "PATCH",
          body: JSON.stringify(formData)
        });
      } else {
        createdPlantilla = await apiFetch<Plantilla>("/crm/resources/plantillas", {
          method: "POST",
          body: JSON.stringify(formData)
        });
      }

      if (selectedFile && createdPlantilla?.id) {
        const formDataUpload = new FormData();
        formDataUpload.append("file", selectedFile);
        formDataUpload.append("nombre_recurso", "Adjunto Principal");

        await apiFetch(`/crm/resources/plantillas/${createdPlantilla.id}/adjuntos`, {
          method: "POST",
          headers: {}, // FormData headers are automatically set by browser
          body: formDataUpload
        }, false); // Ensure JSON parsing is handled properly if it's not JSON
      }

      setIsModalOpen(false);
      setSelectedFile(null);
      setFormData({});
      loadData();
      addToast("Plantilla guardada", "success");
    } catch (err) {
      console.error(err);
      addToast("Error al guardar la plantilla", "error");
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[hsl(var(--text-primary))]">Plantillas de Mensajes</h1>
          <p className="text-sm text-[hsl(var(--text-secondary))]">Configura plantillas para WhatsApp, Email y SMS.</p>
        </div>
        <button
          onClick={() => { setFormData({ canal: "WHATSAPP", variables_requeridas: [] }); setIsModalOpen(true); }}
          className="bg-[hsl(var(--primary))] hover:opacity-90 text-[hsl(var(--primary-foreground))] px-4 py-2 rounded-md font-medium transition-opacity"
        >
          Nueva Plantilla
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-10 gap-3">
          <Loader2 size={20} className="animate-spin text-[hsl(var(--primary))]" />
          <span className="text-sm text-[hsl(var(--text-secondary))]">Cargando plantillas...</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plantillas.map(p => (
            <div key={p.id} className="bg-[hsl(var(--surface-1))] rounded-lg shadow-xs border border-[hsl(var(--border))] p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] px-2 py-1 rounded">
                    {p.canal}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-[hsl(var(--text-primary))]">{p.titulo}</h3>
                <p className="text-sm text-[hsl(var(--text-secondary))] mt-2 line-clamp-3">
                  {p.contenido_texto}
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-[hsl(var(--border))] flex justify-end">
                <button
                  onClick={() => { setFormData(p); setIsModalOpen(true); }}
                  className="text-sm text-[hsl(var(--primary))] hover:underline font-medium transition-all"
                >
                  Editar
                </button>
              </div>
            </div>
          ))}
          {plantillas.length === 0 && (
            <div className="col-span-full text-center py-12 bg-[hsl(var(--surface-2))] rounded-lg border border-dashed border-[hsl(var(--border))]">
              <p className="text-[hsl(var(--text-secondary))]">No hay plantillas creadas.</p>
            </div>
          )}
        </div>
      )}

      <SidePanel
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedFile(null);
          setFormData({});
        }}
        title={formData.id ? "Editar Plantilla" : "Nueva Plantilla"}
        subtitle="Configura el contenido y variables para este canal de comunicación"
        width="w-[520px]"
      >
        <form onSubmit={handleSave} className="flex flex-col gap-4 mt-2 pb-4">
          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text-primary))] mb-1">Categoría</label>
            <select
              required
              value={formData.categoria_id || ""}
              onChange={e => setFormData({...formData, categoria_id: e.target.value})}
              className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md shadow-xs text-[hsl(var(--text-primary))] px-3 py-2 outline-hidden focus:ring-2 focus:ring-[hsl(var(--primary)/0.3)] transition-all"
            >
              <option value="">Selecciona una categoría</option>
              {categorias.map(c => (
                <option key={c.id} value={c.id}>{c.nombre}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text-primary))] mb-1">Título Interno</label>
            <input
              required
              type="text"
              value={formData.titulo || ""}
              onChange={e => setFormData({...formData, titulo: e.target.value})}
              className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md shadow-xs text-[hsl(var(--text-primary))] px-3 py-2 outline-hidden focus:ring-2 focus:ring-[hsl(var(--primary)/0.3)] transition-all"
              placeholder="Ej: Bienvenida Nuevas Personas"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text-primary))] mb-1">Canal</label>
            <select
              required
              value={formData.canal || "WHATSAPP"}
              onChange={e => setFormData({...formData, canal: e.target.value})}
              className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md shadow-xs text-[hsl(var(--text-primary))] px-3 py-2 outline-hidden focus:ring-2 focus:ring-[hsl(var(--primary)/0.3)] transition-all"
            >
              <option value="WHATSAPP">WhatsApp</option>
              <option value="EMAIL">Email</option>
              <option value="SMS">SMS</option>
            </select>
          </div>

          {formData.canal === "EMAIL" && (
            <div>
              <label className="block text-sm font-medium text-[hsl(var(--text-primary))] mb-1">Asunto</label>
              <input
                type="text"
                value={formData.asunto || ""}
                onChange={e => setFormData({...formData, asunto: e.target.value})}
                className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md shadow-xs text-[hsl(var(--text-primary))] px-3 py-2 outline-hidden focus:ring-2 focus:ring-[hsl(var(--primary)/0.3)] transition-all"
                placeholder="Asunto del correo electrónico"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text-primary))] mb-1">Contenido (Usa {'{{var}}'} para dinámicos)</label>
            <textarea
              required
              rows={4}
              value={formData.contenido_texto || ""}
              onChange={e => setFormData({...formData, contenido_texto: e.target.value})}
              className="w-full bg-[hsl(var(--surface-1))] border border-[hsl(var(--border))] rounded-md shadow-xs text-[hsl(var(--text-primary))] px-3 py-2 outline-hidden focus:ring-2 focus:ring-[hsl(var(--primary)/0.3)] transition-all"
              placeholder="Escribe el mensaje..."
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[hsl(var(--text-primary))] mb-1">Archivo Adjunto (SeaweedFS)</label>
            <input
              type="file"
              onChange={e => setSelectedFile(e.target.files?.[0] || null)}
              className="w-full text-sm text-[hsl(var(--text-secondary))] file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-[hsl(var(--primary)/0.1)] file:text-[hsl(var(--primary))] hover:file:bg-[hsl(var(--primary)/0.2)] transition-colors cursor-pointer"
            />
          </div>

          <div className="pt-4 border-t border-[hsl(var(--border))] flex justify-end gap-3">
            <button
              type="button"
              onClick={() => {
                setIsModalOpen(false);
                setSelectedFile(null);
                setFormData({});
              }}
              className="px-4 py-2 text-[hsl(var(--text-secondary))] hover:bg-[hsl(var(--surface-2))] rounded-md font-medium transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-[hsl(var(--primary))] hover:opacity-90 text-[hsl(var(--primary-foreground))] rounded-md font-medium transition-opacity"
            >
              Guardar
            </button>
          </div>
        </form>
      </SidePanel>
    </div>
  );
}
