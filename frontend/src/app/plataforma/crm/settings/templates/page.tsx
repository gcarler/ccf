"use client";

import React, { useState, useEffect } from "react";
import apiFetch from "@/lib/apiFetch";

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
  const [plantillas, setPlantillas] = useState<Plantilla[]>([]);
  const [categorias, setCategorias] = useState<Categoria[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState<Partial<Plantilla>>({});
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [catsRes, plantsRes] = await Promise.all([
        apiFetch("/api/crm/resources/categorias"),
        apiFetch("/api/crm/resources/plantillas")
      ]);
      setCategorias(catsRes);
      setPlantillas(plantsRes);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let createdPlantilla;
      if (formData.id) {
        createdPlantilla = await apiFetch(`/api/crm/resources/plantillas/${formData.id}`, {
          method: "PATCH",
          body: JSON.stringify(formData)
        });
      } else {
        createdPlantilla = await apiFetch("/api/crm/resources/plantillas", {
          method: "POST",
          body: JSON.stringify(formData)
        });
      }

      if (selectedFile && createdPlantilla?.id) {
        const formDataUpload = new FormData();
        formDataUpload.append("file", selectedFile);
        formDataUpload.append("nombre_recurso", "Adjunto Principal");
        
        await apiFetch(`/api/crm/resources/plantillas/${createdPlantilla.id}/adjuntos`, {
          method: "POST",
          headers: {}, // FormData headers are automatically set by browser
          body: formDataUpload
        }, false); // Ensure JSON parsing is handled properly if it's not JSON
      }

      setIsModalOpen(false);
      setSelectedFile(null);
      setFormData({});
      loadData();
    } catch (err) {
      console.error(err);
      alert("Error al guardar la plantilla");
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Plantillas de Mensajes</h1>
          <p className="text-sm text-gray-500">Configura plantillas para WhatsApp, Email y SMS.</p>
        </div>
        <button
          onClick={() => { setFormData({ canal: "WHATSAPP", variables_requeridas: [] }); setIsModalOpen(true); }}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md font-medium"
        >
          Nueva Plantilla
        </button>
      </div>

      {loading ? (
        <div className="text-center py-10">Cargando plantillas...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {plantillas.map(p => (
            <div key={p.id} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300 px-2 py-1 rounded">
                    {p.canal}
                  </span>
                </div>
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100">{p.titulo}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-2 line-clamp-3">
                  {p.contenido_texto}
                </p>
              </div>
              <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 flex justify-end">
                <button
                  onClick={() => { setFormData(p); setIsModalOpen(true); }}
                  className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 font-medium"
                >
                  Editar
                </button>
              </div>
            </div>
          ))}
          {plantillas.length === 0 && (
            <div className="col-span-full text-center py-12 bg-gray-50 dark:bg-gray-900 rounded-lg border border-dashed border-gray-300 dark:border-gray-700">
              <p className="text-gray-500">No hay plantillas creadas.</p>
            </div>
          )}
        </div>
      )}

      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                {formData.id ? "Editar Plantilla" : "Nueva Plantilla"}
              </h2>
            </div>
            
            <form onSubmit={handleSave} className="overflow-y-auto p-6 flex flex-col gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Categoría</label>
                <select
                  required
                  value={formData.categoria_id || ""}
                  onChange={e => setFormData({...formData, categoria_id: e.target.value})}
                  className="w-full border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2"
                >
                  <option value="">Selecciona una categoría</option>
                  {categorias.map(c => (
                    <option key={c.id} value={c.id}>{c.nombre}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Título Interno</label>
                <input
                  required
                  type="text"
                  value={formData.titulo || ""}
                  onChange={e => setFormData({...formData, titulo: e.target.value})}
                  className="w-full border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Canal</label>
                <select
                  required
                  value={formData.canal || "WHATSAPP"}
                  onChange={e => setFormData({...formData, canal: e.target.value})}
                  className="w-full border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2"
                >
                  <option value="WHATSAPP">WhatsApp</option>
                  <option value="EMAIL">Email</option>
                  <option value="SMS">SMS</option>
                </select>
              </div>

              {formData.canal === "EMAIL" && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Asunto</label>
                  <input
                    type="text"
                    value={formData.asunto || ""}
                    onChange={e => setFormData({...formData, asunto: e.target.value})}
                    className="w-full border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Contenido (Usa {'{{var}}'} para dinámicos)</label>
                <textarea
                  required
                  rows={4}
                  value={formData.contenido_texto || ""}
                  onChange={e => setFormData({...formData, contenido_texto: e.target.value})}
                  className="w-full border-gray-300 rounded-md shadow-sm dark:bg-gray-700 dark:border-gray-600 dark:text-white px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Archivo Adjunto (SeaweedFS)</label>
                <input
                  type="file"
                  onChange={e => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                />
              </div>

              <div className="pt-4 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-md font-medium"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md font-medium"
                >
                  Guardar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
