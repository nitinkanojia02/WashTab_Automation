# Roadmap

This roadmap describes the most valuable next steps for evolving the WashTab Automation Framework from a strong MVP into a more governed and scalable AI-assisted automation platform.

## Roadmap Objective

The objective is to improve the framework across five dimensions:
- automation quality
- determinism and governance
- POM and data intelligence
- execution feedback and reliability
- platform maturity and scalability

---

## Near-Term Priorities

### 1. Strengthen Robot generation quality
Focus areas:
- stronger validation of generated Robot suites
- prevention of framework violations in generated output
- improved prompt constraints for POM-first generation
- automatic repair or regeneration when validation fails

### 2. Deepen POM/resource intelligence
Focus areas:
- better parsing of resource files
- classification of page-open, action, and validation keywords
- richer page object generation patterns
- stronger reuse of existing keywords during automation generation

### 3. Introduce a stronger test data strategy
Focus areas:
- central reusable test data definitions
- reduced hardcoded values in generated automation
- improved separation of data from test logic
- future support for test data references from manual tests

### 4. Improve governance and artifact review
Focus areas:
- approval state tracking
- workflow and artifact status visibility
- clearer review feedback in the UI
- version-aware artifact handling

---

## Mid-Term Priorities

### 5. Improve page understanding robustness
Focus areas:
- better DOM heuristics
- stronger locator quality rules
- support for more complex page structures
- improved duplicate handling and semantic naming

### 6. Expand workflow coverage
Focus areas:
- support more than login-style workflows
- handle multi-page business journeys
- improve cross-page artifact relationships
- support broader enterprise application modules

### 7. Improve execution visibility
Focus areas:
- deeper reporting integration in the UI
- better error surfacing
- clearer linkage between generated automation and execution results
- trend and history visibility over time

---

## Long-Term Priorities

### 8. Introduce execution-aware refinement
Focus areas:
- use execution failures to suggest automation updates
- detect likely locator breakage
- connect failed steps back to page resources and test assets
- improve regeneration based on runtime feedback

### 9. Add self-healing capabilities
Focus areas:
- locator repair assistance
- regeneration of impacted page resources
- controlled revalidation of updated automation
- safe review-first healing behavior

### 10. Add knowledge storage and reuse
Focus areas:
- persist reusable learned patterns
- retain stable keyword and locator recommendations
- support cross-workflow reuse
- evolve toward a reusable automation knowledge layer

### 11. Evolve into a broader platform experience
Focus areas:
- richer dashboard and stage visibility
- multi-user collaboration support
- stronger governance and auditability
- improved enterprise-shareable user experience

---

## Recommended Next Implementation Steps

If development is prioritized for immediate impact, the best next sequence is:

1. strengthen `scripts/generate_robot_from_manual.py`
2. improve resource parsing and semantic understanding
3. introduce a formal test data layer
4. strengthen validation and regeneration loops
5. improve workflow and artifact status visibility in the UI
6. expand support for broader workflows beyond the current demo pattern

---

## Expected Outcome of the Roadmap

By following this roadmap, the framework can evolve from:
- a compelling MVP and engineering accelerator

into:
- a governed, reusable, and organization-shareable AI-assisted automation platform

with stronger confidence, maintainability, and long-term value.