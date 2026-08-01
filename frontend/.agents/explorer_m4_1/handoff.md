# Milestone 4 (R4 Complex Blocks Catalog - Gallery & Cards) Investigation Report

## 1. Observation

### Key Files Inspected
- `/root/ccf/frontend/src/app/plataforma/cms/builder-puck/page.tsx` (Lines 497–615)
- `/root/ccf/frontend/src/components/cms/builder/MediaPickerField.tsx`
- `/root/ccf/frontend/src/components/cms/builder/AiField.tsx`
- `/root/ccf/frontend/src/components/cms/builder/PuckSchemaRegistration.test.tsx`
- `/root/ccf/frontend/node_modules/@puckeditor/core/dist/actions-Csn3gOP8.d.ts` (Lines 241–256)
- `/root/ccf/frontend/node_modules/@puckeditor/core/dist/index.js` (Lines 6562–6846)

### Puck Core `ArrayField` Interface (`actions-Csn3gOP8.d.ts`)
```typescript
interface ArrayField<Props extends { [key: string]: any; }[] = { [key: string]: any; }[], UserField extends {} = {}> extends BaseField {
    type: "array";
    arrayFields: {
        [SubPropName in keyof Props[0]]: Field<Props[0][SubPropName], UserField>;
    };
    defaultItemProps?: Props[0] | ((index: number) => Props[0]);
    getItemSummary?: (item: Props[0], index?: number) => ReactNode;
    max?: number;
    min?: number;
}
```

### Current Block Registrations in `page.tsx`

#### 1. `gallery` Block Registration (Lines 497–546)
```typescript
gallery: {
  label: "Galería (Gallery)",
  fields: {
    title: { type: "text", label: "Título de la Sección" },
    body: { type: "textarea", label: "Descripción" },
    items: {
      type: "array",
      label: "Imágenes de la Galería",
      getItemSummary: (item: any) => item.alt || item.url || "Imagen vacía",
      defaultItemProps: { url: "", alt: "Imagen", caption: "" },
      arrayFields: {
        url: {
          type: "custom",
          label: "Imagen",
          render: ({ value, onChange }: any) => (
            <MediaPickerField label="Imagen" value={value} onChange={onChange} />
          )
        },
        alt: { type: "text", label: "Texto Alt" },
        caption: { type: "text", label: "Leyenda / Copete" },
      }
    }
  },
  render: ({ title, body, items }: any) => ( ... )
}
```

#### 2. `cards` Block Registration (Lines 547–615)
```typescript
cards: {
  label: "Tarjetas (Cards)",
  fields: {
    title: { type: "text", label: "Título de la Sección" },
    body: { type: "textarea", label: "Descripción" },
    items: {
      type: "array",
      label: "Tarjetas",
      getItemSummary: (item: any) => item.title || "Tarjeta vacía",
      defaultItemProps: { title: "Título de Tarjeta", body: "Descripción corta...", cta_label: "Saber más", cta_href: "/", image_url: "" },
      arrayFields: {
        title: { type: "text", label: "Título" },
        body: { type: "textarea", label: "Descripción" },
        cta_label: { type: "text", label: "Etiqueta Botón" },
        cta_href: { type: "text", label: "Enlace Botón" },
        image_url: {
          type: "custom",
          label: "Imagen",
          render: ({ value, onChange }: any) => (
            <MediaPickerField label="Imagen" value={value} onChange={onChange} />
          )
        }
      }
    }
  },
  render: ({ title, body, items }: any) => ( ... )
}
```

---

## 2. Logic Chain

1. **Puck Array Registration & Capabilities**:
   - Puck's `ArrayField` natively handles array sub-elements using `arrayFields` for field layout, `defaultItemProps` for newly added items, and `getItemSummary` for item header labels in the sidebar inspector.
   - Built-in UI controls in Puck sidebar enable adding (`+` button), reordering (drag handles), and deleting (trash icon) array items dynamically.

2. **Schema Component-Level `defaultProps` Deficiency**:
   - Neither `gallery` nor `cards` specifies top-level component `defaultProps` in `puckConfig.components`.
   - Result: Dragging a fresh `gallery` or `cards` block onto the canvas initializes `items` as `undefined` / `[]`, causing the component render function to display an empty section.
   - Fix: Defining top-level `defaultProps` (with 3 default image objects for `gallery` and 3 default card objects for `cards`) ensures an immediate populated preview when dropped onto the canvas.

3. **Sub-Item Summary Usability (`getItemSummary`)**:
   - `gallery` uses `defaultItemProps: { url: "", alt: "Imagen", caption: "" }` and `getItemSummary: (item) => item.alt || item.url || "Imagen vacía"`.
   - Since `alt` defaults to `"Imagen"`, adding multiple items renders every item label in the sidebar as `"Imagen"`, making it impossible for users to distinguish items without expanding them.
   - Fix: Enhance `getItemSummary` to include item index, caption, or URL status (e.g. `(item, index) => item.caption || (item.alt && item.alt !== "Imagen" ? item.alt : \`Imagen #${(index ?? 0) + 1}\`)`).

4. **AI Text Generation Integration Gap**:
   - Section-level fields (`title` and `body`) in `gallery` and `cards`, as well as `title` and `body` in `cards` sub-items, currently use standard text inputs (`{ type: "text" }` / `{ type: "textarea" }`).
   - `hero`, `rich_text`, and `cta_banner` use custom `<AiField>` renderers.
   - Fix: Upgrading `cards` sub-fields (or section fields) to `<AiField>` brings parity with AI writing assistance across all Puck blocks.

5. **Visual Rendering Fallbacks & Responsive Grid**:
   - `gallery.render`: When `item.url` is empty (`""`), an empty black square container is shown without any visual placeholder icon or text prompting image selection.
   - `cards.render`: The grid layout is hardcoded to `grid-cols-1 md:grid-cols-3`. If the item count is 1, 2, or 4, grid column alignment can look uneven.
   - Fix: Add placeholder icons/prompts for empty image URLs in `gallery.render`, and adapt `cards.render` grid styling based on array length.

6. **Persistence Layer Compatibility**:
   - `handlePublish` in `page.tsx` strips internal Puck IDs and sends `cleanProps` containing `items: [...]` to `patchCmsSection` / `createCmsSection`.
   - Database serialization for array sub-elements is fully functional and requires no API schema modifications.

---

## 3. Caveats

- **Read-Only Scope**: This report is produced under read-only investigation rules. Implementation changes to `page.tsx` must be executed by the implementer agent.
- **MediaPicker State Closure**: `<MediaPickerField>` uses a global trigger coordinator (`setMediaPickerTrigger`). When used inside array items, it relies on `onChange` passed to the custom render function, which Puck updates correctly per array index.

---

## 4. Conclusion

The current Puck schema definitions for `gallery` and `cards` in `page.tsx` correctly register array fields using `type: "array"`, `arrayFields`, `defaultItemProps`, and `getItemSummary`.

However, the following 6 schema gaps and configuration issues should be addressed in Milestone 4:
1. **Add Component-Level `defaultProps`**: Provide initial 3-item array defaults for `gallery` and `cards` so new blocks drop onto the canvas pre-populated.
2. **Improve `getItemSummary` Functions**: Include item indices and secondary labels so sidebar array items are distinct when `alt` or `title` share default strings.
3. **Integrate AI Writing Assistance (`AiField`)**: Replace plain text inputs in `cards` sub-fields (and section `title`/`body`) with `<AiField>` for AI generation support.
4. **Empty Image URL Placeholder**: Render a visible placeholder (e.g. image icon + "Sin imagen") when `item.url` or `item.image_url` is blank.
5. **Array Boundary Constraints**: Define `min: 1` and `max: 12` (gallery) / `max: 6` (cards) on array field configuration.
6. **Responsive Card Grid Layout**: Adjust `cards.render` CSS grid layout based on card array length for clean alignment.

---

## 5. Verification Method

To verify Puck schema definitions and array field behavior:

1. **Type & Schema Inspection**:
   - Run `npm run typecheck` to confirm zero TypeScript errors with Puck configuration.
2. **Unit & Registration Test Suite**:
   - Run `npx vitest run src/components/cms/builder/PuckSchemaRegistration.test.tsx` to verify block registration assertions.
3. **Manual / E2E Verification**:
   - Load `/plataforma/cms/builder-puck?site=ccf&page=home`.
   - Add a `cards` or `gallery` block from the sidebar. Verify default items render.
   - Click `+` in Puck sidebar array inspector to add an item.
   - Drag handles to reorder items.
   - Click trash icon to delete an item.
   - Verify image selection via `MediaPickerField` updates the target array item.
