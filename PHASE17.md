# Phase 17 - sprite templates + image reference
Unzip over your spriteforge folder. New: engine/templates.py. Changed: engine/generate.py, engine/main.py, engine/projects.py, engine/diag.py, engine/llm.py, ui/index.html.
No packages, no rebuild. Reference generation uses the IP-Adapter you already downloaded for the Reference-pose tab (else ~3 GB, once).

New "Template" tab:
1. Template: upload a plain dummy sprite (or use the Rig source / Reference tab sprite), or press "Make dummy template" for a built-in neutral mannequin
   (32-128 px, normal or chibi proportions, front or side view). The built-in dummy comes with a perfect rig: every pixel is pre-assigned to its bone.
2. Reference image: any picture whose look you want (armour, outfit, colours). Optional: with none, the prompt alone decides.
3. Generate: SDXL repaints INSIDE the template's silhouette only (inpaint), guided by the reference (IP-Adapter) and your prompt.
   Result = exactly the template's pixel size and shape. Controls:
   - Redraw strength: higher = more freedom to redraw, lower = stays closer to the dummy's shading and limb layout
   - Reference strength: how strongly the reference's look is copied
   - Silhouette freedom (px): 0 = exact silhouette; 2+ lets hair, capes and weapons stick out slightly (only where the model really drew something)
   - Palette from: Reference (colours match your picture) or Result; Colors; Clean stray pixels
4. Each result has "Animate (template rig)": opens it in the Animate tab with the template's joints and painted parts already in place, because the size and alignment are identical.
Template, reference image and rig are saved in the project.
Tip: a template with distinct limb shading (like the built-in dummy) gives the model clearer limb structure than a flat-grey silhouette.
