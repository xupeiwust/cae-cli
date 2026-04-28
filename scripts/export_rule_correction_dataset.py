from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "datasets" / "rules" / "cae_cli_rules_v1"
DATASET_NAME = "cae_cli_rule_pairs_v1"
SYSTEM_PROMPT = (
    "You are a CAE rule-correction assistant. "
    "Given an error reference, return strict JSON that identifies the rule, "
    "explains why it is wrong, and provides the corrected example."
)


MATERIALS = [
    ("STEEL", "210000", "0.30"),
    ("AL6061", "69000", "0.33"),
    ("TITANIUM", "110000", "0.34"),
    ("ABS", "2200", "0.38"),
    ("CONCRETE", "30000", "0.20"),
    ("COPPER", "118000", "0.34"),
    ("INCONEL", "205000", "0.29"),
    ("NYLON", "2800", "0.39"),
]

NODE_SETS = ["FIXED", "CLAMP", "SUPPORT", "BASE", "LEFT_EDGE", "ROOT"]
ELEMENT_SETS = ["EALL", "SOLID", "BEAM_SET", "PLATE", "PART_A", "MESH_CORE"]
SURFACES = ["SURF_A", "SURF_B", "MASTER", "SLAVE", "CONTACT_TOP", "CONTACT_BOT"]
PATCHES = ["movingWall", "fixedWalls", "inlet", "outlet", "frontAndBack", "wall"]
FIELDS = ["U", "p", "T", "k", "omega"]


@dataclass(frozen=True)
class RuleCase:
    rule_id: str
    domain: str
    category: str
    severity: str
    title: str
    bad: str
    good: str
    symptom: str
    wrong_reason: str
    fix_summary: str
    validation_checks: list[str]
    tags: list[str]


RuleBuilder = Callable[[int, random.Random], RuleCase]


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _clean(text: str) -> str:
    lines = [line.rstrip() for line in text.strip("\n").splitlines()]
    return "\n".join(lines).strip()


def _mat(i: int) -> tuple[str, str, str]:
    return MATERIALS[i % len(MATERIALS)]


def _node_set(i: int) -> str:
    return NODE_SETS[i % len(NODE_SETS)]


def _elset(i: int) -> str:
    return ELEMENT_SETS[i % len(ELEMENT_SETS)]


def _surface(i: int) -> str:
    return SURFACES[i % len(SURFACES)]


def _patch(i: int) -> str:
    return PATCHES[i % len(PATCHES)]


def _field(i: int) -> str:
    return FIELDS[i % len(FIELDS)]


def _case(
    *,
    rule_id: str,
    domain: str,
    category: str,
    severity: str,
    title: str,
    bad: str,
    good: str,
    symptom: str,
    wrong_reason: str,
    fix_summary: str,
    validation_checks: list[str],
    tags: list[str],
) -> RuleCase:
    return RuleCase(
        rule_id=rule_id,
        domain=domain,
        category=category,
        severity=severity,
        title=title,
        bad=_clean(bad),
        good=_clean(good),
        symptom=symptom,
        wrong_reason=wrong_reason,
        fix_summary=fix_summary,
        validation_checks=validation_checks,
        tags=tags,
    )


def rule_keyword_typo(i: int, rng: random.Random) -> RuleCase:
    name, e, nu = _mat(i)
    typo = rng.choice(["*ELSTIC", "*ELASITC", "*ELASTC", "*ELASTIK"])
    return _case(
        rule_id="inp.syntax.keyword_typo_elastic",
        domain="calculix_inp",
        category="input_syntax",
        severity="error",
        title="Correct misspelled *ELASTIC keyword",
        bad=f"""
        *MATERIAL, NAME={name}
        {typo}
        {e}, {nu}
        """,
        good=f"""
        *MATERIAL, NAME={name}
        *ELASTIC
        {e}, {nu}
        """,
        symptom=f"ERROR in calinput: unknown keyword {typo}",
        wrong_reason="CalculiX keywords are exact; a misspelled material keyword prevents the input deck from being parsed.",
        fix_summary="Replace the misspelled keyword with *ELASTIC and keep the modulus/Poisson data line below it.",
        validation_checks=["keyword is exactly *ELASTIC", "material data line remains directly below keyword"],
        tags=["calculix", "inp", "syntax", "material"],
    )


def rule_missing_elastic(i: int, rng: random.Random) -> RuleCase:
    name, e, nu = _mat(i)
    return _case(
        rule_id="inp.material.missing_elastic",
        domain="calculix_inp",
        category="material",
        severity="error",
        title="Add missing elastic material block",
        bad=f"""
        *MATERIAL, NAME={name}
        *DENSITY
        {7.8e-9 + (i % 5) * 0.1e-9:.2e}
        """,
        good=f"""
        *MATERIAL, NAME={name}
        *ELASTIC
        {e}, {nu}
        *DENSITY
        {7.8e-9 + (i % 5) * 0.1e-9:.2e}
        """,
        symptom=f"ERROR: no elastic constants assigned to material {name}",
        wrong_reason="A structural material used by solid elements needs elastic constants before the solver can assemble stiffness.",
        fix_summary="Insert a *ELASTIC block with validated engineering constants for the referenced material.",
        validation_checks=["material has *ELASTIC", "Young modulus is positive", "Poisson ratio is between -1 and 0.5"],
        tags=["calculix", "inp", "material", "autofix_safe"],
    )


def rule_unit_modulus_pa_in_mm(i: int, rng: random.Random) -> RuleCase:
    name, e, nu = _mat(i)
    pa_value = str(float(e) * 1_000_000)
    return _case(
        rule_id="inp.units.modulus_pa_used_in_n_mm",
        domain="calculix_inp",
        category="units",
        severity="warning",
        title="Use consistent modulus units for N-mm models",
        bad=f"""
        ** Geometry and loads are in mm and N
        *MATERIAL, NAME={name}
        *ELASTIC
        {pa_value}, {nu}
        """,
        good=f"""
        ** Geometry and loads are in mm and N
        *MATERIAL, NAME={name}
        *ELASTIC
        {e}, {nu}
        """,
        symptom="Displacements are about 1e6 times too small; stress scale is inconsistent with N-mm units.",
        wrong_reason="For N-mm-MPa unit systems, Young's modulus should be in MPa, not Pa.",
        fix_summary="Convert Pa to MPa or convert the whole model to a consistent SI unit system.",
        validation_checks=["unit system documented", "elastic modulus scale matches geometry/load units"],
        tags=["calculix", "inp", "units", "material"],
    )


def rule_bad_poisson(i: int, rng: random.Random) -> RuleCase:
    name, e, _ = _mat(i)
    bad_nu = rng.choice(["0.55", "0.75", "-1.20", "1.00"])
    good_nu = rng.choice(["0.25", "0.30", "0.33", "0.38"])
    return _case(
        rule_id="inp.material.invalid_poisson_ratio",
        domain="calculix_inp",
        category="material",
        severity="error",
        title="Keep Poisson ratio in the physical range",
        bad=f"""
        *MATERIAL, NAME={name}
        *ELASTIC
        {e}, {bad_nu}
        """,
        good=f"""
        *MATERIAL, NAME={name}
        *ELASTIC
        {e}, {good_nu}
        """,
        symptom="Material stiffness matrix is invalid or ill-conditioned.",
        wrong_reason="For isotropic linear elasticity, Poisson ratio must be greater than -1 and less than 0.5.",
        fix_summary="Replace the invalid Poisson ratio with a physically justified value from material data.",
        validation_checks=["-1 < nu < 0.5", "material source is documented"],
        tags=["calculix", "inp", "material"],
    )


def rule_missing_step(i: int, rng: random.Random) -> RuleCase:
    set_name = _node_set(i)
    return _case(
        rule_id="inp.step.missing_step_block",
        domain="calculix_inp",
        category="input_syntax",
        severity="error",
        title="Wrap analysis controls and loads in a *STEP block",
        bad=f"""
        *BOUNDARY
        {set_name}, 1, 3, 0.
        *CLOAD
        {100 + i % 20}, 2, {-100 - i % 50}.
        """,
        good=f"""
        *BOUNDARY
        {set_name}, 1, 3, 0.
        *STEP
        *STATIC
        0.1, 1.0
        *CLOAD
        {100 + i % 20}, 2, {-100 - i % 50}.
        *END STEP
        """,
        symptom="Solver reads model data but no analysis step is available.",
        wrong_reason="Loads and procedures must be inside a CalculiX step so the solver knows what analysis to run.",
        fix_summary="Add a minimal *STEP, procedure card, load block, and matching *END STEP.",
        validation_checks=["exactly one opening *STEP for this load case", "*END STEP closes the step"],
        tags=["calculix", "inp", "step", "autofix_safe"],
    )


def rule_missing_end_step(i: int, rng: random.Random) -> RuleCase:
    load = -50 - (i % 80)
    return _case(
        rule_id="inp.step.missing_end_step",
        domain="calculix_inp",
        category="input_syntax",
        severity="error",
        title="Close every *STEP with *END STEP",
        bad=f"""
        *STEP
        *STATIC
        0.1, 1.0
        *CLOAD
        {20 + i % 10}, 3, {load}.
        """,
        good=f"""
        *STEP
        *STATIC
        0.1, 1.0
        *CLOAD
        {20 + i % 10}, 3, {load}.
        *END STEP
        """,
        symptom="Input parser reaches EOF while still inside a step.",
        wrong_reason="An unclosed step makes procedure, output, and following model data ambiguous.",
        fix_summary="Append *END STEP after the final procedure/load/output card for that step.",
        validation_checks=["step_count equals end_step_count", "no model-definition cards are accidentally inside the step"],
        tags=["calculix", "inp", "step", "autofix_safe"],
    )


def rule_static_increment_large(i: int, rng: random.Random) -> RuleCase:
    initial = rng.choice(["1.0", "0.5", "0.25", "2.0"])
    reduced = {"1.0": "0.1", "0.5": "0.05", "0.25": "0.025", "2.0": "0.2"}[initial]
    return _case(
        rule_id="inp.convergence.static_initial_increment_too_large",
        domain="calculix_inp",
        category="convergence",
        severity="warning",
        title="Reduce initial static increment when convergence stalls",
        bad=f"""
        *STEP
        *STATIC
        {initial}, 1.0
        *END STEP
        """,
        good=f"""
        *STEP
        *STATIC
        {reduced}, 1.0, 1e-05, {initial}
        *END STEP
        """,
        symptom="Too many cutbacks or maximum iterations reached before convergence.",
        wrong_reason="A large initial increment can jump over the stable nonlinear path.",
        fix_summary="Start with a smaller initial increment and set min/max increment bounds explicitly.",
        validation_checks=["initial increment is smaller", "minimum increment is positive", "total step time remains unchanged"],
        tags=["calculix", "inp", "convergence", "autofix_safe"],
    )


def rule_missing_boundary(i: int, rng: random.Random) -> RuleCase:
    node = 1 + i % 9
    return _case(
        rule_id="inp.boundary.rigid_body_mode",
        domain="calculix_inp",
        category="boundary_condition",
        severity="error",
        title="Constrain rigid body modes",
        bad=f"""
        *STEP
        *STATIC
        0.1, 1.0
        *CLOAD
        {node}, 2, -100.
        *END STEP
        """,
        good=f"""
        *BOUNDARY
        {_node_set(i)}, 1, 3, 0.
        *STEP
        *STATIC
        0.1, 1.0
        *CLOAD
        {node}, 2, -100.
        *END STEP
        """,
        symptom="Singular matrix or rigid body motion detected.",
        wrong_reason="A structure with loads but no sufficient supports has free rigid body modes.",
        fix_summary="Add physically correct displacement constraints to remove rigid motion without over-constraining the model.",
        validation_checks=["all six rigid modes are controlled for 3D solids", "constraints match real support physics"],
        tags=["calculix", "inp", "boundary"],
    )


def rule_unknown_nset(i: int, rng: random.Random) -> RuleCase:
    bad_set = f"FIXD_{i % 17}"
    good_set = _node_set(i)
    return _case(
        rule_id="inp.boundary.undefined_node_set",
        domain="calculix_inp",
        category="boundary_condition",
        severity="error",
        title="Reference a defined node set in *BOUNDARY",
        bad=f"""
        *NSET, NSET={good_set}
        1, 2, 3, 4
        *BOUNDARY
        {bad_set}, 1, 3, 0.
        """,
        good=f"""
        *NSET, NSET={good_set}
        1, 2, 3, 4
        *BOUNDARY
        {good_set}, 1, 3, 0.
        """,
        symptom=f"Node set {bad_set} has not been defined.",
        wrong_reason="Boundary conditions must reference an existing node id or node set.",
        fix_summary="Correct the set name or create the missing set before it is referenced.",
        validation_checks=["referenced set exists", "set contains at least one node"],
        tags=["calculix", "inp", "boundary", "reference"],
    )


def rule_zero_load(i: int, rng: random.Random) -> RuleCase:
    node = 100 + i % 50
    direction = 1 + i % 3
    load = -100 - i % 500
    return _case(
        rule_id="inp.load.zero_load_vector",
        domain="calculix_inp",
        category="load_transfer",
        severity="warning",
        title="Avoid accidental zero load vectors",
        bad=f"""
        *STEP
        *STATIC
        0.1, 1.0
        *CLOAD
        {node}, {direction}, 0.0
        *END STEP
        """,
        good=f"""
        *STEP
        *STATIC
        0.1, 1.0
        *CLOAD
        {node}, {direction}, {load}.0
        *END STEP
        """,
        symptom="The right-hand side only consists of zeros or response is exactly zero.",
        wrong_reason="A zero load may be intentional, but in a load step it often means the force transfer was lost.",
        fix_summary="Use the intended nonzero load value or remove the load step if it is only a preload placeholder.",
        validation_checks=["load magnitude is nonzero when a response is expected", "load direction is correct"],
        tags=["calculix", "inp", "load"],
    )


def rule_missing_solid_section(i: int, rng: random.Random) -> RuleCase:
    mat, _, _ = _mat(i)
    elset = _elset(i)
    return _case(
        rule_id="inp.section.missing_solid_section",
        domain="calculix_inp",
        category="input_syntax",
        severity="error",
        title="Assign a material section to solid elements",
        bad=f"""
        *ELEMENT, TYPE=C3D8, ELSET={elset}
        1, 1, 2, 3, 4, 5, 6, 7, 8
        *MATERIAL, NAME={mat}
        *ELASTIC
        210000, 0.3
        """,
        good=f"""
        *ELEMENT, TYPE=C3D8, ELSET={elset}
        1, 1, 2, 3, 4, 5, 6, 7, 8
        *MATERIAL, NAME={mat}
        *ELASTIC
        210000, 0.3
        *SOLID SECTION, ELSET={elset}, MATERIAL={mat}
        """,
        symptom=f"Elements in {elset} have no material assignment.",
        wrong_reason="Element definitions alone do not attach a material; a section card connects element set and material.",
        fix_summary="Add *SOLID SECTION with the correct ELSET and MATERIAL names.",
        validation_checks=["section ELSET exists", "section MATERIAL exists"],
        tags=["calculix", "inp", "section", "material"],
    )


def rule_bad_c3d8_node_count(i: int, rng: random.Random) -> RuleCase:
    elset = _elset(i)
    return _case(
        rule_id="inp.mesh.c3d8_wrong_node_count",
        domain="calculix_inp",
        category="mesh",
        severity="error",
        title="Use eight connectivity nodes for C3D8 elements",
        bad=f"""
        *ELEMENT, TYPE=C3D8, ELSET={elset}
        1, 1, 2, 3, 4
        """,
        good=f"""
        *ELEMENT, TYPE=C3D8, ELSET={elset}
        1, 1, 2, 3, 4, 5, 6, 7, 8
        """,
        symptom="Element connectivity is incomplete for element type C3D8.",
        wrong_reason="A C3D8 brick element requires exactly eight node references.",
        fix_summary="Export or repair the mesh so every C3D8 connectivity row has eight valid nodes.",
        validation_checks=["connectivity count matches element type", "all referenced node ids exist"],
        tags=["calculix", "inp", "mesh"],
    )


def rule_missing_output_requests(i: int, rng: random.Random) -> RuleCase:
    return _case(
        rule_id="inp.output.missing_frd_requests",
        domain="calculix_inp",
        category="results",
        severity="warning",
        title="Request FRD output for displacement and stress",
        bad=f"""
        *STEP
        *STATIC
        0.1, 1.0
        *END STEP
        """,
        good=f"""
        *STEP
        *STATIC
        0.1, 1.0
        *NODE FILE
        U
        *EL FILE
        S
        *END STEP
        """,
        symptom="Solver exits but no .frd result file is available for visualization.",
        wrong_reason="Without result output requests, the run can finish without the artifacts expected by the viewer.",
        fix_summary="Add node and element file output requests inside the analysis step.",
        validation_checks=["*NODE FILE is inside *STEP", "*EL FILE is inside *STEP", "requested variables match analysis type"],
        tags=["calculix", "inp", "results", "viewer"],
    )


def rule_contact_missing_interaction(i: int, rng: random.Random) -> RuleCase:
    surf_a = _surface(i)
    surf_b = _surface(i + 1)
    interaction = f"INT_{i % 37}"
    return _case(
        rule_id="inp.contact.missing_surface_interaction",
        domain="calculix_inp",
        category="contact",
        severity="warning",
        title="Define the contact interaction referenced by *CONTACT PAIR",
        bad=f"""
        *CONTACT PAIR, INTERACTION={interaction}
        {surf_a}, {surf_b}
        """,
        good=f"""
        *SURFACE INTERACTION, NAME={interaction}
        *SURFACE BEHAVIOR, PRESSURE-OVERCLOSURE=HARD
        *CONTACT PAIR, INTERACTION={interaction}
        {surf_a}, {surf_b}
        """,
        symptom=f"Contact interaction {interaction} is referenced but not defined.",
        wrong_reason="A contact pair needs a defined interaction model to describe normal/tangential behavior.",
        fix_summary="Add a matching *SURFACE INTERACTION block before the contact pair.",
        validation_checks=["interaction name matches", "contact surfaces are defined"],
        tags=["calculix", "inp", "contact"],
    )


def rule_thermal_missing_conductivity(i: int, rng: random.Random) -> RuleCase:
    mat, _, _ = _mat(i)
    k = 10 + i % 180
    return _case(
        rule_id="inp.thermal.missing_conductivity",
        domain="calculix_inp",
        category="thermal",
        severity="error",
        title="Provide conductivity for heat-transfer steps",
        bad=f"""
        *MATERIAL, NAME={mat}
        *DENSITY
        7.8e-9
        *STEP
        *HEAT TRANSFER
        0.1, 1.0
        *END STEP
        """,
        good=f"""
        *MATERIAL, NAME={mat}
        *CONDUCTIVITY
        {k}.0
        *DENSITY
        7.8e-9
        *STEP
        *HEAT TRANSFER
        0.1, 1.0
        *END STEP
        """,
        symptom="Thermal stiffness cannot be assembled because conductivity is missing.",
        wrong_reason="Heat-transfer analysis requires thermal conductivity for each active material.",
        fix_summary="Add *CONDUCTIVITY using the unit system of the thermal model.",
        validation_checks=["active material has conductivity", "conductivity value is positive"],
        tags=["calculix", "inp", "thermal", "material"],
    )


def rule_dynamic_missing_density(i: int, rng: random.Random) -> RuleCase:
    mat, e, nu = _mat(i)
    density = f"{7.0e-9 + (i % 12) * 0.1e-9:.2e}"
    return _case(
        rule_id="inp.dynamics.missing_density",
        domain="calculix_inp",
        category="dynamics",
        severity="error",
        title="Provide density for dynamic analysis",
        bad=f"""
        *MATERIAL, NAME={mat}
        *ELASTIC
        {e}, {nu}
        *STEP
        *DYNAMIC
        1e-4, 0.01
        *END STEP
        """,
        good=f"""
        *MATERIAL, NAME={mat}
        *ELASTIC
        {e}, {nu}
        *DENSITY
        {density}
        *STEP
        *DYNAMIC
        1e-4, 0.01
        *END STEP
        """,
        symptom="Mass matrix is incomplete for dynamic procedure.",
        wrong_reason="Dynamic simulations require density to compute inertia and mass.",
        fix_summary="Add a physically consistent *DENSITY block to every dynamic material.",
        validation_checks=["density is positive", "density units match geometry/load/time units"],
        tags=["calculix", "inp", "dynamics", "material"],
    )


def rule_docker_missing_image(i: int, rng: random.Random) -> RuleCase:
    model = f"case_{i % 200}.inp"
    return _case(
        rule_id="docker.calculix.image_not_configured",
        domain="cae_cli_docker",
        category="runtime",
        severity="error",
        title="Configure or pass a Docker CalculiX image",
        bad=f"""
        cae docker calculix {model} -o results/case
        """,
        good=f"""
        cae docker pull cae-cli --set-default
        cae docker calculix {model} -o results/case

        # or:
        cae docker calculix {model} --image cae-cli -o results/case
        """,
        symptom="Docker CalculiX requires an image. Pass --image, set CAE_CALCULIX_DOCKER_IMAGE, or configure docker_calculix_image.",
        wrong_reason="The Docker runner intentionally does not guess a solver image when none is configured.",
        fix_summary="Set the local cae-cli image as default or pass --image cae-cli explicitly.",
        validation_checks=["cae-cli:latest exists locally", "docker_calculix_image is set or --image is passed"],
        tags=["docker", "calculix", "cae_cli", "runtime"],
    )


def rule_docker_unifem_ccx_path(i: int, rng: random.Random) -> RuleCase:
    job = f"beam_{i % 99}"
    return _case(
        rule_id="docker.calculix.unifem_ccx_not_on_path",
        domain="cae_cli_docker",
        category="runtime",
        severity="error",
        title="Use the real CalculiX executable path inside unifem image",
        bad=f"""
        docker run --rm -v "$PWD:/work" -w /work unifem/calculix-desktop:latest ccx -i {job}
        """,
        good=f"""
        docker run --rm -v "$PWD:/work" -w /work unifem/calculix-desktop:latest /tmp/calculix/ccx_2.13_MT -i {job}
        """,
        symptom="executable file not found in $PATH: ccx",
        wrong_reason="The unifem CalculiX image stores the executable at /tmp/calculix/ccx_2.13_MT instead of exposing ccx on PATH.",
        fix_summary="Call /tmp/calculix/ccx_2.13_MT directly or use the cae-cli wrapper image that adds a ccx symlink.",
        validation_checks=["solver binary exists", "container command uses correct executable"],
        tags=["docker", "calculix", "image_command"],
    )


def rule_wsl_path(i: int, rng: random.Random) -> RuleCase:
    drive = rng.choice(["C", "D", "E"])
    folder = rng.choice(["CAE", "cae-cli", "sim_cases", "work"])
    return _case(
        rule_id="docker.wsl.windows_path_mount",
        domain="cae_cli_docker",
        category="runtime",
        severity="error",
        title="Convert Windows paths for WSL Docker mounts",
        bad=f"""
        docker run -v {drive}:\\{folder}\\case_{i % 50}:/work cae-cli:latest
        """,
        good=f"""
        docker run -v /mnt/{drive.lower()}/{folder}/case_{i % 50}:/work cae-cli:latest
        """,
        symptom="Docker inside WSL cannot find the Windows drive path.",
        wrong_reason="Docker Engine running in WSL expects Linux mount paths under /mnt/<drive>/...",
        fix_summary="Convert Windows paths before passing them to WSL Docker.",
        validation_checks=["path starts with /mnt/<drive>", "target directory exists from inside WSL"],
        tags=["docker", "wsl", "path"],
    )


def rule_compose_network_conflict(i: int, rng: random.Random) -> RuleCase:
    return _case(
        rule_id="docker.compose.legacy_network_label_conflict",
        domain="cae_cli_docker",
        category="runtime",
        severity="error",
        title="Avoid reusing old manual network names in Compose",
        bad="""
        services:
          cae-cli:
            image: cae-cli:latest
            container_name: cae-cli
            networks:
              - cae-cli
        networks:
          cae-cli:
            name: cae-cli
        """,
        good="""
        name: cae-cli
        services:
          cae-cli:
            image: cae-cli:latest
        """,
        symptom="network cae-cli was found but has incorrect label com.docker.compose.network",
        wrong_reason="A manually created network named cae-cli is not owned by Compose and can conflict with Compose labels.",
        fix_summary="Let Compose own its default resources or mark a truly external network as external.",
        validation_checks=["docker compose config succeeds", "network labels are Compose-owned"],
        tags=["docker", "compose", "onboarding"],
    )


def rule_openfoam_missing_control_dict(i: int, rng: random.Random) -> RuleCase:
    app = rng.choice(["icoFoam", "simpleFoam", "pisoFoam"])
    return _case(
        rule_id="openfoam.case.missing_controlDict",
        domain="openfoam",
        category="runtime",
        severity="error",
        title="Provide system/controlDict for OpenFOAM cases",
        bad="""
        case/
          0/U
          0/p
          constant/physicalProperties
        """,
        good=f"""
        case/
          0/U
          0/p
          constant/physicalProperties
          system/controlDict

        // system/controlDict
        application     {app};
        startFrom       startTime;
        endTime         0.1;
        deltaT          0.001;
        writeInterval   10;
        """,
        symptom="FOAM FATAL IO ERROR: cannot find file system/controlDict",
        wrong_reason="OpenFOAM requires system/controlDict to define application, time controls, and output cadence.",
        fix_summary="Restore system/controlDict with the solver application and time controls.",
        validation_checks=["system/controlDict exists", "application is set", "writeInterval is present"],
        tags=["openfoam", "runtime", "case_layout"],
    )


def rule_openfoam_missing_patch_field(i: int, rng: random.Random) -> RuleCase:
    patch = _patch(i)
    field = _field(i)
    default_value = "uniform (0 0 0)" if field == "U" else "uniform 0"
    return _case(
        rule_id="openfoam.boundaryField.missing_patch_entry",
        domain="openfoam",
        category="boundary_condition",
        severity="error",
        title="Every mesh patch needs a boundaryField entry",
        bad=f"""
        boundaryField
        {{
            inlet
            {{
                type fixedValue;
                value {default_value};
            }}
        }}
        // mesh boundary also contains patch: {patch}
        """,
        good=f"""
        boundaryField
        {{
            inlet
            {{
                type fixedValue;
                value {default_value};
            }}
            {patch}
            {{
                type zeroGradient;
            }}
        }}
        """,
        symptom=f"FOAM FATAL IO ERROR: Cannot find patchField entry for {patch}",
        wrong_reason="Each patch in constant/polyMesh/boundary must have a corresponding field entry under boundaryField.",
        fix_summary="Add the missing patch entry with a boundary condition type appropriate for the field and patch physics.",
        validation_checks=["all mesh patches appear in every 0/* boundaryField", "boundary condition type matches field"],
        tags=["openfoam", "boundary", "field"],
    )


def rule_openfoam_missing_relaxation(i: int, rng: random.Random) -> RuleCase:
    p_relax = round(0.2 + (i % 4) * 0.1, 2)
    u_relax = round(0.5 + (i % 3) * 0.1, 2)
    return _case(
        rule_id="openfoam.fvSolution.missing_relaxationFactors",
        domain="openfoam",
        category="convergence",
        severity="warning",
        title="Set relaxationFactors for steady OpenFOAM solvers",
        bad="""
        solvers
        {
            p { solver PCG; tolerance 1e-06; relTol 0.05; }
            U { solver smoothSolver; tolerance 1e-05; relTol 0.1; }
        }
        """,
        good=f"""
        solvers
        {{
            p {{ solver PCG; tolerance 1e-06; relTol 0.05; }}
            U {{ solver smoothSolver; tolerance 1e-05; relTol 0.1; }}
        }}
        relaxationFactors
        {{
            fields {{ p {p_relax}; }}
            equations {{ U {u_relax}; }}
        }}
        """,
        symptom="Residuals oscillate or steady solver diverges early.",
        wrong_reason="Steady SIMPLE-family solvers often need under-relaxation to stabilize pressure-velocity coupling.",
        fix_summary="Add relaxationFactors tuned for the case and reduce them if residuals oscillate.",
        validation_checks=["relaxationFactors block exists", "factors are between 0 and 1"],
        tags=["openfoam", "convergence", "fvSolution"],
    )


def rule_su2_missing_mesh(i: int, rng: random.Random) -> RuleCase:
    mesh = f"mesh_{i % 64}.su2"
    return _case(
        rule_id="su2.config.missing_mesh_filename",
        domain="su2",
        category="runtime",
        severity="error",
        title="Declare MESH_FILENAME in SU2 configs",
        bad="""
        SOLVER= EULER
        MACH_NUMBER= 0.5
        """,
        good=f"""
        SOLVER= EULER
        MACH_NUMBER= 0.5
        MESH_FILENAME= {mesh}
        """,
        symptom="SU2_CFD exits because the mesh file cannot be resolved.",
        wrong_reason="SU2 needs MESH_FILENAME to locate the mesh sidecar used by the case.",
        fix_summary="Add MESH_FILENAME and ensure the referenced mesh file is copied with the config.",
        validation_checks=["MESH_FILENAME exists", "referenced mesh file exists next to config or at declared path"],
        tags=["su2", "cfg", "mesh", "sidecar"],
    )


def rule_su2_cfl_too_high(i: int, rng: random.Random) -> RuleCase:
    bad_cfl = rng.choice(["100", "75", "50", "35"])
    good_cfl = rng.choice(["5", "10", "15", "20"])
    return _case(
        rule_id="su2.convergence.cfl_too_high",
        domain="su2",
        category="convergence",
        severity="warning",
        title="Reduce CFL when SU2 residuals diverge",
        bad=f"""
        CFL_NUMBER= {bad_cfl}
        CFL_ADAPT= YES
        """,
        good=f"""
        CFL_NUMBER= {good_cfl}
        CFL_ADAPT= YES
        CFL_ADAPT_PARAM= ( 0.5, 1.5, 1.0, 100.0 )
        """,
        symptom="Residuals grow rapidly or solver produces NaN values.",
        wrong_reason="A high starting CFL can destabilize explicit or pseudo-time iterations before the flow field settles.",
        fix_summary="Start with a lower CFL and let adaptive CFL grow gradually after stable residual decrease.",
        validation_checks=["CFL_NUMBER reduced", "adaptive growth is bounded"],
        tags=["su2", "convergence", "cfl"],
    )


def rule_su2_sidecar_not_copied(i: int, rng: random.Random) -> RuleCase:
    mesh = f"mesh/case_{i % 90}.su2"
    return _case(
        rule_id="su2.runtime.sidecar_mesh_not_copied",
        domain="su2",
        category="runtime",
        severity="error",
        title="Copy SU2 sidecar files into the container work directory",
        bad=f"""
        // case.cfg
        MESH_FILENAME= {mesh}

        docker run --rm -v "$PWD/out:/work" local/su2-runtime:8.3.0 SU2_CFD case.cfg
        """,
        good=f"""
        // case.cfg
        MESH_FILENAME= {mesh}

        // runner behavior
        copy case.cfg and {mesh} into the mounted work directory before SU2_CFD starts
        """,
        symptom=f"SU2 cannot open mesh file {mesh}",
        wrong_reason="The config references a sidecar mesh path that was not present inside the container work directory.",
        fix_summary="Copy existing *_FILENAME sidecar inputs together with the SU2 config.",
        validation_checks=["referenced sidecar exists", "sidecar relative path is preserved in workdir"],
        tags=["su2", "docker", "sidecar"],
    )


def rule_code_aster_missing_comm(i: int, rng: random.Random) -> RuleCase:
    comm = f"case_{i % 50}.comm"
    med = f"mesh_{i % 50}.med"
    return _case(
        rule_id="code_aster.export.missing_comm_reference",
        domain="code_aster",
        category="runtime",
        severity="error",
        title="Declare the command file in Code_Aster export files",
        bad=f"""
        P actions make_etude
        F mmed {med} D 20
        """,
        good=f"""
        P actions make_etude
        F comm {comm} D 1
        F mmed {med} D 20
        """,
        symptom="run_aster cannot find the .comm command file for the study.",
        wrong_reason="The export file must declare the command file with an F comm entry.",
        fix_summary="Add an F comm entry pointing to the local .comm file and copy it with the export.",
        validation_checks=["F comm entry exists", ".comm file exists", "unit number is valid"],
        tags=["code_aster", "export", "sidecar"],
    )


def rule_code_aster_export_missing_sidecar(i: int, rng: random.Random) -> RuleCase:
    comm = f"case_{i % 50}.comm"
    med = f"mesh_{i % 50}.med"
    return _case(
        rule_id="code_aster.runtime.export_sidecar_not_copied",
        domain="code_aster",
        category="runtime",
        severity="error",
        title="Copy Code_Aster export sidecars",
        bad=f"""
        F comm {comm} D 1
        F mmed {med} D 20

        docker run -v "$PWD/out:/work" simvia/code_aster:stable run_aster case.export
        """,
        good=f"""
        F comm {comm} D 1
        F mmed {med} D 20

        copy case.export, {comm}, and {med} into /work before run_aster case.export
        """,
        symptom=f"Code_Aster export references {comm} or {med}, but the file is missing inside the container.",
        wrong_reason="The export file is only an index; referenced sidecar files must also be present.",
        fix_summary="Resolve and copy declared F comm/F mmed inputs into the container work directory.",
        validation_checks=["all input sidecars exist", "result-only sidecars are not required before run"],
        tags=["code_aster", "docker", "sidecar"],
    )


def rule_elmer_missing_mesh_db(i: int, rng: random.Random) -> RuleCase:
    mesh_dir = rng.choice(["mesh", "Mesh", "case_mesh"])
    return _case(
        rule_id="elmer.sif.missing_mesh_db",
        domain="elmer",
        category="runtime",
        severity="error",
        title="Declare and provide Elmer mesh database",
        bad="""
        Header
        End
        Simulation
          Coordinate System = Cartesian
        End
        """,
        good=f"""
        Header
          Mesh DB "." "{mesh_dir}"
        End
        Simulation
          Coordinate System = Cartesian
        End
        """,
        symptom="ElmerSolver cannot find mesh.header or mesh.nodes.",
        wrong_reason="Elmer needs Mesh DB to locate the mesh directory and its sidecar files.",
        fix_summary="Set Mesh DB and copy the mesh directory with mesh.header, mesh.nodes, and mesh.elements.",
        validation_checks=["Mesh DB points to existing directory", "mesh.header exists"],
        tags=["elmer", "sif", "mesh", "sidecar"],
    )


def rule_elmer_missing_solver(i: int, rng: random.Random) -> RuleCase:
    equation = rng.choice(["Heat Equation", "Elasticity", "Stat Current Solver"])
    return _case(
        rule_id="elmer.sif.missing_solver_block",
        domain="elmer",
        category="input_syntax",
        severity="error",
        title="Define a Solver block for each active Equation",
        bad=f"""
        Equation 1
          Name = "{equation}"
          Active Solvers(1) = 1
        End
        """,
        good=f"""
        Solver 1
          Equation = "{equation}"
          Procedure = "HeatSolve" "HeatSolver"
        End
        Equation 1
          Name = "{equation}"
          Active Solvers(1) = 1
        End
        """,
        symptom="Equation references Solver 1, but Solver 1 is not defined.",
        wrong_reason="Elmer equations activate solver indices that must correspond to concrete Solver blocks.",
        fix_summary="Add a Solver block with the correct Equation and Procedure for the physics.",
        validation_checks=["active solver index exists", "procedure matches equation physics"],
        tags=["elmer", "sif", "solver"],
    )


RULE_BUILDERS: list[RuleBuilder] = [
    rule_keyword_typo,
    rule_missing_elastic,
    rule_unit_modulus_pa_in_mm,
    rule_bad_poisson,
    rule_missing_step,
    rule_missing_end_step,
    rule_static_increment_large,
    rule_missing_boundary,
    rule_unknown_nset,
    rule_zero_load,
    rule_missing_solid_section,
    rule_bad_c3d8_node_count,
    rule_missing_output_requests,
    rule_contact_missing_interaction,
    rule_thermal_missing_conductivity,
    rule_dynamic_missing_density,
    rule_docker_missing_image,
    rule_docker_unifem_ccx_path,
    rule_wsl_path,
    rule_compose_network_conflict,
    rule_openfoam_missing_control_dict,
    rule_openfoam_missing_patch_field,
    rule_openfoam_missing_relaxation,
    rule_su2_missing_mesh,
    rule_su2_cfl_too_high,
    rule_su2_sidecar_not_copied,
    rule_code_aster_missing_comm,
    rule_code_aster_export_missing_sidecar,
    rule_elmer_missing_mesh_db,
    rule_elmer_missing_solver,
]


TASK_WORDINGS = [
    "Identify the rule violation and provide the corrected example.",
    "Compare the wrong reference with the valid pattern and return the repair JSON.",
    "Diagnose the CAE input/runtime mistake and give a safe corrected example.",
    "Extract the deterministic rule, explain the failure, and show the right form.",
    "Classify this error reference and produce the corrected snippet.",
    "Turn the bad CAE example into a validated rule-correction pair.",
]


def _assistant_target(case: RuleCase) -> dict[str, Any]:
    return {
        "rule_id": case.rule_id,
        "domain": case.domain,
        "category": case.category,
        "severity": case.severity,
        "diagnosis": case.symptom,
        "why_wrong": case.wrong_reason,
        "fix_summary": case.fix_summary,
        "correct_example": case.good,
        "validation_checks": case.validation_checks,
    }


def _messages(case: RuleCase, wording: str) -> list[dict[str, str]]:
    user = f"""Task: {wording}

Rule title: {case.title}
Domain: {case.domain}
Category hint: {case.category}

Error reference:
```text
{case.bad}
```

Observed symptom:
{case.symptom}

Return strict JSON with keys:
rule_id, domain, category, severity, diagnosis, why_wrong, fix_summary, correct_example, validation_checks.
"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _clean(user)},
        {
            "role": "assistant",
            "content": json.dumps(_assistant_target(case), ensure_ascii=False, sort_keys=True),
        },
    ]


def _record(case: RuleCase, *, index: int, split: str, wording: str) -> dict[str, Any]:
    target = _assistant_target(case)
    record_id = f"rule-{index:05d}-{_sha1(case.rule_id + case.bad + case.good)[:10]}"
    return {
        "id": record_id,
        "dataset": DATASET_NAME,
        "split": split,
        "task_type": "rule_correction_pair",
        "rule_id": case.rule_id,
        "domain": case.domain,
        "category": case.category,
        "severity": case.severity,
        "quality_score": 0.92 if case.domain in {"cae_cli_docker", "openfoam", "su2", "code_aster", "elmer"} else 0.94,
        "source_type": "synthetic_rule_template",
        "tags": sorted(set(case.tags + [case.category, case.domain])),
        "error_reference": {
            "title": case.title,
            "snippet": case.bad,
            "symptom": case.symptom,
            "wrong_reason": case.wrong_reason,
        },
        "correct_example": {
            "snippet": case.good,
            "fix_summary": case.fix_summary,
            "validation_checks": case.validation_checks,
        },
        "assistant_target": target,
        "messages": _messages(case, wording),
    }


def _split_for(index: int, target_count: int) -> str:
    train_cutoff = int(target_count * 0.9)
    val_cutoff = int(target_count * 0.95)
    if index < train_cutoff:
        return "train"
    if index < val_cutoff:
        return "val"
    return "test"


def build_records(target_count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    attempts = 0
    while len(records) < target_count:
        attempts += 1
        if attempts > target_count * 20:
            raise RuntimeError("Unable to generate enough unique rule records.")
        idx = len(records)
        builder = RULE_BUILDERS[idx % len(RULE_BUILDERS)]
        case = builder(idx + attempts, rng)
        wording = TASK_WORDINGS[(idx + attempts) % len(TASK_WORDINGS)]
        key = _sha1(case.rule_id + "\n" + case.bad + "\n" + case.good + "\n" + wording)
        if key in seen:
            continue
        seen.add(key)
        records.append(_record(case, index=idx, split=_split_for(idx, target_count), wording=wording))
    return records


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fp:
        for record in records:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")


def _write_chat_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fp:
        for record in records:
            fp.write(json.dumps({"messages": record["messages"]}, ensure_ascii=False) + "\n")


def _counts(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(sorted(Counter(str(record[key]) for record in records).items()))


def _manifest(records: list[dict[str, Any]], seed: int) -> dict[str, Any]:
    return {
        "dataset_name": DATASET_NAME,
        "record_count": len(records),
        "seed": seed,
        "system_prompt": SYSTEM_PROMPT,
        "split_counts": _counts(records, "split"),
        "domain_counts": _counts(records, "domain"),
        "category_counts": _counts(records, "category"),
        "severity_counts": _counts(records, "severity"),
        "rule_count": len(set(str(record["rule_id"]) for record in records)),
        "rule_counts": _counts(records, "rule_id"),
        "schema": {
            "error_reference": ["title", "snippet", "symptom", "wrong_reason"],
            "correct_example": ["snippet", "fix_summary", "validation_checks"],
            "assistant_target": [
                "rule_id",
                "domain",
                "category",
                "severity",
                "diagnosis",
                "why_wrong",
                "fix_summary",
                "correct_example",
                "validation_checks",
            ],
        },
    }


def _write_readme(output_dir: Path, manifest: dict[str, Any]) -> None:
    text = f"""# CAE CLI Rule Correction Dataset v1

This dataset contains deterministic rule-correction pairs for CAE model
diagnosis and repair training.

Each rich record includes:

- `error_reference`: the wrong snippet, observed symptom, and why it is wrong
- `correct_example`: a corrected snippet plus validation checks
- `assistant_target`: the strict JSON answer expected from the model
- `messages`: chat-format training messages

## Summary

- dataset_name: `{manifest["dataset_name"]}`
- record_count: `{manifest["record_count"]}`
- rule_count: `{manifest["rule_count"]}`
- split_counts: `{json.dumps(manifest["split_counts"], ensure_ascii=False)}`
- domain_counts: `{json.dumps(manifest["domain_counts"], ensure_ascii=False)}`
- category_counts: `{json.dumps(manifest["category_counts"], ensure_ascii=False)}`
- severity_counts: `{json.dumps(manifest["severity_counts"], ensure_ascii=False)}`

## Files

- `all.jsonl`: all rich records
- `train.jsonl`, `val.jsonl`, `test.jsonl`: rich split records
- `train_chat.jsonl`, `val_chat.jsonl`, `test_chat.jsonl`: chat-only records
- `manifest.json`: counts and schema metadata

## Coverage

Rules cover CalculiX/INP, Docker/WSL runtime setup, OpenFOAM case dictionaries,
SU2 sidecar and convergence configuration, Code_Aster export sidecars, and Elmer
SIF/mesh references.
"""
    (output_dir / "README.md").write_text(text, encoding="utf-8", newline="\n")


def export_dataset(output_dir: Path, target_count: int, seed: int) -> dict[str, Any]:
    records = build_records(target_count=target_count, seed=seed)
    output_dir.mkdir(parents=True, exist_ok=True)

    split_records: dict[str, list[dict[str, Any]]] = {"train": [], "val": [], "test": []}
    for record in records:
        split_records[str(record["split"])].append(record)

    _write_jsonl(output_dir / "all.jsonl", records)
    for split, items in split_records.items():
        _write_jsonl(output_dir / f"{split}.jsonl", items)
        _write_chat_jsonl(output_dir / f"{split}_chat.jsonl", items)

    manifest = _manifest(records, seed=seed)
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )
    _write_readme(output_dir, manifest)
    return manifest


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export CAE rule correction dataset.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-count", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=20260426)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    manifest = export_dataset(
        output_dir=args.output_dir,
        target_count=args.target_count,
        seed=args.seed,
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
