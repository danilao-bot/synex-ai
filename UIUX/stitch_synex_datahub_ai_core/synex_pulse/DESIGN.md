---
name: Synex Pulse
colors:
  surface: '#081425'
  surface-dim: '#081425'
  surface-bright: '#2f3a4c'
  surface-container-lowest: '#040e1f'
  surface-container-low: '#111c2d'
  surface-container: '#152031'
  surface-container-high: '#1f2a3c'
  surface-container-highest: '#2a3548'
  on-surface: '#d8e3fb'
  on-surface-variant: '#bac9cc'
  inverse-surface: '#d8e3fb'
  inverse-on-surface: '#263143'
  outline: '#849396'
  outline-variant: '#3b494c'
  surface-tint: '#00daf3'
  primary: '#c3f5ff'
  on-primary: '#00363d'
  primary-container: '#00e5ff'
  on-primary-container: '#00626e'
  inverse-primary: '#006875'
  secondary: '#cebdff'
  on-secondary: '#381385'
  secondary-container: '#4f319c'
  on-secondary-container: '#bea8ff'
  tertiary: '#abffcb'
  on-tertiary: '#003920'
  tertiary-container: '#00ee98'
  on-tertiary-container: '#00673f'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#9cf0ff'
  primary-fixed-dim: '#00daf3'
  on-primary-fixed: '#001f24'
  on-primary-fixed-variant: '#004f58'
  secondary-fixed: '#e8ddff'
  secondary-fixed-dim: '#cebdff'
  on-secondary-fixed: '#21005e'
  on-secondary-fixed-variant: '#4f319c'
  tertiary-fixed: '#52ffac'
  tertiary-fixed-dim: '#00e291'
  on-tertiary-fixed: '#002111'
  on-tertiary-fixed-variant: '#005231'
  background: '#081425'
  on-background: '#d8e3fb'
  surface-variant: '#2a3548'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  code-md:
    fontFamily: JetBrains Mono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  metadata:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
  container-max: 1440px
---

## Brand & Style

The design system is engineered for high-performance data environments, evoking a sense of "mission control" for enterprise AI. The brand personality is technical, precise, and authoritative, yet forward-leaning. It targets Data Engineers who require deep focus and rapid information processing.

The aesthetic merges **Modern Corporate SaaS** with **Glassmorphism** and **Cyber-Technical** influences. By utilizing a "space-void" foundation, the UI minimizes ocular strain during extended sessions while highlighting critical data through luminous accents. The interface relies on translucency and refractive depth to separate information layers, creating a sophisticated, multi-dimensional workspace that feels like a living digital engine.

## Colors

The palette is optimized for high-contrast visibility within a dark ecosystem. 

- **Primary (Electric Cyan):** Used for active states, primary actions, and "data flow" indicators. It represents the energy of the system.
- **Secondary (Digital Lavender):** Reserved exclusively for AI reasoning, machine learning status, and intelligence-driven insights.
- **Tertiary (Emerald Green):** Indicates system health, successful deployments, and verified data streams.
- **Warning (Safety Neon Orange):** A high-visibility signal for PII (Personally Identifiable Information) alerts and critical system warnings.
- **Neutral/Surface:** The background is a "Deep Space Void" (#060913). Surfaces use a semi-transparent slate (#0D1527 at 70%) to allow background depth and "glow" effects to permeate the layout.

## Typography

This design system utilizes a dual-font strategy to balance structural clarity with technical precision.

- **Inter** serves as the primary sans-serif for all structural elements, headers, and standard body text. It provides the necessary legibility for complex SaaS navigation.
- **JetBrains Mono** is the functional workhorse for all data-heavy contexts. It must be used for metadata, schema definitions, code snippets, and status labels.

For mobile screens, `headline-lg` should scale down to 24px to maintain density without sacrificing readability. Tighten letter-spacing on larger headers to maintain the "engineered" feel.

## Layout & Spacing

The system follows a strict **4px grid** to ensure high information density required for data engineering workflows. 

- **Layout Model:** A fluid 12-column grid for desktop with 16px gutters. Elements should snap to the grid to maintain a "blueprint" aesthetic.
- **Density:** Use tight padding (8px or 12px) within cards to maximize visible data points. 
- **Breakpoints:** 
    - Desktop: 1200px+ (12 columns)
    - Tablet: 768px - 1199px (8 columns, margins reduced to 24px)
    - Mobile: <767px (4 columns, margins 16px, cards become full-width stacks).

## Elevation & Depth

Hierarchy is achieved through **Glassmorphism** and **Chromatic Glows** rather than traditional shadows.

- **Surface Layers:** All primary containers utilize `backdrop-filter: blur(16px)` and a `1px` solid border (#1E293B) to define edges against the dark background.
- **Interactivity:** On hover, interactive cards scale to `1.01x` and emit a subtle `rgba(0, 229, 255, 0.1)` cyan outer glow.
- **Z-Axis:** Use higher transparency (50%) for background decorative elements and lower transparency (85%) for foreground modals or dropdowns to simulate physical stacking in a digital void.

## Shapes

The shape language is "Soft-Technical." Elements use a subtle **0.25rem (4px)** radius for standard components (inputs, buttons, cards) to maintain a crisp, professional edge that feels precise but not aggressive. 

Larger containers (like main dashboard panels) can use **0.5rem (8px)** to differentiate from smaller utility components. Avoid fully rounded pill shapes except for specific status indicators or badges where high distinction is required.

## Components

- **Glass Cards:** The core container. Must include a `1px` top-light border to simulate a glass edge catching light.
- **Primary Buttons:** Solid Electric Cyan background with black text for maximum contrast. No border-radius exceeding 4px.
- **Technical Chips:** Used for "PII" or "Tier-1" tags. Use JetBrains Mono, all-caps, with a high-contrast background (e.g., Safety Orange for PII) and 0px border-radius for a "stamped" look.
- **Data Inputs:** Darker than the card surface (#050810) with a 1px border. On focus, the border transitions to Electric Cyan with a subtle inner glow.
- **Status Indicators:** Use "Luminous Dots" (small circles with 4px blur shadows) in Emerald Green, Safety Orange, or Digital Lavender to indicate real-time system health.
- **Schema Lists:** Alternating row highlights using 2% white overlay to maintain legibility in dense tables.