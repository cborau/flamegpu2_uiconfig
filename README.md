# FLAME GPU 2 Visual Configurator

A desktop tool for assembling FLAME GPU 2 model configurations to minimize hand-editing. Define agents, globals, layers, logging, and visualization settings through a Qt UI and export ready-to-edit Python and C++ files.

[IMAGE HERE: APPLICATION OVERVIEW]

## Features

- **Agent authoring** – create agent templates with variables, functions, logging modes, and colour assignments.
- **Global parameters** – manage scalar and macro globals with type selection and persistence.
- **Layer sequencing** – build execution layers, add functions, and preview ordering.
- **Interactive canvas** – visual wiring of message connections between agent functions.
- **Visualization presets** – configure domain options, per-agent geometry/colour, and interpolation ranges.
- **Export pipeline** – generate Python starter code aligned with FLAME GPU 2 template placeholders.

## Prerequisites

- Python 3.10+ (tested with Anaconda environments).
- Recommended: a virtual environment (conda or venv).
- Required packages (see `requirements.txt` or install manually):
   - `PySide6`

> _Optional_: Install `pyflamegpu` to execute the generated model scaffolding, but it is **not** required to run the configurator UI.

> _Tip_: If you created a dedicated environment for FLAME GPU, activate it before running the configurator.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/cborau/flamegpu2_uiconfig.git
   cd flamegpu2_uiconfig
   ```
2. (Optional) Create and activate a virtual environment:
   ```bash
   conda create -n flamegpu2vc python=3.11
   conda activate flamegpu2vc
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   If the requirements file is not available, install the packages listed in **Prerequisites** individually.

## Running the Application

```bash
python main.py
```

The main window opens with a tabbed editor on the left and a topology canvas on the right.

[IMAGE HERE: MAIN WINDOW WITH TABS]

## Quick Start Workflow

1. **Create agents**
   - Open the **Agent Config.** tab.
   - Enter an agent name, assign a colour, and add variables.
   - For each variable choose a type and a logging mode (e.g. *Mean*, *Min*).
   - Add runtime functions and specify message input/output types.

   [IMAGE HERE: AGENT CONFIG TAB]

2. **Manage globals**
   - Switch to **Globals**.
   - Add global entries with type, value, and indicate if they are *MacroProperty* (checked).

3. **Build layers**
   - Use **Layers** to place functions in execution order.
   - Drag-and-drop or use the add buttons to include agent functions per layer.

4. **Connect functions**
   - On the canvas (right panel), draw message connections between function nodes when needed.
   - Toggle manual layout to reposition nodes.

   [IMAGE HERE: CANVAS WITH CONNECTIONS]

5. **Configure visualization**
   - Open the **Visualization** tab.
   - Enable *Activate Visualization* to unlock controls.
   - Set domain width, initial pause, and boundary overlay options.
   - In the agent table, choose which agents to include, select shapes (`ICOSPHERE`, `CUBE`, `PYRAMID`, `ARROWHEAD`), and colour mode (`Solid` or `Interpolated`).
   - For interpolated colours, pick variables and numeric ranges in the lower panel.

   [IMAGE HERE: VISUALIZATION TAB]

6. **Review model summary**
   - The **Model** tab lists defined agents; you can tweak variable defaults or function descriptions here and apply changes back to the templates.

7. **Save or export**
   - **File → Save Configuration…** stores everything as JSON (including visualization + logging choices) in the `configs/` directory.
   - **File → Save Configuration For Export…** both saves the JSON and generates a Python scaffold in `model_files/` using the FLAME GPU 2 template.

[IMAGE HERE: EXPORT DIALOG]

## Configuration Files

- Saved JSON files include:
  - Agent definitions, variables, logging modes, and colours.
  - Global parameters with macro flags.
  - Layer ordering and canvas layout.
  - Visualization settings (domain, shapes, colour modes, interpolation values).
- Exported Python files fill the template placeholders for globals, agents, logging setup, and visualization blocks.

## Tips & Best Practices

- Use descriptive names for layers and functions; these feed directly into the template.
- Macro globals are flagged so exporters can emit the correct `env.newMacroProperty…` logic (once implemented).
- Keep placeholder `?` values in exported files until you know model-specific constants—search for `?` to locate them quickly.

## Troubleshooting

- **UI fails to launch**: confirm PySide6 is installed in the active environment.
- **Missing exports**: ensure you have write permissions to `model_files/` and the template file exists under `core/templates/main_template.txt`.
- **Visualization placeholders empty**: check that visualization is activated and agents are marked “Include agent”.

## License

See [`LICENSE`](LICENSE) for details.

## Acknowledgements

- FLAME GPU 2 project and documentation.
- Contributors providing templates and initial scaffolding.
