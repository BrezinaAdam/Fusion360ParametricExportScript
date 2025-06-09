# <img src="icon.svg" width="48" height="48" alt="Parametric Export Icon"> Parametric Export for Fusion 360

This Fusion 360 script, `ParametricExport.py`, allows you to automate the process of exporting multiple variations of your parametric designs. Instead of manually changing parameters and exporting STL files one by one, you can define all desired variations in a simple JSON configuration file and let the script do the work for you.

## Features

- **Configuration-Driven:** Define all your export variations in a simple, human-readable JSON file. No need to edit the Python script for new projects.
- **Batch Processing:** Iterates through every possible combination of the parameters you specify.
- **Dynamic File Naming:** Automatically generates descriptive filenames based on the parameters used for each variant.
- **Folder Grouping:** Automatically organizes exported files into subdirectories based on the parameters of your choosing.
- **User-Friendly:** A progress bar keeps you informed of the export status and allows you to cancel the operation at any time.

## How to Use

1.  **Open Your Design:** Open the Fusion 360 design you wish to export.
2.  **Run the Script:** In Fusion 360, go to the `UTILITIES` tab and select `Scripts and Add-Ins`. Click the `Add` button (the green `+`), navigate to the `ParametricExport.py` file, and click `Run`.
3.  **Select Configuration:** A file dialog will appear. Select the JSON configuration file that defines the exports you want to perform (e.g., `handle_config.json`).
4.  **Export:** The script will begin processing all the variants defined in your file. A progress bar will show the status.
5.  **Done:** Once complete, all your exported STL files will be in the `output` directory (or the directory specified in your config), neatly organized.

## The JSON Configuration File

The power of this script lies in the JSON configuration file. Here is a breakdown of its structure.

### Top-Level Keys

- `outputDirectory`: (String) The name of the folder where the exported files will be saved. This folder is created in the same directory as the configuration file.
- `bodiesToExport`: (List of Strings) A list of the exact names of the bodies you want to export from your Fusion 360 design.
- `parametersToIterate`: (Object) An object where you define the User Parameters from your Fusion 360 design that you want to change.

### `parametersToIterate` Object

Each key in this object must match the **exact name** of a User Parameter in your Fusion 360 design (e.g., `"HandleWidth"`). The value for each key is another object with the following properties:

- `outputName`: (String) A short prefix that will be used in the filename for this parameter.
- `variants`: (List of Numbers/Strings) A list of all the values you want to assign to this parameter. The script will iterate through each of these.
- `grouping`: (Boolean, Optional) If you set this to `true`, this parameter will be used to create a subfolder. If omitted, it defaults to `false`.

---

## Example Configurations

Two example configuration files are included: `handle_config.json` and `drawer_config.json`.

### `handle_config.json`

This example is for a parametric handle.

```json
{
  "outputDirectory": "output",
  "bodiesToExport": [
    "Handle",
    "Handle-wScrewHole"
  ],
  "parametersToIterate": {
    "Size": {
      "outputName": "x",
      "variants": [2, 3, 4, 5],
      "grouping": true
    },
    "HandleAngle": {
      "outputName": "a",
      "variants": [105, 115, 125, 135],
      "grouping": true
    },
    "Thickness": {
      "outputName": "th",
      "variants": [5, 7, 9]
    },
    "HandleWidth": {
      "outputName": "w",
      "variants": [16, 23]
    }
  }
}
```

- **Grouping:** This configuration will create folders based on the `Size` and `HandleAngle` parameters.
- **Example Output:** A file exported with `Size=2`, `HandleAngle=105`, `Thickness=5`, and `HandleWidth=16` will be located at:
  - `output/x2-a105/Handle-x2-a105-th5-w16.stl`

### `drawer_config.json`

This example is for a parametric drawer.

```json
{
  "outputDirectory": "output",
  "bodiesToExport": [
    "Drawer",
    "Drawer-Button",
    "Drawer-Handle"
  ],
  "parametersToIterate": {
    "COLUMNS": {
      "outputName": "width",
      "variants": [1, 2, 3, 4, 5],
      "grouping": true
    },
    "ROWS": {
      "outputName": "depth",
      "variants": [1, 2, 3, 4, 5]
    }
  }
}
```

- **Grouping:** This configuration will create folders based on the `COLUMNS` parameter.
- **Example Output:** A file exported with `COLUMNS=2` and `ROWS=3` will be located at:
  - `output/width2/Drawer-width2-depth3.stl` 