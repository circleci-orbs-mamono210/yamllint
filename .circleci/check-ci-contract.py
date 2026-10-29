#!/usr/bin/env python3
"""Check source -> packed -> compiled configuration and the publication gate.

The probe config is compiled only; it is never submitted as a workflow.
The verified injected.yml is the exact file submitted by orb-tools/continue.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

import yaml


ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = {
    "targets": "PARAM_TARGETS", "config_file": "PARAM_CONFIG_FILE",
    "config_data": "PARAM_CONFIG_DATA", "strict": "PARAM_STRICT",
    "no_warnings": "PARAM_NO_WARNINGS", "list_files": "PARAM_LIST_FILES",
    "format": "PARAM_FORMAT",
}
TAG_FILTER = "/^v[0-9]+\\.[0-9]+\\.[0-9]+$/"
CONFIG_PATH = "/tmp/yamllint-phase5/injected.yml"
PREPARE_COMMAND = "bash .circleci/prepare-ci-contract.sh /tmp/yamllint-phase5-packed/orb_source.tar.gz"
PROBES = [
    {},
    dict(targets="first path.yml\n--version\n./-\n", config_data='extends: "default"\nrules: {}\n',
         strict=True, no_warnings=True, list_files=True, format="parsable"),
    dict(targets="second.yml", config_file="config with spaces.yml", strict=True,
         no_warnings=False, list_files=False, format="standard"),
    dict(targets="-", config_file="settings.yml", config_data="relaxed", strict=False,
         no_warnings=True, list_files=True, format="invalid-format"),
]


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load(path):
    return yaml.safe_load(Path(path).read_text())


def runs(job, name):
    return [step["run"] for step in job["steps"] if isinstance(step, dict)
            and isinstance(step.get("run"), dict) and step["run"].get("name") == name]


def calls(job, command):
    result = []
    for step in job["steps"]:
        if step == command:
            result.append({})
        elif isinstance(step, dict) and command in step:
            result.append(step[command] or {})
    return result


def workflow_jobs(config, workflow):
    entries = config["workflows"][workflow]["jobs"]
    result = {}
    for entry in entries:
        require(isinstance(entry, dict) and len(entry) == 1, "Named workflow entries required")
        name, options = next(iter(entry.items()))
        key = options.get("name", name)
        require(key not in result, "Duplicate workflow job")
        result[key] = options
    return result


def require_dependencies(job, expected):
    require(isinstance(job.get("requires"), list), "Missing success dependencies")
    require(all(isinstance(x, str) for x in job["requires"]), "Failure-tolerant requires is forbidden")
    require(set(job["requires"]) == set(expected), "Required job missing or unexpected dependency")
    if "upstream" in job:
        require(job["upstream"] == {name: ["success"] for name in expected}, "Non-success upstream gate")


def verify_release(config, required, expanded=False):
    jobs = workflow_jobs(config, "test-deploy")
    expected = set(required) | {"orb-tools/pack", "orb-tools/publish"}
    if not expanded:
        expected.remove("compatibility-matrix")
        expected.add("compatibility-<< matrix.yamllint-version >>-py<< matrix.python-version >>")
    require(set(jobs) == expected, "Unexpected release workflow jobs")
    require_dependencies(jobs["orb-tools/pack"], required)
    require_dependencies(jobs["orb-tools/publish"], ["orb-tools/pack"])
    for name, options in jobs.items():
        if name == "orb-tools/publish":
            require(options.get("context") == "CIRCLECI_ORBS", "Publish context mismatch")
            require(options.get("filters") == {"branches": {"ignore": "/.*/"},
                                               "tags": {"only": TAG_FILTER}}, "Publish filter widened")
            if not expanded:
                require(options.get("pub_type") == "production", "Development publish forbidden")
                require(options.get("orb_name") == "orbss/yamllint", "Unexpected publication target")
        else:
            require("context" not in options, "Context leaked to a non-publish job")
            require(options.get("filters") == {"tags": {"only": "/.*/"}}, "Prerequisite tag reachability changed")
    if expanded:
        publishing = runs(config["jobs"]["orb-tools/publish"], "Publishing Orb Release")
        require(len(publishing) == 1, "Expected one publication step")
        env = publishing[0]["environment"]
        require(env["ORB_VAL_PUB_TYPE"] == "production" and env["ORB_VAL_ORB_NAME"] == "orbss/yamllint",
                "Expanded publication target/type changed")
        require(env["ORB_VAL_TAG_PATTERN"] == TAG_FILTER[1:-1], "Expanded tag guard changed")


def resolve(value, parameters):
    if not isinstance(value, str):
        return value
    for key, item in parameters.items():
        value = re.sub(r"<<\s*parameters\." + re.escape(key) + r"\s*>>", str(item), value)
    return value


def expected_environment(command, values):
    require(set(values) <= set(PARAMETERS), "Unknown execute parameter")
    return {env: values.get(name, command["parameters"][name]["default"])
            for name, env in PARAMETERS.items()}


def verify_expanded_job(source, expanded, command, execute_script, install_script, parameters=None):
    parameters = parameters or {}
    wanted = calls(source, "yamllint/execute")
    actual = runs(expanded, "Execute yamllint")
    require(len(actual) == len(wanted), "Execute step count mismatch")
    for values, step in zip(wanted, actual):
        values = {key: resolve(value, parameters) for key, value in values.items()}
        require(step["command"] == execute_script, "Expanded execute script differs from tested source")
        require(step["environment"] == expected_environment(command, values), "Expanded execute mapping mismatch")
    wanted = calls(source, "yamllint/install")
    actual = runs(expanded, "Install yamllint")
    require(len(actual) == len(wanted), "Install step count mismatch")
    for values, step in zip(wanted, actual):
        require(step["command"] == install_script, "Expanded install script mismatch")
        require(step["environment"] == {"PARAM_VERSION": resolve(values.get("version", ""), parameters)},
                "Fixed install.version not propagated")


def verify_setup(source, expanded):
    names = {"orb-tools/lint", "orb-tools/pack", "orb-tools/review", "shellcheck/check", "orb-tools/continue"}
    for config in (source, expanded):
        jobs = workflow_jobs(config, "lint-pack")
        require(set(jobs) == names, "Setup checks changed")
        require_dependencies(jobs["orb-tools/continue"], names - {"orb-tools/continue"})
        for job in jobs.values():
            require("context" not in job, "Context in setup workflow")
            require(job.get("filters") == {"tags": {"only": "/.*/"}}, "Setup tag reachability changed")
    continuation = workflow_jobs(source, "lint-pack")["orb-tools/continue"]
    require(continuation["config_path"] == CONFIG_PATH, "Unverified continuation input")
    require(continuation["inject_orb"] is False and continuation["attach_workspace"] is False
            and continuation["checkout"] is False, "Continuation could overwrite verified input")
    job = expanded["jobs"]["orb-tools/continue"]
    prepare = runs(job, "Verify source, packed Orb, expanded config and release boundary")
    require(len(prepare) == 1 and prepare[0]["command"] == PREPARE_COMMAND, "Contract verifier bypassed")
    steps = [step["run"] for step in job["steps"] if isinstance(step, dict)
             and isinstance(step.get("run"), dict)]
    continuing = runs(job, "Continuing To Orb Testing And Deployment")
    require(len(continuing) == 1 and steps.index(prepare[0]) < steps.index(continuing[0]), "Verifier must run first")
    require(prepare[0].get("when", "on_success") == "on_success", "Verifier may be skipped")
    env = continuing[0]["environment"]
    require(env["ORB_VAL_CONTINUE_CONFIG_PATH"] == CONFIG_PATH and env["ORB_VAL_INJECT_ORB"] is False,
            "Expanded continuation input mismatch")


def read_context(directory):
    directory = Path(directory)
    return dict(
        source=load(ROOT / ".circleci/test-deploy.yml"), setup=load(ROOT / ".circleci/config.yml"),
        command=load(ROOT / "src/commands/execute.yml"),
        install=load(ROOT / "src/commands/install.yml"),
        executor=load(ROOT / "src/executors/default.yml"),
        execute_script=(ROOT / "src/scripts/execute.sh").read_text(),
        install_script=(ROOT / "src/scripts/install.sh").read_text(),
        manifest=json.loads((ROOT / ".circleci/compatibility-contract.json").read_text()),
        packed=load(directory / "orb.yml"), injected=load(directory / "injected.yml"),
        expanded=load(directory / "expanded.yml"), setup_expanded=load(directory / "setup-expanded.yml"),
        probe=load(directory / "parameter-probes.yml"), probe_expanded=load(directory / "parameter-probes-expanded.yml"),
    )


def verify(context):
    c = context
    source, command, manifest = c["source"], c["command"], c["manifest"]
    legacy = manifest["legacy_job_sha256"]
    require(set(command["parameters"]) == set(PARAMETERS), "Public parameter set changed")
    source_run = runs(command, "Execute yamllint")
    require(len(source_run) == 1, "Expected one source execute step")
    require(source_run[0]["environment"] == {env: f"<< parameters.{name} >>" for name, env in PARAMETERS.items()},
            "Source parameter mapping changed")
    for name, script, definition in (("execute", c["execute_script"], command),
                                     ("install", c["install_script"], c["install"])):
        packed = c["packed"]["commands"][name]
        require(packed["parameters"] == definition["parameters"], "Packed API differs from source")
        body = runs(packed, "Execute yamllint" if name == "execute" else "Install yamllint")
        require(len(body) == 1 and body[0]["command"].replace("\\<<", "<<") == script,
                "Packed script differs from tested source")
        require(body[0]["environment"] == runs(definition, body[0]["name"])[0]["environment"],
                "Packed parameter mapping mismatch")
    require(c["packed"]["executors"]["default"] == c["executor"], "Packed executor mismatch")
    injected = copy.deepcopy(source)
    require(injected["orbs"]["yamllint"] == {}, "Source must use inline Orb placeholder")
    injected["orbs"]["yamllint"] = c["packed"]
    require(c["injected"] == injected, "Continuation config is not source plus the checked packed Orb")
    for name, sha in legacy.items():
        require(digest(source["jobs"][name]) == sha, "Legacy job or Phase 1 shim changed: " + name)
        verify_expanded_job(source["jobs"][name], c["expanded"]["jobs"][name], command,
                            c["execute_script"], c["install_script"])
        metadata = runs(c["expanded"]["jobs"][name], "Record resolved runtime for this integration job")
        require(len(metadata) == 1 and metadata[0].get("when") == "always", "Missing default runtime record")
        env = metadata[0]["environment"]
        image = "cimg/python:3.13" if name == "custom-image-test" else "cimg/python:3.14"
        require(env["EVIDENCE_IMAGE"] == image and env["EVIDENCE_CASES"] == name, "Runtime case/image mismatch")
        require(env["EVIDENCE_REQUESTED_VERSION"] == ("1.37.1" if name == "install-version-test" else ""),
                "Default and fixed installation evidence conflated")
        require(c["expanded"]["jobs"][name]["docker"][0]["image"] == image, "Legacy image changed")
    require(c["expanded"]["jobs"]["resource-class-test"]["resource_class"] == "medium",
            "Custom resource class not propagated")
    workflow = workflow_jobs(source, "test-deploy")
    matrix = workflow["compatibility-<< matrix.yamllint-version >>-py<< matrix.python-version >>"]["matrix"]
    require(matrix == {"alias": "compatibility-matrix", "parameters": {
        "yamllint-version": manifest["versions"], "python-version": manifest["python_versions"]}}, "Fixed matrix changed")
    required = []
    for version in manifest["versions"]:
        for python in manifest["python_versions"]:
            name = f"compatibility-{version}-py{python}"
            required.append(name)
            job = c["expanded"]["jobs"][name]
            require(job["docker"][0]["image"] == f"cimg/python:{python}", "Fixed image mismatch")
            require(job["resource_class"] == "small", "Default executor resource class changed")
            verify_expanded_job(source["jobs"]["compatibility-tests"], job, command,
                                c["execute_script"], c["install_script"],
                                {"yamllint-version": version, "python-version": python})
            checks = runs(job, "Run fixed-version feature, refusal and combination checks")
            expected = (f"python .circleci/run-compatibility.py --version {version} "
                        f"--python-version {python} --evidence-dir /tmp/yamllint-compatibility")
            require(len(checks) == 1 and " ".join(checks[0]["command"].split()) == expected,
                    "Fixed behavior/refusal verification bypassed")
    verify_release(source, [*legacy, "compatibility-matrix"])
    verify_release(c["expanded"], [*legacy, *required], expanded=True)
    probe = c["probe"]["jobs"]["parameter-probe"]
    require(calls(probe, "yamllint/execute") == PROBES, "Parameter probe coverage changed")
    verify_expanded_job(probe, c["probe_expanded"]["jobs"]["parameter-probe"], command,
                        c["execute_script"], c["install_script"])
    verify_setup(c["setup"], c["setup_expanded"])
    return required


def identity():
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    dirty = subprocess.run(["git", "diff", "--quiet", "HEAD"], cwd=ROOT, check=False).returncode != 0
    ci = os.environ.get("CIRCLECI") == "true"
    if ci:
        require(commit == os.environ.get("CIRCLE_SHA1") and not dirty, "CI checkout differs from claimed revision")
    fields = ("CIRCLE_SHA1", "CIRCLE_JOB", "CIRCLE_BUILD_URL", "CIRCLE_WORKFLOW_ID", "CIRCLE_PIPELINE_ID")
    return dict(kind="CircleCI" if ci else "local-supplementary", commit=commit, dirty=dirty,
                ci={key: os.environ.get(key, "") for key in fields})


def prepare(directory):
    directory.mkdir(parents=True, exist_ok=True)
    source = load(ROOT / ".circleci/test-deploy.yml")
    packed = load(directory / "orb.yml")
    require(source["orbs"]["yamllint"] == {}, "Expected inline placeholder")
    source["orbs"]["yamllint"] = packed
    (directory / "injected.yml").write_text(yaml.safe_dump(source, sort_keys=False))
    probe = dict(version=2.1, orbs=dict(yamllint=packed), jobs={"parameter-probe": {
        "executor": "yamllint/default", "steps": [
            "yamllint/install", {"yamllint/install": {"version": "1.37.1"}},
            {"yamllint/install": {"version": "1.38.0"}},
            *[{"yamllint/execute": values} for values in PROBES]]}},
        workflows={"compile-only": {"jobs": ["parameter-probe"]}})
    (directory / "parameter-probes.yml").write_text(yaml.safe_dump(probe, sort_keys=False))
    (directory / "identity.json").write_text(json.dumps(identity(), indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "verify"))
    parser.add_argument("--evidence-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.evidence_dir)
        return
    context = read_context(args.evidence_dir)
    required = verify(context)
    manifest = context["manifest"]
    for name, sha in manifest["feature_suite_sha256"].items():
        require(hashlib.sha256((ROOT / ".circleci" / name).read_bytes()).hexdigest() == sha,
                "Feature-owned verification changed without updating its evidence: " + name)
    record = dict(identity=identity(), result="configuration checks passed; behavior results are separate",
                  matrix_jobs=required, legacy_jobs=list(manifest["legacy_job_sha256"]),
                  inherited_verification=manifest, parameters=PARAMETERS,
                  files={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in args.evidence_dir.glob("*.yml")})
    (args.evidence_dir / "contract-result.json").write_text(json.dumps(record, indent=2) + "\n")
    print("Source, packed Orb, expanded mappings, matrix and publication gates: PASS")


if __name__ == "__main__":
    main()
