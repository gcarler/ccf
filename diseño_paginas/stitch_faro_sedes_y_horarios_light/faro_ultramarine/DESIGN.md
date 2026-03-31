# Design System Document: The Illumination Editorial

## 1. Overview & Creative North Star

The creative North Star for this design system is **"The Radiant Guide."** 

Moving away from the generic, blocky layouts of standard community portals, this system adopts a high-end editorial aesthetic. We treat light not just as a theme, but as a functional material. The interface should feel like a premium digital gallery—expansive, intentional, and guided by "beams" of focus. 

We break the "template" look through:
*   **Intentional Asymmetry:** Utilizing the 12-column grid to create unbalanced but harmonious layouts that feel curated rather than automated.
*   **Tonal Depth:** Replacing structural lines with shifts in light and shadow.
*   **Atmospheric Photography:** Integrating high-quality, high-contrast imagery that interacts with the UI through glows and overlaps.

---

## 2. Colors & Light Physics

Our palette is rooted in the transition from deep oceanic navy to the piercing clarity of a lighthouse beam. 

### Surface Hierarchy & Nesting
To achieve a "super pro" feel, we abandon flat UI. We treat the interface as physical layers of light.
*   **Base Layer:** `surface` (#001134).
*   **Nested Containers:** Use `surface_container_low` for subtle sections and `surface_container_high` for prominent interactive cards. This creates a "stadium seating" effect for content, moving it closer to the user through tonal shifts rather than borders.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders for sectioning or containment. 
*   Boundaries must be defined solely through background color shifts (e.g., a `surface_container_lowest` section sitting on a `surface` background).
*   Negative space (`spacing.16` and `spacing.20`) acts as the primary separator.

### The "Glass & Gradient" Rule
To evoke the "Lighthouse" concept:
*   **Glassmorphism:** Floating elements (Modals, Navigation Bars) should use semi-transparent `surface_container` colors with a 20px backdrop-blur. 
*   **Signature Textures:** Use a subtle linear gradient for primary actions: `primary` (#a5c8ff) to `primary_container` (#004581) at a 135-degree angle. This adds "soul" and a metallic, premium finish to the UI.

---

## 3. Typography

The typography strategy pairs the authoritative, wide stance of **Manrope** for editorial impact with the clinical precision of **Inter** for utility.

*   **Display (Manrope):** Use `display-lg` (3.5rem) with tight letter-spacing (-0.02em) for hero statements. This conveys the "Modern Christian" identity as bold and progressive.
*   **Headlines (Manrope):** `headline-lg` (2rem) should be used for section titles, often placed asymmetrically (e.g., spanning 4 columns on the left with 8 columns of whitespace).
*   **Body (Inter):** `body-lg` (1rem) is the workhorse. Maintain a generous line-height (1.6) to ensure the high-end editorial feel is consistent through long-form reading.
*   **Labels (Inter):** `label-md` (0.75rem) should be used in ALL CAPS with increased letter-spacing (0.05em) for small metadata, acting as "fine print" in a luxury magazine.

---

## 4. Elevation & Depth

We eschew traditional drop shadows in favor of **Tonal Layering** and **Ambient Light**.

*   **The Layering Principle:** Depth is achieved by stacking. A `surface_container_highest` element naturally feels "closer" than the `surface_dim` background. 
*   **Ambient Shadows:** If a floating effect is required (e.g., a floating Action Button), use an extra-diffused shadow: `box-shadow: 0 20px 40px rgba(0, 17, 52, 0.4)`. The shadow color must be a tinted version of the background, never pure black.
*   **The "Ghost Border" Fallback:** For accessibility in forms, use the `outline_variant` token at **20% opacity**. This provides a hint of structure without breaking the soft, light-driven aesthetic.
*   **Light Glows:** Use "Light Leak" elements—large, blurry radial gradients of `secondary` (#80d0ff) at 5-10% opacity—placed behind high-quality photography to simulate the glow of the lighthouse.

---

## 5. Components

### Buttons
*   **Primary:** A gradient-fill (Primary to Primary Container) with `roundedness.full`. No border.
*   **Secondary:** `surface_bright` background with `on_surface` text. Use a "Ghost Border" on hover.
*   **Tertiary:** Pure text with `primary` color and a subtle glow on hover.

### Cards (The "Faro" Card)
*   No borders or dividers.
*   Use `surface_container_low` for the card body.
*   Apply `roundedness.xl` (0.75rem).
*   Content must have a minimum of `spacing.6` (2rem) padding to maintain the high-end "breathing room."

### Input Fields
*   Background: `surface_container_highest`.
*   States: On focus, the background remains, but a "glow" (1px `primary` shadow with 10px blur) emanates from the bottom of the field.
*   Label: Use `label-md` positioned above the field, never inside.

### Signature Component: The "Beam" Navigation
The navigation bar should be a floating glassmorphic pill (`roundedness.full`) using `surface_container_high` at 70% opacity. On scroll, it should "illuminate" the section the user is currently in with a subtle `secondary` glow.

---

## 6. Do's and Don'ts

### Do
*   **Do** use overlapping elements. A headline can slightly overlap the edge of a photo to create depth.
*   **Do** use generous whitespace. If you think there is enough space, add `spacing.4` more.
*   **Do** use photography with "God Rays" or natural light sources to reinforce the FARO theme.
*   **Do** ensure high contrast in Dark Mode (use `on_background` #d9e2ff on `background` #001134).

### Don't
*   **Don't** use 1px solid divider lines. Use `spacing.8` or a color shift instead.
*   **Don't** use standard "Material Blue" defaults. Always reference the specific `primary` (#a5c8ff) and `secondary` (#80d0ff) tints.
*   **Don't** use heavy, dark drop shadows. They muddy the "Light" concept.
*   **Don't** cram content. If the layout feels "busy," it is no longer professional or high-end.