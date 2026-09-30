'use client';

import React, { useRef, useState } from 'react';
import { AlertCircle, FileText, Loader2, Trash2, UploadCloud } from 'lucide-react';
import {
  SurveyFileUploadResult,
  SurveyQuestion,
  SurveyQuestionType,
} from './types';
import {
  QuestionValue,
  fileAllowed,
  parseOption,
  parseRowCol,
} from './surveyHelpers';

interface QuestionRendererProps {
  question: SurveyQuestion;
  value: QuestionValue | undefined;
  onChange: (next: QuestionValue) => void;
  /** Marcar visualmente el campo por obligatoriedad incumplida. */
  highlightMissing: boolean;
  /** Sube el archivo al backend y devuelve el resultado canónico. */
  onUpload: (question: SurveyQuestion, file: File) => Promise<SurveyFileUploadResult>;
}

/**
 * Renderiza una pregunta canónica de encuesta (11 tipos + sección).
 * Todos los controles usan tokens semánticos del Design System.
 */
export default function QuestionRenderer({
  question,
  value,
  onChange,
  highlightMissing,
  onUpload,
}: QuestionRendererProps) {
  if (question.tipo_pregunta === SurveyQuestionType.SECCION_SALTO) {
    return (
      <section className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] p-5">
        <h3 className="text-base font-semibold text-[hsl(var(--text-primary))]">{question.titulo}</h3>
        {question.descripcion ? (
          <p className="mt-1 text-sm text-[hsl(var(--text-secondary))]">{question.descripcion}</p>
        ) : null}
      </section>
    );
  }

  return (
    <fieldset className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-5">
      <legend className="sr-only">{question.titulo}</legend>
      <div className="mb-3">
        <span className="block text-sm font-semibold text-[hsl(var(--text-primary))]">
          {`${question.titulo}${question.es_requerida ? ' *' : ''}`}
          {!question.es_requerida ? (
            <span className="ml-2 text-xs font-normal text-[hsl(var(--text-secondary))]">(opcional)</span>
          ) : null}
        </span>
        {question.descripcion ? (
          <span className="mt-0.5 block text-xs text-[hsl(var(--text-secondary))]">{question.descripcion}</span>
        ) : null}
      </div>
      <QuestionInput
        question={question}
        value={value}
        onChange={onChange}
        highlightMissing={highlightMissing && question.es_requerida}
        onUpload={onUpload}
      />
    </fieldset>
  );
}

function QuestionInput({
  question,
  value,
  onChange,
  highlightMissing,
  onUpload,
}: QuestionRendererProps & { highlightMissing: boolean }) {
  const invalid = highlightMissing;

  switch (question.tipo_pregunta) {
    case SurveyQuestionType.TEXTO_CORTO:
      return (
        <TextInput
          question={question}
          value={value?.kind === 'text' ? value.text : ''}
          onChange={(text) => onChange({ kind: 'text', text })}
          invalid={invalid}
        />
      );
    case SurveyQuestionType.PARRAFO:
      return (
        <ParagraphInput
          question={question}
          value={value?.kind === 'text' ? value.text : ''}
          onChange={(text) => onChange({ kind: 'text', text })}
          invalid={invalid}
        />
      );
    case SurveyQuestionType.OPCION_MULTIPLE:
      return <RadioInput question={question} value={value} onChange={onChange} invalid={invalid} />;
    case SurveyQuestionType.CASILLAS:
      return <CheckboxInput question={question} value={value} onChange={onChange} invalid={invalid} />;
    case SurveyQuestionType.DESPLEGABLE:
      return <DropdownInput question={question} value={value} onChange={onChange} invalid={invalid} />;
    case SurveyQuestionType.ESCALA_LINEAL:
      return <ScaleInput question={question} value={value} onChange={onChange} invalid={invalid} />;
    case SurveyQuestionType.CUADRICULA_RADIO:
      return <GridRadioInput question={question} value={value} onChange={onChange} invalid={invalid} />;
    case SurveyQuestionType.CUADRICULA_CASILLAS:
      return <GridCheckboxInput question={question} value={value} onChange={onChange} invalid={invalid} />;
    case SurveyQuestionType.FECHA:
      return (
        <DateInput
          question={question}
          value={value?.kind === 'date' ? value.date : ''}
          onChange={(date) => onChange({ kind: 'date', date })}
          invalid={invalid}
        />
      );
    case SurveyQuestionType.HORA:
      return (
        <TimeInput
          question={question}
          value={value?.kind === 'time' ? value.time : ''}
          onChange={(time) => onChange({ kind: 'time', time })}
          invalid={invalid}
        />
      );
    case SurveyQuestionType.SUBIR_ARCHIVO:
      return <FileInput question={question} value={value} onChange={onChange} onUpload={onUpload} invalid={invalid} />;
    default:
      return null;
  }
}

const inputClass = (invalid: boolean) =>
  `w-full rounded-lg border bg-[hsl(var(--surface-1))] px-3 py-2 text-sm text-[hsl(var(--text-primary))] placeholder:text-[hsl(var(--text-secondary))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--primary))] ${
    invalid ? 'border-[hsl(var(--destructive))]' : 'border-[hsl(var(--border))]'
  }`;

function FieldError({ show, children }: { show: boolean; children: React.ReactNode }) {
  if (!show) return null;
  return (
    <p role="alert" className="mt-2 flex items-center gap-1 text-xs font-medium text-[hsl(var(--destructive))]">
      <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
      {children}
    </p>
  );
}

function TextInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: string;
  onChange: (text: string) => void;
  invalid: boolean;
}) {
  return (
    <div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label={question.titulo}
        aria-invalid={invalid || undefined}
        placeholder="Tu respuesta"
        className={inputClass(invalid)}
      />
      <FieldError show={invalid}>Esta pregunta es obligatoria</FieldError>
    </div>
  );
}

function ParagraphInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: string;
  onChange: (text: string) => void;
  invalid: boolean;
}) {
  return (
    <div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label={question.titulo}
        aria-invalid={invalid || undefined}
        rows={4}
        placeholder="Tu respuesta"
        className={inputClass(invalid)}
      />
      <FieldError show={invalid}>Esta pregunta es obligatoria</FieldError>
    </div>
  );
}

function RadioInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: QuestionValue | undefined;
  onChange: (next: QuestionValue) => void;
  invalid: boolean;
}) {
  const options = (question.opciones || []).map(parseOption);
  const current = value?.kind === 'choice' ? value.optionId : null;
  return (
    <div className={invalid ? 'rounded-lg border border-[hsl(var(--destructive))] p-3' : ''}>
      <div role="radiogroup" aria-label={question.titulo} className="flex flex-col gap-2">
        {options.map((opt) => (
          <label key={opt.id} className="inline-flex cursor-pointer items-center gap-2 text-sm text-[hsl(var(--text-primary))]">
            <input
              type="radio"
              name={question.id}
              checked={current === opt.id}
              onChange={() => onChange({ kind: 'choice', optionId: opt.id })}
              className="h-4 w-4 border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
            />
            {opt.label}
          </label>
        ))}
      </div>
      <FieldError show={invalid}>Selecciona una opción</FieldError>
    </div>
  );
}

function CheckboxInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: QuestionValue | undefined;
  onChange: (next: QuestionValue) => void;
  invalid: boolean;
}) {
  const options = (question.opciones || []).map(parseOption);
  const current = value?.kind === 'multi' ? value.optionIds : [];
  const toggle = (optionId: string) => {
    const next = current.includes(optionId) ? current.filter((id) => id !== optionId) : [...current, optionId];
    onChange({ kind: 'multi', optionIds: next });
  };
  return (
    <div className={invalid ? 'rounded-lg border border-[hsl(var(--destructive))] p-3' : ''}>
      <div className="flex flex-col gap-2">
        {options.map((opt) => (
          <label key={opt.id} className="inline-flex cursor-pointer items-center gap-2 text-sm text-[hsl(var(--text-primary))]">
            <input
              type="checkbox"
              checked={current.includes(opt.id)}
              onChange={() => toggle(opt.id)}
              className="h-4 w-4 rounded border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
            />
            {opt.label}
          </label>
        ))}
      </div>
      <FieldError show={invalid}>Selecciona al menos una opción</FieldError>
    </div>
  );
}

function DropdownInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: QuestionValue | undefined;
  onChange: (next: QuestionValue) => void;
  invalid: boolean;
}) {
  const options = (question.opciones || []).map(parseOption);
  const current = value?.kind === 'choice' && value.optionId ? value.optionId : '';
  return (
    <div>
      <select
        aria-label={question.titulo}
        value={current}
        onChange={(e) => onChange({ kind: 'choice', optionId: e.target.value || null })}
        className={inputClass(invalid)}
      >
        <option value="">Selecciona una opción…</option>
        {options.map((opt) => (
          <option key={opt.id} value={opt.id}>
            {opt.label}
          </option>
        ))}
      </select>
      <FieldError show={invalid}>Selecciona una opción</FieldError>
    </div>
  );
}

function ScaleInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: QuestionValue | undefined;
  onChange: (next: QuestionValue) => void;
  invalid: boolean;
}) {
  const min = question.escala_min ?? 1;
  const max = question.escala_max ?? 5;
  const current = value?.kind === 'scale' ? value.value : null;
  const scaleValues: number[] = [];
  for (let v = min; v <= max; v += 1) scaleValues.push(v);
  return (
    <div>
      <div role="radiogroup" aria-label={question.titulo} className="flex flex-wrap items-center gap-3">
        {scaleValues.map((v) => (
          <label key={v} className="inline-flex cursor-pointer flex-col items-center gap-1">
            <span className="text-xs font-medium text-[hsl(var(--text-secondary))]">{v}</span>
            <input
              type="radio"
              name={question.id}
              checked={current === v}
              onChange={() => onChange({ kind: 'scale', value: v })}
              className="h-4 w-4 border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
            />
          </label>
        ))}
      </div>
      <div className="mt-1 flex items-center justify-between text-xs text-[hsl(var(--text-secondary))]">
        <span>{question.escala_min_etiqueta || ''}</span>
        <span>{question.escala_max_etiqueta || ''}</span>
      </div>
      <FieldError show={invalid}>Selecciona un valor de la escala</FieldError>
    </div>
  );
}

function GridRadioInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: QuestionValue | undefined;
  onChange: (next: QuestionValue) => void;
  invalid: boolean;
}) {
  const rows = (question.filas || []).map(parseRowCol);
  const cols = (question.columnas || []).map(parseRowCol);
  const current = value?.kind === 'grid' ? value.radio : {};
  const setCell = (rowId: string, colId: string) => onChange({ kind: 'grid', radio: { ...current, [rowId]: colId }, checks: value?.kind === 'grid' ? value.checks : {} });
  return (
    <div className={invalid ? 'rounded-lg border border-[hsl(var(--destructive))] p-2' : 'overflow-x-auto'}>
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th scope="col" className="px-2 py-2 text-left font-medium text-[hsl(var(--text-secondary))]"></th>
            {cols.map((c) => (
              <th key={c.id} scope="col" className="px-2 py-2 text-center text-xs font-medium text-[hsl(var(--text-secondary))]">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-[hsl(var(--border))]">
              <th scope="row" className="px-2 py-2 text-left text-sm font-medium text-[hsl(var(--text-primary))]">
                {r.label}
              </th>
              {cols.map((c) => (
                <td key={c.id} className="px-2 py-2 text-center">
                  <input
                    type="radio"
                    name={`${question.id}_${r.id}`}
                    aria-label={`${r.label}: ${c.label}`}
                    checked={current[r.id] === c.id}
                    onChange={() => setCell(r.id, c.id)}
                    className="h-4 w-4 border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <FieldError show={invalid}>Responde todas las filas obligatorias</FieldError>
    </div>
  );
}

function GridCheckboxInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: QuestionValue | undefined;
  onChange: (next: QuestionValue) => void;
  invalid: boolean;
}) {
  const rows = (question.filas || []).map(parseRowCol);
  const cols = (question.columnas || []).map(parseRowCol);
  const current = value?.kind === 'grid' ? value.checks : {};
  const radio = value?.kind === 'grid' ? value.radio : {};
  const toggleCell = (rowId: string, colId: string) => {
    const rowCols = current[rowId] ?? [];
    const next = rowCols.includes(colId) ? rowCols.filter((id) => id !== colId) : [...rowCols, colId];
    onChange({ kind: 'grid', radio, checks: { ...current, [rowId]: next } });
  };
  return (
    <div className={invalid ? 'rounded-lg border border-[hsl(var(--destructive))] p-2' : 'overflow-x-auto'}>
      <table className="w-full text-sm">
        <thead>
          <tr>
            <th scope="col" className="px-2 py-2 text-left font-medium text-[hsl(var(--text-secondary))]"></th>
            {cols.map((c) => (
              <th key={c.id} scope="col" className="px-2 py-2 text-center text-xs font-medium text-[hsl(var(--text-secondary))]">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-t border-[hsl(var(--border))]">
              <th scope="row" className="px-2 py-2 text-left text-sm font-medium text-[hsl(var(--text-primary))]">
                {r.label}
              </th>
              {cols.map((c) => (
                <td key={c.id} className="px-2 py-2 text-center">
                  <input
                    type="checkbox"
                    aria-label={`${r.label}: ${c.label}`}
                    checked={(current[r.id] ?? []).includes(c.id)}
                    onChange={() => toggleCell(r.id, c.id)}
                    className="h-4 w-4 rounded border-[hsl(var(--border))] text-[hsl(var(--primary))] focus:ring-[hsl(var(--primary))]"
                  />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <FieldError show={invalid}>Marca al menos una casilla</FieldError>
    </div>
  );
}

function DateInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: string;
  onChange: (date: string) => void;
  invalid: boolean;
}) {
  return (
    <div>
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label={question.titulo}
        aria-invalid={invalid || undefined}
        className={inputClass(invalid)}
      />
      <FieldError show={invalid}>Selecciona una fecha</FieldError>
    </div>
  );
}

function TimeInput({
  question,
  value,
  onChange,
  invalid,
}: {
  question: SurveyQuestion;
  value: string;
  onChange: (time: string) => void;
  invalid: boolean;
}) {
  return (
    <div>
      <input
        type="time"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label={question.titulo}
        aria-invalid={invalid || undefined}
        className={inputClass(invalid)}
      />
      <FieldError show={invalid}>Selecciona una hora</FieldError>
    </div>
  );
}

function FileInput({
  question,
  value,
  onChange,
  onUpload,
  invalid,
}: {
  question: SurveyQuestion;
  value: QuestionValue | undefined;
  onChange: (next: QuestionValue) => void;
  onUpload: (question: SurveyQuestion, file: File) => Promise<SurveyFileUploadResult>;
  invalid: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const files = value?.kind === 'files' ? value.files : [];
  const maxFiles = question.archivo_max_archivos || 1;
  const maxMb = question.archivo_max_mb || 10;

  const handlePicked = async (picked: FileList | null) => {
    if (!picked || picked.length === 0) return;
    setError(null);
    const nextFiles = [...files];
    for (const file of Array.from(picked)) {
      if (nextFiles.length >= maxFiles) {
        setError(`Máximo ${maxFiles} archivo(s) permitido(s).`);
        break;
      }
      if (file.size > maxMb * 1024 * 1024) {
        setError(`"${file.name}" excede el máximo de ${maxMb}MB.`);
        continue;
      }
      if (!fileAllowed(question, file)) {
        setError(`"${file.name}" no es un tipo de archivo permitido.`);
        continue;
      }
      setUploading(true);
      try {
        const result = await onUpload(question, file);
        nextFiles.push({ url: result.url, filename: result.filename, size: result.size, mime_type: result.mime_type });
      } catch {
        setError(`No se pudo subir "${file.name}". Intenta de nuevo.`);
      } finally {
        setUploading(false);
      }
    }
    onChange({ kind: 'files', files: nextFiles });
    if (inputRef.current) inputRef.current.value = '';
  };

  const removeAt = (index: number) => {
    onChange({ kind: 'files', files: files.filter((_, i) => i !== index) });
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        multiple={maxFiles > 1}
        accept={question.archivo_tipos_permitidos.join(',') || undefined}
        className="sr-only"
        id={`file_${question.id}`}
        aria-label={question.titulo}
        onChange={(e) => void handlePicked(e.target.files)}
      />
      <label
        htmlFor={`file_${question.id}`}
        className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-dashed border-[hsl(var(--border))] px-4 py-3 text-sm font-medium text-[hsl(var(--text-primary))] transition-colors hover:bg-[hsl(var(--surface-2))]"
      >
        {uploading ? (
          <Loader2 className="h-4 w-4 animate-spin text-[hsl(var(--primary))]" aria-hidden="true" />
        ) : (
          <UploadCloud className="h-4 w-4 text-[hsl(var(--primary))]" aria-hidden="true" />
        )}
        {uploading ? 'Subiendo…' : 'Agregar archivo'}
      </label>
      <p className="mt-1 text-xs text-[hsl(var(--text-secondary))]">
        Máximo {maxFiles} archivo(s), {maxMb}MB cada uno.
      </p>
      {files.length > 0 ? (
        <ul className="mt-2 flex flex-col gap-1">
          {files.map((f, i) => (
            <li key={`${f.url}_${i}`} className="flex items-center justify-between gap-2 rounded-lg bg-[hsl(var(--surface-2))] px-3 py-2 text-sm">
              <span className="inline-flex min-w-0 items-center gap-2 text-[hsl(var(--text-primary))]">
                <FileText className="h-4 w-4 shrink-0 text-[hsl(var(--primary))]" aria-hidden="true" />
                <span className="truncate">{f.filename}</span>
              </span>
              <button
                type="button"
                onClick={() => removeAt(i)}
                aria-label={`Quitar ${f.filename}`}
                className="rounded p-1 text-[hsl(var(--text-secondary))] transition-colors hover:bg-[hsl(var(--surface-3))] hover:text-[hsl(var(--destructive))]"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
      ) : null}
      <FieldError show={Boolean(error)}>{error}</FieldError>
      <FieldError show={invalid && files.length === 0 && !error}>Debes subir al menos un archivo</FieldError>
    </div>
  );
}
