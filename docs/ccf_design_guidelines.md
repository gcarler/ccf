# CCF UI/UX Design Patterns (ClickUp Inspired)

Based on the analysis of the reference platform, the CCF ecosystem should adopt a "Clean Productivity" aesthetic.

## 1. Visual Foundation
- **Backgrounds:** use layered whites and ultra-light grays (e.g., `#FFFFFF`, `#F8F9FA`).
- **Surface Elevation:** 
    - Level 0: Main background.
    - Level 1: Sidebar and main containers (soft border, no shadow).
    - Level 2: Floating cards and modals (8-16px border-radius, soft 10% opacity shadows).

## 2. Layout & Navigation
- **Sidebar Hierarchy:** 
    - Narrow global utility bar (64px) for high-level switches.
    - Expandable contextual sidebar (240px) for current module navigation.
- **Header:** Sticky top bar with breadcrumbs and primary actions.
- **Content Area:** Flexible grid/list views with clear padding (24-32px).

## 3. Components
- **Status Pills:** Small, rounded badges with semi-transparent backgrounds and high-contrast text.
- **Cards:** Modern, clean, with ample whitespace and subtle hover-lift effects.
- **Inputs:** Minimalist with focus-accent borders and clear labels.
- **Modals:** Centered, large border-radius (16px), split-layout for detail views.

## 4. Advanced Interactions & Feedback
- **Drag-and-Drop Ghosting:** When moving elements, use a semi-transparent "ghost" of the item following the cursor. Highlight target zones with a sutil border or background shift.
- **Real-time Optimism:** Update UI counters and status indicators immediately upon action completion (optimistic UI) to give a sense of speed.
- **Shimmer Effects:** Use animated shimmer gradients for loading states or to highlight AI-generated content.

## 5. AI Integration Patterns
- **Floating Command Bar (Ctrl+K):** A central hub for global search and natural language commands.
- **Contextual AI Triggers:** Small AI icons/buttons embedded directly where they can help (e.g., "Summarize" in comments, "Generate Subtasks" in hierarchies).
- **Split-View Results:** Display AI outputs in a dedicated side panel to avoid breaking the user's primary workflow.

## 6. Hierarchies & Relationships
- **Anested Lists:** Clearly indent sub-entities with connecting lines or color-coded markers.
- **Relationship Badges:** Use specific icons to denote dependency types (Blocking, Waiting, Related).
- **Predictive Linking:** Use auto-complete search components for fast entity linking across the platform.

## 7. Aesthetic "Wow" Factors
... (existing content)
