#!/usr/bin/env python3
"""Fault controls for the Phase 5 configuration verifier, using compiler output."""
import copy
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location("contract", Path(__file__).with_name("check-ci-contract.py"))
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


class ConfigContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = contract.read_context(os.environ.get("PHASE5_EVIDENCE_DIR", "/tmp/yamllint-phase5"))

    def setUp(self):
        self.c = copy.deepcopy(self.original)

    def rejected(self):
        with self.assertRaises((AssertionError, KeyError)):
            contract.verify(self.c)

    def test_real_compiler_output_passes(self):
        pairs = [f"{v}-py{p}" for v in ("1.37.1", "1.38.0") for p in ("3.13", "3.14")]
        self.assertEqual(contract.verify(self.c), [f"compatibility-{pair}" for pair in pairs]
                         + [f"output-file-{pair}" for pair in pairs])

    def test_packed_script_change(self):
        contract.runs(self.c["packed"]["commands"]["execute"], "Execute yamllint")[0]["command"] += "\ntrue\n"
        self.rejected()

    def test_packed_parameter_mapping_change(self):
        contract.runs(self.c["packed"]["commands"]["execute"], "Execute yamllint")[0]["environment"]["PARAM_LIST_FILES"] = "false"
        self.rejected()

    def test_expanded_script_change(self):
        contract.runs(self.c["expanded"]["jobs"]["command-tests"], "Execute yamllint")[0]["command"] = "true"
        self.rejected()

    def test_expanded_parameter_mapping_change(self):
        contract.runs(self.c["probe_expanded"]["jobs"]["parameter-probe"], "Execute yamllint")[1]["environment"]["PARAM_CONFIG_DATA"] = ""
        self.rejected()

    def test_matrix_case_missing(self):
        del self.c["expanded"]["jobs"]["compatibility-1.37.1-py3.14"]
        self.rejected()

    def test_fixed_install_version_changed(self):
        contract.runs(self.c["expanded"]["jobs"]["compatibility-1.37.1-py3.14"], "Install yamllint")[0]["environment"]["PARAM_VERSION"] = ""
        self.rejected()

    def test_fixed_executor_changed(self):
        self.c["expanded"]["jobs"]["compatibility-1.37.1-py3.14"]["docker"][0]["image"] = "cimg/python:3.13"
        self.rejected()

    def test_pack_dependency_missing(self):
        jobs = contract.workflow_jobs(self.c["expanded"], "test-deploy")
        jobs["orb-tools/pack"]["requires"].remove("compatibility-1.37.1-py3.14")
        self.rejected()

    def test_failed_upstream_allowed(self):
        jobs = contract.workflow_jobs(self.c["expanded"], "test-deploy")
        jobs["orb-tools/pack"]["upstream"]["command-tests"] = ["success", "failed"]
        self.rejected()

    def test_publish_dependency_missing(self):
        contract.workflow_jobs(self.c["expanded"], "test-deploy")["orb-tools/publish"]["requires"] = []
        self.rejected()

    def test_context_on_test_job(self):
        contract.workflow_jobs(self.c["expanded"], "test-deploy")["command-tests"]["context"] = "CIRCLECI_ORBS"
        self.rejected()

    def test_publish_filter_widened(self):
        contract.workflow_jobs(self.c["expanded"], "test-deploy")["orb-tools/publish"]["filters"]["tags"]["only"] = "/.*/"
        self.rejected()

    def test_unverified_continuation_file(self):
        job = self.c["setup_expanded"]["jobs"]["orb-tools/continue"]
        contract.runs(job, "Continuing To Orb Testing And Deployment")[0]["environment"]["ORB_VAL_CONTINUE_CONFIG_PATH"] = ".circleci/test-deploy.yml"
        self.rejected()

    def test_legacy_shim_change(self):
        job = self.c["source"]["jobs"]["targets-test"]
        contract.runs(job, "Prepare target selection verifier")[0]["command"] += "\ntrue\n"
        self.rejected()

    def test_runtime_metadata_missing(self):
        job = self.c["expanded"]["jobs"]["command-tests"]
        job["steps"].remove({"run": contract.runs(job, "Record resolved runtime for this integration job")[0]})
        self.rejected()

    def runtime_job(self):
        return self.c["expanded"]["jobs"]["compatibility-1.37.1-py3.14"]

    def test_runtime_observer_missing(self):
        job = self.runtime_job()
        job["steps"].remove({"run": contract.runs(job, "Verify all body calls and results")[0]})
        self.rejected()

    def test_runtime_observer_duplicated(self):
        job = self.runtime_job()
        job["steps"].append({"run": contract.runs(job, "Verify all body calls and results")[0]})
        self.rejected()

    def test_runtime_step_can_be_skipped(self):
        contract.runs(self.runtime_job(), "Verify all body calls and results")[0]["when"] = "on_fail"
        self.rejected()

    def test_runtime_step_backgrounded(self):
        contract.runs(self.runtime_job(), "Verify all body calls and results")[0]["background"] = True
        self.rejected()

    def test_runtime_parameter_rewritten(self):
        contract.runs(self.runtime_job(), "Execute yamllint")[4]["environment"]["PARAM_NO_WARNINGS"] = "true"
        self.rejected()

    def test_observer_environment_normalization(self):
        contract.runs(self.runtime_job(), "Expect hidden-warning")[0]["environment"] = {"PARAM_NO_WARNINGS": "true"}
        self.rejected()

    def test_runtime_identity_scope_changed(self):
        environment = self.runtime_job()["environment"]
        if isinstance(environment, list):
            environment = next(item for item in environment if "VERIFICATION_SCOPE" in item)
        environment["VERIFICATION_SCOPE"] = "consumer"
        self.rejected()

    def test_runtime_identity_duplicate(self):
        self.runtime_job()["environment"] = [
            {"VERIFICATION_SCOPE": "source"}, {"VERIFICATION_SCOPE": "consumer"}]
        self.rejected()

    def test_source_runtime_case_removed(self):
        job = self.c["source"]["jobs"]["compatibility-tests"]
        job["steps"].remove({"run": contract.runs(job, "Expect hidden-warning")[0]})
        self.rejected()

    def test_runtime_order_changed(self):
        job = self.runtime_job()
        step = {"run": contract.runs(job, "Verify all body calls and results")[0]}
        job["steps"].remove(step)
        job["steps"].insert(1, step)
        self.rejected()

    # output_file (#5508): each check of the new parameter set and mapping
    # must reject its own fault, identified by the check's message.
    def rejected_by(self, message):
        with self.assertRaisesRegex(AssertionError, message):
            contract.verify(self.c)

    def test_output_file_removed_from_source_api(self):
        del self.c["command"]["parameters"]["output_file"]
        self.rejected_by("Public parameter set changed")

    def test_verifier_parameter_set_without_output_file(self):
        parameters = {k: v for k, v in contract.PARAMETERS.items() if k != "output_file"}
        with patch.object(contract, "PARAMETERS", parameters):
            self.rejected_by("Public parameter set changed")

    def test_output_file_source_mapping_changed(self):
        execute = contract.runs(self.c["command"], "Execute yamllint")[0]
        execute["environment"]["PARAM_OUTPUT_FILE"] = "<< parameters.format >>"
        self.rejected_by("Source parameter mapping changed")

    def test_packed_output_file_default_changed(self):
        self.c["packed"]["commands"]["execute"]["parameters"]["output_file"]["default"] = "lint.txt"
        self.rejected_by("Packed API differs from source")

    def test_packed_output_file_mapping_changed(self):
        execute = contract.runs(self.c["packed"]["commands"]["execute"], "Execute yamllint")[0]
        execute["environment"]["PARAM_OUTPUT_FILE"] = "<< parameters.targets >>"
        self.rejected_by("Packed parameter mapping mismatch")

    def test_expanded_output_file_value_changed(self):
        execute = contract.runs(self.c["expanded"]["jobs"]["command-tests"], "Execute yamllint")[0]
        execute["environment"]["PARAM_OUTPUT_FILE"] = "lint.txt"
        self.rejected_by("Expanded execute mapping mismatch")

    def test_expanded_output_file_mapping_missing(self):
        del contract.runs(self.runtime_job(), "Execute yamllint")[0]["environment"]["PARAM_OUTPUT_FILE"]
        self.rejected_by("Expanded execute mapping mismatch")

    # #5510: output_file matrix, its step observer, pack gate, probes, suites and pins.
    OUTPUT_TEMPLATE = "output-file-<< matrix.yamllint-version >>-py<< matrix.python-version >>"

    def output_job(self):
        return self.c["expanded"]["jobs"]["output-file-1.37.1-py3.14"]

    def source_change(self, change):
        """Change the source and the continued config alike, so later checks are reached."""
        for key in ("source", "injected"):
            change(self.c[key])

    def test_output_matrix_case_missing(self):
        del self.c["expanded"]["jobs"]["output-file-1.38.0-py3.13"]
        self.rejected()

    def test_output_matrix_narrowed(self):
        self.source_change(lambda config: contract.workflow_jobs(config, "test-deploy")[self.OUTPUT_TEMPLATE]
                           ["matrix"]["parameters"].update({"python-version": ["3.14"]}))
        self.rejected_by("Fixed matrix changed")

    def test_output_pack_dependency_missing(self):
        jobs = contract.workflow_jobs(self.c["expanded"], "test-deploy")
        jobs["orb-tools/pack"]["requires"].remove("output-file-1.37.1-py3.14")
        self.rejected_by("Required job missing or unexpected dependency")

    def test_output_alias_not_required_by_pack(self):
        self.source_change(lambda config: contract.workflow_jobs(config, "test-deploy")["orb-tools/pack"]
                           ["requires"].remove("output-file-matrix"))
        self.rejected_by("Required job missing or unexpected dependency")

    def test_output_job_image_changed(self):
        self.output_job()["docker"][0]["image"] = "cimg/python:3.13"
        self.rejected_by("Fixed image mismatch")

    def test_output_job_install_version_changed(self):
        contract.runs(self.output_job(), "Install yamllint")[0]["environment"]["PARAM_VERSION"] = "1.38.0"
        self.rejected_by("Fixed install.version not propagated")

    def test_output_value_rewritten(self):
        contract.runs(self.output_job(), "Execute yamllint")[9]["environment"]["PARAM_OUTPUT_FILE"] = "lint.txt"
        self.rejected_by("Expanded execute mapping mismatch")

    def test_output_omitted_case_gets_a_value(self):
        contract.runs(self.output_job(), "Execute yamllint")[0]["environment"]["PARAM_OUTPUT_FILE"] = "lint.txt"
        self.rejected_by("Expanded execute mapping mismatch")

    def test_output_observer_missing(self):
        job = self.output_job()
        job["steps"].remove({"run": contract.runs(job, "Verify output_file observations")[0]})
        self.rejected_by("Runtime observation step missing or duplicated")

    def test_output_observer_skipped(self):
        contract.runs(self.output_job(), "Verify output_file observations")[0]["when"] = "always"
        self.rejected_by("Runtime checks must complete successfully before packing")

    def test_output_observer_backgrounded(self):
        contract.runs(self.output_job(), "Observe hidden-warning")[0]["background"] = True
        self.rejected_by("Runtime checks must complete successfully before packing")

    def test_output_observer_environment(self):
        contract.runs(self.output_job(), "Observe saving-empty")[0]["environment"] = {"PARAM_OUTPUT_FILE": "x"}
        self.rejected_by("Observer must not normalize parameter values")

    def test_output_runtime_identity_changed(self):
        environment = self.output_job()["environment"]
        if isinstance(environment, list):
            environment = next(item for item in environment if "EXPECTED_YAMLLINT" in item)
        environment["EXPECTED_YAMLLINT"] = "1.38.0"
        self.rejected_by("Runtime identity environment changed")

    def test_output_source_case_changed(self):
        def change(config):
            step = next(s for s in config["jobs"]["output-file-tests"]["steps"]
                        if isinstance(s, dict) and s.get("run", {}).get("name") == "Observe config-file")
            step["run"]["command"] += " --local"
        self.source_change(change)
        self.rejected_by("Required runtime cases, typed parameters or observer steps changed")

    def test_output_observer_structure_without_pin_protection(self):
        # Even with the pin moved to the changed job, a job without the final check is rejected.
        def change(config):
            steps = config["jobs"]["output-file-tests"]["steps"]
            steps.remove(next(s for s in steps if isinstance(s, dict)
                              and s.get("run", {}).get("name") == "Verify output_file observations"))
        self.source_change(change)
        self.c["manifest"]["output_runtime_job_sha256"] = contract.digest(self.c["source"]["jobs"]["output-file-tests"])
        self.rejected_by("output_file step observer bypassed")

    def test_output_job_pin_changed(self):
        self.c["manifest"]["output_runtime_job_sha256"] = "0" * 64
        self.rejected_by("Required runtime cases, typed parameters or observer steps changed")

    def test_probe_output_file_value_changed(self):
        probe = self.c["probe_expanded"]["jobs"]["parameter-probe"]
        contract.runs(probe, "Execute yamllint")[4]["environment"]["PARAM_OUTPUT_FILE"] = "results dir/lint.txt"
        self.rejected_by("Expanded execute mapping mismatch")

    def test_probes_without_non_default_output_file(self):
        with patch.object(contract, "PROBES", contract.PROBES[:4]):
            self.rejected_by("Parameter probe coverage changed")

    def test_matrix_suite_removed(self):
        self.c["suites"].remove(("test-output-runtime.py", 23))
        self.rejected_by("Fixed-matrix behavior suites changed")

    def test_matrix_suite_count_changed(self):
        index = self.c["suites"].index(("test-output-file.py", 20))
        self.c["suites"][index] = ("test-output-file.py", 19)
        self.rejected_by("Fixed-matrix behavior suites changed")

    def test_feature_pin_changed(self):
        self.c["manifest"]["feature_suite_sha256"]["verify-output-file.py"] = "0" * 64
        self.rejected_by("Feature-owned verification changed without updating its evidence: verify-output-file.py")

    def test_feature_pin_removed(self):
        del self.c["manifest"]["feature_suite_sha256"]["test-output-phase1.py"]
        self.rejected_by("Feature-owned verification is not pinned: test-output-phase1.py")


if __name__ == "__main__":
    unittest.main()
