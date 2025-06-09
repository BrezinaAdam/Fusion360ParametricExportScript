"""
This script, "ParametricExport", reads a JSON configuration file to export
multiple variants of a Fusion 360 design. It iterates through specified
parameter combinations, updates the model, and saves STL files.
"""

import traceback
import os
import json
import itertools
import adsk.core
import adsk.fusion

# Global application objects
app = adsk.core.Application.get()
ui = app.userInterface

def update_parameter(name: str, value: float) -> bool:
    """Updates a single user parameter in the active design."""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        param = design.userParameters.itemByName(name)
        if param:
            param.expression = str(value)
            return True
        app.log(f'Warning: Parameter not found in design: {name}')
        return False
    except:
        app.log(f"Error updating parameter '{name}':\n{traceback.format_exc()}")
        return False

def find_body(design: adsk.fusion.Design, body_name: str) -> adsk.fusion.BRepBody:
    """Searches all components in a design for a body by name."""
    for comp in design.allComponents:
        for body in comp.bRepBodies:
            if body.name == body_name:
                return body
    return None

def export_body_as_stl(body: adsk.fusion.BRepBody, filename: str) -> bool:
    """Exports a BRepBody to an STL file."""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        export_mgr = adsk.fusion.ExportManager.cast(design.exportManager)
        
        if not filename.lower().endswith('.stl'):
            filename += '.stl'
            
        stl_options = export_mgr.createSTLExportOptions(body)
        stl_options.meshRefinement = adsk.fusion.MeshRefinementSettings.MeshRefinementMedium
        stl_options.filename = filename
        
        export_mgr.execute(stl_options)
        return True
    except:
        app.log(f"Failed to export body: {body.name}\n{traceback.format_exc()}")
        return False

def run(_context: str):
    """Prompts user for a JSON config and exports model variants based on it."""
    progress_bar = None
    try:
        # 1. Get configuration from user
        file_dialog = ui.createFileDialog()
        file_dialog.title = "Select Parametric Export Configuration File"
        file_dialog.filter = "JSON Files (*.json)"
        file_dialog.initialDirectory = os.path.dirname(os.path.abspath(__file__))
        if file_dialog.showOpen() != adsk.core.DialogResults.DialogOK:
            return

        with open(file_dialog.filename, 'r') as f:
            config = json.load(f)

        output_dir_name = config.get("outputDirectory", "output")
        bodies_to_export = config.get("bodiesToExport", [])
        params_to_iterate = config.get("parametersToIterate", {})
        
        base_export_dir = os.path.join(os.path.dirname(file_dialog.filename), output_dir_name)
        os.makedirs(base_export_dir, exist_ok=True)
        
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox("No active design found.")
            return

        # 2. Generate all parameter combinations to process
        param_names = list(params_to_iterate.keys())
        param_value_lists = [p['variants'] for p in params_to_iterate.values()]
        all_combinations = list(itertools.product(*param_value_lists))

        # 3. Set up progress bar and start processing
        total_iterations = len(all_combinations)
        progress_bar = ui.createProgressDialog()
        progress_bar.isCancelButtonShown = True
        progress_bar.show('Parametric Export', f'Processing {total_iterations} variants...', 0, total_iterations)

        for i, combination in enumerate(all_combinations):
            if progress_bar.wasCancelled:
                break

            current_params = dict(zip(param_names, combination))
            progress_bar.message = f"Processing combination {i + 1} of {total_iterations}"
            progress_bar.progressValue = i + 1

            # Update Fusion model parameters for the current variant
            for name, value in current_params.items():
                if not update_parameter(name, value):
                    ui.messageBox(f"Failed to update parameter '{name}'. Aborting.")
                    return
            adsk.doEvents()

            # Build folder and filename parts. Filename will contain all params.
            folder_parts = []
            all_param_parts = []
            for p_name, details in params_to_iterate.items():
                part = f"{details['outputName']}{current_params[p_name]}"
                all_param_parts.append(part)
                if details.get('grouping', False):
                    folder_parts.append(part)
            
            # Create the final export directory for this group
            subfolder_name = "-".join(folder_parts)
            final_export_dir = os.path.join(base_export_dir, subfolder_name)
            os.makedirs(final_export_dir, exist_ok=True)
            
            base_filename = "-".join(all_param_parts)

            # Export all required bodies for this variant
            for body_name in bodies_to_export:
                target_body = find_body(design, body_name)
                if not target_body:
                    ui.messageBox(f'Could not find body "{body_name}" after update. Aborting.')
                    return
                
                output_filename = os.path.join(final_export_dir, f"{target_body.name}-{base_filename}.stl")
                if not export_body_as_stl(target_body, output_filename):
                    ui.messageBox(f'Failed to export file: {os.path.basename(output_filename)}.\nSee Text Commands for details.')
                    return

        if progress_bar.wasCancelled:
            ui.messageBox("Export cancelled by user.")
        else:
            ui.messageBox(f"Export completed successfully.\n{total_iterations} variants exported to '{output_dir_name}'.")

    except:
        if ui: ui.messageBox(f'An unexpected error caused the script to fail:\n{traceback.format_exc()}')
    finally:
        if progress_bar:
            progress_bar.hide() 