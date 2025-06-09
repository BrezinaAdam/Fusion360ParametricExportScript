"""
This script, "ParametricExport", reads a JSON configuration file to export
multiple variants of a Fusion 360 design. It iterates through specified
parameter combinations, updates the model, and saves STL files.
"""

import traceback
import os
import json
import itertools
import time
import adsk.core
import adsk.fusion

# Global application objects
app = adsk.core.Application.get()
ui = app.userInterface

def update_parameter(name: str, value: float) -> str:
    """Updates a single user parameter. Returns None on success, error message string on failure."""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        param = design.userParameters.itemByName(name)
        if param:
            param.expression = str(value)
            return None  # Success
        
        err_msg = f'Parameter not found in design: {name}'
        app.log(err_msg)
        return err_msg
    except:
        err_msg = f"An exception occurred while updating parameter '{name}':\n{traceback.format_exc()}"
        app.log(err_msg)
        return err_msg

def find_body(design: adsk.fusion.Design, body_name: str) -> adsk.fusion.BRepBody:
    """Searches all components in a design for a body by name."""
    for comp in design.allComponents:
        for body in comp.bRepBodies:
            if body.name == body_name:
                return body
    return None

def export_body(body: adsk.fusion.BRepBody, filename: str, export_options: dict) -> bool:
    """Exports a BRepBody to a file based on the provided export options."""
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        export_mgr = adsk.fusion.ExportManager.cast(design.exportManager)
        
        file_type = export_options.get('fileType', 'STL').upper()
        
        # Ensure filename has the correct extension
        if not filename.lower().endswith(f'.{file_type.lower()}'):
            filename += f'.{file_type.lower()}'

        if file_type == 'STL':
            options = export_mgr.createSTLExportOptions(body)
            
            quality_map = {
                'LOW': adsk.fusion.MeshRefinementSettings.MeshRefinementLow,
                'MEDIUM': adsk.fusion.MeshRefinementSettings.MeshRefinementMedium,
                'HIGH': adsk.fusion.MeshRefinementSettings.MeshRefinementHigh,
            }
            quality_str = export_options.get('stlQuality', 'Medium').upper()
            options.meshRefinement = quality_map.get(quality_str, adsk.fusion.MeshRefinementSettings.MeshRefinementMedium)

        elif file_type == 'STEP':
            options = export_mgr.createSTEPExportOptions(filename)
        
        elif file_type == 'IGES':
            options = export_mgr.createIGESExportOptions(filename)

        elif file_type == '3MF':
            # Note: 3MF export requires a component, not just a body. 
            # This is a simplification; for full 3MF support, this would need adjustment.
            ui.messageBox("3MF export is not fully supported in this version. Use STL, STEP, or IGES.")
            return False
            
        else:
            ui.messageBox(f"Unsupported file type: {file_type}")
            return False

        options.filename = filename
        export_mgr.execute(options)
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
        export_options = config.get("exportOptions", {})
        
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
                error = update_parameter(name, value)
                if error:
                    ui.messageBox(f"Failed to update parameter '{name}'.\n\nReason: {error}\n\nAborting script.", "Parameter Error")
                    return
            
            # Optionally force the model to recompute. Default to True if not specified.
            if export_options.get('forceRecompute', True):
                design.computeAll()
            
            adsk.doEvents()

            # Force a visual update in the viewport and pause briefly to make it noticeable
            app.activeViewport.refresh()
            time.sleep(0.5)

            # --- New Filename and Folder Logic ---
            # Build a dictionary for template replacement
            template_values = current_params.copy()

            # Build folder and filename parts.
            folder_parts = []
            for p_name, details in params_to_iterate.items():
                if details.get('grouping', False):
                    # Use a simple "key-value" format for folder names
                    folder_parts.append(f"{p_name}-{current_params[p_name]}")
            
            # Create the final export directory for this group
            subfolder_name = "-".join(folder_parts)
            final_export_dir = os.path.join(base_export_dir, subfolder_name)
            os.makedirs(final_export_dir, exist_ok=True)
            
            file_template = export_options.get('fileNameTemplate', '{bodyName}-{params}')

            # Export all required bodies for this variant
            for body_name in bodies_to_export:
                target_body = find_body(design, body_name)
                if not target_body:
                    ui.messageBox(f'Could not find body "{body_name}" after update. Aborting.')
                    return

                template_values['bodyName'] = target_body.name
                
                # Create a simple param string for the default template
                param_str = "-".join([f"{k}_{v}" for k, v in current_params.items()])
                template_values['params'] = param_str

                # Format the final filename
                try:
                    output_filename_base = file_template.format(**template_values)
                except KeyError as e:
                    ui.messageBox(f"The placeholder '{{{e.args[0]}}}' in your 'fileNameTemplate' is not a valid parameter name. Aborting.")
                    return

                output_filename_full = os.path.join(final_export_dir, output_filename_base)
                
                if not export_body(target_body, output_filename_full, export_options):
                    ui.messageBox(f'Failed to export file: {os.path.basename(output_filename_full)}.\nSee Text Commands for details.')
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