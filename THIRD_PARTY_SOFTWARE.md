# Third-party software

MultiDock1.0 is an automation/workflow application and depends on established third-party scientific software.

| Component | Role in MultiDock1.0 |
| --- | --- |
| AutoDock Vina | Molecular docking engine and scoring |
| RDKit | Molecular structure parsing and processing |
| Meeko | Ligand preparation and PDBQT generation |
| SciPy | Dependency used by the scientific Python stack |
| Gemmi | Dependency used by Meeko/scientific structure handling |
| PyInstaller | Optional packaging of the Windows application |

Third-party software is not authored by the MultiDock1.0 developer and remains subject to its own license, documentation, and citation requirements.

## AutoDock Vina citation

Research using MultiDock1.0 should cite the appropriate AutoDock Vina publications in addition to MultiDock1.0 itself. Consult the official AutoDock Vina documentation for the citation recommended for the Vina version used in a study.

## Distribution note

The public source repository intentionally does not include the AutoDock Vina executable. Obtain the appropriate Vina executable from its official distribution before running/building MultiDock1.0.
