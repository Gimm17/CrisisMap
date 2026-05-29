---
name: CrisisMap Operational System
colors:
  surface: '#f2fbfd'
  surface-dim: '#d3dcde'
  surface-bright: '#f2fbfd'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#ecf5f7'
  surface-container: '#e6eff1'
  surface-container-high: '#e1eaec'
  surface-container-highest: '#dbe4e6'
  on-surface: '#141d1f'
  on-surface-variant: '#40484c'
  inverse-surface: '#293234'
  inverse-on-surface: '#e9f2f4'
  outline: '#70787d'
  outline-variant: '#bfc8cd'
  surface-tint: '#116681'
  primary: '#004a5f'
  on-primary: '#ffffff'
  primary-container: '#09637e'
  on-primary-container: '#98ddfc'
  inverse-primary: '#8bd0ef'
  secondary: '#006877'
  on-secondary: '#ffffff'
  secondary-container: '#8debff'
  on-secondary-container: '#006b7a'
  tertiary: '#0a4c4c'
  on-tertiary: '#ffffff'
  tertiary-container: '#2b6464'
  on-tertiary-container: '#a5dede'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#bce9ff'
  primary-fixed-dim: '#8bd0ef'
  on-primary-fixed: '#001f2a'
  on-primary-fixed-variant: '#004d63'
  secondary-fixed: '#a3eeff'
  secondary-fixed-dim: '#76d4e7'
  on-secondary-fixed: '#001f25'
  on-secondary-fixed-variant: '#004e5a'
  tertiary-fixed: '#b4eded'
  tertiary-fixed-dim: '#98d1d1'
  on-tertiary-fixed: '#002020'
  on-tertiary-fixed-variant: '#0f4f4f'
  background: '#f2fbfd'
  on-background: '#141d1f'
  surface-variant: '#dbe4e6'
  status-intact: '#22C55E'
  status-minor: '#EAB308'
  status-moderate: '#F59E0B'
  status-severe: '#EA580C'
  status-destroyed: '#DC2626'
  surface-white: '#FFFFFF'
  border-muted: '#D1D5DB'
typography:
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Hanken Grotesk
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  stat-value:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  panel-width: 360px
  gutter: 1rem
  control-gap: 0.5rem
  container-padding: 1.5rem
---

## Brand & Style

The design system is engineered for high-stakes geospatial analysis and humanitarian response. The brand personality is **precise, authoritative, and calm**, prioritizing utility over aesthetics to facilitate rapid decision-making in crisis environments. 

The chosen style is **Corporate / Modern** with a focus on **Information Density**. It utilizes a "Map-First" architecture where the interface acts as a functional frame for satellite data. The aesthetic is characterized by:
- **Pragmatic layouts:** Panels and controls are secondary to the data visualization.
- **Operational Clarity:** High-contrast status indicators and minimal decorative elements.
- **Credibility:** A cooling color palette that conveys professional reliability and reduces cognitive load during prolonged use.

## Colors

The palette is strictly divided between **Brand/Action** colors and **Semantic Data** colors.

1.  **Brand & Action:** The Primary Teal (#09637E) is reserved for structural elements like headers and navigation. Secondary Teal (#088395) is the dedicated action color for buttons and interactive controls.
2.  **The Canvas:** #EBF4F6 serves as the global background, providing a soft contrast against the white content cards and the dark satellite imagery of the map.
3.  **Damage Severity (Semantic):** These colors must remain distinct from brand colors. Use the named status colors for building polygons and severity indicators only. 
4.  **Neutral Tones:** Use pure white for panels to ensure a clear "elevation" from the light blue background.

## Typography

This design system uses **Hanken Grotesk** for its sharp, contemporary professional feel and high legibility at small sizes. **JetBrains Mono** is introduced for labels, coordinates, and technical data points to reinforce the "instrumental" nature of the dashboard.

- **Headlines:** Keep them compact and left-aligned. Use `headline-lg` only for major page titles (e.g., Report views).
- **Labels:** Use `label-mono` for all map-based metadata, status badges, and technical readouts.
- **Data Display:** For large summary numbers in stat cards, use `stat-value` to ensure immediate visual hierarchy.

## Layout & Spacing

The layout utilizes a **Fixed-Fluid Hybrid** model optimized for dashboard density.

- **Desktop:** A 100vh full-screen layout. The Map component is fluid, filling all available space. Sidebar panels (Left for navigation/tools, Right for data details) have a fixed width of `360px`.
- **Z-Index Strategy:** Map tools (zoom, draw) float directly on the map surface. Primary data panels should appear pinned to the edges of the screen rather than floating, creating a "docked" industrial feel.
- **Density:** Spacing is compact (`0.5rem` to `1rem`) to maximize the information visible without scrolling.
- **Mobile/Tablet:** Transition to a vertical stack. On mobile, use a collapsible bottom sheet for the detail panel, occupying 40% of the screen height by default.

## Elevation & Depth

This design system uses **Tonal Layers** and **Low-Contrast Outlines** instead of heavy shadows to maintain a clean, technical look.

- **Surface 0:** The global app background (#EBF4F6).
- **Surface 1:** The Map canvas.
- **Surface 2:** Dashboard panels and cards (White). These use a subtle `1px` border (#D1D5DB) and a very soft, high-diffusion shadow (4px blur, 5% opacity) to separate them from the map.
- **Floating Elements:** Map controls and tooltips use a slightly higher elevation to ensure they are clearly interactive against varying map imagery.

## Shapes

The shape language is **Soft (0.25rem)** to maintain a professional, systematic appearance. 

- **Standard Elements:** Buttons, input fields, and small cards use the base `rounded` (4px) setting.
- **Large Panels:** Side panels and main dashboard containers use `rounded-lg` (8px) to soften the perimeter of the workspace.
- **Status Badges:** Use a pill-shape (fully rounded) only for status indicators (e.g., "In Progress", "Complete") to distinguish them from interactive buttons.

## Components

### Buttons & Controls
- **Primary Button:** Solid #088395 background with white text. Used for "Run Assessment" or "Export".
- **Map Tools:** Square icon-only buttons with a white background and teal icons.
- **Segmented Controls:** Used for switching between "Live Data" and "Demo Mode". These should be flush with a light gray toggle background.

### Cards & Stats
- **Stat Cards:** Minimalist white containers with a `label-mono` title and a `stat-value` number. No icons unless they represent the semantic damage color.
- **Building Detail Card:** Uses a vertical "key-value" pair list for data like "Repair Cost" and "Timeline."

### Map Elements
- **Polygons:** Building footprints use 40% opacity fills of the semantic status colors with a 100% opacity stroke of the same color.
- **Legend:** A compact, floating vertical list on the bottom-right of the map.

### Tables & Lists
- **Job History:** A clean, border-bottom only table layout. Use `body-sm` for row data and `label-mono` for table headers in all-caps.
- **Priority List:** A ranked list item with a leading number (e.g., #1) and a color-coded severity indicator.

### Input Fields
- **Operational Inputs:** Date range pickers and search bars should use a 1px border. Focus state uses a 2px Primary Teal outline.