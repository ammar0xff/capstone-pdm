# NASA C-MAPSS FD001 raw files — provenance

These three files are the FD001 subset of the NASA Ames Prognostics Center of
Excellence turbofan engine degradation simulation dataset. They are kept here
so the RUL benchmark is reproducible without a network connection.

| Item | Value |
|---|---|
| Publisher | NASA Diagnostics and Prognostics Group (PCoE), via Zenodo |
| DOI | `10.5281/zenodo.15346912` |
| Landing page | `https://zenodo.org/records/15346912` |
| Archive | `CMAPSSData.zip`, MD5 `79a22f36e80606c69d0e9e4da5bb2b7a` |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0) |
| Citation | A. Saxena, K. Goebel, D. Simon and N. Eklund, "Damage Propagation Modeling for Aircraft Engine Run-to-Failure Simulation", PHM08, Denver, 2008. |

Local copies (do not edit; verify with `md5sum`):

| File | Rows | MD5 |
|---|---:|---|
| `train_FD001.txt` | 20,631 | `259f340bac32ce6fa8894815600fa757` |
| `test_FD001.txt` | 13,096 | `62316d1dd70f88a9a43a1e2690765437` |
| `RUL_FD001.txt` | 100 | `8f4a8b3d2692b2f7d8e72b344927bf4b` |

Each row has 26 whitespace-separated columns: unit id, cycle, three operating
settings and 21 sensor readings. Training units run to simulated failure;
test units stop early and `RUL_FD001.txt` gives the true remaining cycles for
the last cycle of each test unit.

**Scope warning.** These are *simulated turbofan engine* data, not readings
from our induction motor rig. A good score here validates the RUL pipeline on
a public benchmark only; it is not evidence of remaining useful life for our
motor and must never be presented as field validation.
