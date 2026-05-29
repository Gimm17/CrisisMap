# CrisisMap UI/UX Design Prompt for Google Stitch

Design a professional web application called CrisisMap, an AI-powered humanitarian damage assessment dashboard for post-disaster and conflict-zone infrastructure analysis.

The product helps humanitarian responders, NGOs, government disaster teams, analysts, and donor decision makers assess damaged buildings, understand critical infrastructure priorities, and generate reconstruction reports quickly.

This must be an operational dashboard, not a marketing landing page. The first screen should be the actual assessment workspace.

## Visual Direction

Create a calm, credible, geospatial, high-stakes operations interface. The design should feel precise, trustworthy, modern, and humanitarian. Avoid decorative gradients, oversized hero sections, playful illustrations, and marketing-style copy.

The main experience should be map-first. The map is the primary working surface, supported by compact analytical panels.

## Color Palette

Use this palette carefully and professionally:

- Primary: #09637E
  Use for main header, active navigation, strong emphasis, selected primary states.
- Secondary: #088395
  Use for primary buttons, active controls, map drawing actions, progress indicators.
- Support Accent: #7AB2B2
  Use for muted highlights, secondary surfaces, charts, empty states, inactive visual accents.
- Background: #EBF4F6
  Use for the app background and soft dashboard surfaces.

Use white and neutral gray for content cards, panels, borders, and typography.

For damage severity, use semantic status colors separate from the brand palette:

- Intact: green
- Minor: yellow
- Moderate: amber/orange
- Severe: deep orange
- Destroyed/Critical: red

Do not let damage colors clash with the teal brand palette.

## Required Screens

1. Assessment Workspace
Design a full-screen workspace for starting a new assessment.
Include:

- Large interactive map canvas
- AOI polygon drawing controls
- Location search
- Event date input
- Before image date range
- After image date range
- Mode selector: Demo Beirut / Live Data
- Run Assessment button
- Compact job progress panel
- Data source status indicators for OSM, satellite imagery, humanitarian layers, and AI reasoning

2. Results Dashboard
Design the main results screen.
Include:

- Large damage map with color-coded building polygons
- Damage severity legend
- Layer toggles for buildings, hospitals, roads, water, power, population density
- Summary stat cards: buildings assessed, severe damage, critical infrastructure affected, estimated people impacted
- Priority reconstruction list
- Filter controls by infrastructure type and damage severity
- Selected building detail side panel

3. Priority Building Detail
Design a detail panel or page for one priority building.
Include:

- Priority rank
- Damage score
- Infrastructure type
- Humanitarian impact explanation
- Cascade effect reasoning
- Estimated affected population
- Estimated repair cost
- Estimated repair timeline
- Required specialists
- Dependencies
- Confidence and data quality notes

4. Report View
Design an export-ready report screen.
Include:

- Donor summary
- Damage overview
- Top reconstruction priorities
- Phased plan: 0-72 hours, 1-2 weeks, 1-3 months
- Engineering notes
- Export buttons: PDF, DOCX, GeoJSON

5. Job History
Design a table/list of previous assessment runs.
Include:

- Assessment name
- Location
- Status
- Created date
- Runtime
- AI model/provider used
- Open result action
- Re-run action

## Layout Requirements

Desktop:

- Use a split-pane layout.
- Map should take most of the screen.
- Analysis and controls should sit in right or left panels.
- Keep panels dense but readable.

Tablet:

- Stack map and panels vertically.
- Keep primary action controls visible.

Mobile:

- Prioritize the map first.
- Use bottom sheets for filters and building details.
- Keep all touch targets large and clear.

## Component Style

Use:

- Compact stat cards
- Segmented controls
- Icon buttons for map tools
- Toggle switches for layers
- Tabs for dashboard sections
- Tables for job history
- Side panels for details
- Bottom sheets on mobile
- Clear status badges

Avoid:

- Decorative cards inside cards
- Large empty hero sections
- Purple gradients
- Overly rounded playful UI
- Long explanatory text inside the app
- Marketing copy

## Tone Of Copy

Use short, operational labels:

- Run Assessment
- Draw Area
- Clear Area
- View Report
- Export GeoJSON
- Open Priority
- Filter Layers
- Critical Infrastructure
- Data Quality
- Reasoning Summary

The UI should feel like a real tool used during urgent humanitarian analysis.
