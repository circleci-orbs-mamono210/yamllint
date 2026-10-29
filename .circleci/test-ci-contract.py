#!/usr/bin/env python3
"""Fault controls for the Phase 5 configuration verifier, using compiler output."""
import copy
import importlib.util
import os
from pathlib import Path
import unittest


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
        self.assertEqual(len(contract.verify(self.c)), 4)

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


if __name__ == "__main__":
    unittest.main()
