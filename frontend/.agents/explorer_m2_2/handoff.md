# Handoff Report — Explorer M2 2: R2 MediaPicker Integration Analysis

## 1. Observation

### Key Files Inspected
1. `src/app/plataforma/cms/builder-puck/page.tsx`
2. `src/components/cms/builder/MediaPicker.tsx`

### Verbatim Code Evidence & Line References

#### A. Global Coordinator Ref & React State (Lines 18, 117-134)
```tsx
18: // Global coordinator ref to connect static Puck custom fields with the React Page component state
19: let mediaPickerTrigger: ((onChange: (url: string) => void, currentValue: string) => void) | null = null;
...
117:   // MediaPicker state
118:   const [mediaPickerOpen, setMediaPickerOpen] = useState(false);
119:   const [mediaPickerCallback, setMediaPickerCallback] = useState<((url: string) => void) | null>(null);
120:   const [mediaPickerValue, setMediaPickerValue] = useState("");
121: 
122:   // Setup global trigger callback for Puck's custom field renderers
123:   useEffect(() => {
124:     mediaPickerTrigger = (onChange, currentValue) => {
125:       setMediaPickerValue(currentValue);
126:       setMediaPickerCallback(() => (url: string) => {
127:         onChange(url);
128:       });
129:       setMediaPickerOpen(true);
130:     };
131:     return () => {
132:       mediaPickerTrigger = null;
133:     };
134:   }, []);
```

#### B. Hero Block (`bg_image`) Schema Configuration (Lines 216-248)
```tsx
216:             bg_image: {
217:               type: "custom",
218:               render: ({ value, onChange }: any) => (
219:                 <div className="flex flex-col gap-2 my-1.5">
220:                   <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">Imagen de Fondo</label>
221:                   <div className="flex items-center gap-2">
222:                     {value && (
223:                       <img 
224:                         src={value} 
225:                         alt="Miniatura" 
226:                         className="w-12 h-12 object-cover rounded border border-gray-200 dark:border-white/10" 
227:                       />
228:                     )}
229:                     <button
230:                       type="button"
231:                       onClick={() => {
232:                         if (mediaPickerTrigger) {
233:                           mediaPickerTrigger(onChange, value || "");
234:                         }
235:                       }}
236:                       className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 text-xs font-semibold rounded border border-gray-300 dark:border-white/10 transition-colors"
237:                     >
238:                       {value ? "Cambiar Imagen" : "Seleccionar Imagen"}
239:                     </button>
240:                   </div>
241:                   {value && (
242:                     <span className="text-3xs text-gray-500 truncate max-w-[200px]" title={value}>
243:                       {value}
244:                     </span>
245:                   )}
246:                 </div>
247:               )
248:             },
```

#### C. Gallery Block (`items.arrayFields.url`) Schema Configuration (Lines 604-632)
```tsx
604:                 url: {
605:                   type: "custom",
606:                   label: "Imagen",
607:                   render: ({ value, onChange }: any) => (
608:                     <div className="flex flex-col gap-1.5 my-2">
609:                       <div className="flex items-center gap-2">
610:                         {value && (
611:                           <img src={value} alt="Mini" className="w-10 h-10 object-cover rounded border border-gray-200 dark:border-white/10" />
612:                         )}
613:                         <button
614:                           type="button"
615:                           onClick={() => {
616:                             if (mediaPickerTrigger) {
617:                               mediaPickerTrigger(onChange, value || "");
618:                             }
619:                           }}
620:                           className="px-2.5 py-1 bg-gray-100 dark:bg-white/5 border dark:border-white/10 rounded text-xs font-semibold"
621:                         >
622:                           {value ? "Cambiar" : "Seleccionar"}
623:                         </button>
624:                       </div>
625:                       {value && (
626:                         <span className="text-3xs text-gray-500 truncate max-w-[200px]" title={value}>
627:                           {value}
628:                         </span>
629:                       )}
630:                     </div>
631:                   )
632:                 },
```

#### D. Cards Block (`items.arrayFields.image_url`) Schema Configuration (Lines 680-708)
```tsx
680:                 image_url: {
681:                   type: "custom",
682:                   label: "Imagen",
683:                   render: ({ value, onChange }: any) => (
684:                     <div className="flex flex-col gap-1.5 my-2">
685:                       <div className="flex items-center gap-2">
686:                         {value && (
687:                           <img src={value} alt="Mini" className="w-10 h-10 object-cover rounded border border-gray-200 dark:border-white/10" />
688:                         )}
689:                         <button
690:                           type="button"
691:                           onClick={() => {
692:                             if (mediaPickerTrigger) {
693:                               mediaPickerTrigger(onChange, value || "");
694:                             }
695:                           }}
696:                           className="px-2.5 py-1 bg-gray-100 dark:bg-white/5 border dark:border-white/10 rounded text-xs font-semibold"
697:                         >
698:                           {value ? "Cambiar" : "Seleccionar"}
699:                         </button>
700:                       </div>
701:                       {value && (
702:                         <span className="text-3xs text-gray-500 truncate max-w-[200px]" title={value}>
703:                           {value}
704:                         </span>
705:                       )}
706:                     </div>
707:                   )
708:                 }
```

#### E. MediaPicker Component Render & Event Handling (Lines 895-909)
```tsx
895:       {/* Custom MediaPicker Drawer integration */}
896:       {mediaPickerOpen && (
897:         <MediaPicker
898:           open
899:           token={token}
900:           selectedUrl={mediaPickerValue}
901:           onClose={() => setMediaPickerOpen(false)}
902:           onSelect={(item) => {
903:             const url = typeof item === "string" ? item : (item as { url?: string }).url || "";
904:             if (mediaPickerCallback) {
905:               mediaPickerCallback(url);
906:             }
907:             setMediaPickerOpen(false);
908:           }}
909:         />
910:       )}
```

#### F. MediaPicker Component Contracts (`src/components/cms/builder/MediaPicker.tsx`)
```tsx
28: interface MediaPickerProps {
29:   open: boolean;
30:   token?: string | null;
31:   selectedUrl?: string;
32:   onClose: () => void;
33:   onSelect: (item: CmsMediaItem) => void;
34: }
...
79:       onSelect(created);
```

---

## 2. Logic Chain

1. **Puck Custom Field Renderer API**:
   - Puck block configuration (`Config`) allows defining fields with `type: "custom"`.
   - Puck calls the field's `render({ value, onChange })` property function.
   - `value` contains the active field value (URL string or empty).
   - `onChange` is Puck's internal callback function `(val: any) => void` that updates the underlying JSON block state and triggers canvas preview update.

2. **Connecting Static Custom Field Renderers to Page Component State**:
   - In `builder-puck/page.tsx`, `puckConfig` is memoized via `useMemo`. The custom field renderers exist within Puck's inspector DOM tree.
   - To open `<MediaPicker />` (which lives in `PuckBuilderPage` React DOM tree), a coordinator reference `mediaPickerTrigger` is defined at module scope and wired inside `useEffect`.
   - When a user clicks "Seleccionar Imagen" or "Cambiar" on any image field (Hero `bg_image`, Cards `image_url`, Gallery `url`), `mediaPickerTrigger(onChange, value || "")` is executed.

3. **State Transition Sequence**:
   - **Step 1**: Click event in Puck inspector -> `mediaPickerTrigger(onChange, currentValue)` called.
   - **Step 2**: `setMediaPickerValue(currentValue)` highlights the active image in `MediaPicker`.
   - **Step 3**: `setMediaPickerCallback(() => (url: string) => onChange(url))` stores the field-specific `onChange` closure in React state.
   - **Step 4**: `setMediaPickerOpen(true)` mounts the `<MediaPicker />` modal drawer.
   - **Step 5**: User selects an existing image card or uploads a new file in `MediaPicker`.
   - **Step 6**: `MediaPicker` fires `onSelect(item)`.
   - **Step 7**: `onSelect` extracts `url` (`item.url`), executes `mediaPickerCallback(url)` -> invoking Puck's `onChange(url)`.
   - **Step 8**: Puck receives `onChange(url)`, updates the block property, and immediately re-renders the live canvas preview with the selected image URL.
   - **Step 9**: `setMediaPickerOpen(false)` closes the drawer.

---

## 3. Caveats

1. **React State Setter Function Trap**:
   - Because `mediaPickerCallback` stores a function, calling `setMediaPickerCallback(fn)` directly would cause React to treat `fn` as a state reducer (`(prev) => next`). Wrapping it as `setMediaPickerCallback(() => (url: string) => onChange(url))` ensures React stores `(url: string) => onChange(url)` as the state value.
2. **Item Type Extraction**:
   - `MediaPicker` emits `CmsMediaItem` (`{ id, url, filename, ... }`), but type safety requires normalizing both string URLs and `CmsMediaItem` objects via `const url = typeof item === "string" ? item : item.url || ""`.
3. **Module-Scoped Coordinator Reference**:
   - `mediaPickerTrigger` is a module-level variable. The `useEffect` cleanup (`mediaPickerTrigger = null`) guarantees no memory leaks or stale callbacks persist if the editor page unmounts.
4. **Scope Constraint**:
   - Read-only investigation — no code modifications were made during this phase.

---

## 4. Conclusion

The image field schema configuration and MediaPicker integration in `src/app/plataforma/cms/builder-puck/page.tsx` fully satisfy Requirement **R2 (Fase 2: MediaPicker Integration)**:
- Hero `bg_image`, Cards `image_url`, and Gallery `url` fields are registered as Puck custom fields (`type: "custom"`).
- The `mediaPickerTrigger` coordinator pattern bridges Puck custom field `onChange` callbacks (including array item fields) directly into the top-level `<MediaPicker />` drawer component.
- Image selection seamlessly updates Puck's block state, updating the visual canvas in real time without requiring copy-pasting image URLs.

---

## 5. Verification Method

To verify the investigation findings independently:

1. **Type & Lint Checking**:
   ```bash
   cd /root/ccf/frontend
   npm run typecheck
   npm run lint
   ```
2. **File Inspection**:
   - Check `src/app/plataforma/cms/builder-puck/page.tsx`:
     - Line 18: `mediaPickerTrigger` definition
     - Lines 123-134: `useEffect` coordinator setup
     - Lines 216-248: Hero `bg_image` renderer
     - Lines 604-632: Gallery `url` renderer
     - Lines 680-708: Cards `image_url` renderer
     - Lines 895-909: `<MediaPicker />` drawer component render
3. **Behavioral Invalidation Conditions**:
   - If clicking "Seleccionar Imagen" in Puck inspector does not open MediaPicker, verify `mediaPickerTrigger` is initialized.
   - If image URL is not saved into Puck state, check if `mediaPickerCallback` closure receives and passes `item.url` to `onChange`.
